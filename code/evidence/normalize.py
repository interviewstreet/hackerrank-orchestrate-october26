"""Identifier normalisation, free-text extraction and vocabulary maps."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------


def parse_ts(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp into an aware UTC datetime (None on failure)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------

_NULLISH = {"", "null", "none", "nil", "n/a", "-", "no direct identifier"}


def is_nullish(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in _NULLISH)


def norm_email(value: Any) -> Optional[str]:
    if is_nullish(value):
        return None
    s = str(value).strip().strip("<>\"'").lower()
    return s if EMAIL_FULL_RE.fullmatch(s) else None


def norm_phone(value: Any) -> Optional[str]:
    """Digits only (leading + dropped). Needs at least 7 digits."""
    if is_nullish(value):
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits if len(digits) >= 7 else None


def norm_hash(value: Any) -> Optional[str]:
    if is_nullish(value):
        return None
    s = str(value).strip().lower()
    return s if re.fullmatch(r"[0-9a-f]{32,128}", s) else None


def norm_user_id(value: Any) -> Optional[str]:
    if is_nullish(value):
        return None
    s = str(value).strip().lower()
    return s if USER_ID_FULL_RE.fullmatch(s) else None


def norm_resource_id(value: Any) -> Optional[str]:
    if is_nullish(value):
        return None
    return str(value).strip().lower()


def norm_name(value: Any) -> Optional[str]:
    """Case-, accent- and whitespace-insensitive *full* name."""
    if is_nullish(value):
        return None
    s = unicodedata.normalize("NFKD", str(value))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s or None


# ---------------------------------------------------------------------------
# Free-text extraction
# ---------------------------------------------------------------------------

EMAIL_FULL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.[a-z]{2,}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
USER_ID_FULL_RE = re.compile(r"user_\d+")
USER_ID_RE = re.compile(r"(?<![A-Za-z0-9_])user_\d+(?![A-Za-z0-9_])", re.I)
PHONE_RE = re.compile(r"(?<![\w.])\+\d[\d \-()]{6,18}\d")
HASH_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")

# Resource-id prefix -> owning system. Longest prefixes first.
RESOURCE_PREFIX_SYSTEM: list[tuple[str, str]] = [
    ("audit_record_", "security_service"),
    ("data_flow_", "integration_service"),
    ("legal_hold_", "legal_service"),
    ("tombstone_", "identity_service"),
    ("analytics_", "analytics_platform"),
    ("marketing_", "marketing_platform"),
    ("account_", "account_service"),
    ("search_", "search_service"),
    ("support_", "support_platform"),
    ("export_", "export_service"),
    ("backup_", "backup_service"),
]

# Default data category for a resource-id prefix (None = ambiguous).
RESOURCE_PREFIX_CATEGORY: dict[str, Optional[str]] = {
    "audit_record_": "SECURITY_AUDIT_LOG",
    "data_flow_": "DATA_FLOW",
    "legal_hold_": "LEGAL_HOLD_RECORD",
    "tombstone_": "ACCOUNT_TOMBSTONE",
    "analytics_": "ANALYTICS_PROFILE",
    "marketing_": "MARKETING_PROFILE",
    "account_": "USER_PROFILE",
    "search_": "SEARCH_INDEX_ENTRY",
    "support_": None,  # message or attachment
    "export_": "USER_EXPORT",
    "backup_": "BACKUP_ARCHIVE",
}

_prefix_alt = "|".join(re.escape(p) for p, _ in RESOURCE_PREFIX_SYSTEM)
# Lookbehind rejects letters/underscore only, so OCR-glued row numbers such as
# "1data_flow_9846" still match. A trailing letter/underscore rejects
# file names like "support_7731_thumb".
RESOURCE_ID_RE = re.compile(rf"(?<![A-Za-z_])(?:{_prefix_alt})\d+(?![A-Za-z_])", re.I)
FILE_NAME_RE = re.compile(r"(?<![\w/])[A-Za-z0-9][\w\-]*\.(?:pdf|zip|jpg|jpeg|png|csv|tar\.zst)(?![\w])", re.I)

CANONICAL_SYSTEMS = {s for _, s in RESOURCE_PREFIX_SYSTEM}


def prefix_of(resource_id: str) -> Optional[str]:
    rid = resource_id.lower()
    for prefix, _ in RESOURCE_PREFIX_SYSTEM:
        if rid.startswith(prefix):
            return prefix
    return None


def system_for_resource(resource_id: str) -> Optional[str]:
    p = prefix_of(resource_id)
    return dict(RESOURCE_PREFIX_SYSTEM)[p] if p else None


def default_category_for_resource(resource_id: str) -> Optional[str]:
    p = prefix_of(resource_id)
    return RESOURCE_PREFIX_CATEGORY.get(p) if p else None


def _strip_resource_ids(text: str) -> str:
    """Separate resource ids from adjacent tokens (OCR often glues them)."""
    return RESOURCE_ID_RE.sub(lambda m: f" {m.group(0)} ", text)


def extract_emails(text: str) -> list[str]:
    cleaned = _strip_resource_ids(text)
    out = []
    for m in EMAIL_RE.finditer(cleaned):
        e = norm_email(m.group(0).lstrip("-_.·"))
        if e and e not in out:
            out.append(e)
    return out


def extract_phones(text: str) -> list[str]:
    out = []
    for m in PHONE_RE.finditer(text):
        p = norm_phone(m.group(0))
        if p and p not in out:
            out.append(p)
    return out


def extract_user_ids(text: str) -> list[str]:
    out = []
    for m in USER_ID_RE.finditer(text):
        u = m.group(0).lower()
        if u not in out:
            out.append(u)
    return out


def extract_resource_ids(text: str) -> list[str]:
    out = []
    for m in RESOURCE_ID_RE.finditer(text):
        r = m.group(0).lower()
        if r not in out:
            out.append(r)
    return out


def extract_hashes(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(0) for m in HASH_RE.finditer(text.lower())))


def extract_file_names(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(0).lower() for m in FILE_NAME_RE.finditer(text)))


# ---------------------------------------------------------------------------
# Field vocabulary for structured records
# ---------------------------------------------------------------------------

# Field names that hold direct identifiers, by kind.
EMAIL_FIELDS = {
    "email", "owner_email", "customer_email", "requester_email", "uploaded_by",
    "lookup_value", "matched_value", "subject_selector", "correlation_key",
    "lookup_key", "match_key", "subject_key", "scan_key", "owner_key",
    "subject_reference", "customer_reference", "subject_ref",
}
PHONE_FIELDS = {"phone", "owner_phone", "requester_phone", "customer_phone"}
NAME_FIELDS = {"name", "full_name", "display_name", "requester_name", "customer_name"}
HASH_FIELDS = {"email_hash"}
USER_REF_FIELDS = {
    "user_id", "customer_reference", "subject_reference", "subject_ref",
    "lookup_key", "correlation_key", "lookup_value", "subject_key",
}
# Fields that are *query keys*, not stored data: they link a record to a
# subject but are never reported as exposed PII.
QUERY_KEY_FIELDS = {
    "lookup_key", "match_key", "subject_key", "scan_key", "owner_key",
    "correlation_key", "lookup_value", "query",
}
FREE_TEXT_FIELDS = {"message_text", "message_excerpt", "detail", "details"}
FILE_FIELDS = {"file_name", "file", "archive_path", "archive_key", "object_key"}

# Collection / table name -> data category.
COLLECTION_CATEGORY: dict[str, str] = {
    "customer_profiles": "USER_PROFILE",
    "customer_profiles_primary": "USER_PROFILE",
    "customer_profiles_failover_replica": "USER_PROFILE",
    "profile_lookups": "USER_PROFILE",
    "customer_search_documents": "SEARCH_INDEX_ENTRY",
    "search_documents_primary": "SEARCH_INDEX_ENTRY",
    "index_queries": "SEARCH_INDEX_ENTRY",
    "customer_analytics_reports": "ANALYTICS_PROFILE",
    "customer_analytics_profiles": "ANALYTICS_PROFILE",
    "support_conversations": "SUPPORT_MESSAGE",
    "support_records": "SUPPORT_MESSAGE",
    "tickets": "SUPPORT_MESSAGE",
    "ticket_attachments": "SUPPORT_ATTACHMENT",
    "customer_export_jobs": "USER_EXPORT",
    "customer_exports": "USER_EXPORT",
    "exports": "USER_EXPORT",
    "connector_configurations": "DATA_FLOW",
    "connector_subscriptions": "DATA_FLOW",
    "connectors": "DATA_FLOW",
    "backup_catalog": "BACKUP_ARCHIVE",
    "backup_restore_entries": "BACKUP_ARCHIVE",
    "restore_entries": "BACKUP_ARCHIVE",
    "security_audit_events": "SECURITY_AUDIT_LOG",
    "security_audit_records": "SECURITY_AUDIT_LOG",
    "audit_records": "SECURITY_AUDIT_LOG",
    "deleted_customer_references": "ACCOUNT_TOMBSTONE",
    "retained_order_records": "LEGAL_HOLD_RECORD",
}

# Inventory SQL table -> owning system.
INVENTORY_TABLE_SYSTEM: dict[str, str] = {
    "customer_profiles": "account_service",
    "customer_search_documents": "search_service",
    "customer_analytics_profiles": "analytics_platform",
    "support_records": "support_platform",
    "customer_exports": "export_service",
    "connector_subscriptions": "integration_service",
    "backup_restore_entries": "backup_service",
    "security_audit_records": "security_service",
}


def category_for(collection: Optional[str], resource_id: Optional[str], system_id: Optional[str] = None) -> Optional[str]:
    if collection and collection in COLLECTION_CATEGORY:
        return COLLECTION_CATEGORY[collection]
    if resource_id:
        return default_category_for_resource(resource_id)
    return None


def first(values: Iterable[Any]) -> Any:
    for v in values:
        return v
    return None
