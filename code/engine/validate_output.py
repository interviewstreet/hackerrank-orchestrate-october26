"""Structural validation of output.csv against the problem-statement contract."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from .contracts import OPERATION_ORDER, OPERATION_STATE

STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
PHASES = {"FINDING", "REMEDIATION", "VERIFICATION"}
PHASE_RANK = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
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
        if not isinstance(steps, list):
            problems.append(f"{cid}: steps_json must be a JSON array, got {type(steps).__name__}")
            continue
        if status == "NOT_APPLICABLE" and steps != []:
            problems.append(f"{cid}: NOT_APPLICABLE must have steps_json == []")
        if status == "COMPLETE" and not steps:
            problems.append(f"{cid}: COMPLETE needs evidence-backed verification steps")
        audit_at = requests.get(cid, {}).get("audit_at", "")
        last_phase, last_op = -1, -1
        for i, s in enumerate(steps, 1):
            if not isinstance(s, dict):
                problems.append(f"{cid}: step {i} is not an object")
                continue
            if list(s) != FIELDS and sorted(s) != sorted(FIELDS):
                problems.append(f"{cid}: step {i} fields {list(s)}")
                continue
            if s.get("step_no") != i or isinstance(s.get("step_no"), bool):
                problems.append(f"{cid}: step_no {s.get('step_no')} != {i}")
            if any(not isinstance(s.get(k), str) for k in FIELDS[1:]):
                problems.append(f"{cid}: step {i} has a non-text field")
                continue
            phase = s["phase"]
            if phase not in PHASES:
                problems.append(f"{cid}: bad phase {phase}")
            elif PHASE_RANK[phase] < last_phase:
                problems.append(f"{cid}: step {i} {phase} comes after a later phase")
            op = s["operation"]
            if op not in OPERATION_STATE:
                problems.append(f"{cid}: bad operation {op}")
            else:
                if OPERATION_STATE[op] != (phase, s["state"]):
                    problems.append(f"{cid}: step {i} phase/state do not match {op}")
                if phase in PHASE_RANK and PHASE_RANK[phase] == last_phase and OPERATION_ORDER.index(op) < last_op:
                    problems.append(f"{cid}: step {i} {op} is out of order within {phase} "
                                    "(disable flows and block restores before changing records)")
                last_op = OPERATION_ORDER.index(op)
            if phase in PHASE_RANK:
                if PHASE_RANK[phase] != last_phase:
                    last_op = OPERATION_ORDER.index(op) if op in OPERATION_STATE else -1
                last_phase = max(last_phase, PHASE_RANK[phase])
            e = s["evidence_id"]
            if phase == "FINDING" and not e:
                problems.append(f"{cid}: step {i} finding has no evidence_id")
            if phase == "REMEDIATION" and e:
                problems.append(f"{cid}: step {i} remediation must have an empty evidence_id")
            if phase == "VERIFICATION" and status == "COMPLETE" and not e:
                problems.append(f"{cid}: step {i} verification in a COMPLETE case must cite evidence")
            if phase == "VERIFICATION" and status == "INCOMPLETE" and e:
                problems.append(f"{cid}: step {i} future verification must have an empty evidence_id")
            if status == "COMPLETE" and phase != "VERIFICATION":
                problems.append(f"{cid}: COMPLETE case contains a {phase} step")
            if e:
                if e not in manifest:
                    problems.append(f"{cid}: unknown evidence_id {e}")
                elif manifest[e]["captured_at"] > audit_at:
                    problems.append(f"{cid}: {e} captured after audit_at")
    return problems
