"""Generate the aggregate Stage 2 self-supervised training-set report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from code.lineage_training import build_training_examples, render_training_report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument(
        "--output", default="code/evaluation/training_set_report.md"
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    examples, summary = build_training_examples(root)
    if not examples or not summary["positives"] or not summary["hard_negatives"]:
        raise RuntimeError("self-supervised training examples are incomplete")
    train_users = {row["user_id"] for row in examples if row["split"] == "train"}
    validation_users = {
        row["user_id"] for row in examples if row["split"] == "validation"
    }
    if train_users & validation_users:
        raise RuntimeError("training and validation subjects overlap")
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_training_report(summary), encoding="utf-8", newline="\n")
    print(f"Examples: {summary['examples']}")
    print(f"Positive edges: {summary['positives']}")
    print(f"Hard negatives: {summary['hard_negatives']}")
    print(f"Train/validation users: {summary['train_users']}/{summary['validation_users']}")
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
