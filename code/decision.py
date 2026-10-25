"""Evidence-first deletion completeness decision engine."""
from __future__ import annotations

from code.policy import get_required_action

EXPECTED = {
    "DELETE": {"ABSENT"}, "REDACT": {"REDACTED"},
    "ANONYMIZE": {"ANONYMIZED"},
    "RETAIN": {"PRESENT", "ACTIVE", "TOMBSTONE", "REDACTED", "ANONYMIZED"},
}


def _boolean(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    folded = str(value).strip().casefold()
    if folded in {"true", "1", "yes", "active", "enabled"}:
        return True
    if folded in {"false", "0", "no", "inactive", "disabled"}:
        return False
    return default


def _context(hit):
    record = hit.get("record", {})
    state = hit.get("state", "").upper()
    return {
        "has_shared_context": _boolean(record.get("shared_context")),
        "within_retention_period": _boolean(record.get("within_retention_period")),
        "legal_hold_active": _boolean(record.get("legal_hold_active")),
        "restore_can_be_blocked": _boolean(record.get("restore_can_be_blocked")),
        "only_stable_id_needed": state in {"REDACTED", "TOMBSTONE", "ANONYMIZED"},
        "attachment_belongs_only_to_subject": _boolean(record.get("attachment_belongs_only_to_subject")),
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
        raise ValueError(f"{case['case_id']}: identity could not be resolved")
    if not evidence_index:
        raise ValueError(
            f"{case['case_id']}: no eligible evidence proves deletion state at audit_at"
        )

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
    deletion_by_resource = {}
    for event in system_activity_events:
        if event.get("event_type", "").upper() == "DELETE_RECORD":
            resource_id = event.get("resource_id", "")
            deletion_by_resource[resource_id] = max(
                deletion_by_resource.get(resource_id, ""), event.get("event_time", "")
            )
    seen = {(finding.get("type"), finding.get("resource_id")) for finding in findings}
    for event in system_activity_events:
        kind = event.get("event_type", "").upper()
        if kind not in {"SYNC_RECORD", "INDEX_RECORD", "CREATE_EXPORT", "RESTORE_BACKUP"}:
            continue
        resource_id = event.get("resource_id", "")
        if event.get("event_time", "") < case.get("requested_at", ""):
            continue
        if event.get("event_time", "") <= deletion_by_resource.get(resource_id, ""):
            continue
        if event.get("reported_result", "").upper() in {"DISABLED", "FAILED", "BLOCKED"}:
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
    verification_resources = []
    if not complete:
        observed = set(evidence_index)
        for event in user_identity.get("workflow_resources", []):
            resource_id = event.get("resource_id", "")
            if not resource_id or resource_id in observed:
                continue
            # Workflow claims ground which resource was acted on, but never prove its
            # final state.  For an already-incomplete case they support only a future,
            # uncited verification check after remediation.
            verification_resources.append({
                "system_id": event.get("target_system", "unknown"),
                "resource_id": resource_id,
                "required_action": event.get("required_action", "DELETE"),
            })
    return {"status": "COMPLETE" if complete else "INCOMPLETE", "findings": findings,
            "resources": resources, "compliant_resources": compliant,
            "verification_resources": verification_resources}
