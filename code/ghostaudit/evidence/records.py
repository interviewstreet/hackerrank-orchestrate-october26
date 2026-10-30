"""Shared record model: every extractor yields RawRecords, and `to_observation` turns one into facts.

Extractors only flatten their format into a dict of fields. All the interpretation (which system, which
identifiers, what state) lives here so that the SQL, JSON, TXT, log and visual paths agree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from ..identity import norm_identifier
from ..loaders import EMAIL_RE, parse_ts
from ..models import Kind, Observation

PREFIX_SYSTEM = [
    ("account_", "account_service"),
    ("search_", "search_service"),
    ("support_", "support_platform"),
    ("analytics_", "analytics_platform"),
    ("export_", "export_service"),
    ("data_flow_", "integration_service"),
    ("backup_", "backup_service"),
    ("audit_record_", "security_service"),
    ("tombstone_", "identity_service"),
    ("legal_hold_", "legal_service"),
    ("marketing_", "marketing_platform"),
    ("cache_", "cache_service"),
    ("email_delivery_", "email_delivery_service"),
    ("object_", "object_storage"),
]
RESOURCE_RE = re.compile(r"\b(?:" + "|".join(p for p, _ in PREFIX_SYSTEM) + r")\d+\b")
USER_RE = re.compile(r"\buser_\d+\b", re.I)
HASH_RE = re.compile(r"(?<![:0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
PHONE_RE = re.compile(r"^\+?[\d][\d\s().\-]{6,}\d$")

NULLS = {"", "null", "none", "nil", "[redacted]", "redacted", "n/a", "no direct identifier", "-"}

# Fields that hold a direct identifier *inside* the record (exposure), by identifier type.
DIRECT_FIELDS = {
    "email": "email", "requester_email": "email", "owner_email": "email", "customer_email": "email",
    "uploaded_by": "email", "matched_value": None, "subject_selector": None,
    "phone": "phone", "requester_phone": "phone", "owner_phone": "phone",
    "email_hash": "email_hash",
    "name": "name", "full_name": "name", "display_name": "name", "requester_name": "name",
    "first_name": "name", "last_name": "name", "given_name": "name", "family_name": "name", "surname": "name",
    "middle_name": "name",
}
NAME_FIELDS = {k for k, v in DIRECT_FIELDS.items() if v == "name"}
# Fields that only say who the record was looked up for / references (link, not exposure).
REFERENCE_FIELDS = {
    "lookup_key", "match_key", "subject_key", "subject_ref", "scan_key", "owner_key", "correlation_key",
    "subject_reference", "customer_reference", "user_id", "lookup_value", "query", "subject",
}
# For resource ids outside PREFIX_SYSTEM: words in the table / collection / log event -> data category (first match)
COLLECTION_CATEGORY = [
    (("tombstone",), "ACCOUNT_TOMBSTONE"),
    (("email_delivery", "delivery_log", "notification"), "EMAIL_DELIVERY_LOG"),
    (("security_audit", "audit_record", "audit_event"), "SECURITY_AUDIT_LOG"),
    (("legal",), "LEGAL_HOLD_RECORD"),
    (("backup", "archive"), "BACKUP_ARCHIVE"),
    (("attachment",), "SUPPORT_ATTACHMENT"),
    (("support", "ticket", "conversation"), "SUPPORT_MESSAGE"),
    (("search", "index"), "SEARCH_INDEX_ENTRY"),
    (("marketing", "newsletter"), "MARKETING_PROFILE"),
    (("telemetry",), "PRODUCT_TELEMETRY"),
    (("analytics",), "ANALYTICS_PROFILE"),
    (("export",), "USER_EXPORT"),
    (("cache",), "CACHE_ENTRY"),
    (("profile", "account", "customer"), "USER_PROFILE"),
]
# Reference fields whose value is the stable internal user id, whatever its naming scheme.
USER_REFERENCE_FIELDS = {"user_id", "customer_reference", "subject_reference", "subject_ref"}
ID_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*[_-][A-Za-z0-9_-]+")
TEXT_FIELDS = {"message_text", "message_excerpt", "message", "note", "details"}


def system_for(resource_id: str, hint: str | None = None) -> str:
    for prefix, system in PREFIX_SYSTEM:
        if resource_id.startswith(prefix):
            return system
    return hint or "unknown"


def is_null(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip().lower() in NULLS)


def truthy(v) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "allowed", "enabled", "active"}:
        return True
    if s in {"0", "false", "no", "n", "denied", "deny", "disabled", "blocked", "stopped"}:
        return False
    return None


def classify_value(v: str) -> tuple[str, str] | None:
    """Type an identifier-bearing value by its shape."""
    if is_null(v):
        return None
    s = str(v).strip()
    if EMAIL_RE.fullmatch(s):
        return norm_identifier("email", s)
    if USER_RE.fullmatch(s):
        return norm_identifier("user_id", s)
    if re.fullmatch(r"[0-9a-fA-F]{64}", s):
        return norm_identifier("email_hash", s)
    if PHONE_RE.match(s) and sum(c.isdigit() for c in s) >= 7:
        return norm_identifier("phone", s)
    return None


@dataclass
class RawRecord:
    evidence_id: str
    captured_at: datetime
    resource_id: str
    fields: dict
    observed_at: datetime | None = None
    system_hint: str | None = None
    location: str = ""
    collection: str = ""
    source_format: str = ""
    explicit: bool = True
    extra_ids: set = field(default_factory=set)


def extract_identifiers(fields: dict) -> tuple[set, set, set]:
    """Return (all identifiers, direct-exposure identifiers, referenced resource ids)."""
    ids: set = set()
    direct: set = set()
    refs: set = set()
    for k, v in fields.items():
        if v is None or isinstance(v, (dict, list)):
            continue
        key = k.lower()
        sval = str(v)
        if is_null(sval):
            continue
        if key in DIRECT_FIELDS:
            typed = DIRECT_FIELDS[key]
            n = norm_identifier(typed, sval) if typed else classify_value(sval)
            if typed == "email" and n and not EMAIL_RE.fullmatch(sval.strip()):
                n = classify_value(sval)
            if n:
                ids.add(n)
                direct.add(n)
            continue
        if key in REFERENCE_FIELDS:
            n = classify_value(sval)
            if n is None and key in USER_REFERENCE_FIELDS and ID_TOKEN_RE.fullmatch(sval.strip()) \
                    and not RESOURCE_RE.fullmatch(sval.strip()):
                n = norm_identifier("user_id", sval)  # any stable internal id, not only "user_<n>"
            if n:
                ids.add(n)
            for rid in RESOURCE_RE.findall(sval):
                refs.add(rid)
            continue
        if key in TEXT_FIELDS:
            for e in EMAIL_RE.findall(sval):
                n = norm_identifier("email", e)
                ids.add(n)
                direct.add(n)
            continue
        if key.endswith("_email") or key.endswith("email"):
            n = classify_value(sval)
            if n:
                ids.add(n)
                direct.add(n)
    return ids, direct, refs


def _num(v) -> int | None:
    try:
        return int(str(v).strip().strip('"'))
    except (TypeError, ValueError):
        return None


def category_hint(resource_id: str, f: dict, collection: str) -> str | None:
    rt = str(f.get("record_type") or f.get("category") or "").upper()
    if rt and rt not in {"NONE", "NULL"}:
        if rt == "DATA_FLOW":
            return None
        return rt
    if str(f.get("account_status") or "").strip().upper() == "TOMBSTONE":
        return "ACCOUNT_TOMBSTONE"
    col = (collection or "").lower()
    ev = str(f.get("event") or "").lower()
    if resource_id.startswith("support_"):
        if "attachment" in col or "attachment" in ev or f.get("file") or f.get("file_name") \
                or str(f.get("storage_class", "")).lower() == "ticket_attachment":
            return "SUPPORT_ATTACHMENT"
        if "message" in ev or "conversation" in col or "support_records" in col or "ticket" in ev \
                or any(k in f for k in ("message_text", "message_excerpt")):
            return "SUPPORT_MESSAGE"
        return None
    if resource_id.startswith("analytics_"):
        if "email_opt_in" in f or "contact" in ev or "marketing" in col:
            return "MARKETING_PROFILE"
        return "ANALYTICS_PROFILE"
    if resource_id.startswith("account_"):
        return "USER_PROFILE"
    if resource_id.startswith("search_"):
        return "SEARCH_INDEX_ENTRY"
    if resource_id.startswith("export_"):
        return "USER_EXPORT"
    if resource_id.startswith("audit_record_"):
        return "SECURITY_AUDIT_LOG"
    if resource_id.startswith("legal_hold_"):
        return "LEGAL_HOLD_RECORD"
    if resource_id.startswith("backup_"):
        return "BACKUP_ARCHIVE"
    if resource_id.startswith("tombstone_"):
        return "ACCOUNT_TOMBSTONE"
    if resource_id.startswith("marketing_"):
        return "MARKETING_PROFILE"
    if resource_id.startswith("cache_"):
        return "CACHE_ENTRY"
    if resource_id.startswith("email_delivery_"):
        return "EMAIL_DELIVERY_LOG"
    if system_for(resource_id) == "unknown":
        # an id outside the known prefixes: the table / collection / log event names what the record is
        where = f"{col} {ev}"
        for words, cat in COLLECTION_CATEGORY:
            if any(w in where for w in words):
                return cat
    return None


def classify_state(resource_id: str, system: str, f: dict, direct: set) -> Kind | None:
    """Decide what a record says about its resource. None = no state (pure link)."""
    result = str(f.get("result") or f.get("status") or "").strip().strip('"').upper()
    status_code = _num(f.get("status_code") or f.get("http_status"))
    rows = _num(f.get("rows"))
    total = _num(f.get("total_hits") if f.get("total_hits") is not None else f.get("total"))

    absent = (
        result in {"NOT_FOUND", "MISS", "ABSENT", "DELETED_CONFIRMED"}
        or status_code == 404 or rows == 0 or total == 0
        or str(f.get("profile", "x")).lower() in {"none", "null"}
        or truthy(f.get("archive_present")) is False and system != "backup_service"
        or truthy(f.get("available")) is False and system == "export_service"
    )
    if absent:
        return Kind.ABSENT

    if system == "integration_service":
        if result in {"ACTIVE"}:
            return Kind.FLOW_ACTIVE
        if result in {"DISABLED", "STOPPED"}:
            return Kind.FLOW_DISABLED
        en = truthy(f.get("enabled"))
        if en is None and f.get("scheduler_registered") is not None:
            en = truthy(f.get("scheduler_registered"))
        if en is True:
            return Kind.FLOW_ACTIVE
        if en is False:
            return Kind.FLOW_DISABLED
        return None

    if system == "backup_service":
        if result in {"ACTIVE", "RESTORABLE", "ALLOWED"}:
            return Kind.RESTORE_ALLOWED
        if result in {"BLOCKED", "DENIED"}:
            return Kind.RESTORE_BLOCKED
        ra = truthy(f.get("restore_allowed"))
        if ra is None and f.get("eligible") is not None:
            ra = truthy(f.get("eligible")) and not truthy(f.get("deletion_block"))
        if ra is None and f.get("decision") is not None:
            ra = truthy(f.get("decision"))
        if ra is True:
            return Kind.RESTORE_ALLOWED
        if ra is False:
            return Kind.RESTORE_BLOCKED
        if result in {"FOUND", "PRESENT", "HIT"} or (rows or 0) > 0 or status_code == 200:
            # the archive is shown to exist and nothing shows its restore blocked: an unproven block is a restore
            # path ("COMPLETE only when no restore path can recreate the data")
            return Kind.RESTORE_ALLOWED
        return None

    if system in {"security_service", "legal_service"}:
        return Kind.RETAINED

    exposed = bool(direct)
    if result == "IDENTIFIABLE":
        exposed = True
    if result in {"ANONYMIZED"}:
        return Kind.ANONYMIZED
    if result in {"REDACTED"}:
        return Kind.REDACTED
    di = _num(f.get("direct_identifiers"))
    if di is not None:
        exposed = di > 0

    if system == "analytics_platform":
        attributable = exposed or any(
            not is_null(f.get(k)) and classify_value(str(f.get(k))) for k in ("user_id", "customer_reference")
        )
        if "email_opt_in" in f:
            return Kind.PRESENT
        return Kind.PRESENT if attributable else Kind.ANONYMIZED

    if system in {"identity_service"} or str(f.get("account_status") or "").strip().upper() == "TOMBSTONE":
        return Kind.PRESENT if exposed else Kind.REDACTED

    if system == "support_platform":
        cat = category_hint(resource_id, f, "")
        msg = str(f.get("message_text") or "")
        if cat == "SUPPORT_ATTACHMENT" or result == "FOUND" or rows:
            return Kind.PRESENT if (exposed or cat == "SUPPORT_ATTACHMENT" or result == "FOUND" or rows) else Kind.REDACTED
        if exposed:
            return Kind.PRESENT
        if msg.strip().upper() == "[REDACTED]" or any(k in f for k in ("requester_email", "requester_name", "message_text", "message_excerpt")):
            return Kind.REDACTED
        return None

    # account, search, export, marketing, cache, email logs, objects: existence is what matters
    exists = (
        result in {"FOUND", "HIT", "PRESENT", "IDENTIFIABLE"} or status_code == 200 or (rows or 0) > 0
        or (total or 0) > 0 or exposed or truthy(f.get("available")) is True
    )
    if exists:
        return Kind.PRESENT
    return None


def to_observation(raw: RawRecord) -> Observation | None:
    f = raw.fields
    system = system_for(raw.resource_id, raw.system_hint)
    ids, direct, refs = extract_identifiers(f)
    ids |= raw.extra_ids
    refs.discard(raw.resource_id)
    kind = classify_state(raw.resource_id, system, f, direct) if raw.explicit else Kind.ABSENT
    if kind is None:
        kind = Kind.LINK
    attrs = {k: str(v) for k, v in f.items() if not isinstance(v, (dict, list)) and v is not None}
    if refs:
        attrs["_refs"] = " ".join(sorted(refs))
    if direct:
        attrs["_direct"] = " ".join(sorted(f"{a}:{b}" for a, b in direct))
    observed = raw.observed_at or parse_ts(str(f.get("observed_at") or f.get("recorded_at") or "")) or raw.captured_at
    return Observation(
        evidence_id=raw.evidence_id,
        observed_at=observed,
        captured_at=raw.captured_at,
        system_id=system,
        resource_id=raw.resource_id,
        kind=kind,
        category=category_hint(raw.resource_id, f, raw.collection),
        identifiers=frozenset(ids),
        location=raw.location,
        attrs=attrs,
        explicit=raw.explicit,
    )
