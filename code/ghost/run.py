"""Run the pipeline over a list of requests and write all outputs."""
from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from .config import REQUESTS_CSV, REVIEW_JSONL, SAMPLE_REQUESTS_CSV, Settings
from .dataset_io import load_requests, write_output
from .logging_setup import stage
from .models import CaseResult, Request
from .tables.build import load_or_build
from .pipeline.case import CasePipeline
from .pipeline.intent import IntentClassifier
from .pipeline.linkage import build_linkage
from .llm.client import ModelClient
from .llm.intent_fallback import make_fallback
from .pipeline.policy import Policy

log = logging.getLogger(__name__)


def build_context(settings: Settings, use_cache: bool = True) -> CasePipeline:
    """Build or load the startup tables, load the policy, and wire the per-case pipeline."""
    client = ModelClient(settings)
    ctx = load_or_build(use_cache=use_cache, client=client)
    intent = IntentClassifier(fallback=make_fallback(client))
    # Linkage is global: both request files share one activity stream, so both are considered.
    all_requests = load_requests(REQUESTS_CSV) + load_requests(SAMPLE_REQUESTS_CSV)
    with stage(log, "window linkage"):
        linkage = build_linkage(ctx, all_requests, lambda text: intent(text)[0] == "DELETE")
    pipeline = CasePipeline(ctx, Policy.load(), intent, linkage)
    pipeline.client = client
    return pipeline


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


def write_all(results: list[CaseResult], output_path: Path, pipeline: CasePipeline | None = None) -> None:
    write_output(results, output_path)
    if pipeline is not None and getattr(pipeline, "client", None) is not None:
        pipeline.client.save_usage(cases=len(results))
    flagged = [r for r in results if r.notes]
    with REVIEW_JSONL.open("w", encoding="utf-8") as fh:
        for r in sorted(flagged, key=lambda r: r.case_id):
            fh.write(json.dumps({"case_id": r.case_id, "status": r.status, "notes": r.notes},
                                sort_keys=True) + "\n")
    log.info("review items: %d (see %s)", len(flagged), REVIEW_JSONL)
