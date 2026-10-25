"""Table 2: run every evidence parser once and collect normalised observations."""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Callable

from ..config import DATASET_DIR
from ..errors import ParseError
from ..models import Observation
from ..parsers import handover_txt, json_records, service_logs, sql_snapshot
from ..parsers.base import RESULTS, ParseResult, merge
from .files import EvidenceFile

log = logging.getLogger(__name__)

Parser = Callable[[Path, str, str], ParseResult]
PARSERS: dict[str, Parser] = {
    "sql": sql_snapshot.parse,
    "json": json_records.parse,
    "txt": handover_txt.parse,
    "log": service_logs.parse,
}
# png and pdf are handled by the extraction stage (milestone M5) and plug in here.
EXTRA_PARSERS: dict[str, Parser] = {}


def build_observations(files: list[EvidenceFile]) -> tuple[list[Observation], dict[str, list], list[dict]]:
    """Return (observations, scopes, failures). A failing file is reported, never fatal."""
    observations: list[Observation] = []
    scopes: dict[str, list] = {}
    failures: list[dict] = []
    per_kind: Counter = Counter()

    for f in files:
        parser = PARSERS.get(f.kind) or EXTRA_PARSERS.get(f.kind)
        if parser is None:
            log.info("%s: no parser yet for %s (%s)", f.evidence_id, f.kind, f.path)
            failures.append({"evidence_id": f.evidence_id, "reason": f"no parser for {f.kind}"})
            continue
        try:
            res = parser(DATASET_DIR / f.path, f.evidence_id, f.captured_at)
        except ParseError as exc:
            log.error("parse failed: %s", exc)
            failures.append({"evidence_id": f.evidence_id, "reason": str(exc)})
            continue
        except Exception as exc:  # a parser bug must not hide the other 93 files
            log.exception("%s: unexpected parser error", f.evidence_id)
            failures.append({"evidence_id": f.evidence_id, "reason": f"{type(exc).__name__}: {exc}"})
            continue

        bad = [o for o in res.observations if o.result not in RESULTS]
        if bad:
            log.error("%s: %d observations with invalid result dropped", f.evidence_id, len(bad))
        rows = [o for o in res.observations if o.result in RESULTS]
        observations.extend(rows)
        scopes[f.evidence_id] = sorted(res.scope)
        per_kind[f.kind] += len(rows)
        log.debug("%s %s: %d observations, %d scope entries, %d skipped",
                  f.evidence_id, f.path, len(rows), len(res.scope), res.skipped)

    merged = merge(observations)
    log.info("observations: %d rows (%d before merge) %s; %d files not parsed",
             len(merged), len(observations), dict(sorted(per_kind.items())), len(failures))
    return merged, scopes, failures
