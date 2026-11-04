"""run_all_cases(dataset_dir) and exact output.csv generation."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

from .case_analyzer import EngineContext, analyze_case, build_context
from .contracts import CaseAuditResult

HEADER = ["case_id", "deletion_status", "steps_json"]


def run_cases(requests: Iterable[Dict[str, str]], ec: EngineContext) -> List[CaseAuditResult]:
    return [analyze_case(r, ec) for r in requests]


def run_all_cases(dataset_dir) -> List[CaseAuditResult]:
    """Structured results for every request in deletion_requests.csv (shared contract for Member 1's API)."""
    ec = build_context(dataset_dir)
    return run_cases(ec.ctx.requests, ec)


def write_output_csv(results: List[CaseAuditResult], path) -> None:
    rows = sorted(results, key=lambda r: r.case_id)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(HEADER)
        for r in rows:
            w.writerow([r.case_id, r.deletion_status, json.dumps(r.steps, separators=(",", ":"), ensure_ascii=False)])
