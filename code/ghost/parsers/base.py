"""Shared vocabulary for evidence parsers.

Every parser turns its file into Observation rows plus a scope: the (system_id, observed_at)
pairs the file covers completely, so a resource missing from it can be proven absent.

Result enum (state of one record in one file):
  NOT_FOUND        record does not exist
  IDENTIFIABLE     record exists and still holds a direct identifier (email, phone, hash, name)
  REFERENCED       record exists, holds only a stable internal reference (user_id)
  REDACTED         source explicitly says identifiers were removed
  ANONYMIZED       record exists with no link to any person
  ACTIVE/DISABLED  data flow state
  RESTORE_ALLOWED/RESTORE_BLOCKED  backup restore state
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..identifiers import find_identifiers, norm_email, norm_hash, norm_phone
from ..models import Observation

RESULTS = ("NOT_FOUND", "IDENTIFIABLE", "REFERENCED", "REDACTED", "ANONYMIZED",
           "ACTIVE", "DISABLED", "RESTORE_ALLOWED", "RESTORE_BLOCKED")

# When one file shows the same resource twice at the same moment (primary + replica tables),
# the worse state wins: a copy anywhere is a copy.
_SEVERITY = {"IDENTIFIABLE": 5, "REFERENCED": 4, "REDACTED": 3, "ANONYMIZED": 2, "NOT_FOUND": 1,
             "ACTIVE": 2, "DISABLED": 1, "RESTORE_ALLOWED": 2, "RESTORE_BLOCKED": 1}

_PREFIX_SYSTEM = (
    ("audit_record_", "security_service"),
    ("data_flow_", "integration_service"),
    ("email_delivery_", "email_delivery_service"),
    ("legal_hold_", "legal_service"),
    ("tombstone_", "identity_service"),
    ("analytics_", "analytics_platform"),
    ("marketing_", "marketing_platform"),
    ("account_", "account_service"),
    ("support_", "support_platform"),
    ("search_", "search_service"),
    ("export_", "export_service"),
    ("backup_", "backup_service"),
    ("object_", "object_storage"),
    ("cache_", "cache_service"),
)

# Collection / table names -> deletion_rules.csv data_category (DATA_FLOW is a process, not a rule row).
COLLECTION_CATEGORY = {
    "customer_profiles": "USER_PROFILE",
    "customer_search_documents": "SEARCH_INDEX_ENTRY",
    "search_documents": "SEARCH_INDEX_ENTRY",
    "customer_analytics_profiles": "ANALYTICS_PROFILE",
    "customer_analytics_reports": "ANALYTICS_PROFILE",
    "support_records": "SUPPORT_MESSAGE",
    "support_conversations": "SUPPORT_MESSAGE",
    "ticket_attachments": "SUPPORT_ATTACHMENT",
    "customer_exports": "USER_EXPORT",
    "customer_export_jobs": "USER_EXPORT",
    "connector_subscriptions": "DATA_FLOW",
    "connector_configurations": "DATA_FLOW",
    "backup_restore_entries": "BACKUP_ARCHIVE",
    "backup_catalog": "BACKUP_ARCHIVE",
    "security_audit_records": "SECURITY_AUDIT_LOG",
    "security_audit_events": "SECURITY_AUDIT_LOG",
    "deleted_customer_references": "ACCOUNT_TOMBSTONE",
    "retained_order_records": "LEGAL_HOLD_RECORD",
}

DIRECT_FIELDS = frozenset({
    "email", "owner_email", "customer_email", "requester_email", "uploaded_by",
    "phone", "owner_phone", "requester_phone", "email_hash",
    "full_name", "name", "display_name", "requester_name", "matched_value",
})
REFERENCE_FIELDS = frozenset({"customer_reference", "subject_reference", "user_id",
                              "subject_selector", "subject_ref"})
NAME_FIELDS = frozenset({"full_name", "name", "display_name", "requester_name"})
_NULLS = {"", "null", "none", "nil"}
_USER_ID = re.compile(r"^user_\d+$")


def system_for(resource_id: str, fallback: str = "") -> str:
    for prefix, system in _PREFIX_SYSTEM:
        if resource_id.startswith(prefix):
            return system
    return fallback


def is_null(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in _NULLS)


def norm_subject(key: str, value: str) -> str | None:
    """Normalise one identifier-bearing field value, or None when it holds no identifier."""
    v = value.strip()
    if _USER_ID.match(v):
        return v
    if "@" in v:
        return norm_email(v)
    if re.fullmatch(r"[0-9a-fA-F]{64}", v):
        return norm_hash(v)
    if "phone" in key or re.fullmatch(r"\+[\d\s().-]{7,}", v):
        p = norm_phone(v)
        return p if len(p) > 6 else None
    return None


def _flatten(record: dict, prefix: str = "") -> Iterable[tuple[str, Any]]:
    for k, v in record.items():
        if isinstance(v, dict):
            yield from _flatten(v, prefix)
        else:
            yield k, v


def classify_record(record: dict) -> tuple[str, tuple[str, ...]]:
    """Existence state and linked identifiers for a raw record that is known to exist."""
    direct, reference = False, False
    subjects: set[str] = set()
    for key, value in _flatten(record):
        if is_null(value) or isinstance(value, (bool, int, float, list)):
            continue
        text = str(value)
        if key in DIRECT_FIELDS:
            subj = norm_subject(key, text)
            if subj and _USER_ID.match(subj):
                reference = True
            elif subj or key in NAME_FIELDS:
                direct = True
            if subj:
                subjects.add(subj)
        elif key in REFERENCE_FIELDS:
            subj = norm_subject(key, text)
            if subj:
                subjects.add(subj)
                if _USER_ID.match(subj):
                    reference = True
                else:
                    direct = True  # an email used as the reference is still a direct identifier
        elif key not in ("resource_id",):
            # Free text (message bodies, file names) is scanned for emails only: seals and
            # checksums are 64-hex strings too, and only a field named as a hash is a hash.
            embedded = {s for s in find_identifiers(text) if "@" in s}
            if embedded:  # e.g. an email pasted inside a message body
                direct = True
                subjects |= embedded
    result = "IDENTIFIABLE" if direct else "REFERENCED" if reference else "ANONYMIZED"
    return result, tuple(sorted(subjects))


def flag(value: Any) -> bool | None:
    """Parse 1/0, true/false, yes/no style flags. None when absent or unrecognised."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "allow", "allowed"):
            return True
        if v in ("0", "false", "no", "n", "deny", "denied"):
            return False
    return None


def state_for(category: str, record: dict) -> tuple[str, tuple[str, ...]]:
    """State of an existing raw record, with flow/restore flags taking precedence."""
    result, subjects = classify_record(record)
    if category == "DATA_FLOW":
        enabled = flag(record.get("enabled"))
        result = "ACTIVE" if enabled else "DISABLED"
    elif category == "BACKUP_ARCHIVE":
        allowed = flag(record.get("restore_allowed"))
        result = "RESTORE_ALLOWED" if allowed else "RESTORE_BLOCKED"
    return result, subjects


# Ledger vocabulary (handover text, *_ledger/manifest/configurations JSON, record_lookup logs).
def ledger_result(category: str, word: str, subject: str | None) -> str | None:
    w = word.strip().upper()
    if w == "NOT_FOUND":
        return "NOT_FOUND"
    if category == "DATA_FLOW":
        return {"ACTIVE": "ACTIVE", "DISABLED": "DISABLED", "FOUND": "ACTIVE"}.get(w)
    if category == "BACKUP_ARCHIVE":
        return {"ACTIVE": "RESTORE_ALLOWED", "BLOCKED": "RESTORE_BLOCKED",
                "DISABLED": "RESTORE_BLOCKED"}.get(w)
    if w == "FOUND":
        return "REFERENCED" if subject and _USER_ID.match(subject) else "IDENTIFIABLE"
    if w in ("IDENTIFIABLE", "REDACTED", "ANONYMIZED"):
        return w
    return None


@dataclass
class ParseResult:
    observations: list[Observation] = field(default_factory=list)
    scope: set[tuple[str, str]] = field(default_factory=set)   # (system_id, observed_at)
    skipped: int = 0                                           # records that could not be used

    def add(self, **kw: Any) -> None:
        self.observations.append(Observation(**kw))


def merge(observations: list[Observation]) -> list[Observation]:
    """Collapse rows for the same (file, resource, moment): worst state, union of subjects."""
    groups: dict[tuple[str, str, str], Observation] = {}
    for o in observations:
        key = (o.evidence_id, o.resource_id, o.observed_at)
        prev = groups.get(key)
        if prev is None:
            groups[key] = o
            continue
        worse = o if _SEVERITY.get(o.result, 0) > _SEVERITY.get(prev.result, 0) else prev
        groups[key] = Observation(
            evidence_id=prev.evidence_id, captured_at=prev.captured_at, observed_at=prev.observed_at,
            system_id=prev.system_id, resource_id=prev.resource_id,
            category=prev.category if prev.category != "UNKNOWN" else o.category,
            result=worse.result,
            subjects=tuple(sorted(set(prev.subjects) | set(o.subjects))),
            retention_until=prev.retention_until or o.retention_until,
            raw_ref=";".join(sorted({*prev.raw_ref.split(";"), *o.raw_ref.split(";")} - {""})),
        )
    return sorted(groups.values(), key=lambda o: (o.evidence_id, o.resource_id, o.observed_at))
