"""
evaluate.py — score a predictions CSV against an expected CSV.

    python code/main.py --requests sample_deletion_requests.csv --output evaluation/sample_predictions.csv
    python code/evaluate.py evaluation/sample_predictions.csv dataset/sample_output.csv

Metrics (all deterministic, no model calls):
  * case status accuracy        deletion_status equal
  * exact case accuracy         status and the full step list equal
  * step-level accuracy         position-wise: step i equal in all 7 fields,
                                over max(len(pred), len(exp)) positions
  * step precision / recall / F1 order-insensitive multiset of steps
                                (step_no ignored)
  * field-level accuracy        position-wise per field, over max lengths
  * sequence accuracy           ordered (phase, system_id, resource_id,
                                operation) list equal
JSON object-key order and whitespace are ignored, array order is kept.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")


def load(path: str | Path) -> dict[str, tuple[str, list[dict]]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"] or "[]"))
                for r in csv.DictReader(fh)}


def _key(s: dict) -> tuple:
    return tuple(s.get(f) for f in FIELDS if f != "step_no")


def score(pred: dict, exp: dict) -> dict:
    cases = sorted(exp)
    n = len(cases)
    status_ok = exact_ok = seq_ok = 0
    pos_total = pos_ok = 0
    field_ok = Counter()
    tp = fp = fn = 0
    failures = []
    for cid in cases:
        es, esteps = exp[cid]
        ps, psteps = pred.get(cid, ("<missing>", []))
        status_ok += ps == es
        same_steps = [_key(s) for s in psteps] == [_key(s) for s in esteps] and \
            [s.get("step_no") for s in psteps] == [s.get("step_no") for s in esteps]
        exact_ok += (ps == es and same_steps)
        seq = lambda st: [(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation")) for s in st]  # noqa: E731
        seq_ok += seq(psteps) == seq(esteps)
        m = max(len(psteps), len(esteps))
        pos_total += m
        for i in range(m):
            p = psteps[i] if i < len(psteps) else {}
            e = esteps[i] if i < len(esteps) else {}
            if p and e and all(p.get(f) == e.get(f) for f in FIELDS):
                pos_ok += 1
            for f in FIELDS:
                field_ok[f] += bool(p) and bool(e) and p.get(f) == e.get(f)
        pc, ec = Counter(map(_key, psteps)), Counter(map(_key, esteps))
        inter = sum((pc & ec).values())
        tp += inter
        fp += sum(pc.values()) - inter
        fn += sum(ec.values()) - inter
        if ps != es or not same_steps:
            failures.append({"case_id": cid, "expected_status": es, "predicted_status": ps,
                             "missing": sorted(set(map(_key, esteps)) - set(map(_key, psteps))),
                             "extra": sorted(set(map(_key, psteps)) - set(map(_key, esteps)))})
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    return {
        "cases": n,
        "status_accuracy": status_ok / n,
        "exact_case_accuracy": exact_ok / n,
        "sequence_accuracy": seq_ok / n,
        "step_level_accuracy": pos_ok / pos_total if pos_total else 1.0,
        "step_precision": prec, "step_recall": rec,
        "step_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "field_accuracy": {f: field_ok[f] / pos_total if pos_total else 1.0 for f in FIELDS},
        "failures": failures,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    res = score(load(argv[1]), load(argv[2]))
    for k, v in res.items():
        if k == "failures":
            continue
        if isinstance(v, dict):
            print(f"{k}:")
            for f, x in v.items():
                print(f"    {f:<12} {x:.3f}")
        else:
            print(f"{k:<22} {v:.3f}" if isinstance(v, float) else f"{k:<22} {v}")
    print(f"failing cases: {len(res['failures'])}")
    for f in res["failures"]:
        print(f"  {f['case_id']}: expected {f['expected_status']}, got {f['predicted_status']}")
        for s in f["missing"]:
            print("      missing", s)
        for s in f["extra"]:
            print("      extra  ", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
