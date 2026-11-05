"""
code/evaluation/main.py — reproduce the numbers in evaluation_report.md.

    python code/evaluation/main.py

1. Runs the full pipeline on dataset/sample_deletion_requests.csv
   (the 32 public requests with published answers), writing
   code/evaluation/sample_predictions.csv.
2. Validates it against the output contract.
3. Scores it against dataset/sample_output.csv (code/evaluate.py) and prints
   status, exact-case, step-level, field-level and sequence accuracy plus the
   per-case differences.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent
REPO = CODE.parent
sys.path.insert(0, str(CODE))

import evaluate  # noqa: E402
import main as pipeline  # noqa: E402
import validate_output  # noqa: E402


def run() -> int:
    pred = HERE / "sample_predictions.csv"
    pipeline.main(["--requests", "sample_deletion_requests.csv", "--output", str(pred)])
    errs = validate_output.validate(pred, REPO / "dataset" / "sample_deletion_requests.csv")
    print(f"contract check: {'VALID' if not errs else errs}")
    return evaluate.main(["evaluate", str(pred), str(REPO / "dataset" / "sample_output.csv")])


if __name__ == "__main__":
    raise SystemExit(run())
