"""Planner: states -> ordered findings / remediation / verification steps."""
from .config import OP_ORDER, OP_STATE, PHASE_ORDER
from .policy import RuleBook
from .state import VIOLATION_KINDS

_FINDING_OP = {
    "VIOLATION_REMAINING": "REPORT_REMAINING_RECORD",
    "VIOLATION_EXPOSED": "REPORT_EXPOSED_PII",
    "VIOLATION_FLOW": "REPORT_ACTIVE_DATA_FLOW",
    "VIOLATION_RESTORE": "REPORT_RESTORE_RISK",
}


def _remediation_op(state):
    if state.verdict == "VIOLATION_REMAINING":
        return "DELETE_RECORD"
    if state.verdict == "VIOLATION_FLOW":
        return "DISABLE_DATA_FLOW"
    if state.verdict == "VIOLATION_RESTORE":
        return "BLOCK_RESTORE"
    treatment = RuleBook.treatment(state.category)
    if treatment == "ANONYMIZE":
        return "ANONYMIZE_RECORD"
    return "REDACT_RECORD"


def _verification_op(state):
    if state.verdict == "OK_ABSENT" or \
            (state.verdict == "VIOLATION_REMAINING"):
        return "VERIFY_RECORD_ABSENT"
    if state.verdict in ("VIOLATION_FLOW", "OK_DISABLED"):
        return "VERIFY_DATA_FLOW_DISABLED"
    if state.verdict in ("VIOLATION_RESTORE", "OK_BLOCKED"):
        return "VERIFY_RESTORE_BLOCKED"
    treatment = RuleBook.treatment(state.category)
    if treatment == "REDACT":
        return "VERIFY_RECORD_REDACTED"
    if treatment == "ANONYMIZE":
        return "VERIFY_RECORD_ANONYMIZED"
    if treatment == "RETAIN":
        return "VERIFY_RECORD_PRESENT"
    return "VERIFY_RECORD_ABSENT"


def _step(phase, state, operation, evidence_id):
    return {"step_no": 0, "phase": phase, "system_id": state.system_id,
            "resource_id": state.resource_id, "operation": operation,
            "state": OP_STATE[operation], "evidence_id": evidence_id}


def sort_steps(steps):
    steps = sorted(steps, key=lambda s: (PHASE_ORDER[s["phase"]],
                                         OP_ORDER[s["operation"]],
                                         s["system_id"], s["resource_id"]))
    for i, s in enumerate(steps, start=1):
        s["step_no"] = i
    return steps


def build_steps(intent, states):
    """Return (deletion_status, steps)."""
    if intent != "DELETE":
        return "NOT_APPLICABLE", []
    # Note: with no linked states there is also no violation, so the case
    # falls through to COMPLETE with an empty step list (nothing remains
    # in any eligible evidence and there is nothing to verify). This
    # matches the sample behaviour for fully-anonymized subjects.
    violations = [s for s in states if s.verdict in VIOLATION_KINDS]
    steps = []
    if not violations:
        for s in states:
            steps.append(_step("VERIFICATION", s, _verification_op(s),
                               s.evidence_id))
        return "COMPLETE", sort_steps(steps)
    for s in violations:
        steps.append(_step("FINDING", s, _FINDING_OP[s.verdict], s.evidence_id))
        steps.append(_step("REMEDIATION", s, _remediation_op(s), ""))
    for s in states:
        steps.append(_step("VERIFICATION", s, _verification_op(s), ""))
    # Dedupe identical (phase, system, resource, operation)
    seen, unique = set(), []
    for s in steps:
        key = (s["phase"], s["system_id"], s["resource_id"], s["operation"])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return "INCOMPLETE", sort_steps(unique)
