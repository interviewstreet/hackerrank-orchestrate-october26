"""Evaluation: sample accuracy against sample_output.csv, plus custom cases.

    python code/evaluation/main.py            # uses cached model answers, calls the API for anything new
    python code/evaluation/main.py --offline  # cached answers only

Custom cases are test requests from deletion_requests.csv whose correct handling we derived
by hand from the evidence (they have no published answer). Each one checks a specific
behaviour with explicit expectations rather than a full reference row, because the rest of
the row was not independently verified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent
sys.path.insert(0, str(CODE))

from audit.data import read_csv  # noqa: E402
from audit.llm import Claude  # noqa: E402
from audit.scoring import score  # noqa: E402
from main import ROOT, build  # noqa: E402

# (case_id, what it tests, expected status, steps that must appear, resources that must not appear)
# a step is (phase, resource_id, operation, evidence_id); None in a slot means "any"
CUSTOM_CASES = [
    ("case_46", "tombstone that keeps only the stable user_id is compliant (read from a screenshot)",
     "COMPLETE", [("VERIFICATION", "tombstone_17", "VERIFY_RECORD_REDACTED", "evidence_42")], []),
    ("case_61", "attachment linked by catalog alias (file name -> object_19); a same-named file of "
     "another customer (support_3802) must not be linked",
     "INCOMPLETE", [("FINDING", "object_19", "REPORT_REMAINING_RECORD", "evidence_46"),
                    ("REMEDIATION", "object_19", "DELETE_RECORD", "")], ["support_3802"]),
    ("case_33", "PDF statement number resolved to an export id across systems "
     "(NST-2026-0718-1842 -> export_1842)",
     "INCOMPLETE", [("FINDING", "export_1842", "REPORT_REMAINING_RECORD", "evidence_18")], []),
    ("case_55", "backup screenshot with restore still possible is a restore risk, not a deletion",
     "INCOMPLETE", [("FINDING", "backup_9287", "REPORT_RESTORE_RISK", "evidence_32"),
                    ("REMEDIATION", "backup_9287", "BLOCK_RESTORE", "")], []),
    ("case_50", "analytics profile still showing user_id and email must be anonymized, not deleted",
     "INCOMPLETE", [("FINDING", "analytics_7438", "REPORT_EXPOSED_PII", "evidence_19"),
                    ("REMEDIATION", "analytics_7438", "ANONYMIZE_RECORD", "")], []),
    ("case_539", "information request that explicitly says it is not an erasure request",
     "NOT_APPLICABLE", [], []),
    ("case_45", "retained security audit records read from a screenshot are verified as kept",
     "COMPLETE", [("VERIFICATION", "audit_record_003", "VERIFY_RECORD_PRESENT", None)], []),
]


def check_custom(rows: dict) -> list[dict]:
    out = []
    for cid, desc, status, must, must_not in CUSTOM_CASES:
        row = rows[cid]
        steps = json.loads(row["steps_json"])
        problems = []
        if row["deletion_status"] != status:
            problems.append(f"status {row['deletion_status']} != {status}")
        for phase, rid, op, ev in must:
            hit = [s for s in steps if s["phase"] == phase and s["resource_id"] == rid and s["operation"] == op
                   and (ev is None or s["evidence_id"] == ev)]
            if not hit:
                problems.append(f"missing {phase} {op} {rid} ({ev})")
        for rid in must_not:
            if any(s["resource_id"] == rid for s in steps):
                problems.append(f"unexpected {rid}")
        if status == "NOT_APPLICABLE" and steps:
            problems.append("NOT_APPLICABLE must have no steps")
        out.append({"case_id": cid, "tests": desc, "passed": not problems, "problems": problems})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    dataset = ROOT / "dataset"
    claude = Claude(offline=args.offline)
    auditor, sample, tests, intents, _ = build(dataset, claude, log=lambda *_: None)

    from main import audit_rows
    pred = {r["case_id"]: r for r in audit_rows(auditor, sample, intents)}
    gold = {r["case_id"]: r for r in read_csv(dataset / "sample_output.csv")}
    m = score(pred, gold)
    print(json.dumps({k: v for k, v in m.items() if k != "per_case"}, indent=2))
    for cid, pc in m["per_case"].items():
        if not pc["row_ok"]:
            print(f"  {cid}: status_ok={pc['status_ok']} sequence_ok={pc['sequence_ok']}")
            for x in pc["missing"]:
                print("     missing", x)
            for x in pc["extra"]:
                print("     extra  ", x)

    test_rows = {r["case_id"]: r for r in audit_rows(auditor, tests, intents)}
    custom = check_custom(test_rows)
    print(f"\ncustom cases: {sum(c['passed'] for c in custom)}/{len(custom)} passed")
    for c in custom:
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['case_id']}: {c['tests']}")
        for p in c["problems"]:
            print("        ", p)


if __name__ == "__main__":
    main()
