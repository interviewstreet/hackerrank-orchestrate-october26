"""Parser for plain-text handover checklists (``*.txt``).

Recognised row shape (leading bullet optional)::

    - <timestamp> | <system> | <resource_id> | <record_type> | <result> | <subject_reference>

These are second-hand lookup results, so observations are ``claim_only``.
"""

from __future__ import annotations

import re

from ..models import ParseIssue
from ..normalize import RESOURCE_ID_RE, parse_ts
from .common import ParseResult, ledger_presence, make_record

FMT = "txt"
SNAPSHOT_RE = re.compile(r"^\s*Snapshot:\s*(\S+)", re.I | re.M)


def parse_text(ev) -> ParseResult:
    res = ParseResult()
    try:
        text = ev.absolute_path.read_text(encoding="utf-8")
    except OSError as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"cannot read: {exc}"))
        return res
    m = SNAPSHOT_RE.search(text)
    fallback = (parse_ts(m.group(1)) if m else None) or ev.captured_at

    for lineno, line in enumerate(text.splitlines(), start=1):
        body = line.strip().lstrip("-*• ").strip()
        if "|" not in body:
            continue
        parts = [p.strip() for p in body.split("|")]
        if len(parts) < 5:
            res.issues.append(ParseIssue(ev.file_id, "warning", f"line {lineno}: pipe row with {len(parts)} fields"))
            continue
        ts = parse_ts(parts[0])
        if ts is None:
            parts = [""] + parts  # row without timestamp
            ts = fallback
        _, system, rid, rtype, result, *rest = parts + [""] * (6 - len(parts))
        if not RESOURCE_ID_RE.fullmatch(rid):
            res.issues.append(ParseIssue(ev.file_id, "warning", f"line {lineno}: unrecognised resource id {rid!r}"))
            continue
        subject = rest[0] if rest else ""
        payload = {
            "recorded_at": parts[0] or None,
            "system": system,
            "resource_id": rid,
            "record_type": rtype,
            "result": result,
            "subject_reference": subject,
        }
        res.records.append(make_record(
            ev, system_id=system, resource_id=rid, observed_at=ts, presence=ledger_presence(result),
            payload=payload, claim_only=True, source_format=FMT, locator=f"line {lineno}",
            data_category=rtype or None, pii_override={},
        ))
        res.bump("ledger_records")
    if not res.records:
        res.issues.append(ParseIssue(ev.file_id, "unsupported", "no recognisable checklist rows"))
    return res
