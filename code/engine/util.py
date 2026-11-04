"""Small shared helpers: identifier extraction and timestamp handling."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
USER_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])")

PHONE_KEYS = {"phone", "requester_phone", "owner_phone"}
NAME_KEYS = {"name", "full_name", "display_name", "requester_name"}
SKIP_KEYS = {"integrity_seal"}

RESOURCE_PREFIX_CATEGORY = [
    ("account_", "account_service", "USER_PROFILE"),
    ("search_", "search_service", "SEARCH_INDEX_ENTRY"),
    ("analytics_", "analytics_platform", "ANALYTICS_PROFILE"),
    ("support_", "support_platform", "SUPPORT_MESSAGE"),
    ("export_", "export_service", "USER_EXPORT"),
    ("data_flow_", "integration_service", "DATA_FLOW"),
    ("backup_", "backup_service", "BACKUP_ARCHIVE"),
    ("audit_record_", "security_service", "SECURITY_AUDIT_LOG"),
    ("tombstone_", "identity_service", "ACCOUNT_TOMBSTONE"),
    ("legal_hold_", "legal_service", "LEGAL_HOLD_RECORD"),
    ("marketing_", "marketing_platform", "MARKETING_PROFILE"),
    ("cache_", "cache_service", "CACHE_ENTRY"),
]
RESOURCE_ID_RE = re.compile(
    r"\b(?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|legal_hold|marketing|object|cache)_\d+\b")


def category_for_resource(resource_id: str):
    """Return (system_id, data_category) inferred from the resource-id prefix, or (None, None)."""
    for prefix, system, cat in RESOURCE_PREFIX_CATEGORY:
        if resource_id.startswith(prefix):
            return system, cat
    return None, None


def extract_identifiers(obj: Any) -> Dict[str, List[str]]:
    """Walk a record and collect emails, user refs, email hashes, phones and names (deduplicated, ordered)."""
    out: Dict[str, List[str]] = {"emails": [], "user_refs": [], "hashes": [], "phones": [], "names": []}

    def add(kind: str, value: str):
        if value and value not in out[kind]:
            out[kind].append(value)

    def walk(node: Any, key: str = ""):
        if key in SKIP_KEYS:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            text = node.strip()
            if not text or text.lower() in ("null", "none", "[redacted]"):
                return
            for m in EMAIL_RE.findall(text):
                add("emails", m.lower())
            for m in USER_RE.findall(text):
                add("user_refs", m)
            for m in HASH_RE.findall(text.lower()):
                add("hashes", m)
            if key in PHONE_KEYS:
                add("phones", text)
            if key in NAME_KEYS:
                add("names", text)

    walk(obj)
    return out


def unique(seq: Iterable) -> list:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
