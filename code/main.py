"""Deletion audit agent: reads dataset/, writes output.csv (one row per test case).

    python code/main.py                      # full run -> ./output.csv
    python code/main.py --sample             # audit the sample cases -> code/evaluation/sample_predictions.csv
    python code/main.py --offline            # never call the API; use cached model answers only

Claude is used for two things only: reading screenshots/PDFs into structured records, and
classifying free-form request texts. Everything else (identity resolution, linking, state at
audit time, the step list) is deterministic code in audit/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from audit.data import read_csv  # noqa: E402
from audit.engine import Auditor  # noqa: E402
from audit.intent import classify_requests  # noqa: E402
from audit.llm import Claude  # noqa: E402
from audit.visual import visual_facts  # noqa: E402


def case_key(cid: str):
    tail = cid.rsplit("_", 1)[-1]
    return (int(tail) if tail.isdigit() else 0, cid)


def build(dataset: Path, claude: Claude, log=print):
    sample = read_csv(dataset / "sample_deletion_requests.csv")
    tests = read_csv(dataset / "deletion_requests.csv")
    activity = read_csv(dataset / "system_activity.csv")
    log("reading screenshots and PDFs")
    facts, _ = visual_facts(dataset, claude, activity, log)
    log("classifying request intent")
    intents, reasons = classify_requests(sample + tests, claude, log)
    auditor = Auditor(dataset, facts)
    if auditor.unparsed:
        log(f"  evidence files without facts: {', '.join(auditor.unparsed)}")
    # linking is global: deletion batches are shared between sample and test requests
    auditor.prepare(sample + tests, intents)
    return auditor, sample, tests, intents, reasons


def audit_rows(auditor, requests, intents):
    rows = []
    for req in sorted(requests, key=lambda r: case_key(r["case_id"])):
        res = auditor.audit(req, intents.get(req["case_id"], True))
        rows.append({"case_id": res.case_id, "deletion_status": res.status,
                     "steps_json": json.dumps(res.steps, separators=(",", ":"), sort_keys=True)})
    return rows


def write_csv(path: Path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["case_id", "deletion_status", "steps_json"])
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(ROOT / "dataset"))
    ap.add_argument("--out", default=str(ROOT / "output.csv"))
    ap.add_argument("--sample", action="store_true", help="audit the sample cases instead of the test cases")
    ap.add_argument("--offline", action="store_true", help="use cached model answers only")
    args = ap.parse_args()

    claude = Claude(offline=args.offline)
    if claude.offline:
        print("model calls disabled (offline or ANTHROPIC_API_KEY not set): using cached answers only")
    auditor, sample, tests, intents, _ = build(Path(args.dataset), claude)
    if args.sample:
        out = HERE / "evaluation" / "sample_predictions.csv"
        rows = audit_rows(auditor, sample, intents)
    else:
        out = Path(args.out)
        rows = audit_rows(auditor, tests, intents)
    write_csv(out, rows)
    n_calls = len(claude.session_calls)
    tin = sum(c["input_tokens"] for c in claude.session_calls)
    tout = sum(c["output_tokens"] for c in claude.session_calls)
    print(f"wrote {len(rows)} rows to {out}; new model calls this run: {n_calls} "
          f"({tin} input / {tout} output tokens)")


if __name__ == "__main__":
    main()
