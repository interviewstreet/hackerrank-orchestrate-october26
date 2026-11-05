"""Evaluation against dataset/sample_output.csv: case, step, field and sequence accuracy.

Usage (from the repository root):
    python3 code/evaluation/main.py                 # metrics for the 32 public sample cases
    python3 code/evaluation/main.py --diff case_18  # show expected vs predicted steps for one case
    python3 code/evaluation/main.py --diff all
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from engine.case_analyzer import build_context          # noqa: E402
from engine.pipeline import run_cases                    # noqa: E402

FIELDS = ["phase", "system_id", "resource_id", "operation", "state", "evidence_id"]


def load_expected(path):
    return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
            for r in csv.DictReader(open(path, encoding="utf-8"))}


def key(s):
    return (s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"])


def evaluate(results, expected):
    n = len(results)
    status_ok = exact_ok = 0
    tp = pred_n = exp_n = 0
    field_hits = {f: 0 for f in FIELDS}
    field_total = 0
    seq_scores = []
    for r in results:
        est, esteps = expected[r.case_id]
        status_ok += r.deletion_status == est
        exact_ok += [key(s) for s in r.steps] == [key(s) for s in esteps]
        pk, ek = [key(s) for s in r.steps], [key(s) for s in esteps]
        tp += len(set(pk) & set(ek)); pred_n += len(set(pk)); exp_n += len(set(ek))
        # field accuracy: align steps on (phase, system, resource, operation); compare every field of the expected step
        pidx = {(s["phase"], s["system_id"], s["resource_id"], s["operation"]): s for s in r.steps}
        for e in esteps:
            p = pidx.get((e["phase"], e["system_id"], e["resource_id"], e["operation"]))
            field_total += 1
            for f in FIELDS:
                field_hits[f] += bool(p) and p[f] == e[f]
        seq_scores.append(SequenceMatcher(None, pk, ek).ratio() if (pk or ek) else 1.0)
    prec = tp / pred_n if pred_n else 1.0
    rec = tp / exp_n if exp_n else 1.0
    return {
        "cases": n, "status_accuracy": status_ok / n, "exact_case_match": exact_ok / n,
        "step_precision": prec, "step_recall": rec, "step_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "field_accuracy": {f: field_hits[f] / field_total for f in FIELDS} if field_total else {},
        "sequence_similarity": sum(seq_scores) / n,
        "counts": {"status_ok": status_ok, "exact_ok": exact_ok, "tp": tp, "pred": pred_n, "exp": exp_n},
    }


def show_diff(result, expected):
    est, esteps = expected[result.case_id]
    pk = {key(s): s for s in result.steps}; ek = {key(s): s for s in esteps}
    print(f"### {result.case_id}: expected {est}  predicted {result.deletion_status}")
    for k in ek:
        if k not in pk:
            print("   MISSING  ", k[0][:4], k[1], k[2], k[3], repr(k[5]))
    for k in pk:
        if k not in ek:
            print("   EXTRA    ", k[0][:4], k[1], k[2], k[3], repr(k[5]))
    if [key(s) for s in result.steps if key(s) in ek] != [key(s) for s in esteps if key(s) in pk]:
        print("   (order differs)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", help="case id or 'all'")
    ap.add_argument("--dataset", default=str(ROOT / "dataset"))
    a = ap.parse_args()
    ec = build_context(a.dataset)
    expected = load_expected(Path(a.dataset) / "sample_output.csv")
    results = run_cases(ec.ctx.sample_requests, ec)
    if a.diff:
        for r in results:
            if a.diff == "all" or r.case_id == a.diff:
                if a.diff != "all" or [key(s) for s in r.steps] != [key(s) for s in expected[r.case_id][1]]:
                    show_diff(r, expected)
        return
    print(json.dumps(evaluate(results, expected), indent=2))


if __name__ == "__main__":
    main()
