#!/usr/bin/env python3
"""Validate the submission CSV structure and the allowed step contract."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEADER = ["case_id", "deletion_status", "steps_json"]
STEP_FIELDS = {
    "step_no",
    "phase",
    "system_id",
    "resource_id",
    "operation",
    "state",
    "evidence_id",
}
PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
OPERATION_STATE = {
    "REPORT_REMAINING_RECORD": ("FINDING", "PRESENT"),
    "REPORT_EXPOSED_PII": ("FINDING", "PRESENT"),
    "REPORT_ACTIVE_DATA_FLOW": ("FINDING", "ACTIVE"),
    "REPORT_RESTORE_RISK": ("FINDING", "ACTIVE"),
    "DISABLE_DATA_FLOW": ("REMEDIATION", "DISABLED"),
    "BLOCK_RESTORE": ("REMEDIATION", "BLOCKED"),
    "DELETE_RECORD": ("REMEDIATION", "ABSENT"),
    "REDACT_RECORD": ("REMEDIATION", "REDACTED"),
    "ANONYMIZE_RECORD": ("REMEDIATION", "ANONYMIZED"),
    "VERIFY_RECORD_ABSENT": ("VERIFICATION", "ABSENT"),
    "VERIFY_RECORD_PRESENT": ("VERIFICATION", "PRESENT"),
    "VERIFY_RECORD_REDACTED": ("VERIFICATION", "REDACTED"),
    "VERIFY_RECORD_ANONYMIZED": ("VERIFICATION", "ANONYMIZED"),
    "VERIFY_DATA_FLOW_DISABLED": ("VERIFICATION", "DISABLED"),
    "VERIFY_RESTORE_BLOCKED": ("VERIFICATION", "BLOCKED"),
}


def validate(output_path: Path) -> dict[str, int]:
    with (ROOT / "dataset" / "deletion_requests.csv").open(
        encoding="utf-8-sig", newline=""
    ) as source:
        requests = list(csv.DictReader(source))
    with output_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Unexpected output columns: {reader.fieldnames}")
        rows = list(reader)

    expected_ids = sorted(row["case_id"] for row in requests)
    actual_ids = [row["case_id"] for row in rows]
    if len(rows) != 518 or actual_ids != expected_ids:
        raise ValueError(
            f"Expected 518 rows ordered by case_id; found {len(rows)} rows."
        )

    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
    step_count = 0
    for row in rows:
        status = row["deletion_status"]
        if status not in status_counts:
            raise ValueError(f"Invalid deletion_status for {row['case_id']}: {status}")
        status_counts[status] += 1
        try:
            steps = json.loads(row["steps_json"])
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid steps_json for {row['case_id']}") from error
        if not isinstance(steps, list):
            raise ValueError(f"steps_json for {row['case_id']} is not an array")
        if status == "NOT_APPLICABLE":
            if steps:
                raise ValueError(f"NOT_APPLICABLE case {row['case_id']} must use []")
            continue

        last_phase = -1
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict) or set(step) != STEP_FIELDS:
                raise ValueError(f"Invalid step fields for {row['case_id']} step {index}")
            if step["step_no"] != index:
                raise ValueError(f"Non-consecutive step numbering for {row['case_id']}")
            phase = step["phase"]
            if phase not in PHASE_ORDER or PHASE_ORDER[phase] < last_phase:
                raise ValueError(f"Invalid phase order for {row['case_id']}")
            last_phase = PHASE_ORDER[phase]
            expected_phase_state = OPERATION_STATE.get(step["operation"])
            if expected_phase_state != (phase, step["state"]):
                raise ValueError(f"Invalid operation/state for {row['case_id']} step {index}")
            for field in ("system_id", "resource_id", "evidence_id"):
                if not isinstance(step[field], str):
                    raise ValueError(f"Non-string {field} for {row['case_id']} step {index}")
            if status == "COMPLETE":
                if phase != "VERIFICATION" or not step["evidence_id"]:
                    raise ValueError(f"COMPLETE case {row['case_id']} lacks evidence-backed verification")
            elif phase == "FINDING" and not step["evidence_id"]:
                raise ValueError(f"INCOMPLETE finding in {row['case_id']} has no evidence")
            elif phase != "FINDING" and step["evidence_id"]:
                raise ValueError(f"INCOMPLETE future step in {row['case_id']} cites past evidence")
            step_count += 1

    return {"requests": len(requests), "rows": len(rows), "steps": step_count, **status_counts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "output.csv")
    args = parser.parse_args()
    print(json.dumps(validate(args.output.resolve()), indent=2))


if __name__ == "__main__":
    main()
