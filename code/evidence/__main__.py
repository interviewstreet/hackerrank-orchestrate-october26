"""Full-corpus scan report.

Usage (from the repository root)::

    python -m evidence                       # needs code/ on PYTHONPATH, or:
    python code/evidence/__main__.py [--dataset DIR] [--ocr-mode auto|cache_only|force]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence.scanner import EvidenceScanner  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scan all evidence listed in evidence_files.csv")
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2] / "dataset"))
    ap.add_argument("--ocr-mode", default="auto", choices=["auto", "cache_only", "force"])
    ap.add_argument("--per-file", action="store_true", help="print per-file statistics")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    scanner = EvidenceScanner(args.dataset, ocr_mode=args.ocr_mode)
    scanner.load()
    elapsed = time.perf_counter() - t0

    summary = scanner.summary()
    summary["load_seconds"] = round(elapsed, 2)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.per_file:
        for ev in scanner.files():
            st = scanner.file_stats().get(ev.file_id, {})
            print(f"{ev.file_id}  {ev.extension:4}  recs={st.get('records', 0):4}  scopes={st.get('scopes', 0):3}  "
                  f"issues={st.get('issues', 0)}  {ev.file_path}")
    if scanner.issues:
        print("\nIssues:")
        for i in scanner.issues:
            print(f"  [{i.severity}] {i.evidence_id}: {i.message}")
    else:
        print("\nIssues: none")
    hard = [i for i in scanner.issues if i.severity in ("error", "unsupported")]
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
