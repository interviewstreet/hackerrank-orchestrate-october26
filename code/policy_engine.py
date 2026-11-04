"""
policy_engine.py — Stage 3: deletion-policy and evidence validation
(owner: Person 3).

    decide(identity, records, case) -> dict

Inputs
------
identity  P1's IdentityBundle (current + historical identifiers at audit_at).
records   P2's ObservedRecord list from evidence_search.find_records()
          (scanner.find_records(SubjectIdentifiers(**identity.as_subject_kwargs()),
          audit_at)). An empty list is fine: decide() queries the scanner
          itself for resources it links through catalog and workflow
          activity.
case      the deletion_requests.csv row.

What it does
------------
1. Builds the subject's identifier set (P1 adapter) and adds resource ids
   that activity explicitly links to the subject (data-catalog links, the
   request's own deletion workflow, connectors/restores that repopulated the
   subject's resources).
2. Re-validates every observation: timezone-aware, observed_at and the
   file's captured_at both at or before audit_at; name-only matches are weak
   and only kept when the same resource is confirmed by a strong identifier.
3. Groups observations by (system_id, resource_id) and keeps every copy
   (primary / replica / table) separate. For each copy the state at audit_at
   is the latest *authoritative* observation; same-instant PRESENT/ABSENT
   conflicts resolve to PRESENT and are reported in ``conflicts``.
   Claim-only observations may show a record or risk is still there but can
   never prove absence. Absence proofs are re-validated (COMPLETE, no file
   errors, right system / category / copy, captured at or before audit_at,
   not contradicted in-window, newer than the last PRESENT sighting).
4. Applies dataset/deletion_rules.csv (rules.RuleBook) to every record and
   derives findings, ordered remediation and verification.
5. Returns the decision dict consumed by step_builder.build_steps().

Decision dict
-------------
{
  "case_id": str,
  "deletion_status": "COMPLETE" | "INCOMPLETE",
  "findings":     [step-like dicts, already ordered],
  "remediation":  [...],
  "verification": [...],
  "resources":    [per-resource assessment, for audit trail / debugging],
  "conflicts":    [same-instant authoritative conflicts],
  "unverified":   [required states that evidence could not prove],
  "notes":        [str],
}
Each step-like dict has exactly system_id, resource_id, operation, state,
evidence_id. build_steps() numbers them and emits the output contract.
"""
from __future__ import annotations

import csv
import dataclasses
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from activity import (
    ACCOUNT_SLOT,
    ANALYTICS_SLOT,
    ActivityLog,
    RiskSignal,
    WorkflowCase,
    WorkflowLinker,
)
from evidence import ABSENT, COMPLETE, PRESENT, AbsenceProof, EvidenceScanner, ObservedRecord, SubjectIdentifiers
from evidence.normalize import default_category_for_resource, norm_email, norm_hash, norm_phone
from models import IdentityBundle
from rules import ANONYMIZE, DELETE, NONE, REDACT, RETAIN, RecordFacts, RuleBook
from utils import parse_ts, warn

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"

# --------------------------------------------------------------------------
# Output vocabulary (AGENTS.md §6.4) and canonical ordering
# --------------------------------------------------------------------------
FINDING_OPS = ("REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK")
REMEDIATION_OPS = ("DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD")
VERIFICATION_OPS = ("VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED",
                    "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED")
OP_STATE = {
    "REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED", "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

# Process-like categories (not records in deletion_rules.csv)
DATA_FLOW = "DATA_FLOW"
BACKUP = "BACKUP_ARCHIVE"
TOMBSTONE = "ACCOUNT_TOMBSTONE"
SUPPORT_MESSAGE = "SUPPORT_MESSAGE"

# identifier kinds that confirm identity on their own (a full name does not)
STRONG_MATCH_KINDS = {"email", "phone", "email_hash", "user_id", "resource_id"}
LINKED_MATCH_KINDS = {"linked_resource_id", "linked_file_name"}
DIRECT_ID_FIELDS = {"name", "full_name", "display_name", "email", "phone", "email_hash",
                    "requester_name", "requester_email", "requester_phone", "owner_email",
                    "owner_phone", "customer_email", "customer_name", "customer_phone",
                    "matched_value", "subject_selector", "uploaded_by", "message_text",
                    "lookup_value"}
USER_REF_KEYS = ("user_id", "customer_reference", "subject_reference", "subject_ref", "correlation_key")

_SHARED_CONTEXT_TEXT = re.compile(
    r"another customer|other customer|someone else|conversation itself|shared (conversation|thread)|"
    r"(conversation|thread|message)s? .*(need|has|have) to stay|relate to another", re.I)
# a support screen / document that shows an agent conversation or an order
_CONVERSATION_TEXT = re.compile(r"\bORD-\d+|assigned agent|internal notes|\bconversation\b", re.I)
_CLAIM_PRESENT = {"FOUND", "IDENTIFIABLE", "ACTIVE", "PRESENT"}
_CLAIM_CLEAN = {"ANONYMIZED", "REDACTED"}


# ==========================================================================
# Context: everything loaded once per run
# ==========================================================================
class PolicyContext:
    def __init__(self, dataset_dir: Path | str = DATASET_DIR, *, scanner: Optional[EvidenceScanner] = None,
                 rules: Optional[RuleBook] = None, activity: Optional[ActivityLog] = None,
                 resolver: Any = None, request_files: Iterable[str] = ("deletion_requests.csv",
                                                                         "sample_deletion_requests.csv")):
        self.dataset_dir = Path(dataset_dir)
        self.rules = rules or RuleBook.load(self.dataset_dir / "deletion_rules.csv")
        if scanner is None:
            scanner = EvidenceScanner(self.dataset_dir, ocr_mode="cache_only")
        scanner.load()
        self.scanner = scanner
        self.activity = activity or ActivityLog.load(self.dataset_dir / "system_activity.csv")
        self._resolver = resolver
        self._request_files = tuple(request_files)
        self._linker: Optional[WorkflowLinker] = None
        self._owners: Optional[dict[str, list[tuple[str, datetime]]]] = None
        self._id_maps: Optional[dict[str, dict[str, set[str]]]] = None

    # ------------------------------------------------------------ identity maps
    @property
    def resolver(self):
        if self._resolver is None:
            from identity_resolver import IdentityResolver
            self._resolver = IdentityResolver(self.dataset_dir / "user_identities.csv",
                                              self.dataset_dir / "user_audit_log.csv")
        return self._resolver

    def id_maps(self) -> dict[str, dict[str, set[str]]]:
        """Normalised email / phone / hash -> user ids (current and historical)."""
        if self._id_maps is None:
            maps: dict[str, dict[str, set[str]]] = {"email": defaultdict(set), "phone": defaultdict(set),
                                                    "email_hash": defaultdict(set)}
            norms = {"email": norm_email, "phone": norm_phone, "email_hash": norm_hash}
            with open(self.dataset_dir / "user_identities.csv", newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    for k, fn in norms.items():
                        v = fn(r.get(k))
                        if v:
                            maps[k][v].add(r["user_id"])
            with open(self.dataset_dir / "user_audit_log.csv", newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    k = r["field_name"]
                    if k in norms:
                        for val in (r["old_value"], r["new_value"]):
                            v = norms[k](val)
                            if v:
                                maps[k][v].add(r["user_id"])
            self._id_maps = maps
        return self._id_maps

    def owners_of(self, rec: ObservedRecord) -> set[str]:
        """Users a record is tied to by a strong identifier (never by name)."""
        maps = self.id_maps()
        out: set[str] = set()
        if rec.subject_reference and rec.subject_reference.startswith("user_"):
            out.add(rec.subject_reference)
        for kind, val in rec.linked_terms:
            if kind == "user_id":
                out.add(val)
            elif kind in maps:
                out |= maps[kind].get(val, set())
        return out

    def owners(self) -> dict[str, list[tuple[str, datetime]]]:
        """resource_id (lower) -> [(user_id, observed_at)] from all evidence and catalog links."""
        if self._owners is None:
            own: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
            for rec in self.scanner.records:
                for uid in self.owners_of(rec):
                    own[rec.resource_id.lower()].append((uid, rec.observed_at))
            for link in self.activity.links:
                own[link.resource_id.lower()].append((link.user_id, link.event_time))
            self._owners = own
        return self._owners

    # ------------------------------------------------------------ workflow linker
    def _workflow_case(self, case: dict, identity: Optional[IdentityBundle]) -> Optional[WorkflowCase]:
        req = parse_ts(case.get("requested_at"), context=f"{case.get('case_id')} requested_at")
        rep = parse_ts(case.get("reported_at"), context=f"{case.get('case_id')} reported_at")
        aud = parse_ts(case.get("audit_at"), context=f"{case.get('case_id')} audit_at")
        if not (req and rep and aud):
            return None
        if identity is None:
            identity = self.resolver.resolve(case["email"], audit_at=aud, requested_at=req,
                                             case_id=case.get("case_id", ""))
        if identity is None:
            return None
        recs = self.scanner.find_records(SubjectIdentifiers(**identity.as_subject_kwargs()), aud)
        recs = [r for r in recs if r.observed_at >= req and _strong(r)]
        return WorkflowCase(
            case_id=case["case_id"], user_id=identity.user_id, requested_at=req, reported_at=rep, audit_at=aud,
            has_account=any(r.system_id == "account_service" for r in recs),
            has_analytics=any(r.system_id == "analytics_platform" for r in recs),
            evidence_files=frozenset(r.evidence_id for r in recs))

    def resource_files(self) -> dict[str, list[tuple[str, datetime]]]:
        """resource_id (lower) -> [(evidence_id, observed_at)] over all evidence."""
        if getattr(self, "_resource_files", None) is None:
            rf: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
            for rec in self.scanner.records:
                rf[rec.resource_id.lower()].append((rec.evidence_id, max(rec.observed_at, rec.captured_at)))
            self._resource_files = rf
        return self._resource_files

    def linker(self) -> WorkflowLinker:
        """Two-pass workflow attribution over every known request.

        Pass 1 attributes deleted accounts. Pass 2 attributes anonymised
        analytics rows, but only to requests whose own evidence (with the
        pass-1 account) shows no violation: a timing-only link is too weak to
        add a speculative obligation to a request that is already
        incomplete, and it is exactly the proof a compliant request needs.
        """
        if self._linker is None:
            from request_classifier import classify_request
            from models import ClassificationResult
            wcases: list[tuple[WorkflowCase, dict]] = []
            seen = set()
            for name in self._request_files:
                path = self.dataset_dir / name
                if not path.exists():
                    continue
                with open(path, newline="", encoding="utf-8") as fh:
                    for case in csv.DictReader(fh):
                        key = (case["case_id"], case["email"], case["requested_at"])
                        if key in seen:
                            continue
                        seen.add(key)
                        if classify_request(case["request_text"]).label == ClassificationResult.NOT_APPLICABLE:
                            continue
                        wc = self._workflow_case(case, None)
                        if wc:
                            wcases.append((wc, case))
            owners, files = self._owner_sets(), self.resource_files()
            accounts = WorkflowLinker(self.activity, [w for w, _ in wcases], owners, files, slots={ACCOUNT_SLOT})
            self._linker = accounts  # used by the preliminary decisions below
            eligible = []
            for wc, case in wcases:
                identity = self.resolver.resolve(case["email"], audit_at=wc.audit_at,
                                                 requested_at=wc.requested_at, case_id=wc.case_id)
                if identity is not None and not decide(identity, [], case, context=self)["findings"]:
                    eligible.append(wc)
            analytics = WorkflowLinker(self.activity, eligible, owners, files, slots={ANALYTICS_SLOT})
            accounts.merge(analytics)
            self._linker = accounts
        return self._linker

    def _owner_sets(self) -> dict[str, set[str]]:
        return {rid: {u for u, _ in lst} for rid, lst in self.owners().items()}

    def workflow_resources(self, case: dict, identity: IdentityBundle) -> dict:
        linker = self.linker()
        if case["case_id"] in linker.case_ids:
            return linker.resources_for(case["case_id"])
        # A case outside the pre-built request files (tests, ad-hoc calls):
        # link it on its own.
        wc = self._workflow_case(case, identity)
        if wc is None:
            return {}
        return WorkflowLinker(self.activity, [wc], self._owner_sets(),
                              self.resource_files()).resources_for(case["case_id"])

    # ------------------------------------------------------------ absence proofs
    def valid_absence_proofs(self, system_id: str, resource_id: str, category: Optional[str],
                             audit_at: datetime, replica: Any = "any",
                             not_before: Optional[datetime] = None,
                             collection: Optional[str] = None) -> list[AbsenceProof]:
        """Re-validated absence proofs for one resource copy (newest first).

        ``replica``: "any" for every copy, else the exact replica_or_table
        (None = primary) the proof must cover. A primary-copy proof never
        covers a replica and vice versa. ``collection``: when the copy was
        observed in a named collection/table, the proof must enumerate that
        same collection (a listing of another store proves nothing about it).
        """
        try:
            proofs = self.scanner.absence_proofs(system_id, resource_id, audit_at, category,
                                                 include_unverified=True)
        except Exception as exc:  # noqa: BLE001
            warn(f"absence_proofs({system_id}, {resource_id}) failed: {exc}")
            return []
        out = []
        for p in proofs:
            if p.completeness != COMPLETE or p.errors or p.contradicted_by:
                continue
            if p.system_id != system_id or (category and p.data_category != category):
                continue
            if p.captured_at > audit_at or self.scanner.get_file(p.evidence_id).captured_at > audit_at:
                continue
            if replica != "any" and p.replica_or_table != replica:
                continue
            if not_before is not None and p.captured_at < not_before:
                continue
            if collection and p.collection and p.collection.lower() != collection.lower():
                continue
            out.append(p)
        return out


_DEFAULT_CONTEXT: Optional[PolicyContext] = None


def configure(context: PolicyContext) -> None:
    """Install the context main.py built (shares one scanner / resolver)."""
    global _DEFAULT_CONTEXT
    _DEFAULT_CONTEXT = context


def get_context() -> PolicyContext:
    global _DEFAULT_CONTEXT
    if _DEFAULT_CONTEXT is None:
        _DEFAULT_CONTEXT = PolicyContext()
    return _DEFAULT_CONTEXT


# ==========================================================================
# Observation helpers
# ==========================================================================
def _match_kinds(rec: ObservedRecord) -> set[str]:
    return {m.split(":", 1)[0] for m in rec.identifiers_matched}


def _strong(rec: ObservedRecord) -> bool:
    return bool(_match_kinds(rec) & STRONG_MATCH_KINDS)


def _aware(dt: Any) -> bool:
    return isinstance(dt, datetime) and dt.tzinfo is not None and dt.utcoffset() is not None


def _obs_key(r: ObservedRecord) -> tuple:
    return (r.evidence_id, r.locator, r.system_id, r.resource_id.lower(), r.replica_or_table or "",
            r.observed_at, r.presence, r.claim_only)


def _claim_result(r: ObservedRecord) -> str:
    return str(r.raw_state.get("result") or "").upper() if r.claim_only else ""


def _truthy(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "yes", "1", "enabled", "allowed", "allow", "active"):
        return True
    if s in ("false", "no", "0", "disabled", "denied", "deny", "blocked", "stopped"):
        return False
    return None


def _parse_date(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return parse_ts(s, context="retention date")
    except ValueError:
        return None


def _direct_ids(r: ObservedRecord) -> set[str]:
    """Direct identifiers still stored in the record (P2 lists only non-null ones)."""
    return {k for k, v in (r.pii_fields or {}).items() if v not in (None, "", [], {})}


def _has_email(r: ObservedRecord) -> bool:
    for k, v in (r.pii_fields or {}).items():
        if "email" in k and "hash" not in k and v:
            return True
        if isinstance(v, str) and "@" in v:
            return True
    return False


def _user_ref(r: ObservedRecord) -> Optional[str]:
    for k in USER_REF_KEYS:
        v = r.raw_state.get(k)
        if isinstance(v, str) and v.strip().lower().startswith("user_"):
            return v.strip()
    return r.subject_reference if (r.subject_reference or "").startswith("user_") else None


# ==========================================================================
# Per-resource assessment
# ==========================================================================
@dataclass
class Signal:
    """One dated state observation of a resource copy (evidence or activity)."""
    at: datetime
    evidence_id: str
    authoritative: bool        # store state / direct observation (not a ledger claim)
    presence: str              # PRESENT | ABSENT
    record: Optional[ObservedRecord] = None
    active: Optional[bool] = None   # flows: enabled; backups: restorable


@dataclass
class CopyState:
    replica: Optional[str]
    presence: str                       # PRESENT | ABSENT | UNKNOWN
    proven: bool                        # backed by authoritative evidence / valid proof
    evidence_id: str = ""
    latest: Optional[Signal] = None
    conflict: bool = False


@dataclass
class Assessment:
    system_id: str
    resource_id: str
    category: Optional[str]
    copies: list[CopyState] = field(default_factory=list)
    rule_id: str = ""
    action: str = ""
    finding: Optional[str] = None
    finding_evidence: str = ""
    remediation: Optional[str] = None
    verification: Optional[str] = None
    verification_evidence: str = ""
    linked_by: str = ""
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "system_id": self.system_id, "resource_id": self.resource_id, "category": self.category,
            "rule_id": self.rule_id, "action": self.action, "finding": self.finding,
            "finding_evidence": self.finding_evidence, "remediation": self.remediation,
            "verification": self.verification, "verification_evidence": self.verification_evidence,
            "linked_by": self.linked_by, "reason": self.reason,
            "copies": [{"replica_or_table": c.replica, "presence": c.presence, "proven": c.proven,
                        "evidence_id": c.evidence_id, "conflict": c.conflict} for c in self.copies],
        }


def _latest_signal(signals: list[Signal]) -> tuple[Optional[Signal], bool]:
    """Latest authoritative signal of one copy; claim-only signals are used
    only when the copy has no authoritative observation at all (a claim never
    overrides store state). Returns (signal, same_instant_conflict)."""
    if not signals:
        return None, False
    auth = [s for s in signals if s.authoritative]
    pool = auth or signals
    t = max(s.at for s in pool)
    top = [s for s in pool if s.at == t]
    presences = {s.presence for s in top}
    actives = {s.active for s in top if s.active is not None}
    conflict = len(presences) > 1 or len(actives) > 1
    # conservative: PRESENT beats ABSENT, active beats inactive at the same instant
    top.sort(key=lambda s: (s.presence == PRESENT, s.active is True, s.authoritative, s.evidence_id), reverse=True)
    return top[0], conflict


def _state_signal(r: ObservedRecord, category: Optional[str]) -> Optional[Signal]:
    """Turn one observation into a dated signal; None if it says nothing."""
    if r.presence not in (PRESENT, ABSENT):
        return None
    if r.claim_only:
        res = _claim_result(r)
        if r.presence == ABSENT or res == "NOT_FOUND":
            return Signal(r.observed_at, r.evidence_id, False, ABSENT, r)
        active = None
        if category in (DATA_FLOW, BACKUP):
            active = True if res == "ACTIVE" else False if res in ("DISABLED", "BLOCKED") else None
        return Signal(r.observed_at, r.evidence_id, False, PRESENT, r, active)
    active = None
    if r.presence == PRESENT and category == DATA_FLOW:
        active = _truthy(r.raw_state.get("enabled"))
        if active is None:
            active = _truthy(r.raw_state.get("scheduler_registered"))
    elif r.presence == PRESENT and category == BACKUP:
        st = r.raw_state
        if "restore_allowed" in st:
            active = _truthy(st.get("restore_allowed"))
        elif "decision" in st:
            active = _truthy(st.get("decision"))
        elif "deletion_block" in st or "eligible" in st:
            blocked = _truthy(st.get("deletion_block"))
            eligible = _truthy(st.get("eligible"))
            active = False if blocked else (eligible if eligible is not None else None)
    presence = r.presence
    if presence == PRESENT and category == "USER_EXPORT" and _truthy(r.raw_state.get("available")) is False:
        presence = ABSENT
    return Signal(r.observed_at, r.evidence_id, True, presence, r, active)


def _facts(category: str, r: Optional[ObservedRecord], audit_at: datetime, request_text: str,
           subject_only: Optional[bool]) -> RecordFacts:
    if r is None:
        return RecordFacts(category=category)
    st = r.raw_state
    res = _claim_result(r)
    ids = _direct_ids(r)
    if res in _CLAIM_CLEAN:
        ids = set()
    has_ids = bool(ids) or res == "IDENTIFIABLE" or str(st.get("direct_identifiers", "")).strip() == "1"
    attributable = has_ids or (category in ("ANALYTICS_PROFILE", "PRODUCT_TELEMETRY")
                               and res not in _CLAIM_CLEAN and _user_ref(r) is not None)
    shared = None
    if category == SUPPORT_MESSAGE:
        # A ticket/conversation record (message body, ticket fields, requester
        # block, PII scan of message content) is shared customer/agent/order
        # context; a bare row-count lookup carries no conversation at all.
        content_keys = {"message_excerpt", "message_text", "ticket_id", "channel", "subject_ref", "detector",
                        "orders", "tickets", "customer_reference", "requester_email", "requester_name",
                        "requester_phone"}
        text = " ".join(str(st.get(k) or "") for k in ("ocr_text", "document_text"))
        shared = bool(content_keys & set(st)) or res in ("IDENTIFIABLE", "REDACTED") \
            or bool(_SHARED_CONTEXT_TEXT.search(request_text or "")) or bool(_CONVERSATION_TEXT.search(text))
    retention = None
    if "retention_until" in st or "retained_until" in st:
        until = _parse_date(st.get("retention_until") or st.get("retained_until"))
        retention = None if until is None else until > audit_at
    legal = retention
    if str(st.get("access", "")).lower() == "allowed" and legal is None:
        legal = True
    deleted = None
    if category == TOMBSTONE:
        status = str(st.get("account_status") or "").upper()
        deleted = None if not status else status == "DELETED"
    return RecordFacts(category=category, has_direct_identifiers=has_ids,
                       has_email=_has_email(r) or res == "IDENTIFIABLE" and category == "EMAIL_DELIVERY_LOG",
                       attributable=attributable, shared_context=shared, subject_only=subject_only,
                       retention_active=retention, legal_hold_active=legal, account_deleted=deleted)


# ==========================================================================
# decide()
# ==========================================================================
def decide(identity: IdentityBundle, records: list, case: dict,
           context: Optional[PolicyContext] = None) -> dict:
    """Apply deletion_rules.csv to every record of the subject and decide the case."""
    ctx = context or get_context()
    case_id = case.get("case_id", "")
    audit_at = parse_ts(case.get("audit_at"), context=f"{case_id} audit_at")
    if audit_at is None or not _aware(audit_at):
        # Without a cutoff the state "at audit_at" cannot be established, so
        # nothing can be verified and nothing may be claimed complete.
        warn(f"{case_id}: no usable audit_at; deletion cannot be verified")
        return {"case_id": case_id, "deletion_status": "INCOMPLETE", "findings": [], "remediation": [],
                "verification": [], "resources": [], "conflicts": [], "unverified": [],
                "identity": {"user_id": identity.user_id, "history_audit_ids": []},
                "notes": ["audit_at missing: state at the cutoff cannot be established"]}
    requested_at = parse_ts(case.get("requested_at"), context=f"{case_id} requested_at") or audit_at
    notes: list[str] = []
    conflicts: list[dict] = []
    unverified: list[dict] = []

    # -- 1. identifiers (P1) and explicitly linked resources (activity) ------
    history = [h for h in identity.history
               if (t := parse_ts(h.event_time, context=h.audit_id)) is not None and t <= audit_at]
    seeds: dict[str, str] = {}   # resource_id(lower) -> how it was linked
    subject_only: dict[str, bool] = {}
    for link in ctx.activity.links_for_user(identity.user_id, audit_at):
        seeds[link.resource_id.lower()] = f"catalog:{link.activity_id}"
        if link.subject_only:
            subject_only[link.resource_id.lower()] = True
    workflow = ctx.workflow_resources(case, identity)
    for slot, act in workflow.items():
        rid = (act.target_resource or act.resource_id).lower()
        seeds.setdefault(rid, f"workflow:{act.activity_id}")

    base = SubjectIdentifiers(**identity.as_subject_kwargs())
    ids = dataclasses.replace(base, resource_ids=frozenset(base.resource_ids | set(seeds)))
    pool: dict[tuple, ObservedRecord] = {}
    found = ctx.scanner.find_records(ids, audit_at)
    aliases = _alias_ids(ctx, identity.user_id, audit_at)
    for r in list(records or []) + found + _alias_records(ctx, identity.user_id, audit_at):
        if not isinstance(r, ObservedRecord):
            continue
        if r.resource_id.lower() in aliases:
            continue  # represented under the catalog's canonical resource id
        pool.setdefault(_obs_key(r), r)

    # -- 2. validate observations ------------------------------------------
    obs: list[ObservedRecord] = []
    for r in pool.values():
        if not (_aware(r.observed_at) and _aware(r.captured_at)):
            notes.append(f"dropped {r.evidence_id}/{r.resource_id}: naive timestamp")
            continue
        if r.observed_at > audit_at or r.captured_at > audit_at:
            continue  # after the audit cutoff: never used
        obs.append(r)

    by_res: dict[tuple[str, str], list[ObservedRecord]] = defaultdict(list)
    for r in obs:
        by_res[(r.system_id, r.resource_id.lower())].append(r)

    strong_res = {k for k, rs in by_res.items() if any(_strong(r) for r in rs) or k[1] in seeds}
    subject_confirmed = bool(strong_res)
    keep: dict[tuple[str, str], list[ObservedRecord]] = {}
    for k, rs in by_res.items():
        kinds = set().union(*(_match_kinds(r) for r in rs))
        if k in strong_res:
            keep[k] = rs
        elif kinds & LINKED_MATCH_KINDS and subject_confirmed and not (kinds & {"name"}):
            keep[k] = rs  # de-identified copy reached through a confirmed resource link
        elif kinds <= {"name"} or "name" in kinds:
            # name-only: weak. Keep only if nothing ties the record to someone else
            # AND the record itself carries a stable reference to this subject.
            others = set().union(*(ctx.owners_of(r) for r in rs)) - {identity.user_id}
            if not others and any(_user_ref(r) == identity.user_id for r in rs):
                keep[k] = rs
            else:
                notes.append(f"ignored name-only match {k[0]}/{k[1]}")
        else:
            keep[k] = rs

    # drop records that a strong identifier ties to a different subject only
    for k in list(keep):
        rs = keep[k]
        owners = set().union(*(ctx.owners_of(r) for r in rs))
        if owners and identity.user_id not in owners and k[1] not in seeds:
            notes.append(f"ignored {k[0]}/{k[1]}: evidence links it to {sorted(owners)}")
            del keep[k]

    # -- 3. recreation signals from activity --------------------------------
    subject_rids = {k[1] for k in keep} | set(seeds)
    risk_by_res: dict[tuple[str, str], list[RiskSignal]] = defaultdict(list)
    for sig in ctx.activity.risks_until(audit_at):
        key = (sig.system_id, sig.resource_id.lower())
        if key in keep or sig.resource_id.lower() in seeds or (
                sig.downstream_resource and sig.downstream_resource.lower() in subject_rids):
            risk_by_res[key].append(sig)

    # -- 4. assess each resource -------------------------------------------
    assessments: list[Assessment] = []
    for key in sorted(set(keep) | set(risk_by_res) | _seed_keys(seeds, keep, workflow)):
        system_id, rid_l = key
        rs = keep.get(key, [])
        risks = risk_by_res.get(key, [])
        linked_by = seeds.get(rid_l, "identity")
        # relevance: something about the resource at or after the request
        fresh = [r for r in rs if r.observed_at >= requested_at] or [s for s in risks if s.event_time >= requested_at]
        if not fresh and not linked_by.startswith("workflow:"):
            if rs or risks:
                notes.append(f"ignored {system_id}/{rid_l}: only observed before requested_at")
            continue
        rid = rs[0].resource_id if rs else _orig_rid(risks, workflow, rid_l)
        a = _assess(ctx, system_id, rid, rs, risks, audit_at, requested_at, case.get("request_text", ""),
                    subject_only.get(rid_l), conflicts, linked_by)
        if a is not None:
            assessments.append(a)

    # -- 5. status and steps -------------------------------------------------
    findings, remediation, verification = [], [], []
    for a in assessments:
        if a.finding:
            findings.append(_step(a, a.finding, a.finding_evidence))
        if a.remediation:
            remediation.append(_step(a, a.remediation, ""))
    status = "INCOMPLETE" if findings else "COMPLETE"
    for a in assessments:
        if not a.verification:
            continue
        if status == "INCOMPLETE":
            verification.append(_step(a, a.verification, ""))
        elif a.verification_evidence:
            verification.append(_step(a, a.verification, a.verification_evidence))
        else:
            unverified.append({"system_id": a.system_id, "resource_id": a.resource_id,
                               "operation": a.verification, "reason": "no evidence proves this state at audit_at"})

    return {
        "case_id": case_id,
        "deletion_status": status,
        "findings": _ordered(findings, FINDING_OPS),
        "remediation": _ordered(remediation, REMEDIATION_OPS),
        "verification": _ordered(verification, VERIFICATION_OPS),
        "resources": [a.as_dict() for a in assessments],
        "conflicts": conflicts,
        "unverified": unverified,
        "identity": {"user_id": identity.user_id, "history_audit_ids": [h.audit_id for h in history]},
        "notes": notes,
    }


def _alias_records(ctx: PolicyContext, user_id: str, audit_at: datetime) -> list[ObservedRecord]:
    """Observations that carry a data-catalog alias of the subject's resource.

    A catalog link says "resource R (alias A) belongs to <subject>", where A
    is how R appears in business artefacts: a document reference on a
    statement PDF, or a file name in a storage browser. Evidence showing A
    is evidence about R, so it is re-keyed to (link system, R). Only links
    and observations at or before audit_at are used.
    """
    out = []
    for link in ctx.activity.links_for_user(user_id, audit_at):
        alias = link.alias.strip().lower()
        if not alias or alias == link.resource_id.lower():
            continue
        category = default_category_for_resource(link.resource_id.lower()) or (
            "SUPPORT_ATTACHMENT" if link.subject_only else None)
        for rec in ctx.scanner.records:
            if rec.observed_at > audit_at or rec.captured_at > audit_at:
                continue
            # the record must *be* the aliased artefact (its id, document
            # reference or file name), not merely mention the same subject
            if rec.resource_id.lower() != alias and ("file_name", alias) not in rec.linked_terms \
                    and ("resource_id", alias) not in rec.linked_terms:
                continue
            others = ctx.owners_of(rec) - {user_id}
            if others and rec.resource_id.lower() != alias:
                continue  # the alias appears on someone else's record
            by_file = ("file_name", alias) in rec.linked_terms
            out.append(dataclasses.replace(
                rec, system_id=link.system_id, resource_id=link.resource_id, data_category=category,
                identifiers_matched=[f"resource_id:{link.resource_id.lower()}"],
                # a file listed under the subject's own name is the subject's file
                pii_fields=rec.pii_fields or ({"file_name": link.alias} if by_file else {})))
    return out


def _alias_ids(ctx: PolicyContext, user_id: str, audit_at: datetime) -> set[str]:
    """Resource ids that are only catalog aliases of another resource."""
    return {l.alias.strip().lower() for l in ctx.activity.links_for_user(user_id, audit_at)
            if l.alias.strip() and l.alias.strip().lower() != l.resource_id.lower()}


def _seed_keys(seeds: dict[str, str], keep: dict, workflow: dict) -> set[tuple[str, str]]:
    """Workflow-linked resources with no in-window observation still need a
    verification step (e.g. a deleted account seen only in the workflow)."""
    have = {k[1] for k in keep}
    out = set()
    for act in workflow.values():
        rid = (act.target_resource or act.resource_id).lower()
        if rid not in have:
            out.add((act.target_system, rid))
    return out


def _orig_rid(risks: list[RiskSignal], workflow: dict, rid_l: str) -> str:
    for s in risks:
        if s.resource_id.lower() == rid_l:
            return s.resource_id
    for act in workflow.values():
        rid = act.target_resource or act.resource_id
        if rid.lower() == rid_l:
            return rid
    return rid_l


def _category(rs: list[ObservedRecord], rid: str) -> Optional[str]:
    counts: dict[str, int] = defaultdict(int)
    for r in rs:
        if r.data_category:
            counts[r.data_category] += 1
    if counts:
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return default_category_for_resource(rid.lower())


def _assess(ctx: PolicyContext, system_id: str, rid: str, rs: list[ObservedRecord], risks: list[RiskSignal],
            audit_at: datetime, requested_at: datetime, request_text: str, subject_only: Optional[bool],
            conflicts: list[dict], linked_by: str) -> Optional[Assessment]:
    category = _category(rs, rid)
    a = Assessment(system_id=system_id, resource_id=rid, category=category, linked_by=linked_by)

    # signals per copy
    per_copy: dict[Optional[str], list[Signal]] = defaultdict(list)
    for r in rs:
        s = _state_signal(r, category)
        if s is not None:
            per_copy[r.replica_or_table].append(s)
    for sig in risks:  # an observed enabled flow / restorable archive on the primary copy
        if sig.resource_id.lower() == rid.lower():
            per_copy[None].append(Signal(sig.event_time, sig.activity_id, True, PRESENT, None, True))

    copies: list[CopyState] = []
    for replica in sorted(per_copy, key=lambda x: x or ""):
        latest, conflict = _latest_signal(per_copy[replica])
        if latest is None:
            continue
        if conflict:
            conflicts.append({"system_id": system_id, "resource_id": rid, "replica_or_table": replica,
                              "at": latest.at.isoformat(), "evidence_ids": sorted(
                                  {s.evidence_id for s in per_copy[replica] if s.at == latest.at})})
        presence, proven, ev = latest.presence, latest.authoritative, latest.evidence_id
        if presence == PRESENT:
            # the state is decided by store evidence; cite the newest
            # observation that agrees with it (a ledger claim may confirm a
            # record or risk is still there, never that it is gone)
            agree = [s for s in per_copy[replica] if s.presence == PRESENT and s.at >= latest.at
                     and (latest.active is None or s.active in (None, latest.active))]
            ev = max(agree, key=lambda s: (s.at, s.authoritative, s.evidence_id)).evidence_id
        if presence == PRESENT and latest.authoritative and category not in (DATA_FLOW, BACKUP):
            # a newer valid absence proof of this very copy supersedes the sighting
            coll = latest.record.collection if latest.record is not None else None
            proofs = ctx.valid_absence_proofs(system_id, rid, category, audit_at, replica, not_before=latest.at,
                                              collection=coll)
            # a proof only supersedes a sighting of the same collection; a
            # sighting with no named collection is not covered by any listing
            proofs = [p for p in proofs if p.captured_at > latest.at and coll]
            if proofs:
                presence, proven, ev = ABSENT, True, proofs[0].evidence_id
        copies.append(CopyState(replica, presence, proven, ev, latest, conflict))
    a.copies = copies

    present = [c for c in copies if c.presence == PRESENT]

    # ---- processes: data flows and backups --------------------------------
    if category == DATA_FLOW:
        active = [c for c in present if c.latest.active is not False]
        if active:
            c = _pick(active)
            a.finding, a.finding_evidence = "REPORT_ACTIVE_DATA_FLOW", c.evidence_id
            a.remediation, a.verification = "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"
            a.reason = "connector can still copy the subject's data"
        elif present:
            a.verification = "VERIFY_DATA_FLOW_DISABLED"
            a.verification_evidence = _pick([c for c in present if c.proven] or present).evidence_id \
                if any(c.proven for c in present) else ""
            a.reason = "connector observed disabled"
        else:
            return None
        return a

    if category == BACKUP:
        rule = ctx.rules.rule_for(BACKUP)
        a.rule_id = rule.rule_id if rule else ""
        a.action = rule.required_action if rule else ""
        restorable = [c for c in present if c.latest.active is not False]
        if restorable:
            c = _pick(restorable)
            a.finding, a.finding_evidence = "REPORT_RESTORE_RISK", c.evidence_id
            a.remediation, a.verification = "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"
            a.reason = "archive can still restore the subject's data"
        elif present:
            a.verification = "VERIFY_RESTORE_BLOCKED"
            proven = [c for c in present if c.proven]
            a.verification_evidence = _pick(proven).evidence_id if proven else ""
            a.reason = "restore access blocked"
        else:
            return None
        return a

    # ---- records governed by deletion_rules.csv --------------------------
    rule = ctx.rules.rule_for(category)
    if rule is None:
        a.reason = f"no deletion rule for category {category!r}; not assessed"
        return None
    a.rule_id = rule.rule_id

    if present:
        violations = []
        decisions = []
        for c in present:
            facts = _facts(category, c.latest.record, audit_at, request_text, subject_only)
            d = ctx.rules.apply(facts)
            decisions.append((c, d, facts))
        # the strictest required action across copies decides the record
        rank = {DELETE: 4, ANONYMIZE: 3, REDACT: 2, RETAIN: 1, NONE: 0}
        c, d, facts = max(decisions, key=lambda t: (rank[t[1].action], t[0].latest.at, t[0].evidence_id))
        a.action, a.reason = d.action, d.reason
        if d.action == DELETE:
            a.finding, a.finding_evidence = "REPORT_REMAINING_RECORD", c.evidence_id
            a.remediation, a.verification = "DELETE_RECORD", "VERIFY_RECORD_ABSENT"
        elif d.action in (REDACT, ANONYMIZE):
            needs = [(cc, dd, ff) for cc, dd, ff in decisions if dd.action == d.action and (
                ff.has_direct_identifiers or ff.attributable or ff.has_email)]
            op, done = ("REDACT", "REDACTED") if d.action == REDACT else ("ANONYMIZE", "ANONYMIZED")
            if needs:
                cc = max(needs, key=lambda t: (t[0].latest.at, t[0].evidence_id))[0]
                a.finding, a.finding_evidence = "REPORT_EXPOSED_PII", cc.evidence_id
                a.remediation, a.verification = f"{op}_RECORD", f"VERIFY_RECORD_{done}"
            else:
                a.verification = f"VERIFY_RECORD_{done}"
                proven = [cc for cc, _, _ in decisions if cc.proven]
                a.verification_evidence = _pick(proven).evidence_id if proven else ""
        elif d.action == NONE:
            # trigger condition not met: the record already has the treatment
            target = rule.required_action
            op = {REDACT: "REDACTED", ANONYMIZE: "ANONYMIZED"}.get(target)
            if op is None:
                return None
            a.verification = f"VERIFY_RECORD_{op}"
            proven = [cc for cc, _, _ in decisions if cc.proven]
            a.verification_evidence = _pick(proven).evidence_id if proven else ""
        elif d.action == RETAIN:
            # Presence may be shown by a ledger claim (a claim is only barred
            # from proving absence or a cleaned state); prefer store evidence.
            a.verification = "VERIFY_RECORD_PRESENT"
            proven = [cc for cc, _, _ in decisions if cc.proven]
            a.verification_evidence = _pick(proven or [cc for cc, _, _ in decisions]).evidence_id
        return a

    # ---- no copy present at audit_at ---------------------------------------
    if rule.required_action == RETAIN or category == TOMBSTONE:
        a.reason = "policy-retained record not observed at audit_at"
        return None
    a.action = rule.required_action
    a.verification = "VERIFY_RECORD_ABSENT"
    a.reason = "record absent at audit_at"
    proven_absent = [c for c in copies if c.presence == ABSENT and c.proven]
    # a never-observed resource (e.g. linked through the workflow) needs a proof
    proofs = ctx.valid_absence_proofs(system_id, rid, category, audit_at, "any", not_before=requested_at)
    # every copy ever seen PRESENT must be covered by a later absence of that copy
    seen_present = {r.replica_or_table for r in rs if r.presence == PRESENT and not r.claim_only}
    covered = {c.replica for c in proven_absent}
    if seen_present - covered:
        return a
    # cite a direct read-back of the resource first (a 404 / zero-row lookup
    # names the resource itself); fall back to a snapshot that omits it
    if proven_absent:
        a.verification_evidence = max((c.latest.at, c.evidence_id) for c in proven_absent)[1]
    elif proofs:
        a.verification_evidence = max((p.captured_at, p.evidence_id) for p in proofs)[1]
    return a


def _pick(copies: list[CopyState]) -> CopyState:
    return max(copies, key=lambda c: (c.latest.at, c.proven, c.evidence_id))


def _step(a: Assessment, operation: str, evidence_id: str) -> dict:
    return {"system_id": a.system_id, "resource_id": a.resource_id, "operation": operation,
            "state": OP_STATE[operation], "evidence_id": evidence_id}


def _ordered(steps: list[dict], ops: tuple[str, ...]) -> list[dict]:
    """Canonical order inside a phase: operation table order (data flows and
    restores before record changes), then system_id, then resource_id."""
    order = {op: i for i, op in enumerate(ops)}
    seen, out = set(), []
    for s in sorted(steps, key=lambda s: (order[s["operation"]], s["system_id"], _rid_key(s["resource_id"]))):
        k = (s["system_id"], s["resource_id"].lower(), s["operation"])
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def _rid_key(rid: str) -> tuple:
    m = re.fullmatch(r"(.*?)(\d+)", rid)
    return (m.group(1), int(m.group(2))) if m else (rid, -1)
