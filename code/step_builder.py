"""
step_builder.py — Stage 4: decision -> ordered output steps.

NOTE (P3): P4's version of this file was still the placeholder that returned
[], so output.csv would carry no steps. This implementation only numbers and
validates what policy_engine.decide() already ordered; P4 can replace it
as long as the same decision keys are read.

Reads decision["findings"], decision["remediation"], decision["verification"]
(each a list of {system_id, resource_id, operation, state, evidence_id}) and
returns steps with exactly the AGENTS.md §6.3 fields, numbered from 1 and
phased FINDING -> REMEDIATION -> VERIFICATION. Raises ValueError on any value
outside the contract so a bad decision can never reach output.csv.
"""
from __future__ import annotations

PHASE_OPS = {
    "FINDING": {"REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
                "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE"},
    "REMEDIATION": {"DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED", "DELETE_RECORD": "ABSENT",
                    "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED"},
    "VERIFICATION": {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
                     "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
                     "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED"},
}
_PHASE_KEYS = (("FINDING", "findings"), ("REMEDIATION", "remediation"), ("VERIFICATION", "verification"))
STEP_FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")


def build_steps(decision: dict) -> list[dict]:
    status = decision.get("deletion_status")
    if status == "NOT_APPLICABLE":
        return []
    steps: list[dict] = []
    for phase, key in _PHASE_KEYS:
        for item in decision.get(key, []) or []:
            op = item["operation"]
            if op not in PHASE_OPS[phase]:
                raise ValueError(f"{op!r} is not a {phase} operation")
            state = item.get("state") or PHASE_OPS[phase][op]
            if state != PHASE_OPS[phase][op]:
                raise ValueError(f"{op} must have state {PHASE_OPS[phase][op]}, got {state!r}")
            evidence_id = item.get("evidence_id") or ""
            future = status == "INCOMPLETE" and phase in ("REMEDIATION", "VERIFICATION")
            if future:
                evidence_id = ""  # proposed work: no evidence exists yet
            elif not evidence_id:
                raise ValueError(f"{phase} step {op} for {item['resource_id']} needs an evidence_id")
            steps.append({
                "step_no": len(steps) + 1,
                "phase": phase,
                "system_id": item["system_id"],
                "resource_id": item["resource_id"],
                "operation": op,
                "state": state,
                "evidence_id": evidence_id,
            })
    if status == "COMPLETE" and any(s["phase"] != "VERIFICATION" for s in steps):
        raise ValueError("a COMPLETE case may only contain verification steps")
    return steps
