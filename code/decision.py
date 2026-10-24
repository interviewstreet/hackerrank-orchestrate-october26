"""Evidence-first deletion completeness decision engine."""
from __future__ import annotations

from code.policy import get_required_action

EXPECTED = {
    "DELETE": {"ABSENT"}, "REDACT": {"REDACTED"},
    "ANONYMIZE": {"ANONYMIZED"}, "RETAIN": {"PRESENT", "ACTIVE", "TOMBSTONE"},
}


def _context(hit):
    record = hit.get("record", {})
    state = hit.get("state", "").upper()
    return {
        "has_shared_context": bool(record.get("shared_context", True)),
        "within_retention_period": bool(record.get("within_retention_period", True)),
        "legal_hold_active": bool(record.get("legal_hold_active", True)),
        "restore_can_be_blocked": bool(record.get("restore_can_be_blocked", True)),
        "only_stable_id_needed": state in {"REDACTED", "TOMBSTONE", "ANONYMIZED"},
        "attachment_belongs_only_to_subject": bool(record.get("attachment_belongs_only_to_subject", True)),
        "record_still_attributable": state not in {"ANONYMIZED", "ABSENT"},
        "log_contains_email": bool(record.get("email") or hit.get("identifiers_found")),
    }


def _latest(hits):
    return max(hits, key=lambda hit: (hit.get("captured_at", ""), hit.get("file_id", "")))


def decide(case, user_identity, evidence_index, system_activity_events, deletion_rules, classify_fn):
    intent = classify_fn(case["request_text"], case["case_id"])
    if intent == "NOT_APPLICABLE":
        return {"status": "NOT_APPLICABLE", "findings": [], "resources": [], "compliant_resources": []}
    if user_identity is None:
        return {"status": "INCOMPLETE", "findings": [{"type": "identity_unresolved",
                "system_id": "identity_service", "resource_id": case.get("email", ""),
                "evidence_id": ""}], "resources": [], "compliant_resources": []}

    findings, compliant, resources = [], [], []
    for resource_id, hits in evidence_index.items():
        hit = _latest(hits)
        category, state = hit["data_category"], hit.get("state", "").upper()
        resource = {**hit, "resource_id": resource_id}
        if category == "DATA_FLOW":
            resource["required_action"] = "DISABLE"
            if state == "DISABLED":
                compliant.append(resource)
            else:
                findings.append({**resource, "type": "active_data_flow"})
        elif category == "BACKUP_ARCHIVE":
            resource["required_action"] = "BLOCK_RESTORE"
            if state == "BLOCKED":
                compliant.append(resource)
            elif state == "ACTIVE" or hit.get("record", {}).get("restore_allowed") is True:
                findings.append({**resource, "type": "restore_risk"})
            else:
                # A retained archive is compliant only when subject restore is blocked.
                findings.append({**resource, "type": "restore_risk"})
        else:
            action = get_required_action(category, _context(hit), deletion_rules)
            resource["required_action"] = action
            if state in EXPECTED[action]:
                compliant.append(resource)
            else:
                findings.append({**resource, "type": "non_compliant_resource"})
        resources.append(resource)

    # Activity is useful for recreation risks only when identity resolution grounded it.
    deletion_times = [event.get("event_time", "") for event in system_activity_events
                      if event.get("event_type", "").upper() == "DELETE_RECORD"]
    after = max(deletion_times) if deletion_times else ""
    seen = {(finding.get("type"), finding.get("resource_id")) for finding in findings}
    for event in system_activity_events:
        kind = event.get("event_type", "").upper()
        if kind not in {"SYNC_RECORD", "INDEX_RECORD", "CREATE_EXPORT", "RESTORE_BACKUP"}:
            continue
        if event.get("event_time", "") <= after or event.get("reported_result", "").upper() in {"DISABLED", "FAILED", "BLOCKED"}:
            continue
        finding_type = "restore_risk" if kind == "RESTORE_BACKUP" else "active_data_flow"
        key = (finding_type, event.get("resource_id", ""))
        if key in seen:
            continue
        findings.append({"type": finding_type,
            "system_id": event.get("target_system") or event.get("source_system", "unknown"),
            "resource_id": event.get("resource_id", ""), "evidence_id": event.get("activity_id", ""),
            "state": "ACTIVE", "required_action": "BLOCK_RESTORE" if finding_type == "restore_risk" else "DISABLE"})
        seen.add(key)

    complete = not findings and len(compliant) == len(evidence_index)
    return {"status": "COMPLETE" if complete else "INCOMPLETE", "findings": findings,
            "resources": resources, "compliant_resources": compliant}
