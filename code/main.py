#!/usr/bin/env python3
"""Ghost Data Still Exists — deletion-audit agent.

Usage:
    python3 code/main.py                       # 518 evaluation requests -> ./output.csv
    python3 code/main.py --cases sample        # 32 public samples -> ./sample_predictions.csv
    python3 code/main.py --dataset-dir DIR --requests FILE --out PATH --trace-dir DIR

LLM backend: GDA_LLM_BACKEND=replay (default, committed cache) | claude_cli | anthropic | openai | ollama | offline.
Vision: GDA_VISION=1 (default; 0 = no vision model), GDA_VISION_GROUNDING=1 (default; drop vision records the image's OCR text does not show),
GDA_VISION_OCR_FALLBACK=1 (default; read a screenshot/PDF by OCR when no vision result exists). See README.md.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ghostaudit.config import (  # noqa: E402
    BACKENDS, CACHE_DIR, DEFAULT_DATASET_DIR, EXIT_INPUT_MISSING, EXIT_INVALID_OUTPUT, EXIT_OK, EXIT_UNVERIFIED_EVIDENCE, REPO_ROOT,
    DatasetPaths,
)
from ghostaudit.llm.budget import BudgetExceeded  # noqa: E402
from ghostaudit.pipeline import run  # noqa: E402

MODEL_PATH = CACHE_DIR / "workflow_model.json"


def main(argv: list[str] | None = None) -> NoReturn:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    ap.add_argument("--cases", choices=["eval", "sample"], default="eval")
    ap.add_argument("--requests", type=Path, help="override the request CSV")
    ap.add_argument("--out", type=Path, help="output CSV path")
    ap.add_argument("--trace-dir", type=Path, help="write one <case_id>.json decision trace per case")
    ap.add_argument("--backend", choices=BACKENDS, help="override GDA_LLM_BACKEND")
    ap.add_argument("--workflow-model", type=Path,
                    help=f"frozen workflow model (default for the bundled dataset: {MODEL_PATH.relative_to(REPO_ROOT)})")
    ap.add_argument("--relearn-workflow-model", action="store_true", help="learn the workflow model and save it")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    root = args.dataset_dir.resolve()
    default_req = root / ("sample_deletion_requests.csv" if args.cases == "sample" else "deletion_requests.csv")
    requests = (args.requests or default_req).resolve()
    out = args.out or (REPO_ROOT / ("sample_predictions.csv" if args.cases == "sample" else "output.csv"))
    missing = [p for p in (root, requests, *(DatasetPaths(root, requests).required())) if not p.exists()]
    if missing:
        print("error: dataset input not found: " + ", ".join(str(p) for p in missing), file=sys.stderr)
        print("hint: pass --dataset-dir pointing at the participant dataset/ folder", file=sys.stderr)
        sys.exit(EXIT_INPUT_MISSING)
    try:
        model = args.workflow_model
        if model is None and root == DEFAULT_DATASET_DIR.resolve() and not args.relearn_workflow_model:
            model = MODEL_PATH
        save = MODEL_PATH if args.relearn_workflow_model else None
        res = run(DatasetPaths(root, requests), out, args.trace_dir, backend=args.backend,
                  workflow_model=model, save_model=save)
    except BudgetExceeded as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(BudgetExceeded.exit_code)
    counts: dict[str, int] = {}
    for r in res.results:
        counts[r.deletion_status] = counts.get(r.deletion_status, 0) + 1
    print(f"wrote {len(res.results)} rows to {out}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if res.llm is not None:
        print(res.llm.spend_line())
    unread = sorted(res.context.store.unreadable)
    at_risk = [r.case_id for r in res.results if r.trace.get("unverified_evidence")]
    if unread:
        print(f"warning: {len(unread)} evidence file(s) could not be fully read (missing, no vision-model result, or OCR only: {', '.join(f for f, _ in unread)}); "
              f"{len(at_risk)} COMPLETE verdict(s) are unverified against them (see 'unverified_evidence' in traces)",
              file=sys.stderr)
        if at_risk and os.environ.get("GDA_STRICT_EVIDENCE", "1") != "0":
            # fail loudly rather than towards COMPLETE: every row is written, but the run is not a clean pass
            print("error: some COMPLETE verdicts rest on evidence that could not be read; restore the missing file, "
                  "the LLM cache or a vision backend, or set GDA_STRICT_EVIDENCE=0 to accept them", file=sys.stderr)
            sys.exit(EXIT_UNVERIFIED_EVIDENCE)
    if res.errors:
        print(f"{len(res.errors)} output validation error(s):", file=sys.stderr)
        for e in res.errors[:20]:
            print("  " + e, file=sys.stderr)
        sys.exit(EXIT_INVALID_OUTPUT)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
