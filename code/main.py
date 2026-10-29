#!/usr/bin/env python3
"""Ghost Data Still Exists - Deletion Audit Agent Entry Point.
Implements the full pipeline (Stages 1‑4) and writes the required
`dataset/output.csv`.
"""

import csv
import json
from pathlib import Path

from .load import load_dataset
from .decision import classify_requests
from .remediation import plan_remediation


def _steps_json(steps: list[dict]) -> str:
    """Compact JSON for the `steps_json` column."""
    return json.dumps(steps, separators=(",", ":"))


def run_pipeline(root: Path | None = None) -> None:
    """Execute the end‑to‑end pipeline and write the final CSV.

    Args:
        root: Repository root; defaults to the package parent directory.
    """
    data = load_dataset(root)
    requests = data["deletion_requests"]
    identities = data["user_identities"]
    audit_log = data["user_audit_log"]
    system_activity = data["system_activity"]
    deletion_rules = data["deletion_rules"]
    evidence_files = data["evidence_files"]

    # Classification of each request
    classification = classify_requests(
        requests, identities, audit_log, system_activity, deletion_rules, evidence_files
    )

    rows = []
    for req in requests:
        case_id = req["case_id"]
        status = classification.get(case_id, "INCOMPLETE")
        steps = plan_remediation(req, identities, audit_log, system_activity, deletion_rules, evidence_files) if status == "INCOMPLETE" else []
        rows.append({
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": _steps_json(steps),
        })

    # Sort by case_id as required
    rows.sort(key=lambda r: r["case_id"])

    out_path = (Path(__file__).resolve().parent.parent / "output.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    run_pipeline()
