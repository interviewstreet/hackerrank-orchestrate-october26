"""Screenshots and PDFs: ordinary business artifacts, read for the facts they contain.

Text comes from pypdf (PDF) or, for screenshots, from the vision model when a key is configured
and from tesseract OCR otherwise. Facts are then derived line by line by the same rules for both:
  - a resource id on a line becomes an observation of that resource
  - identifiers on the same line (or in a single-person document) become its subjects
  - an extracted email counts only if it exactly matches a known identity: OCR misreads such as
    'outiook.com' then lose a link instead of inventing one
  - state words on the line refine data-flow and backup state; 'retain until <date>' is kept
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ..errors import ModelUnavailable, ParseError
from ..identifiers import norm_email, norm_phone
from .base import ParseResult, system_for

log = logging.getLogger(__name__)

_RESOURCE = re.compile(r"\b(?:account|search|analytics|support|export|data_flow|backup|audit_record|"
                       r"tombstone|marketing|object|email_delivery|legal_hold)_\d+\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_USER = re.compile(r"\buser_\d+\b")
_PHONE = re.compile(r"\+\d[\d\s().-]{7,}\d")
_RETAIN = re.compile(r"retain(?:ed)?\s+until\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{4}-\d{2}-\d{2})", re.I)
_PREFIX_CATEGORY = {
    "account_": "USER_PROFILE", "search_": "SEARCH_INDEX_ENTRY", "analytics_": "ANALYTICS_PROFILE",
    "support_": "SUPPORT_MESSAGE", "export_": "USER_EXPORT", "data_flow_": "DATA_FLOW",
    "backup_": "BACKUP_ARCHIVE", "audit_record_": "SECURITY_AUDIT_LOG",
    "tombstone_": "ACCOUNT_TOMBSTONE", "marketing_": "MARKETING_PROFILE",
    "legal_hold_": "LEGAL_HOLD_RECORD", "object_": "USER_EXPORT",
}

VISION_SYSTEM = (
    "You transcribe internal admin-console screenshots. Return JSON {\"lines\": [string, ...]}: "
    "one string per visible table row or labelled field group, keeping every resource id "
    "(like account_123, support_45, backup_9), email, phone, user_N reference, status word and "
    "date exactly as shown. Do not interpret or summarise."
)


PAIRING_WINDOW_MIN = 30  # a catalog row written within 30 min after capture describes the file


def make_parser(known_identifiers: frozenset[str], client=None, catalog=()):
    """Bind the identity table (to validate extracted emails), the optional model client and the
    data-catalog links (to know which resource and person a document is about)."""

    def parse(path: Path, evidence_id: str, captured_at: str) -> ParseResult:
        lines, source = _text_lines(path, evidence_id, client)
        cap = _ts(captured_at)
        paired = [c for c in catalog
                  if cap is not None and (t := _ts(c.event_time)) is not None
                  and 0 <= (t - cap).total_seconds() <= PAIRING_WINDOW_MIN * 60]
        return _facts(lines, source, evidence_id, captured_at, known_identifiers, paired)

    return parse


def _ts(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def _text_lines(path: Path, evidence_id: str, client) -> tuple[list[str], str]:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ParseError(evidence_id, "pypdf not installed (pip install -r requirements.txt)") from exc
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except Exception as exc:
            raise ParseError(evidence_id, f"pdf extraction failed: {exc}") from exc
        return _join_wrapped(text.splitlines()), "pypdf"

    if client is not None:
        try:
            data = client.complete_json("vision", VISION_SYSTEM,
                                        "Transcribe this screenshot.", image=path, max_tokens=2500)
            lines = [str(x) for x in data.get("lines", []) if str(x).strip()]
            if lines:
                return lines, "vision"
        except ModelUnavailable as exc:
            log.debug("%s: vision unavailable (%s), using OCR", evidence_id, exc)
    if shutil.which("tesseract") is None:
        raise ParseError(evidence_id, "no vision model and tesseract not installed")
    try:
        proc = subprocess.run(["tesseract", str(path), "-", "--psm", "6"], capture_output=True,
                              text=True, timeout=120, check=True)
    except (subprocess.SubprocessError, OSError) as exc:
        raise ParseError(evidence_id, f"tesseract failed: {exc}") from exc
    return [l for l in proc.stdout.splitlines() if l.strip()], "ocr"


def _join_wrapped(lines: list[str]) -> list[str]:
    """pypdf splits 'Detail' label rows from their values; keep values, drop bare labels."""
    return [l.strip() for l in lines if l.strip() and l.strip() not in ("Detail", "Record", "Item")]


def _date(text: str) -> str | None:
    for fmt in ("%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%dT23:59:59Z")
        except ValueError:
            continue
    return None


def _facts(lines: list[str], source: str, evidence_id: str, captured_at: str,
           known: frozenset[str], paired=()) -> ParseResult:
    out = ParseResult()
    whole = "\n".join(lines)
    primary = {c.resource_id: c for c in paired}
    doc_ids = _identifiers(whole, known)
    doc_people = {i for i in doc_ids if "@" in i or i.startswith("user_")}
    single_person = len({i for i in doc_people if i.startswith("user_")}) <= 1 and \
        len({i for i in doc_people if "@" in i}) <= 1
    attachment_doc = bool(re.search(r"\battachment\b|\.pdf\b|\buploader\b", whole, re.I))
    retention = next((d for m in _RETAIN.finditer(whole) if (d := _date(m.group(1)))), None)

    # The document's own subject, named by the data catalog: subjects come from the catalog,
    # state from the lines that mention the resource or its alias.
    for rid, link in sorted(primary.items()):
        mentions = [l for l in lines if rid in l or (link.alias and link.alias in l)] or lines
        category = next(c for p, c in _PREFIX_CATEGORY.items() if rid.startswith(p))
        if (category in ("SUPPORT_MESSAGE", "USER_EXPORT") and link.exclusive) or \
                (category == "SUPPORT_MESSAGE" and attachment_doc):
            category = "SUPPORT_ATTACHMENT"
        shown = _identifiers(whole, known) - {s for s in link.identifiers if s.startswith("user_")}
        result = _state(category, " ".join(mentions), shown)
        out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=captured_at,
                # Linking is left to the catalog link itself, which discovery scopes to the
                # case window; repeating its identifiers here would bypass that scope.
                system_id=system_for(rid), resource_id=rid, category=category, result=result,
                subjects=(),
                retention_until=retention if category == "SECURITY_AUDIT_LOG" else None,
                raw_ref=f"{source} catalog {link.activity_id}")

    for n, line in enumerate(lines, start=1):
        for rid in sorted(set(_RESOURCE.findall(line)) - set(primary)):
            line_ids = _identifiers(line, known)
            subjects = line_ids or (doc_ids if single_person and not primary else set())
            category = next(c for p, c in _PREFIX_CATEGORY.items() if rid.startswith(p))
            if category == "SUPPORT_MESSAGE" and attachment_doc:
                category = "SUPPORT_ATTACHMENT"
            result = _state(category, line, subjects)
            out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=captured_at,
                    system_id=system_for(rid), resource_id=rid, category=category, result=result,
                    subjects=tuple(sorted(subjects)),
                    retention_until=retention if category == "SECURITY_AUDIT_LOG" else None,
                    raw_ref=f"{source} line {n}")
    if not out.observations:
        out.skipped += 1
        log.info("%s: no resource ids found via %s", evidence_id, source)
    return out


def _identifiers(text: str, known: frozenset[str]) -> set[str]:
    ids = {norm_email(e) for e in _EMAIL.findall(text)}
    ids = {e for e in ids if e in known}                       # exact known identities only
    ids |= set(_USER.findall(text))
    ids |= {p for p in (norm_phone(x) for x in _PHONE.findall(text)) if p in known}
    return ids


def _state(category: str, line: str, subjects: set[str]) -> str:
    low = line.lower()
    if category == "DATA_FLOW":
        if re.search(r"\b(disabled|paused|stopped|inactive|off)\b", low):
            return "DISABLED"
        return "ACTIVE"
    if category == "BACKUP_ARCHIVE":
        # A visible archive is restorable unless the screen says restores are blocked.
        if re.search(r"\b(blocked|denied|deny|restore disabled|not restorable|deletion block)\b", low):
            return "RESTORE_BLOCKED"
        return "RESTORE_ALLOWED"
    if re.search(r"\b(deleted|not found|removed|404)\b", low) and category == "USER_PROFILE":
        return "NOT_FOUND"
    direct = any("@" in s or s.startswith("+") for s in subjects)
    return "IDENTIFIABLE" if direct else "REFERENCED"
