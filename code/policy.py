"""Deterministic application of deletion policy conditions."""
from __future__ import annotations
CONDITION_KEYS={
 "SUPPORT_MESSAGE":"has_shared_context", "SECURITY_AUDIT_LOG":"within_retention_period",
 "LEGAL_HOLD_RECORD":"legal_hold_active", "BACKUP_ARCHIVE":"restore_can_be_blocked",
 "ACCOUNT_TOMBSTONE":"only_stable_id_needed", "SUPPORT_ATTACHMENT":"attachment_belongs_only_to_subject",
 "ANALYTICS_PROFILE":"record_still_attributable", "PRODUCT_TELEMETRY":"record_still_attributable",
 "EMAIL_DELIVERY_LOG":"log_contains_email",
}
FALSE_ACTION={
 "SUPPORT_MESSAGE":"DELETE", "SUPPORT_ATTACHMENT":"DELETE",
 "ANALYTICS_PROFILE":"RETAIN", "PRODUCT_TELEMETRY":"RETAIN",
 "EMAIL_DELIVERY_LOG":"RETAIN", "SECURITY_AUDIT_LOG":"RETAIN",
 "LEGAL_HOLD_RECORD":"RETAIN", "BACKUP_ARCHIVE":"RETAIN", "ACCOUNT_TOMBSTONE":"RETAIN",
}
def get_required_action(data_category: str, context: dict, deletion_rules: dict) -> str:
    rule=deletion_rules.get(data_category)
    if not rule: raise KeyError(f"Unknown data category: {data_category}")
    key=CONDITION_KEYS.get(data_category)
    if key is None or context.get(key,False): return rule["required_action"]
    return FALSE_ACTION.get(data_category,"RETAIN")
