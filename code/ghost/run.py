"""Run the pipeline over a list of requests and write all outputs."""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from .config import REVIEW_JSONL, Settings
from .dataset_io import write_output
from .logging_setup import stage
from .models import CaseResult, Request
from .tables.build import load_or_build
from .pipeline.case import CasePipeline
from .pipeline.intent import IntentClassifier
from .pipeline.policy import Policy

log = logging.getLogger(__name__)


def build_context(settings: Settings, use_cache: bool = True) -> CasePipeline:
    """Build or load the startup tables, load the policy, and wire the per-case pipeline."""
    ctx = load_or_build(use_cache=use_cache)
    return CasePipeline(ctx, Policy.load(), IntentClassifier(fallback=None))


def run_case(request: Request, pipeline: CasePipeline) -> CaseResult:
    return pipeline.run(request)


def run_all(requests: list[Request], ctx: CasePipeline) -> list[CaseResult]:
    results: list[CaseResult] = []
    with stage(log, f"cases ({len(requests)})"):
        for req in requests:
            try:
                result = run_case(req, ctx)
            except Exception:  # one bad case must not sink the run
                log.exception("%s: unhandled error, emitting INCOMPLETE with no steps", req.case_id)
                result = CaseResult(req.case_id, "INCOMPLETE", notes=["unhandled error"])
            log.debug("%s: %s, %d steps", req.case_id, result.status, len(result.steps))
            results.append(result)
    counts = Counter(r.status for r in results)
    log.info("status counts: %s", dict(sorted(counts.items())))
    return results


def write_all(results: list[CaseResult], output_path: Path) -> None:
    write_output(results, output_path)
    flagged = [r for r in results if r.notes]
    with REVIEW_JSONL.open("w", encoding="utf-8") as fh:
        for r in sorted(flagged, key=lambda r: r.case_id):
            fh.write(json.dumps({"case_id": r.case_id, "status": r.status, "notes": r.notes},
                                sort_keys=True) + "\n")
    log.info("review items: %d (see %s)", len(flagged), REVIEW_JSONL)
