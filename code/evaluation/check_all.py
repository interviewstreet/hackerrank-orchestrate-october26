#!/usr/bin/env python3
"""Quality gate (SPEC §13.5): unit + e2e tests, sample regression vs the committed baseline, and the
label-free invariants on a fresh 518-case replay run. Exits non-zero on any failure.

    python3 code/evaluation/check_all.py            # ~1 minute, offline (replay cache)
    python3 code/evaluation/check_all.py --update-baseline
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
CODE = EVAL_DIR.parent
REPO = CODE.parent
BASELINE = EVAL_DIR / "baseline.json"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(EVAL_DIR))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args()
    results: list[tuple[str, bool, str]] = []
    t0 = time.time()

    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                          cwd=CODE, capture_output=True, text=True)
    tail = (proc.stderr.strip().splitlines() or ["?"])[-1]
    ran = next((l for l in proc.stderr.splitlines() if l.startswith("Ran ")), "")
    results.append(("unit + e2e tests", proc.returncode == 0, f"{ran}; {tail}"))

    import main as evaluation
    with tempfile.TemporaryDirectory(prefix="gda_gate_") as tmp:
        tmp = Path(tmp)
        sample = evaluation.sample_metrics(tmp, "replay")
        dev, hold = sample["dev"], sample["holdout"]
        current = {k: round(dev[k], 4) for k in ("status_accuracy", "step_f1", "sequence_accuracy", "citation_accuracy")}
        if args.update_baseline or not BASELINE.exists():
            BASELINE.write_text(json.dumps(current, indent=2) + "\n")
        base = json.loads(BASELINE.read_text())
        regress = [k for k in base if current[k] + 1e-9 < base[k]]
        results.append(("sample dev regression", not regress,
                         f"dev {current} vs baseline; holdout status {hold['status_accuracy']:.3f} seq {hold['sequence_accuracy']:.3f}"
                         + (f"; REGRESSED: {regress}" if regress else "")))

        out = tmp / "output.csv"
        p = subprocess.run([sys.executable, str(CODE / "main.py"), "--out", str(out)], capture_output=True, text=True)
        results.append(("518-case replay run", p.returncode == 0 and out.exists(), (p.stdout + p.stderr).strip().splitlines()[0]
                        if (p.stdout + p.stderr).strip() else "no output"))
        import invariants
        from ghostaudit.config import DEFAULT_DATASET_DIR as D
        inv = invariants.run_all(out, D, D / "deletion_requests.csv")
        for k, v in inv.items():
            if isinstance(v, list):
                results.append((f"invariant: {k}", not v, "ok" if not v else f"{len(v)} failure(s): {v[0]}"))
        submitted = REPO / "output.csv"
        same = submitted.exists() and submitted.read_bytes() == out.read_bytes()
        results.append(("output.csv matches a fresh replay", same, str(submitted)))

    width = max(len(n) for n, _, _ in results)
    print(f"\n{'check'.ljust(width)}  result  detail")
    for name, ok, detail in results:
        print(f"{name.ljust(width)}  {'PASS' if ok else 'FAIL'}    {detail}")
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - t0:.0f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
