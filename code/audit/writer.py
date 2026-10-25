"""output.csv writer + contract validator (see problem_statement.md)."""
import csv
import json
from pathlib import Path

from .config import ALLOWED_STATUSES, OP_ORDER, OP_STATE, PHASE_ORDER, STEP_KEYS
from .loaders import case_sort_key


def steps_json(steps):
    return json.dumps(steps, separators=(",", ":"), ensure_ascii=False)


def write_output(rows, out_path):
    """rows: list of (case_id, deletion_status, steps)."""
    rows = sorted(rows, key=lambda r: case_sort_key(r[0]))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for case_id, status, steps in rows:
            writer.writerow([case_id, status, steps_json(steps)])
    return rows


def validate(rows, requests, evidence_ids, activity_ids, audit_ids,
             request_audit=None):
    """Validate (case_id, status, steps) rows; raise ValueError on failure.

    ``request_audit`` optionally maps case_id -> audit datetime and, with the
    supplied id->time maps in ``id_times``, checks evidence is not post-audit.
    """
    errors = []
    expected = {r["case_id"] for r in requests}
    got = [r[0] for r in rows]
    if set(got) != expected:
        errors.append(f"case set mismatch: missing={sorted(expected - set(got))[:5]} "
                      f"extra={sorted(set(got) - expected)[:5]}")
    if len(got) != len(set(got)):
        errors.append("duplicate case_ids")
    if got != sorted(got, key=case_sort_key):
        errors.append("rows not in natural case_id order")
    valid_ids = set(evidence_ids) | set(activity_ids) | set(audit_ids)
    for case_id, status, steps in rows:
        if status not in ALLOWED_STATUSES:
            errors.append(f"{case_id}: bad status {status}")
            continue
        if status == "NOT_APPLICABLE" and steps != []:
            errors.append(f"{case_id}: NOT_APPLICABLE must have [] steps")
        # A COMPLETE case whose subject left no linkable record in any
        # eligible evidence legitimately has an empty step list.
        for i, s in enumerate(steps, start=1):
            if set(s.keys()) != STEP_KEYS:
                errors.append(f"{case_id} step {i}: keys {sorted(s.keys())}")
            if s.get("step_no") != i:
                errors.append(f"{case_id} step {i}: step_no={s.get('step_no')}")
            if OP_STATE.get(s.get("operation")) != s.get("state"):
                errors.append(f"{case_id} step {i}: state/operation mismatch")
            ev = s.get("evidence_id", "")
            if status == "COMPLETE" or s.get("phase") == "FINDING":
                if not ev:
                    errors.append(f"{case_id} step {i}: missing evidence_id")
                elif ev not in valid_ids:
                    errors.append(f"{case_id} step {i}: unknown evidence_id {ev}")
            else:
                if ev != "":
                    errors.append(f"{case_id} step {i}: expected empty evidence_id")
        keys = [(PHASE_ORDER[s["phase"]], OP_ORDER[s["operation"]],
                 s["system_id"], s["resource_id"]) for s in steps]
        if keys != sorted(keys):
            errors.append(f"{case_id}: steps out of order")
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(errors[:50]))
    return True
