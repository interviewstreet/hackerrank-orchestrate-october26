"""ERASIGHT deletion-audit agent: reads dataset/, writes the root output.csv.

Usage (from the repository root):
    python code/main.py [--dataset dataset] [--output output.csv]
Deterministic: no network access and no model calls.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine.pipeline import run_all_cases, write_output_csv      # noqa: E402
from engine.validate_output import validate_output_csv            # noqa: E402


def main() -> int:
    root = HERE.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default=str(root / "dataset"))
    ap.add_argument("--output", default=str(root / "output.csv"))
    args = ap.parse_args()

    results = run_all_cases(args.dataset)
    write_output_csv(results, args.output)
    problems = validate_output_csv(args.output, args.dataset)
    counts = Counter(r.deletion_status for r in results)
    print(f"wrote {args.output}: {len(results)} cases {dict(counts)}")
    if problems:
        print(f"{len(problems)} validation problem(s):")
        for p in problems[:25]:
            print("  -", p)
        return 1
    print("output validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
