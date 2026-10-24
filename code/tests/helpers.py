"""Shared test helpers: put code/ on sys.path and build small fixtures."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

REQUEST_HEADER = ["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"]


def write_requests(path: Path, case_ids: list[str], audit_at: str = "2026-09-01T00:00:00Z") -> Path:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(REQUEST_HEADER)
        for cid in case_ids:
            writer.writerow([cid, f"{cid}@example.com", "2026-08-01T00:00:00Z", "COMPLETE",
                             "2026-08-02T00:00:00Z", audit_at, "Please delete my account."])
    return path


def write_rows(path: Path, rows: list[list[str]], header: list[str] | None = None) -> Path:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header or ["case_id", "deletion_status", "steps_json"])
        writer.writerows(rows)
    return path
