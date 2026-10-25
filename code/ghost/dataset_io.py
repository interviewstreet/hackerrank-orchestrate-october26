"""CSV reading with header validation, and atomic output writing."""
from __future__ import annotations

import csv
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .config import OUTPUT_COLUMNS, STATUSES
from .errors import DatasetError
from .models import CaseResult, Request

log = logging.getLogger(__name__)

REQUEST_COLUMNS = (
    "case_id", "email", "requested_at", "reported_status",
    "reported_at", "audit_at", "request_text",
)


def read_csv(path: Path, required: Iterable[str]) -> list[dict[str, str]]:
    """Read a CSV into dicts, failing fast if a required column is missing."""
    if not path.is_file():
        raise DatasetError(f"missing dataset file: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = set(required) - set(reader.fieldnames or ())
        if missing:
            raise DatasetError(f"{path.name}: missing columns {sorted(missing)}")
        rows = list(reader)
    log.debug("read %s: %d rows", path.name, len(rows))
    return rows


def load_requests(path: Path) -> list[Request]:
    rows = read_csv(path, REQUEST_COLUMNS)
    requests = [Request(**{k: r[k] for k in REQUEST_COLUMNS}) for r in rows]
    ids = [r.case_id for r in requests]
    if len(ids) != len(set(ids)):
        raise DatasetError(f"{path.name}: duplicate case_id values")
    return requests


def write_output(results: list[CaseResult], path: Path) -> None:
    """Validate and write output.csv atomically (temp file, then rename)."""
    results = sorted(results, key=lambda r: r.case_id)
    for r in results:
        if r.status not in STATUSES:
            raise ValueError(f"{r.case_id}: invalid status {r.status}")
        if r.status == "NOT_APPLICABLE" and r.steps:
            raise ValueError(f"{r.case_id}: NOT_APPLICABLE must have no steps")

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".output-", suffix=".csv", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(OUTPUT_COLUMNS)
            for r in results:
                writer.writerow((r.case_id, r.status, r.steps_json()))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    log.info("wrote %s: %d rows", path, len(results))
