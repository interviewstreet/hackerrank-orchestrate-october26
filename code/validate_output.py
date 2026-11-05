"""
validate_output.py — check output.csv against the AGENTS.md §6.3/§6.4 contract.

    python code/validate_output.py [output.csv] [dataset/deletion_requests.csv]

Checks: exact header, one row per request (no missing / duplicate / extra
case_id), rows sorted by case_id, allowed statuses, steps_json is a JSON
array, exactly the 7 step fields, consecutive step_no from 1, phase order
FINDING -> REMEDIATION -> VERIFICATION, allowed operation/state per phase,
NOT_APPLICABLE -> [], COMPLETE -> verification only with evidence ids,
INCOMPLETE -> at least one finding, findings cite evidence, future steps
use "", every cited id exists in the manifest / activity / audit log and
was captured at or before the case's audit_at.
Exit code 0 when valid.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from step_builder import PHASE_OPS, STEP_FIELDS  # noqa: E402
from utils import parse_ts  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PHASES = ("FINDING", "REMEDIATION", "VERIFICATION")


def _key(cid: str):
    m = re.fullmatch(r"(.*?)(\d+)", cid)
    return (m.group(1), int(m.group(2))) if m else (cid, -1)


def evidence_times(dataset: Path) -> dict[str, object]:
    times = {}
    for name, idc, tc in (("evidence_files.csv", "file_id", "captured_at"),
                          ("system_activity.csv", "activity_id", "event_time"),
                          ("user_audit_log.csv", "audit_id", "event_time")):
        with open(dataset / name, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                times[r[idc]] = parse_ts(r[tc], context=r[idc])
    return times


def validate(output: Path, requests: Path) -> list[str]:
    errs: list[str] = []
    with open(requests, newline="", encoding="utf-8") as fh:
        cases = {r["case_id"]: r for r in csv.DictReader(fh)}
    times = evidence_times(requests.parent)
    with open(output, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    if header != ["case_id", "deletion_status", "steps_json"]:
        errs.append(f"bad header {header}")
    ids = [r[0] for r in rows]
    dup = [c for c, n in Counter(ids).items() if n > 1]
    if dup:
        errs.append(f"duplicate case_ids: {dup}")
    if set(ids) != set(cases):
        errs.append(f"missing {sorted(set(cases) - set(ids))[:10]} extra {sorted(set(ids) - set(cases))[:10]}")
    if ids != sorted(ids, key=_key):
        errs.append("rows are not sorted by case_id")
    for row in rows:
        if len(row) != 3:
            errs.append(f"{row[:1]}: expected 3 columns")
            continue
        cid, status, sj = row
        if status not in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"):
            errs.append(f"{cid}: bad status {status}")
        try:
            steps = json.loads(sj)
        except json.JSONDecodeError as exc:
            errs.append(f"{cid}: steps_json not JSON ({exc})")
            continue
        if not isinstance(steps, list):
            errs.append(f"{cid}: steps_json is not an array")
            continue
        if status == "NOT_APPLICABLE" and steps:
            errs.append(f"{cid}: NOT_APPLICABLE must have []")
        audit_at = parse_ts(cases.get(cid, {}).get("audit_at"), context=cid) if cid in cases else None
        last_phase = 0
        for i, s in enumerate(steps, 1):
            if not isinstance(s, dict) or set(s) != set(STEP_FIELDS):
                errs.append(f"{cid} step {i}: fields {sorted(s) if isinstance(s, dict) else s}")
                continue
            if s["step_no"] != i:
                errs.append(f"{cid} step {i}: step_no {s['step_no']}")
            ph = s["phase"]
            if ph not in PHASES:
                errs.append(f"{cid} step {i}: bad phase {ph}")
                continue
            if PHASES.index(ph) < last_phase:
                errs.append(f"{cid} step {i}: phase order")
            last_phase = PHASES.index(ph)
            if s["operation"] not in PHASE_OPS[ph] or PHASE_OPS[ph][s["operation"]] != s["state"]:
                errs.append(f"{cid} step {i}: {ph}/{s['operation']}/{s['state']} not allowed")
            ev = s["evidence_id"]
            needs_ev = ph == "FINDING" or status == "COMPLETE"
            if needs_ev and not ev:
                errs.append(f"{cid} step {i}: missing evidence_id")
            if not needs_ev and ev:
                errs.append(f"{cid} step {i}: future step must have empty evidence_id")
            if ev:
                if ev not in times:
                    errs.append(f"{cid} step {i}: unknown evidence id {ev}")
                elif audit_at and times[ev] and times[ev] > audit_at:
                    errs.append(f"{cid} step {i}: {ev} is after audit_at")
        if status == "COMPLETE" and any(s.get("phase") != "VERIFICATION" for s in steps if isinstance(s, dict)):
            errs.append(f"{cid}: COMPLETE with non-verification steps")
        if status == "INCOMPLETE" and not any(isinstance(s, dict) and s.get("phase") == "FINDING" for s in steps):
            errs.append(f"{cid}: INCOMPLETE without findings")
    return errs


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else REPO / "output.csv"
    req = Path(argv[2]) if len(argv) > 2 else REPO / "dataset" / "deletion_requests.csv"
    errs = validate(out, req)
    for e in errs:
        print("ERROR", e)
    print(f"{out}: {'VALID' if not errs else f'{len(errs)} problems'}")
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
