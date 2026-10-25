"""Metrics comparing predicted rows with reference rows (sample_output.csv).

- case accuracy: deletion_status matches
- row accuracy: status and the full step list (every field, in order) match exactly
- sequence accuracy: the ordered list of (phase, system, resource, operation) matches
- step precision / recall / F1: steps matched as whole tuples, ignoring order
- field accuracy: per field, comparing step i of the prediction with step i of the reference
"""

from __future__ import annotations

import json
from collections import Counter

FIELDS = ["phase", "system_id", "resource_id", "operation", "state", "evidence_id"]


def _steps(row):
    s = row["steps_json"]
    return json.loads(s) if isinstance(s, str) else s


def step_key(step):
    return tuple(step.get(f, "") for f in FIELDS)


def seq_key(step):
    """What the order of a plan is judged on: which operation, on which resource."""
    return (step.get("phase", ""), step.get("system_id", ""), step.get("resource_id", ""), step.get("operation", ""))


def score(pred_rows: dict, gold_rows: dict) -> dict:
    """pred_rows / gold_rows: case_id -> {"deletion_status", "steps_json"}."""
    n = len(gold_rows)
    status_ok = seq_ok = row_ok = 0
    tp = fp = fn = 0
    field_hits = Counter()
    field_total = 0
    per_case = {}
    for cid, gold in gold_rows.items():
        pred = pred_rows.get(cid, {"deletion_status": "", "steps_json": "[]"})
        gs, ps = _steps(gold), _steps(pred)
        s_ok = pred["deletion_status"] == gold["deletion_status"]
        status_ok += s_ok
        q_ok = [seq_key(x) for x in ps] == [seq_key(x) for x in gs]
        r_ok = [step_key(x) for x in ps] == [step_key(x) for x in gs] and s_ok
        seq_ok += q_ok
        row_ok += r_ok
        gc, pc = Counter(map(step_key, gs)), Counter(map(step_key, ps))
        inter = sum((gc & pc).values())
        tp += inter
        fp += sum(pc.values()) - inter
        fn += sum(gc.values()) - inter
        # field accuracy: positional comparison against the reference step list
        for i, g in enumerate(gs):
            field_total += 1
            p = ps[i] if i < len(ps) else {}
            for f in FIELDS:
                field_hits[f] += p.get(f) == g.get(f)
        per_case[cid] = {"status_ok": s_ok, "sequence_ok": q_ok, "row_ok": r_ok,
                         "missing": sorted(set(gc) - set(pc)), "extra": sorted(set(pc) - set(gc))}
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    return {
        "cases": n,
        "status_accuracy": status_ok / n if n else 0,
        "row_accuracy": row_ok / n if n else 0,
        "sequence_accuracy": seq_ok / n if n else 0,
        "step_precision": prec,
        "step_recall": rec,
        "step_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0,
        "field_accuracy": {f: field_hits[f] / field_total if field_total else 0 for f in FIELDS},
        "per_case": per_case,
    }
