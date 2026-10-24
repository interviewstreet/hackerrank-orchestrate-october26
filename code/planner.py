"""Deterministic evidence, remediation, and verification plan construction."""
from __future__ import annotations

OPERATION_STATE = {
    "FINDING": {"REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
                "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE"},
    "REMEDIATION": {"DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED",
                    "DELETE_RECORD": "ABSENT", "REDACT_RECORD": "REDACTED",
                    "ANONYMIZE_RECORD": "ANONYMIZED"},
    "VERIFICATION": {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
                     "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                     "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED"},
}
PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
OP_ORDER = {operation: index for phase in ("FINDING", "REMEDIATION", "VERIFICATION")
            for index, operation in enumerate(OPERATION_STATE[phase])}
VERIFY = {"DELETE": "VERIFY_RECORD_ABSENT", "REDACT": "VERIFY_RECORD_REDACTED",
          "ANONYMIZE": "VERIFY_RECORD_ANONYMIZED", "RETAIN": "VERIFY_RECORD_PRESENT",
          "DISABLE": "VERIFY_DATA_FLOW_DISABLED", "BLOCK_RESTORE": "VERIFY_RESTORE_BLOCKED"}
REMEDIATE = {"DELETE": "DELETE_RECORD", "REDACT": "REDACT_RECORD",
             "ANONYMIZE": "ANONYMIZE_RECORD", "DISABLE": "DISABLE_DATA_FLOW",
             "BLOCK_RESTORE": "BLOCK_RESTORE"}


def _step(phase, system, resource, operation, evidence=""):
    return {"step_no": 0, "phase": phase, "system_id": system or "unknown",
            "resource_id": resource or "unknown", "operation": operation,
            "state": OPERATION_STATE[phase][operation], "evidence_id": evidence or ""}


def plan_steps(decision_result, user_identity, evidence_index):
    del user_identity, evidence_index
    status = decision_result["status"]
    if status == "NOT_APPLICABLE":
        return []
    steps = []
    if status == "COMPLETE":
        for resource in decision_result.get("compliant_resources", []):
            steps.append(_step("VERIFICATION", resource.get("system_id"), resource.get("resource_id"),
                               VERIFY[resource["required_action"]],
                               resource.get("file_id") or resource.get("evidence_id")))
    else:
        # Current compliant resources still need post-remediation verification, but future
        # checks do not cite the evidence that established today's state.
        for resource in decision_result.get("compliant_resources", []):
            steps.append(_step("VERIFICATION", resource.get("system_id"), resource.get("resource_id"),
                               VERIFY[resource["required_action"]]))
        for finding in decision_result.get("findings", []):
            kind, action = finding.get("type"), finding.get("required_action", "DELETE")
            if kind == "active_data_flow":
                action = "DISABLE"
            elif kind == "restore_risk":
                action = "BLOCK_RESTORE"
            operation = {"active_data_flow": "REPORT_ACTIVE_DATA_FLOW",
                         "restore_risk": "REPORT_RESTORE_RISK",
                         "identity_unresolved": "REPORT_REMAINING_RECORD"}.get(
                             kind, "REPORT_REMAINING_RECORD" if action == "DELETE" else "REPORT_EXPOSED_PII")
            steps.append(_step("FINDING", finding.get("system_id"), finding.get("resource_id"), operation,
                               finding.get("file_id") or finding.get("evidence_id")))
            if kind == "identity_unresolved":
                continue
            remediation = REMEDIATE.get(action)
            if remediation:
                steps.append(_step("REMEDIATION", finding.get("system_id"), finding.get("resource_id"), remediation))
                steps.append(_step("VERIFICATION", finding.get("system_id"), finding.get("resource_id"), VERIFY[action]))
    # De-duplicate repeated observations while retaining the newest evidence-selected step.
    unique = {}
    for step in steps:
        unique[(step["phase"], step["system_id"], step["resource_id"], step["operation"])] = step
    steps = sorted(unique.values(), key=lambda step: (PHASE_ORDER[step["phase"]],
                   OP_ORDER[step["operation"]], step["system_id"], step["resource_id"]))
    for number, step in enumerate(steps, 1):
        step["step_no"] = number
    return steps
