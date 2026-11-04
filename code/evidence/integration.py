"""P1 -> P2 -> P3 integration layer (minimal, dictionary-based).

Entry points: ``find_case_evidence(identity, case)`` for a deletion_requests.csv
row, or ``find_evidence(identity, audit_at)`` with an already parsed cutoff.

``find_evidence(identity, audit_at)`` turns P1's identity bundle into P2's
``SubjectIdentifiers`` with P1's adapter, runs the existing scanner queries
with one validated cutoff, and returns a plain dictionary with exactly five
keys (see ``code/evidence/README.md``):

    records, latest_by_resource, referenced_resources, absence_proofs,
    identifier_provenance

Nothing from P1 is imported. The identity object is used only through the
attributes P1 documents in ``code/README_identity.md``:

    as_subject_kwargs(), user_id, current_email, current_phone,
    current_email_hash, current_name,
    history[*].audit_id / field_name / old_value / new_value / event_time

Scanner APIs are used unchanged and with their safe defaults, so WEAK
(name-only) and conflicting observations stay in ``records`` but never reach
``latest_by_resource``, link expansion or ``referenced_resources``.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import SubjectIdentifiers
from .normalize import norm_email, norm_hash, norm_name, norm_phone, norm_user_id, parse_ts
from .scanner import EvidenceScanner

CURRENT = "CURRENT"
HISTORICAL = "HISTORICAL"

# P1's documented IdentityChange.field_name values -> (provenance kind, normaliser)
_HISTORY_FIELDS = {
    "email": ("email", norm_email),
    "phone": ("phone", norm_phone),
    "email_hash": ("email_hash", norm_hash),
}
_KWARG_KINDS = (("emails", "email", norm_email), ("phones", "phone", norm_phone),
                ("email_hashes", "email_hash", norm_hash), ("names", "name", norm_name))

DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
_SCANNERS: dict[tuple[str, str], EvidenceScanner] = {}


# --------------------------------------------------------------------------
# Scanner lifecycle
# --------------------------------------------------------------------------
def get_scanner(dataset_dir: Optional[Path | str] = None, *, ocr_mode: str = "auto") -> EvidenceScanner:
    """Return a loaded scanner, created once per process for each
    (resolved dataset directory, OCR mode)."""
    root = Path(dataset_dir) if dataset_dir is not None else DEFAULT_DATASET_DIR
    key = (str(root.resolve()), ocr_mode)
    scanner = _SCANNERS.get(key)
    if scanner is None:
        scanner = EvidenceScanner(root, ocr_mode=ocr_mode)
        scanner.load()
        _SCANNERS[key] = scanner
    return scanner


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def _validate_audit_at(audit_at: Any) -> datetime:
    if audit_at is None:
        raise ValueError("audit_at is required")
    if not isinstance(audit_at, datetime):
        raise TypeError(f"audit_at must be a timezone-aware datetime, got {type(audit_at).__name__}")
    if audit_at.tzinfo is None or audit_at.utcoffset() is None:
        raise ValueError(f"audit_at must be timezone-aware, got naive datetime {audit_at!r}")
    return audit_at.astimezone(timezone.utc)


def _history_time(change: Any, audit_at: datetime) -> Optional[datetime]:
    """Parse a history row's event_time and enforce the cutoff.

    P1: an empty event_time "is kept as if it happened before audit_at", so it
    is accepted and reported as None. Text that is not a timestamp, or a time
    after audit_at, means the bundle does not belong to this cutoff.
    """
    raw = getattr(change, "event_time", "")
    if raw is None or not str(raw).strip():
        return None
    when = parse_ts(raw)
    if when is None:
        raise ValueError(f"history {getattr(change, 'audit_id', '?')}: unparseable event_time {raw!r}")
    if when > audit_at:
        raise ValueError(
            f"history {getattr(change, 'audit_id', '?')} at {when.isoformat()} is after audit_at "
            f"{audit_at.isoformat()}: the identity bundle was resolved for a different cutoff")
    return when


# --------------------------------------------------------------------------
# Identifier provenance
# --------------------------------------------------------------------------
def _entry(source: str, audit_id: Optional[str], event_time: Optional[datetime], basis: str) -> dict:
    return {"source": source, "audit_id": audit_id, "event_time": event_time, "basis": basis}


def identifier_provenance(identity: Any, identifiers: SubjectIdentifiers,
                          audit_at: datetime) -> dict[tuple[str, str], list[dict]]:
    """Provenance of every identifier the subject is searched with.

    Keys are (kind, normalised value), the same normalisation the scanner uses,
    so they join to ``ObservedRecord.identifiers_matched`` ("kind:value").
    Each value is a list of entries {source, audit_id, event_time, basis}; a
    value that was both current and historical (or changed more than once)
    has one entry per fact.
    """
    prov: dict[tuple[str, str], list[dict]] = {}

    def add(kind: str, value: Optional[str], entry: dict) -> None:
        if value and entry not in prov.setdefault((kind, value), []):
            prov[(kind, value)].append(entry)

    history = list(getattr(identity, "history", None) or [])
    times = [_history_time(ch, audit_at) for ch in history]  # validates every row first

    # Historical values: old_value of each change (used until event_time).
    for ch, when in zip(history, times):
        spec = _HISTORY_FIELDS.get(getattr(ch, "field_name", ""))
        if spec is None:
            continue  # not an identifier field documented by P1
        kind, norm = spec
        add(kind, norm(getattr(ch, "old_value", "")), _entry(HISTORICAL, ch.audit_id, when, "history.old_value"))

    # Current values, with the change that made them current when one exists.
    current = {
        "email": norm_email(getattr(identity, "current_email", "")),
        "phone": norm_phone(getattr(identity, "current_phone", "")),
        "email_hash": norm_hash(getattr(identity, "current_email_hash", "")),
    }
    for kind, value in current.items():
        if not value:
            continue
        intro = [(ch, when) for ch, when in zip(history, times)
                 if _HISTORY_FIELDS.get(getattr(ch, "field_name", ""), ("", None))[0] == kind
                 and _HISTORY_FIELDS[ch.field_name][1](getattr(ch, "new_value", "")) == value]
        if intro:
            for ch, when in intro:
                add(kind, value, _entry(CURRENT, ch.audit_id, when, "history.new_value"))
        else:
            add(kind, value, _entry(CURRENT, None, None, "snapshot"))
    add("user_id", norm_user_id(getattr(identity, "user_id", None)), _entry(CURRENT, None, None, "snapshot"))
    add("name", norm_name(getattr(identity, "current_name", "")), _entry(CURRENT, None, None, "snapshot"))

    # Hashes P1 computes as SHA-256 of a historical email (no audit row of their own).
    for (kind, value), entries in list(prov.items()):
        if kind != "email" or not any(e["source"] == HISTORICAL for e in entries):
            continue
        digest = hashlib.sha256(value.encode()).hexdigest()
        if digest in identifiers.email_hashes and not prov.get(("email_hash", digest)):
            add("email_hash", digest, _entry(HISTORICAL, None, None, "computed_sha256_of_historical_email"))

    # Every searched identifier must be explained by documented P1 data.
    n = identifiers.normalized()
    searched = {("email", v) for v in n.emails} | {("phone", v) for v in n.phones} \
        | {("email_hash", v) for v in n.email_hashes} | {("name", v) for v in n.names}
    if n.user_id:
        searched.add(("user_id", n.user_id))
    unexplained = sorted(searched - set(prov))
    if unexplained:
        raise ValueError(f"identifiers not explained by the identity snapshot or history: {unexplained}")
    return {k: prov[k] for k in sorted(prov) if k in searched}


# --------------------------------------------------------------------------
# Absence proofs
# --------------------------------------------------------------------------
def _absence_proofs(scanner: EvidenceScanner, records: list, references: list,
                    audit_at: datetime) -> dict[tuple[str, str], list]:
    """Valid absence proofs for referenced resources and for resources seen in
    confirmed, authoritative observations. Only resources with a known
    system_id are checked; only COMPLETE, uncontradicted proofs are kept."""
    targets: dict[tuple[str, str], tuple[str, str]] = {}  # (system, rid.lower()) -> (system, rid)

    def want(system_id: Optional[str], resource_id: str) -> None:
        if system_id:
            targets.setdefault((system_id, resource_id.lower()), (system_id, resource_id))

    for ref in references:
        want(ref.system_id, ref.resource_id)
    for rec in records:
        if rec.is_confirmed and not rec.claim_only:
            want(rec.system_id, rec.resource_id)

    out: dict[tuple[str, str], list] = {}
    for key in sorted(targets):
        system_id, resource_id = targets[key]
        proofs = [p for p in scanner.absence_proofs(system_id, resource_id, audit_at) if p.is_valid_proof]
        out[(system_id, resource_id)] = proofs
    return out


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def find_evidence(identity: Any, audit_at: datetime, *, scanner: Optional[EvidenceScanner] = None,
                  dataset_dir: Optional[Path | str] = None, ocr_mode: str = "auto") -> dict:
    """Evidence findings for one subject at ``audit_at``.

    ``identity`` is P1's identity bundle (used via its documented attributes).
    ``scanner`` defaults to :func:`get_scanner` (loaded once per process).

    Raises ValueError for a missing or naive ``audit_at``, a history row after
    ``audit_at``, or an identifier the bundle cannot explain; TypeError for a
    non-datetime ``audit_at``.
    """
    cutoff = _validate_audit_at(audit_at)
    identifiers = SubjectIdentifiers(**identity.as_subject_kwargs())
    provenance = identifier_provenance(identity, identifiers, cutoff)
    scanner = scanner or get_scanner(dataset_dir, ocr_mode=ocr_mode)

    records = scanner.find_records(identifiers, cutoff)
    latest = scanner.latest_by_resource(identifiers, cutoff)
    references = scanner.referenced_resources(identifiers, cutoff)
    return {
        "records": records,
        "latest_by_resource": latest,
        "referenced_resources": references,
        "absence_proofs": _absence_proofs(scanner, records, references, cutoff),
        "identifier_provenance": provenance,
    }


_EXPLICIT_OFFSET_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$", re.I)


def case_audit_at(case: Any) -> datetime:
    """The validated, aware UTC cutoff of a case row.

    ``case["audit_at"]`` may be a timezone-aware ``datetime`` or an ISO-8601
    string with an explicit offset (``Z`` / ``+HH:MM``), as in
    ``deletion_requests.csv``. Missing or empty, naive datetimes and
    offset-less strings raise ``ValueError``; any other type (or a ``case``
    that is not a mapping) raises ``TypeError``.
    """
    if not isinstance(case, Mapping):
        raise TypeError(f"case must be a mapping (a deletion_requests.csv row), got {type(case).__name__}")
    value = case.get("audit_at")
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{case.get('case_id', '?')}: audit_at is missing")
    if isinstance(value, datetime):
        return _validate_audit_at(value)
    if not isinstance(value, str):
        raise TypeError(f"{case.get('case_id', '?')}: audit_at must be a datetime or ISO-8601 string, "
                        f"got {type(value).__name__}")
    text = value.strip()
    if not _EXPLICIT_OFFSET_RE.search(text):
        raise ValueError(f"{case.get('case_id', '?')}: audit_at {value!r} has no explicit UTC offset (e.g. 'Z')")
    parsed = parse_ts(text)
    if parsed is None:
        raise ValueError(f"{case.get('case_id', '?')}: audit_at {value!r} is not an ISO-8601 timestamp")
    return _validate_audit_at(parsed)


def find_case_evidence(identity: Any, case: Any, *, scanner: Optional[EvidenceScanner] = None,
                       dataset_dir: Optional[Path | str] = None, ocr_mode: str = "auto") -> dict:
    """Evidence findings for one ``deletion_requests.csv`` row.

    Same result as ``find_evidence(identity, case_audit_at(case), ...)``: the
    same five-key dictionary, scanner defaults and safeguards.
    """
    return find_evidence(identity, case_audit_at(case), scanner=scanner,
                         dataset_dir=dataset_dir, ocr_mode=ocr_mode)
