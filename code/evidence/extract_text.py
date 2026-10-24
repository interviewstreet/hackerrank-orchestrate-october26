"""Text evidence: plain-text handover records, PDF documents (pypdf) and PNG grounding text.

Handover records -> read-back observations.

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

from evidence.common import (
    PRESENT,
    RE_EMAIL,
    RE_RESOURCE_ID,
    STATE_READBACK,
    Extraction,
    Identifiers,
    Observation,
    ShapeError,
    lookup_identifiers,
    result_state,
)
from loaders import EvidenceFile, normalize_email, normalize_phone, parse_ts

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


# ------------------------------------------------------------------ PDF documents
#
# A PDF is a business artifact (statement, register, journal extract, support attachment).
# Text comes from pypdf (deterministic), so its rows count as facts. A document that names a
# resource - by its id, or by a catalog alias such as a statement number - shows that the
# record existed with the identifiers printed on it when the file was captured.

ORIGIN_SYSTEM = {"legal_retention_service": "legal_service"}
RE_DOC_RESOURCE = re.compile(r"\b[a-z]+(?:_[a-z]+)*_\d+\b")
RE_DOC_PHONE = re.compile(r"(?<![\w-])\+\d[\d ]{7,}\d\b")
RE_DOC_USER = re.compile(r"\buser_\d+\b")
RE_DOC_DATE = re.compile(r"\b(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})\b")
RE_RETAIN = re.compile(r"retain(?:-|\s)until\s+(\d{1,2} [A-Z][a-z]{2} \d{4})", re.I)
MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                      "Nov", "Dec"), start=1)}


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def _doc_date(text: str):
    m = RE_DOC_DATE.fullmatch(text.strip())
    if not m or m.group(2) not in MONTHS:
        return None
    return parse_ts(f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}T23:59:59Z")


def extract_pdf(ev: EvidenceFile, path: Path, aliases: dict[str, tuple[str, str]] | None = None) -> Extraction:
    """``aliases`` maps a catalog display reference (e.g. a statement number) to (system, resource)."""
    out = Extraction(family="pdf_document")
    text = pdf_text(path)
    if not text.strip():
        raise ShapeError(f"{ev.file_id}: PDF without a text layer")
    flat = " ".join(text.split())
    ids = Identifiers()
    ids.update(scan_text_identifiers(flat))
    ids.phones.update(normalize_phone(p) for p in RE_DOC_PHONE.findall(flat))

    targets: dict[str, str] = {}
    for rid in RE_DOC_RESOURCE.findall(flat):
        if RE_DOC_USER.fullmatch(rid):
            continue
        targets.setdefault(rid, ORIGIN_SYSTEM.get(ev.origin, ev.origin))
    for alias, (system, rid) in (aliases or {}).items():
        if alias in flat:
            targets.setdefault(rid, system)
    if not targets:
        # A register of orders / users without resource ids: nothing to observe, counted.
        out.skip("document without a resource id", 1)
        out.rows_parsed += 1
        return out

    retention = RE_RETAIN.search(flat)
    attachment = bool(re.search(r"\battachment\b", flat, re.I))
    for rid, system in sorted(targets.items()):
        record_type = "SUPPORT_ATTACHMENT" if attachment and system == "support_platform" else ""
        fields = {"document": ev.file_path.rsplit("/", 1)[-1]}
        if retention:
            fields["retention_until"] = _doc_date(retention.group(1)).isoformat()
        out.observations.append(Observation(
            obs_id=f"{ev.file_id}#{rid}", file_id=ev.file_id, source_kind="pdf", family=out.family,
            available_at=ev.captured_at, state_observed_at=ev.captured_at, system_id=system, resource_id=rid,
            assertion=STATE_READBACK, record_type=record_type, link_ids=ids, exposed_ids=ids, fields=fields,
            detail="pdf text", exists=PRESENT))
        out.rows_parsed += 1
    return out


def scan_text_identifiers(text: str) -> Identifiers:
    ids = Identifiers()
    ids.emails.update(normalize_email(e) for e in RE_EMAIL.findall(text))
    ids.user_ids.update(RE_DOC_USER.findall(text))
    return ids


# ------------------------------------------------------------------ PNG grounding text
#
# PNG screenshots are not facts in this phase. Tesseract OCR text is kept per file as
# grounding text only: Phase 4 vision rows are accepted only when their ids appear in it.

TESSERACT_PATHS = ("tesseract", r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def ocr_text(path: Path, cache_dir: Path | None = None) -> str | None:
    """OCR text of an image, cached by content hash. None when Tesseract is not installed."""
    import hashlib
    import shutil
    import subprocess

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cached = cache_dir / f"{digest}.txt" if cache_dir else None
    if cached is not None and cached.exists():
        return cached.read_text(encoding="utf-8")
    exe = next((p for p in TESSERACT_PATHS if shutil.which(p) or Path(p).exists()), None)
    if exe is None:
        return None
    result = subprocess.run([exe, str(path), "-", "--psm", "6"], capture_output=True, text=True,  # noqa: S603 - fixed exe, no shell
                            encoding="utf-8", check=False)
    if result.returncode != 0:
        raise ShapeError(f"tesseract failed on {path.name}: {result.stderr.strip()[:80]}")
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(result.stdout, encoding="utf-8")
    return result.stdout
