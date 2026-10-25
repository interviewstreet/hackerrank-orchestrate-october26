"""Score predictions against labeled answers.

    python3 code/evaluation/main.py                 # run pipeline on the 32 samples, then score
    python3 code/evaluation/main.py --pred FILE     # score an existing predictions CSV
    python3 code/evaluation/main.py --show case_21  # print a step-by-step diff for cases

Metrics
  case accuracy      deletion_status equal
  sequence accuracy  whole steps_json array equal (order included, step_no included)
  step P/R/F1        multiset match of full steps (phase, system, resource, operation, state, evidence)
  field accuracy     gold steps aligned to predictions on (phase, system_id, resource_id);
                     per field, share of gold steps whose aligned prediction has the same value
Groups: all, hand-made samples 01-10, realistic samples 11-32.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from ghost.config import CACHE_DIR, SAMPLE_OUTPUT_CSV  # noqa: E402

FIELDS = ("operation", "state", "evidence_id")
STEP_KEYS = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")


def load(path: Path) -> dict[str, tuple[str, list[dict]]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
                for r in csv.DictReader(fh)}


def step_tuple(s: dict) -> tuple:
    return tuple(s.get(k, "") for k in STEP_KEYS)


def score(gold: dict, pred: dict, case_ids: list[str]) -> dict:
    m = Counter()
    for cid in case_ids:
        g_status, g_steps = gold[cid]
        p_status, p_steps = pred.get(cid, ("<missing>", []))
        m["cases"] += 1
        m["status_ok"] += g_status == p_status
        m["seq_ok"] += g_steps == p_steps

        g_multi, p_multi = Counter(map(step_tuple, g_steps)), Counter(map(step_tuple, p_steps))
        m["tp"] += sum((g_multi & p_multi).values())
        m["gold_steps"] += sum(g_multi.values())
        m["pred_steps"] += sum(p_multi.values())

        aligned = {(s["phase"], s["system_id"], s["resource_id"]): s for s in p_steps}
        for s in g_steps:
            p = aligned.get((s["phase"], s["system_id"], s["resource_id"]))
            m["resource_found"] += p is not None
            for f in FIELDS:
                m[f"field_{f}"] += p is not None and p.get(f) == s.get(f)

    def ratio(a: str, b: str) -> float:
        return m[a] / m[b] if m[b] else 0.0

    precision, recall = ratio("tp", "pred_steps"), ratio("tp", "gold_steps")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    out = {
        "cases": m["cases"],
        "case_accuracy": ratio("status_ok", "cases"),
        "sequence_accuracy": ratio("seq_ok", "cases"),
        "step_precision": precision,
        "step_recall": recall,
        "step_f1": f1,
        "resource_recall": ratio("resource_found", "gold_steps"),
    }
    out.update({f"field_{f}": ratio(f"field_{f}", "gold_steps") for f in FIELDS})
    return out


def print_report(gold: dict, pred: dict) -> dict[str, dict]:
    ids = sorted(gold)
    groups = {
        "all": ids,
        "01-10": [c for c in ids if int(c.split("_")[1]) <= 10],
        "11-32": [c for c in ids if int(c.split("_")[1]) > 10],
    }
    reports = {name: score(gold, pred, cids) for name, cids in groups.items()}
    metrics = [k for k in reports["all"] if k != "cases"]
    print(f"{'metric':<20}" + "".join(f"{g:>10}" for g in groups))
    print(f"{'cases':<20}" + "".join(f"{reports[g]['cases']:>10}" for g in groups))
    for k in metrics:
        print(f"{k:<20}" + "".join(f"{reports[g][k]:>10.1%}" for g in groups))
    return reports


def show(gold: dict, pred: dict, case_id: str) -> None:
    g_status, g_steps = gold[case_id]
    p_status, p_steps = pred.get(case_id, ("<missing>", []))
    print(f"\n== {case_id}  gold={g_status}  pred={p_status}")
    g_set, p_set = Counter(map(step_tuple, g_steps)), Counter(map(step_tuple, p_steps))
    for t in sorted(set(g_set) | set(p_set)):
        mark = "  " if g_set[t] and p_set[t] else ("- " if g_set[t] else "+ ")
        print(mark + " ".join(t))
    print("(- missing from prediction, + extra in prediction)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gold", type=Path, default=SAMPLE_OUTPUT_CSV)
    ap.add_argument("--pred", type=Path, default=None, help="predictions CSV; default runs the pipeline")
    ap.add_argument("--show", nargs="*", default=[], help="case ids to diff, or 'failed'")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", type=Path, default=None, help="also write metrics as JSON")
    args = ap.parse_args(argv)

    pred_path = args.pred
    if pred_path is None:
        import main as pipeline_main  # code/main.py
        pred_path = CACHE_DIR / "sample_predictions.csv"
        flags = ["--input", "sample", "--output", str(pred_path)]
        if args.offline:
            flags.append("--offline")
        if pipeline_main.main(flags) != 0:
            return 1

    gold, pred = load(args.gold), load(pred_path)
    reports = print_report(gold, pred)

    targets = args.show
    if targets == ["failed"]:
        targets = [c for c in sorted(gold) if gold[c] != pred.get(c)]
    for cid in targets:
        show(gold, pred, cid)
    if args.json:
        args.json.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
