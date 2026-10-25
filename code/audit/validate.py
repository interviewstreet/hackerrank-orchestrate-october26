"""Structural validator for output.csv. Usage: python -m audit.validate output.csv [requests.csv]"""
import csv, json, sys
from .constants import *
from .steps import sort_key

def validate_row(case_id, status, raw):
    errs = []
    if status not in STATUSES:
        return [f"{case_id}: bad status {status}"]
    try:
        steps = json.loads(raw)
    except Exception as e:
        return [f"{case_id}: invalid JSON ({e})"]
    if not isinstance(steps, list):
        return [f"{case_id}: steps_json not an array"]
    if status == "NOT_APPLICABLE" and steps:
        errs.append(f"{case_id}: NOT_APPLICABLE must be []")
    for i, s in enumerate(steps, 1):
        if set(s) != set(STEP_KEYS): errs.append(f"{case_id}#{i}: keys {sorted(s)}")
        if s.get("step_no") != i: errs.append(f"{case_id}#{i}: step_no {s.get('step_no')}")
        op = s.get("operation")
        if op not in OP_PHASE: errs.append(f"{case_id}#{i}: unknown op {op}"); continue
        if s["phase"] != OP_PHASE[op] or s["state"] != OP_STATE[op]:
            errs.append(f"{case_id}#{i}: phase/state mismatch for {op}")
        if status == "COMPLETE" and (s["phase"] != "VERIFICATION" or not s["evidence_id"]):
            errs.append(f"{case_id}#{i}: COMPLETE needs cited verification only")
        if status == "INCOMPLETE" and s["phase"] != "FINDING" and s["evidence_id"]:
            errs.append(f"{case_id}#{i}: non-finding must have empty evidence_id")
    try:
        if [sort_key(s) for s in steps] != sorted(sort_key(s) for s in steps):
            errs.append(f"{case_id}: steps not in required order")
    except Exception: pass
    return errs

def validate(path, requests_path=None, expected_rows=None):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    errs = []
    ids = [r["case_id"] for r in rows]
    if ids != sorted(ids): errs.append("rows not sorted by case_id")
    if len(set(ids)) != len(ids): errs.append("duplicate case_ids")
    if requests_path:
        want = {r["case_id"] for r in csv.DictReader(open(requests_path, newline="", encoding="utf-8"))}
        if set(ids) != want: errs.append(f"case_id mismatch: missing={sorted(want-set(ids))[:5]} extra={sorted(set(ids)-want)[:5]}")
    if expected_rows and len(rows) != expected_rows:
        errs.append(f"expected {expected_rows} rows, got {len(rows)}")
    for r in rows:
        errs += validate_row(r["case_id"], r["deletion_status"], r["steps_json"])
    return errs

if __name__ == "__main__":
    e = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("\n".join(e) if e else "OK"); sys.exit(1 if e else 0)
