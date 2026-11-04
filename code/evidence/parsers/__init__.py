"""Format dispatch: one parser per file extension."""

from __future__ import annotations

from typing import Callable, Optional

from ..models import EvidenceFile, ParseIssue
from .common import ParseResult


def _parser_for(ext: str) -> Optional[Callable[..., ParseResult]]:
    if ext == "json":
        from .json_records import parse_json
        return parse_json
    if ext == "sql":
        from .sql_snapshots import parse_sql
        return parse_sql
    if ext == "log":
        from .logs import parse_log
        return parse_log
    if ext == "txt":
        from .text_handover import parse_text
        return parse_text
    if ext == "pdf":
        from .pdf_documents import parse_pdf
        return parse_pdf
    if ext == "png":
        from .images import parse_image
        return parse_image
    return None


def parse_file(ev: EvidenceFile, **options) -> ParseResult:
    parser = _parser_for(ev.extension)
    if parser is None:
        res = ParseResult()
        res.issues.append(ParseIssue(ev.file_id, "unsupported", f"no parser for .{ev.extension}"))
        return res
    if not ev.absolute_path.is_file():
        res = ParseResult()
        res.issues.append(ParseIssue(ev.file_id, "error", f"file missing on disk: {ev.file_path}"))
        return res
    try:
        if ev.extension == "png":
            return parser(ev, **options)
        return parser(ev)
    except Exception as exc:  # never let one bad file stop the corpus load
        res = ParseResult()
        res.issues.append(ParseIssue(ev.file_id, "error", f"{type(exc).__name__}: {exc}"))
        return res
