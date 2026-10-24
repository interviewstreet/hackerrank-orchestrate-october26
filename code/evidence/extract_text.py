"""Plain-text handover records -> read-back observations.

Known shape (``customer_account_handover_*.txt``)::

    CUSTOMER PLATFORM - SHIFT HANDOVER
    Snapshot: 2026-10-01T12:00:00Z
    <free heading lines ending with ':'>
    - <time> | <system> | <resource_id> | <record_type> | <result> | <subject>

``subject`` is an email, a ``user_id`` or the phrase "no direct identifier". Any other
non-empty line raises ``ShapeError``.
"""

from __future__ import annotations

import re
from pathlib import Path

from evidence.common import (RE_RESOURCE_ID, STATE_READBACK, Extraction, Identifiers, Observation,
                             ShapeError, lookup_identifiers, result_state)
from loaders import EvidenceFile, parse_ts

RE_TITLE = re.compile(r"^[A-Z][A-Z0-9 \-]+$")
RE_SNAPSHOT = re.compile(r"^Snapshot:\s*(\S+)$")
RE_HEADING = re.compile(r"^[A-Z][^|]*:$")
RE_ROW = re.compile(r"^-\s*(.+)$")
NO_IDENTIFIER = "no direct identifier"


def extract(ev: EvidenceFile, path: Path) -> Extraction:
    out = Extraction(family="txt_handover")
    snapshot_at = None
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if m := RE_SNAPSHOT.match(line):
            snapshot_at = parse_ts(m.group(1))
            continue
        if RE_TITLE.match(line) or RE_HEADING.match(line):
            continue
        m = RE_ROW.match(line)
        if not m:
            raise ShapeError(f"{ev.file_id}:{line_no}: unknown line {line[:60]!r}")
        parts = [p.strip() for p in m.group(1).split("|")]
        if len(parts) != 6:
            raise ShapeError(f"{ev.file_id}:{line_no}: expected 6 fields, got {len(parts)}")
        at, system, resource_id, record_type, result, subject = parts
        if not RE_RESOURCE_ID.fullmatch(resource_id):
            raise ShapeError(f"{ev.file_id}:{line_no}: bad resource id {resource_id!r}")
        observed = parse_ts(at) or snapshot_at
        if observed is None:
            raise ShapeError(f"{ev.file_id}:{line_no}: no time for row")
        link = Identifiers() if subject.lower() == NO_IDENTIFIER else lookup_identifiers(subject)
        out.observations.append(Observation(
            obs_id=f"{ev.file_id}#{line_no}", file_id=ev.file_id, source_kind="txt", family=out.family,
            available_at=ev.captured_at, state_observed_at=observed, system_id=system,
            resource_id=resource_id, assertion=STATE_READBACK, record_type=record_type,
            link_ids=link, fields={"result": result, "subject": subject}, detail=f"line {line_no}",
            **result_state(result, record_type)))
        out.rows_parsed += 1
    return out
