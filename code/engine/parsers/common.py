"""Helpers shared by the evidence parsers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..contracts import Observation
from ..util import category_for_resource, extract_identifiers

RESULT_TO_STATE = {
    "FOUND": "PRESENT", "PRESENT": "PRESENT", "IDENTIFIABLE": "PRESENT",
    "NOT_FOUND": "ABSENT", "ABSENT": "ABSENT", "DELETED": "ABSENT",
    "ANONYMIZED": "ANONYMIZED", "REDACTED": "REDACTED",
    "ACTIVE": "ACTIVE", "ENABLED": "ACTIVE", "DISABLED": "DISABLED", "BLOCKED": "BLOCKED",
}

COLLECTION_CATEGORY = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_reports": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support_conversations": ("support_platform", "SUPPORT_MESSAGE"),
    "ticket_attachments": ("support_platform", "SUPPORT_ATTACHMENT"),
    "customer_export_jobs": ("export_service", "USER_EXPORT"),
    "connector_configurations": ("integration_service", "DATA_FLOW"),
    "backup_catalog": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_events": ("security_service", "SECURITY_AUDIT_LOG"),
    "deleted_customer_references": ("identity_service", "ACCOUNT_TOMBSTONE"),
    "retained_order_records": ("legal_service", "LEGAL_HOLD_RECORD"),
}


def truthy(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no"):
            return False
    return None


def derive_state(category: str, record: Dict[str, Any], default: str = "PRESENT") -> str:
    """State of a record that physically exists in a snapshot."""
    if category == "DATA_FLOW":
        en = truthy(record.get("enabled"))
        if en is not None:
            return "ACTIVE" if en else "DISABLED"
    if category == "BACKUP_ARCHIVE":
        ra = truthy(record.get("restore_allowed"))
        if ra is not None:
            return "ACTIVE" if ra else "BLOCKED"
    return default


def make_obs(evidence_id: str, captured_at: str, record: Dict[str, Any], *, system_id: str = "", category: str = "",
             state: str = "", observed_at: str = "", source_format: str = "", locator: str = "",
             confidence: float = 1.0, extra_attrs: Optional[Dict[str, Any]] = None) -> Optional[Observation]:
    rid = str(record.get("resource_id") or "").strip()
    if not rid:
        return None
    sys_guess, cat_guess = category_for_resource(rid)
    system_id = system_id or sys_guess or ""
    category = category or cat_guess or ""
    ids = extract_identifiers({k: v for k, v in record.items() if k != "resource_id"})
    attrs = dict(record)
    if extra_attrs:
        attrs.update(extra_attrs)
    return Observation(
        evidence_id=evidence_id, captured_at=captured_at, system_id=system_id, resource_id=rid,
        data_category=category, state=state or derive_state(category, record),
        observed_at=observed_at or captured_at, emails=ids["emails"], user_refs=ids["user_refs"],
        hashes=ids["hashes"], phones=ids["phones"], names=ids["names"], attrs=attrs,
        source_format=source_format, locator=locator, confidence=confidence)
