"""Pipe-delimited ledger text: '- <ts> | <system> | <resource> | <TYPE> | <RESULT> | <subject>'."""
from __future__ import annotations

from pathlib import Path

from ..errors import ParseError
from .base import ParseResult, ledger_result, norm_subject


def parse(path: Path, evidence_id: str, captured_at: str) -> ParseResult:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ParseError(evidence_id, f"not UTF-8 text: {exc}") from exc
    out = ParseResult()
    for n, line in enumerate(lines, start=1):
        rows = parse_ledger_line(line)
        if rows is None:
            continue
        ts, system, rid, category, word, raw_subject = rows
        subject = norm_subject("subject", raw_subject) if raw_subject else None
        result = ledger_result(category, word, subject)
        if result is None:
            out.skipped += 1
            continue
        out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=ts or captured_at,
                system_id=system, resource_id=rid, category=category, result=result,
                subjects=(subject,) if subject else (), raw_ref=f"line {n}")
    if not out.observations:
        raise ParseError(evidence_id, "no ledger lines found")
    return out


def parse_ledger_line(line: str) -> tuple[str, str, str, str, str, str] | None:
    """Split one ledger line, or None when the line is prose. Shared with the PDF parser."""
    text = line.strip().lstrip("-•* ").strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 6 or not parts[2] or not parts[3].isupper():
        return None
    return parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
