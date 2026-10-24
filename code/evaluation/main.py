"""Scorer: run the pipeline on the public samples and compare with the sample answers.

Usage:
    python code/evaluation/main.py [--requests PATH] [--gold PATH] [--pred PATH] [--details]

Without ``--pred`` the pipeline runs on ``--requests`` in memory.

Metrics
- status accuracy: share of cases with the gold ``deletion_status``.
- step precision / recall / F1: micro-averaged multiset match of step tuples
  (phase, system_id, resource_id, operation, state, evidence_id); ``step_no`` is excluded.
- field accuracy: steps aligned by position inside a case; denominator per case is
  max(len(gold), len(pred)), so missing and extra steps count as wrong.
- sequence accuracy: share of cases whose full step array equals gold exactly.
- row accuracy: status and sequence both exact.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from loaders import DATASET_DIR, load_requests  # noqa: E402

STEP_FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")
TUPLE_FIELDS = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")


def _load_pipeline():
    spec = importlib.util.spec_from_file_location("audit_pipeline", CODE_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up here
    spec.loader.exec_module(module)
    return module


def read_answers(path: Path) -> dict[str, tuple[str, list[dict]]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: (row["deletion_status"], json.loads(row["steps_json"] or "[]"))
                for row in csv.DictReader(handle)}


def predict(requests_path: Path) -> dict[str, tuple[str, list[dict]]]:
    pipeline = _load_pipeline()
    ctx = pipeline.build_context()
    results = pipeline.run_cases(load_requests(requests_path), ctx)
    return {r.case_id: (r.status, json.loads(pipeline.serialize_steps(r.steps))) for r in results}


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def score(gold: dict[str, tuple[str, list[dict]]], pred: dict[str, tuple[str, list[dict]]]) -> dict:
    n = len(gold)
    status_ok = seq_ok = row_ok = 0
    tp = n_gold_steps = n_pred_steps = 0
    field_hits = Counter()
    field_den = 0
    confusion = Counter()
    per_case = []
    for case_id, (g_status, g_steps) in gold.items():
        p_status, p_steps = pred.get(case_id, ("MISSING", []))
        confusion[(g_status, p_status)] += 1
        s_ok = g_status == p_status
        q_ok = g_steps == p_steps
        status_ok += s_ok
        seq_ok += q_ok
        row_ok += s_ok and q_ok

        g_tuples = Counter(tuple(s.get(f) for f in TUPLE_FIELDS) for s in g_steps)
        p_tuples = Counter(tuple(s.get(f) for f in TUPLE_FIELDS) for s in p_steps)
        hit = sum((g_tuples & p_tuples).values())
        tp += hit
        n_gold_steps += len(g_steps)
        n_pred_steps += len(p_steps)

        width = max(len(g_steps), len(p_steps))
        field_den += width
        for i in range(min(len(g_steps), len(p_steps))):
            for f in STEP_FIELDS:
                field_hits[f] += g_steps[i].get(f) == p_steps[i].get(f)
        per_case.append((case_id, g_status, p_status, len(g_steps), len(p_steps), hit))

    precision = _ratio(tp, n_pred_steps)
    recall = _ratio(tp, n_gold_steps)
    f1 = _ratio(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {
        "cases": n,
        "status_accuracy": (status_ok, n),
        "sequence_accuracy": (seq_ok, n),
        "row_accuracy": (row_ok, n),
        "steps": {"gold": n_gold_steps, "pred": n_pred_steps, "matched": tp,
                  "precision": precision, "recall": recall, "f1": f1},
        "field_accuracy": {f: (field_hits[f], field_den) for f in STEP_FIELDS},
        "confusion": confusion,
        "per_case": per_case,
    }


def render(report: dict, details: bool = False) -> str:
    def frac(pair):
        num, den = pair
        return f"{num}/{den} = {_ratio(num, den):.3f}"

    st = report["steps"]
    lines = [
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| Cases | {report['cases']} |",
        f"| Status accuracy | {frac(report['status_accuracy'])} |",
        f"| Sequence accuracy (exact steps) | {frac(report['sequence_accuracy'])} |",
        f"| Row accuracy (status + steps) | {frac(report['row_accuracy'])} |",
        f"| Steps gold / pred / matched | {st['gold']} / {st['pred']} / {st['matched']} |",
        f"| Step precision / recall / F1 | {st['precision']:.3f} / {st['recall']:.3f} / {st['f1']:.3f} |",
    ]
    for f, pair in report["field_accuracy"].items():
        lines.append(f"| Field accuracy `{f}` | {frac(pair)} |")
    lines.append("")
    lines.append("Status confusion (gold -> pred): " + ", ".join(
        f"{g}->{p}: {c}" for (g, p), c in sorted(report["confusion"].items())))
    if details:
        lines.append("")
        lines.append("| case | gold | pred | gold steps | pred steps | matched |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in report["per_case"]:
            lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score predictions against the sample answers")
    parser.add_argument("--requests", default=str(DATASET_DIR / "sample_deletion_requests.csv"))
    parser.add_argument("--gold", default=str(DATASET_DIR / "sample_output.csv"))
    parser.add_argument("--pred", help="score an existing output CSV instead of running the pipeline")
    parser.add_argument("--details", action="store_true", help="print a per-case table")
    args = parser.parse_args(argv)

    gold = read_answers(Path(args.gold))
    pred = read_answers(Path(args.pred)) if args.pred else predict(Path(args.requests))
    print(render(score(gold, pred), details=args.details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
