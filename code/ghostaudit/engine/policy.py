"""Data category -> required end state, and the finding / remediation / verification operations for it."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..loaders import parse_ts
from ..models import Kind, Rule

# How a required treatment is expressed in steps.
TREATMENTS = {
    "DELETE": ("ABSENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    "REDACT": ("REDACTED", "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
    "ANONYMIZE": ("ANONYMIZED", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
    "RETAIN": ("PRESENT", None, None, "VERIFY_RECORD_PRESENT"),
    "BLOCK_RESTORE": ("BLOCKED", "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"),
    "DISABLE_FLOW": ("DISABLED", "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"),
}
FINDING_STATE = {
    "REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE",
}
STATE_OF_OP = {
    "DELETE_RECORD": "ABSENT", "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED",
    "BLOCK_RESTORE": "BLOCKED", "DISABLE_DATA_FLOW": "DISABLED",
    "VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT", "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

# Observed states that satisfy each treatment.
COMPLIANT = {
    "DELETE": {Kind.ABSENT},
    "REDACT": {Kind.REDACTED, Kind.ABSENT},
    "ANONYMIZE": {Kind.ANONYMIZED, Kind.ABSENT},
    "RETAIN": {Kind.RETAINED, Kind.PRESENT},
    "BLOCK_RESTORE": {Kind.RESTORE_BLOCKED, Kind.ABSENT},
    "DISABLE_FLOW": {Kind.FLOW_DISABLED, Kind.ABSENT},
}

DEFAULT_CATEGORY_BY_SYSTEM = {
    "account_service": "USER_PROFILE",
    "search_service": "SEARCH_INDEX_ENTRY",
    "support_platform": "SUPPORT_ATTACHMENT",  # a support copy with no message context is the subject's own record
    "analytics_platform": "ANALYTICS_PROFILE",
    "export_service": "USER_EXPORT",
    "security_service": "SECURITY_AUDIT_LOG",
    "legal_service": "LEGAL_HOLD_RECORD",
    "backup_service": "BACKUP_ARCHIVE",
    "identity_service": "ACCOUNT_TOMBSTONE",
    "marketing_platform": "MARKETING_PROFILE",
    "cache_service": "CACHE_ENTRY",
    "email_delivery_service": "EMAIL_DELIVERY_LOG",
    "object_storage": "SUPPORT_ATTACHMENT",
}


@dataclass(frozen=True)
class Decision:
    category: str
    treatment: str          # key of TREATMENTS
    rule_id: str
    reason: str


class Policy:
    def __init__(self, rules: list[Rule]):
        self.by_category = {r.data_category: r for r in rules}

    def decide(self, system_id: str, category: str | None, attrs: dict, audit_at: datetime) -> Decision:
        if system_id == "integration_service":
            return Decision("DATA_FLOW", "DISABLE_FLOW", "", "active sync can recreate deleted data")
        cat = category or DEFAULT_CATEGORY_BY_SYSTEM.get(system_id, "USER_PROFILE")
        rule = self.by_category.get(cat)
        action = rule.required_action if rule else "DELETE"
        rid = rule.rule_id if rule else ""
        if cat == "BACKUP_ARCHIVE":
            return Decision(cat, "BLOCK_RESTORE", rid, "retain archive, block restore of the subject's data")
        if action == "RETAIN":
            until = parse_ts(attrs.get("retention_until") or attrs.get("retained_until") or "")
            if until is not None and until < audit_at:
                return Decision(cat, "DELETE", rid, f"retention ended {until.isoformat()}")
            return Decision(cat, "RETAIN", rid, rule.condition if rule else "retain")
        if action in TREATMENTS:
            return Decision(cat, action, rid, rule.condition if rule else action)
        return Decision(cat, "DELETE", rid, "default delete")
