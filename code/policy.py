"""Deletion policy as data (plan 9.5) plus the safety invariants (decision 5).

``evaluate(state, cutoff)`` maps one resolved resource to a ``Decision``:
the category, the rule, the outcome (compliant / violation / unknown / missing retained
record / not a target) and the finding, remediation and verification operations.
Branches that no sample exercises carry ``hypothesis=True`` and go to the trace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from evidence.common import (
    ABSENT,
    ACTIVE,
    ANONYMIZED,
    BLOCKED,
    DISABLED,
    IDENTIFIABLE,
    OPEN,
    OPERATION_CLAIM,
    PRESENT,
    REDACTED,
    Identifiers,
)
from links import STRONG, Target
from loaders import DATASET_DIR, Rule, load_rules, parse_ts
from resolver import CONFLICT, UNKNOWN, ResourceState, exists_rollup
from schema import Operation as Op

COMPLIANT, VIOLATION, UNPROVEN, MISSING_RETAINED, NOT_TARGET = (
    "compliant", "violation", "unproven", "missing_retained", "not_target")

# Categories that the request must never delete or anonymize (safety invariant 1).
RETAINED = frozenset({"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE", "ACCOUNT_TOMBSTONE",
                      "SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG"})

# Category -> (check, finding, remediation, verification). The rule id comes from deletion_rules.csv.
#   check: "exists"  - violation while any copy is PRESENT
#          "direct"  - violation while a present copy exposes direct identifiers
#          "linked"  - violation while a present copy is attributable (any identifier, user_id too)
#          "retain"  - the record must stay PRESENT
#          "flow"    - violation while the flow is ACTIVE
#          "restore" - violation while restore is OPEN
TREATMENT: dict[str, tuple[str, Op | None, Op | None, Op]] = {
    "USER_PROFILE": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "SECONDARY_IDENTIFIER": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD,
                             Op.VERIFY_RECORD_ABSENT),
    "SEARCH_INDEX_ENTRY": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "CACHE_ENTRY": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "SUPPORT_MESSAGE": ("direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "SUPPORT_ATTACHMENT": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "ANALYTICS_PROFILE": ("linked", Op.REPORT_EXPOSED_PII, Op.ANONYMIZE_RECORD, Op.VERIFY_RECORD_ANONYMIZED),
    "PRODUCT_TELEMETRY": ("linked", Op.REPORT_EXPOSED_PII, Op.ANONYMIZE_RECORD, Op.VERIFY_RECORD_ANONYMIZED),
    "USER_EXPORT": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "MARKETING_PROFILE": ("exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "EMAIL_DELIVERY_LOG": ("direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "SECURITY_AUDIT_LOG": ("retain", None, None, Op.VERIFY_RECORD_PRESENT),
    "LEGAL_HOLD_RECORD": ("retain", None, None, Op.VERIFY_RECORD_PRESENT),
    "BACKUP_ARCHIVE": ("restore", Op.REPORT_RESTORE_RISK, Op.BLOCK_RESTORE, Op.VERIFY_RESTORE_BLOCKED),
    "ACCOUNT_TOMBSTONE": ("direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "DATA_FLOW": ("flow", Op.REPORT_ACTIVE_DATA_FLOW, Op.DISABLE_DATA_FLOW, Op.VERIFY_DATA_FLOW_DISABLED),
}

# deletion_rules.csv required_action -> the checks that carry it out.
ACTION_CHECKS = {"DELETE": {"exists"}, "REDACT": {"direct"}, "ANONYMIZE": {"linked"},
                 "RETAIN": {"retain", "restore"}}
FLOW_RULE = "flow"   # DATA_FLOW is a process, not a data category of deletion_rules.csv


def bind_rules(rules: list[Rule]) -> dict[str, tuple[str, str, Op | None, Op | None, Op]]:
    """category -> (rule_id, check, finding, remediation, verification). The rule id and the
    required action come from ``deletion_rules.csv``; a category with no treatment, or an
    action that the treatment does not carry out, stops the run."""
    bound: dict[str, tuple[str, str, Op | None, Op | None, Op]] = {}
    for rule in rules:
        treatment = TREATMENT.get(rule.data_category)
        if treatment is None or rule.data_category == "DATA_FLOW":
            raise ValueError(f"{rule.rule_id}: no treatment for category {rule.data_category}")
        if treatment[0] not in ACTION_CHECKS.get(rule.required_action, ()):
            raise ValueError(f"{rule.rule_id}: action {rule.required_action} does not fit check {treatment[0]}")
        bound[rule.data_category] = (rule.rule_id, *treatment)
    missing = set(TREATMENT) - set(bound) - {"DATA_FLOW"}
    if missing:
        raise ValueError(f"no rule in deletion_rules.csv for {sorted(missing)}")
    bound["DATA_FLOW"] = (FLOW_RULE, *TREATMENT["DATA_FLOW"])
    return bound


RULES = bind_rules(load_rules(DATASET_DIR / "deletion_rules.csv"))

# Fallback category when the record states none: (system_id, collection) then system_id.
COLLECTION_CATEGORY = {
    ("support_platform", "ticket_attachments"): "SUPPORT_ATTACHMENT",
}
SYSTEM_CATEGORY = {
    "account_service": "USER_PROFILE",
    "search_service": "SEARCH_INDEX_ENTRY",
    "analytics_platform": "ANALYTICS_PROFILE",
    "support_platform": "SUPPORT_MESSAGE",
    "export_service": "USER_EXPORT",
    "integration_service": "DATA_FLOW",
    "backup_service": "BACKUP_ARCHIVE",
    "security_service": "SECURITY_AUDIT_LOG",
    "legal_service": "LEGAL_HOLD_RECORD",
    "identity_service": "ACCOUNT_TOMBSTONE",
    "cache_service": "CACHE_ENTRY",
    "email_delivery_service": "EMAIL_DELIVERY_LOG",
    "marketing_platform": "MARKETING_PROFILE",
}
# Category from the words that describe a record (D10), for records that state none: catalog
# link text such as "Attachment catalog confirmed ...". Ids, file names and emails are removed
# first, so only descriptive words count. Two different categories give none (UNPROVEN).
CONTENT_CATEGORY: tuple[tuple[re.Pattern, str], ...] = tuple((re.compile(p, re.I), c) for p, c in (
    (r"\battachments?\b", "SUPPORT_ATTACHMENT"),
    (r"\bsearch[- ]?index\b|\bsearch documents?\b", "SEARCH_INDEX_ENTRY"),
    (r"\bcache\b", "CACHE_ENTRY"),
    (r"\btelemetry\b", "PRODUCT_TELEMETRY"),
    (r"\bmarketing\b|\bnewsletter\b", "MARKETING_PROFILE"),
    (r"\banalytics\b", "ANALYTICS_PROFILE"),
    (r"\bdata exports?\b|\bexport (?:job|archive|file)s?\b", "USER_EXPORT"),
    (r"\bbackups?\b", "BACKUP_ARCHIVE"),
    (r"\btombstones?\b", "ACCOUNT_TOMBSTONE"),
    (r"\blegal hold\b", "LEGAL_HOLD_RECORD"),
    (r"\bsecurity audit\b|\baudit log\b", "SECURITY_AUDIT_LOG"),
    (r"\bemail delivery\b|\bdelivery log\b", "EMAIL_DELIVERY_LOG"),
    (r"\bsupport (?:ticket|conversation|message)s?\b", "SUPPORT_MESSAGE"),
    (r"\bconnector\b|\bdata flow\b", "DATA_FLOW"),
))
AMBIGUOUS_CATEGORY = "?ambiguous"   # category_of: the catalog words name two or more categories
NOT_WORDS = re.compile(r"\S+@\S+|\S*\d\S*|\([^)]*\)")
RETENTION_KEYS = ("retention_until", "retain_until", "retained_until", "retention_expires_at")
# rule_13 retains a legal hold record only while "a supplied legal hold is active". The hold
# status is an explicit status field, else the hold's retention end date (``retained_until``).
HOLD_STATUS_KEYS = ("hold_status", "legal_hold_status", "status")
HOLD_RELEASED = frozenset({"INACTIVE", "RELEASED"})


@dataclass
class Decision:
    category: str
    rule_id: str
    outcome: str
    finding: Op | None = None
    remediation: Op | None = None
    verification: Op | None = None
    check: str = ""                # effective rule check (see RULES)
    copy: str = ""                 # the copy that violates (citation) or proves compliance
    bad_copies: list[str] = field(default_factory=list)   # every copy in the violating state
    attribute: str = ""            # the resolved attribute the outcome rests on
    hypothesis: list[str] = field(default_factory=list)
    reason: str = ""


def category_of(state: ResourceState) -> str:
    return category_source(state)[0]


def category_source(state: ResourceState) -> tuple[str, str]:
    """(category, source). Source: ``structured`` (a stated record type or data category),
    ``collection``, ``content`` (catalog words), ``ambiguous`` or ``system_default``.
    Every admissible structured category counts, not the first one met (r3-#4): two different
    ones give ``ambiguous``, so the record stays unproven."""
    structured = {value for cs in state.copies.values() for st in cs.statements if st.obs is not None
                  for value in (st.obs.record_type, st.obs.fields.get("record_type"),
                                st.obs.fields.get("data_category"))
                  if isinstance(value, str) and value in RULES}
    structured |= {value for value in (state.record_type, *state.record_types) if value in RULES}
    if len(structured) > 1:
        return AMBIGUOUS_CATEGORY, "ambiguous"
    if structured:
        return structured.pop(), "structured"
    system = state.target.system_id
    if (system, state.collection) in COLLECTION_CATEGORY:
        return COLLECTION_CATEGORY[(system, state.collection)], "collection"
    named = content_categories(state.target.descriptions)
    if len(named) > 1:   # the words name two categories: no category, the record stays unproven
        return AMBIGUOUS_CATEGORY, "ambiguous"
    if named:
        return named.pop(), "content"
    return SYSTEM_CATEGORY.get(system, ""), "system_default"


def content_categories(texts) -> set[str]:
    """Every category named by the descriptive words of a record's catalog text."""
    return {category for text in texts for pattern, category in CONTENT_CATEGORY
            if pattern.search(NOT_WORDS.sub(" ", text))}


def content_category(texts) -> str:
    """The one category the catalog text names, or ``""`` when it names none or several."""
    named = content_categories(texts)
    return named.pop() if len(named) == 1 else ""


def _present_copies(state: ResourceState) -> list:
    return [cs for _, cs in sorted(state.copies.items()) if cs.get("exists") == PRESENT]


def _exposure(cs, check: str) -> str:
    """IDENTIFIABLE / clean / UNKNOWN for one present copy."""
    treatment = cs.get("treatment")
    if treatment in (IDENTIFIABLE,):
        return IDENTIFIABLE
    if treatment in (ANONYMIZED, REDACTED):
        return "clean"
    ids = cs.get("exposed_ids")
    if isinstance(ids, Identifiers):
        hit = ids.direct() if check == "direct" else ids.any()
        return IDENTIFIABLE if hit else "clean"
    return UNKNOWN


def _retention_expired(state: ResourceState, cutoff) -> bool | str | None:
    """Is the retention end date at or before ``cutoff``? The newest statement that states a date
    decides (time, then tier, then ``evidence_id``), in every copy order (r3-#3). ``None``: no date.
    ``CONFLICT``: statements of the same time and tier state different dates."""
    dated = []
    for cs in state.copies.values():
        for st in cs.statements:
            if st.obs is None:
                continue
            for key in RETENTION_KEYS:
                until = parse_ts(str(st.obs.fields[key])) if st.obs.fields.get(key) else None
                if until is not None:
                    dated.append((st, until))
                    break
    if not dated:
        return None
    best, until = max(dated, key=lambda pair: (pair[0].at, pair[0].rank, pair[0].evidence_id))
    if len({u for st, u in dated if (st.at, st.rank) == (best.at, best.rank)}) > 1:
        return CONFLICT
    return until <= cutoff


def attachment_exclusive(target: Target) -> bool:
    """The SUPPORT_ATTACHMENT rule deletes an attachment that "belongs only to the deletion subject". Proof: a catalog
    says so (``exclusive``), or the record itself carries the subject's identifier (a strong
    identifier edge) and no other user is linked to it."""
    if target.exclusive:
        return True
    return not target.shared_with and any(e.kind == "identifier" and e.tier == STRONG for e in target.edges)


def _hold_status(state: ResourceState) -> str:
    """Explicit status of a legal hold (newest statement first), upper case, or ``""``.
    A workflow operation claim is not a status."""
    stated = [st.obs for cs in state.copies.values() for st in cs.statements
              if st.obs is not None and st.obs.assertion != OPERATION_CLAIM]
    for obs in sorted(stated, key=lambda o: (o.state_observed_at, o.obs_id), reverse=True):
        for key in HOLD_STATUS_KEYS:
            value = obs.fields.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    return ""


def _exposure_decision(d: Decision, state: ResourceState, check: str, exists: str) -> Decision:
    """REDACT / ANONYMIZE rules: the record stays; the exposure of each present copy decides."""
    if exists == ABSENT:
        # The record is gone although policy keeps it redacted/anonymized (H).
        d.hypothesis.append("redact_target_absent")
        d.outcome, d.attribute, d.verification = COMPLIANT, "exists", Op.VERIFY_RECORD_ABSENT
        d.finding = d.remediation = None
        return d
    present = _present_copies(state)
    exposures = [(cs, _exposure(cs, check)) for cs in present]
    bad = [cs for cs, e in exposures if e == IDENTIFIABLE]
    if bad:
        d.outcome, d.copy, d.attribute = VIOLATION, bad[0].copy, "exposure"
        d.bad_copies = [cs.copy for cs in bad]
    elif present and all(e == "clean" for _, e in exposures):
        d.outcome, d.copy, d.attribute = COMPLIANT, present[0].copy, "exposure"
    if d.category == "SUPPORT_MESSAGE":
        d.hypothesis.append("support_shared_context_assumed")
    return d


def holds_subject(ids, keys: Identifiers) -> bool:
    """``ids`` hold one of the subject's direct identifiers (email, phone, email hash)."""
    return isinstance(ids, Identifiers) and any(getattr(ids, k) & getattr(keys, k)
                                                for k in ("emails", "phones", "hashes"))


def _process_decision(d: Decision, state: ResourceState, check: str) -> Decision:
    """Data flows and backups: any ACTIVE / OPEN copy is a violation. Compliant needs every copy DISABLED /
    BLOCKED; only a copy proven ABSENT may leave the state unknown (an absent copy runs no flow).
    A backup with no restore state on any copy is a violation when a present copy holds the
    subject's direct identifiers (r5-#2): REPORT_RESTORE_RISK is "A backup or restore path can
    bring deleted data back", and no BLOCKED observation stops that path."""
    attr, bad_value, good_value = (("flow_state", ACTIVE, DISABLED) if check == "flow"
                                   else ("restore_state", OPEN, BLOCKED))
    values = {name: cs.get(attr) for name, cs in sorted(state.copies.items())}
    bad = [name for name, v in values.items() if v == bad_value]
    if bad:
        d.outcome, d.copy, d.attribute = VIOLATION, bad[0], attr
        d.bad_copies = bad
    elif values and all(v == good_value or (v == UNKNOWN and state.copies[name].get("exists") == ABSENT)
                        for name, v in values.items()) \
            and any(v == good_value for v in values.values()):
        d.outcome, d.copy, d.attribute = COMPLIANT, next(n for n, v in values.items() if v == good_value), attr
    elif any(v == CONFLICT for v in values.values()):
        d.reason = "conflict"
    elif check == "restore" and all(v == UNKNOWN for v in values.values()):
        held = [cs.copy for cs in _present_copies(state) if holds_subject(cs.get("exposed_ids"), state.keys)]
        if held:
            d.outcome, d.copy, d.attribute, d.bad_copies = VIOLATION, held[0], "exposure", held
            d.hypothesis.append("restore_block_not_shown")
    return d


def evaluate(state: ResourceState, cutoff) -> Decision:
    category = category_of(state)
    if category == AMBIGUOUS_CATEGORY:   # no rule applies with proof: unproven, never the first match
        return Decision("", "", UNPROVEN, reason="ambiguous category")
    if category not in RULES:
        return Decision(category, "", NOT_TARGET, reason="out of rules")
    rule_id, check, finding, remediation, verify = RULES[category]
    d = Decision(category, rule_id, UNPROVEN, finding, remediation, verify, check=check)
    if category == "SUPPORT_ATTACHMENT" and not attachment_exclusive(state.target):
        d.finding = d.remediation = d.verification = None   # no rule applies with proof: no DELETE_RECORD
        d.reason = "attachment not proven exclusive"
        return d
    exists = exists_rollup(state)

    if check == "retain":
        expired = _retention_expired(state, cutoff)
        if expired == CONFLICT:   # two equal statements, two dates: unproven, never a delete
            d.finding = d.remediation = None
            d.reason = "retention dates contradict"
            return d
        if category == "LEGAL_HOLD_RECORD":
            status = _hold_status(state)   # an explicit status governs; the end date counts only without one
            if status in HOLD_RELEASED:   # an explicit released hold is not retained
                expired = True
                d.hypothesis.append(f"legal_hold_{status.lower()}")
            elif status and expired:   # an active status with a past end date: a contradiction, never delete
                d.finding = d.remediation = None
                d.reason = "legal hold status contradicts its end date"
                return d
            elif status:
                expired = False
                d.hypothesis.append(f"legal_hold_{status.lower()}")
            elif expired is None:   # no status and no end date: active is not proven
                d.finding = d.remediation = None
                d.reason = "legal hold status missing"
                return d
        if expired:
            d.hypothesis.append("retention_expired_delete")
            d.finding, d.remediation, d.verification = (Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD,
                                                        Op.VERIFY_RECORD_ABSENT)
            check = d.check = "exists"
        else:
            if expired is None:
                d.hypothesis.append("retention_unknown_retain")
            d.finding = d.remediation = None
            if exists == PRESENT:
                d.outcome, d.copy, d.attribute = COMPLIANT, _present_copies(state)[0].copy, "exists"
            elif exists == ABSENT:
                d.outcome, d.attribute = MISSING_RETAINED, "exists"
                d.hypothesis.append("retained_record_missing")
            return d

    if check == "exists":
        if exists == PRESENT:
            d.outcome, d.copy, d.attribute = VIOLATION, _present_copies(state)[0].copy, "exists"
            d.bad_copies = [cs.copy for cs in _present_copies(state)]
        elif exists == ABSENT:
            d.outcome, d.attribute = COMPLIANT, "exists"
        return d

    if check in ("direct", "linked"):
        return _exposure_decision(d, state, check, exists)
    return _process_decision(d, state, check)


# ------------------------------------------------------------------ safety invariants

class SafetyViolation(AssertionError):
    pass


def check_safety(decision: Decision, *, foreign_only: bool, proof_assertions: list[str]) -> None:
    """Raise when a planned step breaks a decision-5 invariant.

    A retained category may be deleted only when its retention is proven expired.
    """
    category, remediation = decision.category, decision.remediation
    retained = category in RETAINED and "retention_expired_delete" not in decision.hypothesis
    if remediation in (Op.DELETE_RECORD, Op.ANONYMIZE_RECORD) and retained:
        raise SafetyViolation(f"{remediation} on retained category {category}")
    if remediation is not None and foreign_only:
        raise SafetyViolation("action on a record linked only to another user")
    if "operation_claim" in proof_assertions:
        raise SafetyViolation("operation claim used as proof")
