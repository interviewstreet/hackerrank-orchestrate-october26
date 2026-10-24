"""Scorer and evaluation suite.

Usage:
    python code/evaluation/main.py [--requests PATH] [--gold PATH] [--pred PATH] [--details]
                                   [--no-llm] [--out PATH] [--skip-suite]

Without ``--pred`` the pipeline runs on ``--requests`` in memory, in the same mode as the
submission run: model results replayed from ``llm_snapshot.py`` (``--no-llm``: deterministic
only). It then runs the frozen custom cases (``custom.py``) and the metamorphic checks
(``metamorphic.py``), prints everything and writes it to ``--out`` (Markdown) and a JSON twin.

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
import json
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import custom  # noqa: E402
import metamorphic  # noqa: E402
from llm_client import LLMClient  # noqa: E402
from loaders import DATASET_DIR, load_requests  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent / "results.md"

STEP_FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")
CONTENT_FIELDS = STEP_FIELDS[1:]
# "exact": a step matches only when all 7 fields are equal (a step shifted by a missing earlier
# step does not match). "content": the 6 fields without step_no (which step, not where).
STEP_METRICS = {"exact": STEP_FIELDS, "content": CONTENT_FIELDS}


def read_answers(path: Path) -> dict[str, tuple[str, list[dict]]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: (row["deletion_status"], json.loads(row["steps_json"] or "[]"))
                for row in csv.DictReader(handle)}


def predict(requests_path: Path, use_llm: bool = True):
    """Rows plus the context (agent stats). ``use_llm``: replay the snapshot, never the network."""
    pipeline = custom.load_pipeline()
    client = LLMClient.from_config(offline=True) if use_llm else None
    ctx = pipeline.build_context(client=client, vision=use_llm, agent=use_llm)
    results = pipeline.run_cases(load_requests(requests_path), ctx)
    return {r.case_id: (r.status, json.loads(pipeline.serialize_steps(r.steps))) for r in results}, ctx


def _ratio(num: float, den: float) -> float:
    return num / den if den else 0.0


def _matched(g_steps: list[dict], p_steps: list[dict], fields: tuple[str, ...]) -> int:
    """Multiset matches of steps compared on ``fields``."""
    g = Counter(tuple(s.get(f) for f in fields) for s in g_steps)
    p = Counter(tuple(s.get(f) for f in fields) for s in p_steps)
    return sum((g & p).values())


def _prf(tp: int, n_gold: int, n_pred: int) -> dict:
    precision, recall = _ratio(tp, n_pred), _ratio(tp, n_gold)
    f1 = _ratio(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {"gold": n_gold, "pred": n_pred, "matched": tp, "precision": precision, "recall": recall, "f1": f1}


def score(gold: dict[str, tuple[str, list[dict]]], pred: dict[str, tuple[str, list[dict]]]) -> dict:
    n = len(gold)
    status_ok = seq_ok = row_ok = 0
    tp = dict.fromkeys(STEP_METRICS, 0)
    n_gold_steps = n_pred_steps = 0
    field_hits: Counter[str] = Counter()
    field_den = 0
    confusion: Counter[tuple[str, str]] = Counter()
    per_case = []
    for case_id, (g_status, g_steps) in gold.items():
        p_status, p_steps = pred.get(case_id, ("MISSING", []))
        confusion[(g_status, p_status)] += 1
        s_ok = g_status == p_status
        q_ok = g_steps == p_steps
        status_ok += s_ok
        seq_ok += q_ok
        row_ok += s_ok and q_ok

        hits = {name: _matched(g_steps, p_steps, fields) for name, fields in STEP_METRICS.items()}
        for name, hit in hits.items():
            tp[name] += hit
        n_gold_steps += len(g_steps)
        n_pred_steps += len(p_steps)

        width = max(len(g_steps), len(p_steps))
        field_den += width
        for i in range(min(len(g_steps), len(p_steps))):
            for f in STEP_FIELDS:
                field_hits[f] += g_steps[i].get(f) == p_steps[i].get(f)
        per_case.append((case_id, g_status, p_status, len(g_steps), len(p_steps), hits["exact"], hits["content"]))

    return {
        "cases": n,
        "status_accuracy": (status_ok, n),
        "sequence_accuracy": (seq_ok, n),
        "row_accuracy": (row_ok, n),
        "steps": {name: _prf(tp[name], n_gold_steps, n_pred_steps) for name in STEP_METRICS},
        "field_accuracy": {f: (field_hits[f], field_den) for f in STEP_FIELDS},
        "confusion": confusion,
        "per_case": per_case,
    }


def render(report: dict, details: bool = False) -> str:
    def frac(pair):
        num, den = pair
        return f"{num}/{den} = {_ratio(num, den):.3f}"

    ex, co = report["steps"]["exact"], report["steps"]["content"]
    lines = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Cases | {report['cases']} |",
        f"| Status accuracy | {frac(report['status_accuracy'])} |",
        f"| Sequence accuracy (exact steps) | {frac(report['sequence_accuracy'])} |",
        f"| Row accuracy (status + steps) | {frac(report['row_accuracy'])} |",
        f"| Steps gold / pred | {ex['gold']} / {ex['pred']} |",
        f"| Exact step (7 fields incl. step_no): matched, P / R / F1 | {ex['matched']}, "
        f"{ex['precision']:.3f} / {ex['recall']:.3f} / {ex['f1']:.3f} |",
        f"| Content match (6 fields, no step_no): matched, P / R / F1 | {co['matched']}, "
        f"{co['precision']:.3f} / {co['recall']:.3f} / {co['f1']:.3f} |",
    ]
    for f, pair in report["field_accuracy"].items():
        lines.append(f"| Field accuracy `{f}` | {frac(pair)} |")
    lines += ["", *confusion_table(report["confusion"])]
    if details:
        lines.append("")
        lines.append("| case | gold | pred | gold steps | pred steps | exact matched | content matched |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in report["per_case"]:
            lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


STATUSES = ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")


def confusion_table(confusion: Counter) -> list[str]:
    preds = list(STATUSES) + sorted({p for _, p in confusion} - set(STATUSES))
    lines = ["Status confusion (rows: gold, columns: predicted):", "",
             "| gold \\ pred | " + " | ".join(preds) + " |", "| --- |" + " --- |" * len(preds)]
    for g in STATUSES:
        lines.append(f"| {g} | " + " | ".join(str(confusion.get((g, p), 0)) for p in preds) + " |")
    return lines


def render_suite(cases: list[dict], checks: list[dict], agent: dict | None) -> str:
    lines = ["", "Custom cases (frozen, expected rows written from the rules):", "",
             "| case | result | status | problems |", "| --- | --- | --- | --- |"]
    for c in cases:
        lines.append(f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} | {c['status']} | "
                     f"{'; '.join(c['problems']) or '-'} |")
    lines += ["", "Metamorphic checks:", "", "| check | result |", "| --- | --- |"]
    lines += [f"| {m['name']} | {'PASS' if m['passed'] else 'FAIL'} |" for m in checks]
    if agent is not None:
        lines += ["", "Agent on the scored requests: " + ", ".join(f"{k}={v}" for k, v in agent.items())]
    return "\n".join(lines)


def _agent_stats(ctx) -> dict | None:
    if ctx is None:
        return None
    s = ctx.agent_stats
    return {"runs": s.runs, "proposals": s.proposals, "accepted": s.accepted, "rejected": dict(s.rejected)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score predictions against the sample answers")
    parser.add_argument("--requests", default=str(DATASET_DIR / "sample_deletion_requests.csv"))
    parser.add_argument("--gold", default=str(DATASET_DIR / "sample_output.csv"))
    parser.add_argument("--pred", help="score an existing output CSV instead of running the pipeline")
    parser.add_argument("--details", action="store_true", help="print a per-case table")
    parser.add_argument("--no-llm", action="store_true", help="deterministic pipeline only")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Markdown report path ('' to skip)")
    parser.add_argument("--skip-suite", action="store_true", help="score only: no custom or metamorphic run")
    args = parser.parse_args(argv)

    gold = read_answers(Path(args.gold))
    ctx = None
    if args.pred:
        pred = read_answers(Path(args.pred))
    else:
        pred, ctx = predict(Path(args.requests), use_llm=not args.no_llm)
    report = score(gold, pred)
    text = render(report, details=args.details)
    cases = checks = []
    if not args.skip_suite:
        cases = [custom.check(c) for c in custom.load_cases()]
        checks = metamorphic.all_checks()
        text += "\n" + render_suite(cases, checks, _agent_stats(ctx))
    print(text)
    if args.out:
        out = Path(args.out)
        out.write_text(text + "\n", encoding="utf-8")
        summary = {k: v for k, v in report.items() if k not in ("confusion", "per_case")}
        summary["confusion"] = {f"{g}->{p}": c for (g, p), c in sorted(report["confusion"].items())}
        summary["custom_cases"] = [{k: c[k] for k in ("name", "passed", "problems", "agent")} for c in cases]
        summary["metamorphic"] = checks
        summary["agent"] = _agent_stats(ctx)
        out.with_suffix(".json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    failed = [c for c in cases if not c["passed"]] + [m for m in checks if not m["passed"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
