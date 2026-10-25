"""Evaluation-only public-sample diagnostics; never imported by prediction code."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from code.evaluation.observability import audit_observability
from code.ingest import load_all
from code.main import run_pipeline

FIELDS = ("phase", "operation", "state", "system_id", "resource_id", "evidence_id")


def _key(step):
    return tuple(step.get(field) for field in FIELDS)


def build_diagnostics(root: Path) -> str:
    data = load_all(root)
    actual = {row["case_id"]: row for row in run_pipeline(root, sample=True, no_cache=True)}
    truth = data["sample_output"]
    observability = audit_observability(root)
    blocked = {(row["case_id"], row["resource_id"]): row["category"]
               for row in observability["blocked"]}
    expected_total = predicted_total = true_positive = 0
    rows = []
    causes = Counter()
    for case_id in sorted(truth):
        expected_row = truth[case_id]
        actual_row = actual.get(case_id, {})
        expected = json.loads(expected_row["steps_json"])
        predicted = json.loads(actual_row.get("steps_json", "[]"))
        expected_counts = Counter(map(_key, expected))
        predicted_counts = Counter(map(_key, predicted))
        matched = expected_counts & predicted_counts
        expected_total += sum(expected_counts.values())
        predicted_total += sum(predicted_counts.values())
        true_positive += sum(matched.values())
        missing = list((expected_counts - predicted_counts).elements())
        extra = list((predicted_counts - expected_counts).elements())
        status_ok = expected_row["deletion_status"] == actual_row.get("deletion_status")
        if status_ok and not missing and not extra:
            continue
        case_causes = set()
        if not status_ok:
            case_causes.add("status decision")
        for item in missing:
            category = blocked.get((case_id, item[4]))
            if category:
                case_causes.add(f"unavailable canonical resource ({category})")
            elif not any(step.get("resource_id") == item[4] for step in predicted):
                case_causes.add("resource lineage/retrieval gap")
            else:
                case_causes.add("policy/treatment or evidence mismatch")
        if extra:
            grounded_extra = any(item[0] == "FINDING" and item[5] for item in extra)
            case_causes.add(
                "additional evidence-grounded resource not in canonical sequence"
                if grounded_extra else "ordering/treatment consequence of an additional resource"
            )
        for cause in case_causes:
            causes[cause] += 1
        rows.append((case_id, status_ok, missing, extra, sorted(case_causes)))
    precision = true_positive / predicted_total if predicted_total else 1.0
    recall = true_positive / expected_total if expected_total else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    lines = [
        "# Public Benchmark Diagnostics", "",
        "This report is evaluation-only. Public labels are never imported by prediction modules.", "",
        "## Exact Step Precision, Recall, and F1", "",
        f"- Exact-step true positives: **{true_positive}**",
        f"- Predicted steps: **{predicted_total}**",
        f"- Expected steps: **{expected_total}**",
        f"- Precision: **{precision:.1%}**",
        f"- Recall: **{recall:.1%}**",
        f"- F1: **{f1:.1%}**", "",
        "## Root-Cause Matrix", "",
        "| Generalizable cause | Affected sample cases |", "|---|---:|",
    ]
    lines.extend(f"| {cause} | {count} |" for cause, count in sorted(causes.items()))
    lines.extend(["", "## Complete Remaining Case Diagnostics", "",
                  "| Case | Status correct | Missing exact steps | Extra exact steps | Causes |",
                  "|---|---:|---:|---:|---|"])
    for case_id, status_ok, missing, extra, case_causes in rows:
        lines.append(f"| `{case_id}` | {'yes' if status_ok else 'no'} | {len(missing)} | "
                     f"{len(extra)} | {', '.join(case_causes)} |")
    lines.extend(["", "## Evidence-Limitation Detail", "",
                  "See `observability_report.md` for each canonical resource that is absent globally "
                  "or appears only after its case's audit cutoff.", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output", default="code/evaluation/benchmark_diagnostics.md")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    output = (root / args.output).resolve()
    output.write_text(build_diagnostics(root), encoding="utf-8", newline="\n")
    print(f"Diagnostics: {output}")


if __name__ == "__main__":
    main()
