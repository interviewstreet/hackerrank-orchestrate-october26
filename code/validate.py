"""Validate an output file against the full output contract.

Usage:
    python code/validate.py [OUTPUT] [--requests PATH] [--phase1] [--no-evidence-check]

Exit code 0 when valid, 1 when any error is found. ``--phase1`` allows the
placeholder row ``INCOMPLETE,[]`` that Phase 1 writes for deletion cases.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from loaders import DATASET_DIR, REPO_ROOT, case_number, load_requests, parse_ts, read_csv

HEADER = ["case_id", "deletion_status", "steps_json"]
STATUSES = ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")
PHASES = ("FINDING", "REMEDIATION", "VERIFICATION")
STEP_KEYS = frozenset({"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"})

# (phase, operation, state) in the mandated table order. Index = sort rank.
OPERATIONS = (
    ("FINDING", "REPORT_REMAINING_RECORD", "PRESENT"),
    ("FINDING", "REPORT_EXPOSED_PII", "PRESENT"),
    ("FINDING", "REPORT_ACTIVE_DATA_FLOW", "ACTIVE"),
    ("FINDING", "REPORT_RESTORE_RISK", "ACTIVE"),
    ("REMEDIATION", "DISABLE_DATA_FLOW", "DISABLED"),
    ("REMEDIATION", "BLOCK_RESTORE", "BLOCKED"),
    ("REMEDIATION", "DELETE_RECORD", "ABSENT"),
    ("REMEDIATION", "REDACT_RECORD", "REDACTED"),
    ("REMEDIATION", "ANONYMIZE_RECORD", "ANONYMIZED"),
    ("VERIFICATION", "VERIFY_RECORD_ABSENT", "ABSENT"),
    ("VERIFICATION", "VERIFY_RECORD_PRESENT", "PRESENT"),
    ("VERIFICATION", "VERIFY_RECORD_REDACTED", "REDACTED"),
    ("VERIFICATION", "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"),
    ("VERIFICATION", "VERIFY_DATA_FLOW_DISABLED", "DISABLED"),
    ("VERIFICATION", "VERIFY_RESTORE_BLOCKED", "BLOCKED"),
)
OP_RANK = {op: i for i, (_, op, _) in enumerate(OPERATIONS)}
OP_PHASE = {op: phase for phase, op, _ in OPERATIONS}
OP_STATE = {op: state for _, op, state in OPERATIONS}


def step_sort_key(step: dict) -> tuple:
    """Mandated order: phase, operation table order, system_id, resource_id."""
    return (PHASES.index(step["phase"]), OP_RANK[step["operation"]], step["system_id"], step["resource_id"])


def evidence_times(dataset_dir: Path = DATASET_DIR) -> dict[str, datetime]:
    """Availability time of every citable id: file_id, activity_id, audit_id."""
    times: dict[str, datetime] = {}
    for row in read_csv(dataset_dir / "evidence_files.csv"):
        times[row["file_id"].strip()] = parse_ts(row["captured_at"])
    for row in read_csv(dataset_dir / "system_activity.csv"):
        times[row["activity_id"].strip()] = parse_ts(row["event_time"])
    for row in read_csv(dataset_dir / "user_audit_log.csv"):
        times[row["audit_id"].strip()] = parse_ts(row["event_time"])
    return times


def validate_steps(case_id: str, status: str, steps_json: str, *, phase1: bool = False,
                   audit_at: datetime | None = None,
                   ev_times: dict[str, datetime] | None = None) -> list[str]:
    """Return contract errors for one row."""
    errors: list[str] = []
    err = lambda msg: errors.append(f"{case_id}: {msg}")  # noqa: E731

    if status not in STATUSES:
        err(f"bad deletion_status {status!r}")
    try:
        steps = json.loads(steps_json)
    except (json.JSONDecodeError, TypeError) as exc:
        err(f"steps_json is not valid JSON ({exc})")
        return errors
    if not isinstance(steps, list):
        err("steps_json is not a JSON array")
        return errors

    if status == "NOT_APPLICABLE":
        if steps:
            err("NOT_APPLICABLE must have steps_json=[]")
        return errors
    if not steps:
        if not (phase1 and status == "INCOMPLETE"):
            err(f"{status} must have at least one step")
        return errors

    well_formed = True
    for i, step in enumerate(steps, start=1):
        where = f"step {i}"
        if not isinstance(step, dict):
            err(f"{where}: not a JSON object")
            well_formed = False
            continue
        keys = set(step)
        if keys != STEP_KEYS:
            missing, extra = sorted(STEP_KEYS - keys), sorted(keys - STEP_KEYS)
            err(f"{where}: keys mismatch (missing={missing}, extra={extra})")
            well_formed = False
            continue
        if type(step["step_no"]) is not int or step["step_no"] != i:
            err(f"{where}: step_no must be {i}, got {step['step_no']!r}")
        bad_types = [k for k in sorted(STEP_KEYS - {"step_no"}) if not isinstance(step[k], str)]
        if bad_types:
            err(f"{where}: must be strings: {bad_types}")
            well_formed = False
            continue
        if not step["system_id"] or not step["resource_id"]:
            err(f"{where}: empty system_id or resource_id")
        if step["phase"] not in PHASES:
            err(f"{where}: bad phase {step['phase']!r}")
            well_formed = False
            continue
        op = step["operation"]
        if op not in OP_RANK:
            err(f"{where}: bad operation {op!r}")
            well_formed = False
            continue
        if OP_PHASE[op] != step["phase"]:
            err(f"{where}: operation {op} is not allowed in phase {step['phase']}")
            well_formed = False
        if OP_STATE[op] != step["state"]:
            err(f"{where}: operation {op} needs state {OP_STATE[op]}, got {step['state']!r}")

        ev = step["evidence_id"]
        if status == "COMPLETE":
            if step["phase"] != "VERIFICATION":
                err(f"{where}: COMPLETE allows only VERIFICATION steps")
            if not ev:
                err(f"{where}: COMPLETE verification must cite evidence")
        elif status == "INCOMPLETE":
            if step["phase"] == "FINDING" and not ev:
                err(f"{where}: FINDING must cite evidence")
            if step["phase"] in ("REMEDIATION", "VERIFICATION") and ev:
                err(f"{where}: INCOMPLETE {step['phase']} must have evidence_id \"\"")
        if ev and ev_times is not None:
            if ev not in ev_times:
                err(f"{where}: unknown evidence_id {ev!r}")
            elif audit_at is not None and ev_times[ev] > audit_at:
                err(f"{where}: evidence {ev} is after audit_at")

    if well_formed:
        keys = [step_sort_key(s) for s in steps]
        if keys != sorted(keys):
            err("steps are not in canonical order (phase, operation, system_id, resource_id)")
        targets = [(s["operation"], s["system_id"], s["resource_id"]) for s in steps]
        if len(set(targets)) != len(targets):
            err("duplicate step for the same operation and target")
        if status == "INCOMPLETE" and not any(s["phase"] == "REMEDIATION" for s in steps) \
                and not any(s["phase"] == "VERIFICATION" for s in steps):
            err("INCOMPLETE needs remediation or verification steps")
    return errors


def validate_file(output_path: Path, requests_path: Path, *, phase1: bool = False,
                  check_evidence: bool = True, dataset_dir: Path = DATASET_DIR) -> list[str]:
    errors: list[str] = []
    requests = load_requests(requests_path)
    expected_ids = [r.case_id for r in requests]
    audit_at = {r.case_id: r.audit_at for r in requests}
    ev_times = evidence_times(dataset_dir) if check_evidence else None

    with open(output_path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != HEADER:
        errors.append(f"header must be {','.join(HEADER)}, got {rows[0] if rows else 'empty file'}")
        return errors
    body = rows[1:]

    ids: list[str] = []
    for line_no, row in enumerate(body, start=2):
        if len(row) != 3:
            errors.append(f"line {line_no}: expected 3 columns, got {len(row)}")
            continue
        case_id, status, steps_json = row
        ids.append(case_id)
        errors.extend(validate_steps(case_id, status, steps_json, phase1=phase1,
                                     audit_at=audit_at.get(case_id), ev_times=ev_times))

    if len(body) != len(expected_ids):
        errors.append(f"expected {len(expected_ids)} data rows, got {len(body)}")
    seen = set()
    dupes = sorted({i for i in ids if i in seen or seen.add(i)})
    if dupes:
        errors.append(f"duplicate case_id: {dupes[:10]}")
    missing = sorted(set(expected_ids) - set(ids), key=case_number)
    extra = sorted(set(ids) - set(expected_ids))
    if missing:
        errors.append(f"missing case_id ({len(missing)}): {missing[:10]}")
    if extra:
        errors.append(f"unknown case_id ({len(extra)}): {extra[:10]}")
    try:
        numeric = sorted(ids, key=case_number)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if ids != numeric:
            errors.append("rows are not sorted by numeric case_id")
    if not missing and not extra and not dupes and ids != expected_ids:
        errors.append("row order differs from the input file order")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", nargs="?", default=str(REPO_ROOT / "output.csv"))
    parser.add_argument("--requests", default=str(DATASET_DIR / "deletion_requests.csv"))
    parser.add_argument("--phase1", action="store_true", help="allow INCOMPLETE,[] placeholder rows")
    parser.add_argument("--no-evidence-check", action="store_true", help="skip evidence id / audit_at checks")
    args = parser.parse_args(argv)

    errors = validate_file(Path(args.output), Path(args.requests), phase1=args.phase1,
                           check_evidence=not args.no_evidence_check)
    with open(args.output, encoding="utf-8-sig", newline="") as handle:
        n_rows = max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    if errors:
        for line in errors[:50]:
            print("ERROR", line)
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
        print(f"INVALID: {len(errors)} error(s) in {args.output} ({n_rows} rows)")
        return 1
    print(f"VALID: {args.output} ({n_rows} rows{', phase1 placeholders allowed' if args.phase1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
