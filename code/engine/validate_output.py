"""Structural validation of output.csv against the problem-statement contract."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from .contracts import OPERATION_STATE

STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
PHASES = {"FINDING", "REMEDIATION", "VERIFICATION"}
FIELDS = ["step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"]


def validate_output_csv(path, dataset_dir) -> List[str]:
    problems: List[str] = []
    d = Path(dataset_dir)
    with open(d / "deletion_requests.csv", encoding="utf-8", newline="") as fh:
        requests = {r["case_id"]: r for r in csv.DictReader(fh)}
    with open(d / "evidence_files.csv", encoding="utf-8", newline="") as fh:
        manifest = {r[0]: {"captured_at": r[-1]} for r in csv.reader(fh) if r and r[0].startswith("evidence_")}
    with open(path, encoding="utf-8", newline="") as fh:
        rdr = csv.reader(fh)
        header = next(rdr, [])
        if header != ["case_id", "deletion_status", "steps_json"]:
            problems.append(f"bad header {header}")
        rows = list(rdr)
    ids = [r[0] for r in rows]
    if len(rows) != len(requests):
        problems.append(f"expected {len(requests)} rows, found {len(rows)}")
    if ids != sorted(ids):
        problems.append("rows are not sorted by case_id")
    if len(set(ids)) != len(ids):
        problems.append("duplicate case_id")
    if set(ids) != set(requests):
        problems.append("case_id set differs from deletion_requests.csv")
    for r in rows:
        cid, status, raw = r
        if status not in STATUSES:
            problems.append(f"{cid}: bad status {status}")
        try:
            steps = json.loads(raw)
        except json.JSONDecodeError as e:
            problems.append(f"{cid}: steps_json is not valid JSON ({e})")
            continue
        if status == "NOT_APPLICABLE" and steps:
            problems.append(f"{cid}: NOT_APPLICABLE must have no steps")
        audit_at = requests.get(cid, {}).get("audit_at", "")
        for i, s in enumerate(steps, 1):
            if list(s) != FIELDS:
                problems.append(f"{cid}: step {i} fields {list(s)}")
            if s.get("step_no") != i:
                problems.append(f"{cid}: step_no {s.get('step_no')} != {i}")
            if s.get("phase") not in PHASES:
                problems.append(f"{cid}: bad phase {s.get('phase')}")
            if s.get("operation") not in OPERATION_STATE:
                problems.append(f"{cid}: bad operation {s.get('operation')}")
            elif OPERATION_STATE[s["operation"]] != (s["phase"], s["state"]):
                problems.append(f"{cid}: step {i} phase/state do not match {s['operation']}")
            e = s.get("evidence_id", "")
            if e:
                if e not in manifest:
                    problems.append(f"{cid}: unknown evidence_id {e}")
                elif manifest[e]["captured_at"] > audit_at:
                    problems.append(f"{cid}: {e} captured after audit_at")
    return problems
