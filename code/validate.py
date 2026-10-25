"""Submission contract validation."""
from __future__ import annotations

import json
import re

from code.planner import OPERATION_STATE, OP_ORDER

STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
PHASES = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
STEP_FIELDS = {
    "step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"
}
RESOURCE_ID_RE = re.compile(
    r"^(?:account|search|support|analytics|export|backup|data_flow|audit_record|"
    r"tombstone|cache|marketing|email_delivery|object|telemetry|legal)_"
    r"[A-Za-z0-9.-]*\d[A-Za-z0-9.-]*$",
    re.IGNORECASE,
)


def validate_output(rows: list) -> list[str]:
    errors = []
    seen_cases = set()
    for index, row in enumerate(rows, 1):
        case_id = row.get("case_id", "")
        prefix = f"row {index} ({case_id}):"
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix} missing case_id")
        elif case_id in seen_cases:
            errors.append(f"{prefix} duplicate case_id")
        seen_cases.add(case_id)

        status = row.get("deletion_status")
        if status not in STATUSES:
            errors.append(f"{prefix} invalid deletion_status")
        try:
            steps = json.loads(row.get("steps_json", ""))
        except (json.JSONDecodeError, TypeError):
            errors.append(f"{prefix} steps_json is not valid JSON")
            continue
        if not isinstance(steps, list):
            errors.append(f"{prefix} steps_json must be an array")
            continue
        if status == "NOT_APPLICABLE" and steps:
            errors.append(f"{prefix} NOT_APPLICABLE steps_json must be []")
        if status == "COMPLETE" and not steps:
            errors.append(f"{prefix} COMPLETE requires at least one evidence-backed verification")
        if status == "COMPLETE" and any(
            step.get("phase") != "VERIFICATION" for step in steps if isinstance(step, dict)
        ):
            errors.append(f"{prefix} COMPLETE must contain verification steps only")
        if status == "INCOMPLETE" and not any(
            isinstance(step, dict) and step.get("phase") == "FINDING" for step in steps
        ):
            errors.append(f"{prefix} INCOMPLETE must contain at least one FINDING")

        expected_order = sorted(
            (step for step in steps if isinstance(step, dict)),
            key=lambda step: (
                PHASES.get(step.get("phase"), 99),
                OP_ORDER.get(step.get("operation"), 99),
                str(step.get("system_id", "")),
                str(step.get("resource_id", "")),
            ),
        )
        if all(isinstance(step, dict) for step in steps) and steps != expected_order:
            errors.append(f"{prefix} steps are not in canonical operation/system/resource order")

        last_phase = -1
        for position, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                errors.append(f"{prefix} step {position} is not an object")
                continue
            if set(step) != STEP_FIELDS:
                errors.append(f"{prefix} step {position} must have exactly 7 fields")
            number = step.get("step_no")
            if isinstance(number, bool) or not isinstance(number, int) or number != position:
                errors.append(f"{prefix} step_no gap at step {position}")
            phase = step.get("phase")
            if phase not in PHASES:
                errors.append(f"{prefix} invalid phase at step {position}")
                phase_order = -1
            else:
                phase_order = PHASES[phase]
            if phase_order < last_phase:
                errors.append(f"{prefix} wrong phase order at step {position}")
            last_phase = max(last_phase, phase_order)
            if OPERATION_STATE.get(phase, {}).get(step.get("operation")) != step.get("state"):
                errors.append(f"{prefix} invalid operation+state pair at step {position}")
            for field in ("system_id", "resource_id"):
                if not isinstance(step.get(field), str) or not step.get(field):
                    errors.append(f"{prefix} {field} required at step {position}")
            resource_id = step.get("resource_id", "")
            if isinstance(resource_id, str) and resource_id and not RESOURCE_ID_RE.fullmatch(resource_id):
                errors.append(f"{prefix} invalid resource_id format at step {position}")
            evidence = step.get("evidence_id")
            if not isinstance(evidence, str):
                errors.append(f"{prefix} evidence_id must be a string at step {position}")
            elif phase == "REMEDIATION" and evidence != "":
                errors.append(f"{prefix} non-empty evidence_id on REMEDIATION step {position}")
            elif status == "INCOMPLETE" and phase == "VERIFICATION" and evidence != "":
                errors.append(f"{prefix} non-empty evidence_id on future VERIFICATION step {position}")
            elif (phase == "FINDING" or (status == "COMPLETE" and phase == "VERIFICATION")) and not evidence:
                errors.append(f"{prefix} evidence_id required at step {position}")
    return errors


def validate_row_count(rows: list, expected=518) -> list[str]:
    errors = []
    if len(rows) != expected:
        errors.append(f"expected {expected} rows, got {len(rows)}")
    case_ids = [row.get("case_id", "") for row in rows]
    if len(case_ids) != len(set(case_ids)):
        errors.append("rows contain duplicate case_id values")
    if case_ids != sorted(case_ids):
        errors.append("rows are not sorted by case_id")
    return errors


def validate_case_coverage(rows: list, expected_case_ids) -> list[str]:
    """Require exactly one output for every input case, not merely the same row count."""
    actual = {row.get("case_id", "") for row in rows}
    expected = set(expected_case_ids)
    errors = []
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        preview = ", ".join(missing[:10])
        errors.append(f"missing case_id values: {preview}" + (" ..." if len(missing) > 10 else ""))
    if unexpected:
        preview = ", ".join(unexpected[:10])
        errors.append(f"unexpected case_id values: {preview}" + (" ..." if len(unexpected) > 10 else ""))
    return errors
