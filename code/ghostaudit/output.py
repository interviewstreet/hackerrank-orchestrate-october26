"""Step ordering, serialization and contract validation for output.csv (SPEC §4.3)."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .loaders import natural_case_key
from .models import CaseResult, Step

PHASES = ["FINDING", "REMEDIATION", "VERIFICATION"]

# Operation order follows the problem-statement tables; the state each operation must carry.
OPERATIONS: dict[str, list[tuple[str, str]]] = {
    "FINDING": [
        ("REPORT_REMAINING_RECORD", "PRESENT"),
        ("REPORT_EXPOSED_PII", "PRESENT"),
        ("REPORT_ACTIVE_DATA_FLOW", "ACTIVE"),
        ("REPORT_RESTORE_RISK", "ACTIVE"),
    ],
    "REMEDIATION": [
        ("DISABLE_DATA_FLOW", "DISABLED"),
        ("BLOCK_RESTORE", "BLOCKED"),
        ("DELETE_RECORD", "ABSENT"),
        ("REDACT_RECORD", "REDACTED"),
        ("ANONYMIZE_RECORD", "ANONYMIZED"),
    ],
    "VERIFICATION": [
        ("VERIFY_RECORD_ABSENT", "ABSENT"),
        ("VERIFY_RECORD_PRESENT", "PRESENT"),
        ("VERIFY_RECORD_REDACTED", "REDACTED"),
        ("VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"),
        ("VERIFY_DATA_FLOW_DISABLED", "DISABLED"),
        ("VERIFY_RESTORE_BLOCKED", "BLOCKED"),
    ],
}
OP_STATE = {op: st for ops in OPERATIONS.values() for op, st in ops}
OP_PHASE = {op: ph for ph, ops in OPERATIONS.items() for op, _ in ops}
OP_INDEX = {op: i for ops in OPERATIONS.values() for i, (op, _) in enumerate(ops)}
STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
HEADER = ["case_id", "deletion_status", "steps_json"]
STEP_KEYS = ["step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"]


def step_sort_key(step: Step):
    """Phase, then operation index from the contract tables, then system_id, then resource_id."""
    return (PHASES.index(step.phase), OP_INDEX[step.operation], step.system_id, step.resource_id)


def order_steps(steps: list[Step]) -> list[Step]:
    unique = list(dict.fromkeys(steps))
    return sorted(unique, key=step_sort_key)


def steps_to_json(steps: list[Step]) -> str:
    payload = []
    for i, s in enumerate(order_steps(steps), start=1):
        payload.append({
            "step_no": i,
            "phase": s.phase,
            "system_id": s.system_id,
            "resource_id": s.resource_id,
            "operation": s.operation,
            "state": s.state,
            "evidence_id": s.evidence_id,
        })
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def validate_row(case_id: str, status: str, steps_json: str) -> list[str]:
    """Return a list of contract violations for one output row (empty when valid)."""
    errors: list[str] = []
    if status not in STATUSES:
        errors.append(f"{case_id}: bad status {status!r}")
    try:
        steps = json.loads(steps_json)
    except json.JSONDecodeError as exc:
        return errors + [f"{case_id}: invalid JSON ({exc})"]
    if not isinstance(steps, list):
        return errors + [f"{case_id}: steps_json is not an array"]
    if status == "NOT_APPLICABLE" and steps:
        errors.append(f"{case_id}: NOT_APPLICABLE must have []")
    if status == "INCOMPLETE" and not steps:
        errors.append(f"{case_id}: INCOMPLETE must have steps")
    last_phase = 0
    for i, s in enumerate(steps, start=1):
        if not isinstance(s, dict) or sorted(s.keys()) != sorted(STEP_KEYS):
            errors.append(f"{case_id}: step {i} has wrong keys")
            continue
        if s["step_no"] != i:
            errors.append(f"{case_id}: step_no {s['step_no']} != {i}")
        op = s["operation"]
        if op not in OP_STATE:
            errors.append(f"{case_id}: unknown operation {op}")
            continue
        if OP_PHASE[op] != s["phase"]:
            errors.append(f"{case_id}: {op} not allowed in {s['phase']}")
        if OP_STATE[op] != s["state"]:
            errors.append(f"{case_id}: {op} must have state {OP_STATE[op]}")
        ph = PHASES.index(s["phase"]) if s["phase"] in PHASES else -1
        if ph < last_phase:
            errors.append(f"{case_id}: phase order violated at step {i}")
        last_phase = max(last_phase, ph)
        if status == "COMPLETE" and (s["phase"] != "VERIFICATION" or not s["evidence_id"]):
            errors.append(f"{case_id}: COMPLETE allows only cited VERIFICATION steps")
        if status == "INCOMPLETE":
            if s["phase"] == "FINDING" and not s["evidence_id"]:
                errors.append(f"{case_id}: finding without evidence at step {i}")
            if s["phase"] != "FINDING" and s["evidence_id"]:
                errors.append(f"{case_id}: future step {i} must have empty evidence_id")
    if status == "INCOMPLETE" and not any(s.get("phase") == "FINDING" for s in steps if isinstance(s, dict)):
        errors.append(f"{case_id}: INCOMPLETE needs at least one FINDING")
    return errors


def render_csv(results: list[CaseResult]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    # natural case_id order (case_99 before case_100): the order of deletion_requests.csv
    for r in sorted(results, key=lambda x: natural_case_key(x.case_id)):
        writer.writerow([r.case_id, r.deletion_status, steps_to_json(r.steps)])
    return buf.getvalue()


def write_output(results: list[CaseResult], path: Path, expected_case_ids: list[str]) -> list[str]:
    """Validate then write. Returns validation errors (the file is written regardless, for inspection)."""
    text = render_csv(results)
    errors = validate_csv_text(text, expected_case_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return errors


def validate_csv_text(text: str, expected_case_ids: list[str]) -> list[str]:
    errors: list[str] = []
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != HEADER:
        return ["bad header"]
    body = rows[1:]
    ids = [r[0] for r in body]
    if sorted(ids, key=natural_case_key) != ids:
        errors.append("rows are not sorted by case_id")
    if len(ids) != len(set(ids)):
        errors.append("duplicate case_id rows")
    if set(ids) != set(expected_case_ids):
        errors.append(f"case_id set mismatch: {len(ids)} rows vs {len(expected_case_ids)} expected")
    for r in body:
        if len(r) != 3:
            errors.append(f"{r[:1]}: wrong column count")
            continue
        errors.extend(validate_row(*r))
    return errors
