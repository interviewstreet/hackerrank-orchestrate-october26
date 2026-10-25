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
        # Defaults are condition-specific. Missing retention/hold facts preserve data;
        # missing destructive authorization never permits deleting a shared attachment.
        "has_shared_context": _boolean(record.get("shared_context"), True),
        "within_retention_period": _boolean(record.get("within_retention_period"), True),
        "legal_hold_active": _boolean(record.get("legal_hold_active"), True),
        # Supplied backup-control records are actionable unless they explicitly state
        # that subject-level restore cannot be blocked.
        "restore_can_be_blocked": _boolean(record.get("restore_can_be_blocked"), True),
        # A tombstone's stable internal reference is the reason for retaining it; the
        # presence of direct PII determines compliance, not whether retention applies.
        "only_stable_id_needed": bool(
            record.get("user_id") or record.get("subject_reference")
            or record.get("customer_reference")
        ),
        "attachment_belongs_only_to_subject": _boolean(
            record.get("attachment_belongs_only_to_subject"), False
        ),
        "record_still_attributable": state not in {"ANONYMIZED", "ABSENT"},
        "log_contains_email": bool(record.get("email") or any(
            "@" in str(value) for value in hit.get("identifiers_found", [])
        )),
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
            policy_action = get_required_action(category, _context(hit), deletion_rules)
            if state == "BLOCKED":
                resource["required_action"] = "BLOCK_RESTORE"
                compliant.append(resource)
            elif policy_action == "DELETE":
                resource["required_action"] = "DELETE"
                if state == "ABSENT":
                    compliant.append(resource)
                else:
                    findings.append({**resource, "type": "non_compliant_resource"})
            else:
                # Retention is allowed only after subject-specific restore is blocked.
                resource["required_action"] = "BLOCK_RESTORE"
                findings.append({**resource, "type": "restore_risk"})
        else:
            action = get_required_action(category, _context(hit), deletion_rules)
            # When conditional anonymization/redaction has already succeeded, preserve
            # that evidence-backed treatment in verification rather than weakening the
            # check to generic presence merely because the trigger is now false.
            if state == "ANONYMIZED" and category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"}:
                action = "ANONYMIZE"
            elif state == "REDACTED" and category == "ACCOUNT_TOMBSTONE":
                action = "REDACT"
            resource["required_action"] = action
            if state in EXPECTED[action]:
                compliant.append(resource)
            else:
                findings.append({**resource, "type": "non_compliant_resource"})
        resources.append(resource)

    # Activity can identify a recreation risk, but operation outcomes and deletion
    # claims never prove the risk was removed. Only authoritative evidence state does.
    disabled_resources = {
        resource.get("resource_id", "") for resource in compliant
        if resource.get("state", "").upper() in {"DISABLED", "BLOCKED"}
    }
    resolved_at = {
        resource.get("resource_id", ""): resource.get("captured_at", "")
        for resource in compliant
        if resource.get("state", "").upper() in {
            "ABSENT", "ANONYMIZED", "REDACTED", "DISABLED", "BLOCKED"
        }
    }
    seen = {(finding.get("type"), finding.get("resource_id")) for finding in findings}
    for event in system_activity_events:
        kind = event.get("event_type", "").upper()
        if kind not in {"SYNC_RECORD", "INDEX_RECORD", "CREATE_EXPORT", "RESTORE_BACKUP"}:
            continue
        resource_id = event.get("resource_id", "")
        if event.get("event_time", "") < case.get("requested_at", ""):
            continue
        if resource_id in disabled_resources:
            continue
        if resolved_at.get(resource_id, "") >= event.get("event_time", ""):
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
