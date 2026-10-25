#!/usr/bin/env python3
"""Evaluate sample predictions against dataset/sample_output.csv.

Run:  python3 code/evaluation/evaluate.py [--self-check]
Metrics: status accuracy, step precision/recall/F1 (key = phase, system,
resource, operation, state), field accuracy on matched steps, evidence
accuracy, step-count accuracy, exact sequence match and LCS ratio.
Results are saved to code/evaluation/results_latest.json.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import run as run_pipeline                  # noqa: E402
from audit.config import DEFAULT_DATASET_DIR, EVALUATION_DIR, REPO_ROOT  # noqa: E402
from audit.loaders import case_sort_key               # noqa: E402

FIELDS = ["phase", "system_id", "resource_id", "operation", "state",
          "evidence_id"]


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
                for r in csv.DictReader(fh)}


def step_key(s):
    return (s["phase"], s["system_id"], s["resource_id"], s["operation"],
            s["state"])


def lcs_len(a, b):
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, start=1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


def evaluate(pred_path, gold_path):
    pred, gold = load_rows(pred_path), load_rows(gold_path)
    cases = sorted(gold, key=case_sort_key)
    status_ok = 0
    tp = fp = fn = 0
    field_ok = Counter()
    field_total = Counter()
    evidence_ok = evidence_total = 0
    exact = 0
    count_ok = 0
    lcs_scores = []
    diffs = []
    for cid in cases:
        p_status, p_steps = pred.get(cid, ("MISSING", []))
        g_status, g_steps = gold[cid]
        if p_status == g_status:
            status_ok += 1
        if len(p_steps) == len(g_steps):
            count_ok += 1
        p_keys = [step_key(s) for s in p_steps]
        g_keys = [step_key(s) for s in g_steps]
        if p_status == g_status and p_steps == g_steps:
            exact += 1
        lcs_scores.append(lcs_len(p_keys, g_keys) / max(len(p_keys), len(g_keys), 1))
        p_counter, g_counter = Counter(p_keys), Counter(g_keys)
        matched = p_counter & g_counter
        tp += sum(matched.values())
        fp += sum((p_counter - g_counter).values())
        fn += sum((g_counter - p_counter).values())
        # field accuracy over position-aligned steps + evidence on matches
        for ps, gs in zip(p_steps, g_steps):
            for f in FIELDS:
                field_total[f] += 1
                if ps.get(f) == gs.get(f):
                    field_ok[f] += 1
        gold_by_key = {}
        for gs in g_steps:
            gold_by_key.setdefault(step_key(gs), []).append(gs)
        for ps in p_steps:
            bucket = gold_by_key.get(step_key(ps))
            if bucket:
                gs = bucket.pop(0)
                evidence_total += 1
                if ps["evidence_id"] == gs["evidence_id"]:
                    evidence_ok += 1
        if p_steps != g_steps or p_status != g_status:
            diffs.append((cid, p_status, g_status,
                          sorted((g_counter - p_counter).elements()),
                          sorted((p_counter - g_counter).elements()),
                          [(p["resource_id"], p["evidence_id"], g["evidence_id"])
                           for p, g in zip(p_steps, g_steps)
                           if p["evidence_id"] != g["evidence_id"]]))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    results = {
        "cases": len(cases),
        "status_accuracy": status_ok / len(cases),
        "status_correct": status_ok,
        "step_precision": precision, "step_recall": recall, "step_f1": f1,
        "field_accuracy": {f: (field_ok[f] / field_total[f] if field_total[f] else 0)
                           for f in FIELDS},
        "evidence_accuracy_matched": (evidence_ok / evidence_total
                                      if evidence_total else 0),
        "step_count_accuracy": count_ok / len(cases),
        "exact_match_cases": exact,
        "exact_match_rate": exact / len(cases),
        "mean_lcs_ratio": sum(lcs_scores) / len(lcs_scores),
    }
    print(f"Cases: {len(cases)}")
    print(f"Status accuracy: {status_ok}/{len(cases)} = {results['status_accuracy']:.3f}")
    print(f"Step P/R/F1: {precision:.3f} / {recall:.3f} / {f1:.3f}")
    print("Field accuracy:", {k: round(v, 3) for k, v in results["field_accuracy"].items()})
    print(f"Evidence accuracy (matched steps): {results['evidence_accuracy_matched']:.3f}")
    print(f"Step-count accuracy: {results['step_count_accuracy']:.3f}")
    print(f"Exact ordered match: {exact}/{len(cases)}")
    print(f"Mean LCS ratio: {results['mean_lcs_ratio']:.3f}")
    diffs.sort(key=lambda d: -(len(d[3]) + len(d[4])))
    print("\nWorst cases:")
    for cid, ps, gs, missing, extra, ev in diffs[:10]:
        print(f"  {cid}: pred={ps} gold={gs} MISSING={missing} EXTRA={extra} "
              f"WRONG_EVIDENCE={ev[:3]}")
    (EVALUATION_DIR / "results_latest.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    return results


def self_check(out_path):
    with open(out_path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    rows = list(csv.DictReader(open(out_path, newline="", encoding="utf-8")))
    counts = Counter(r["deletion_status"] for r in rows)
    print(f"Self-check: {len(rows)} rows, sha256={digest}")
    print("Status distribution:", dict(counts))
    # determinism: file already written once by main; caller re-runs to compare
    return digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--no-llm", action="store_true", default=True)
    args = ap.parse_args()
    pred_path = EVALUATION_DIR / "sample_predictions.csv"
    run_pipeline(DEFAULT_DATASET_DIR, pred_path, use_llm=False,
                   requests_file="sample_deletion_requests.csv")
    evaluate(pred_path, DEFAULT_DATASET_DIR / "sample_output.csv")
    if args.self_check:
        out = REPO_ROOT / "output.csv"
        if out.exists():
            self_check(out)


if __name__ == "__main__":
    main()
