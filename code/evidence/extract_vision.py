"""PNG screenshots (and PDFs without a text layer) -> grounded vision observations (plan 7.3).

Flow per file:

1. The local text (Tesseract OCR for PNG, pypdf for PDF) is screened for injection first.
   A hit means the file is not sent; it is flagged and keeps no vision rows (D20).
2. The model reads the image and returns ``schema.VisionExtraction`` (validated with the
   known systems / categories and the file id as context; one retry with the error).
3. Grounding (decision from Phase 2): a row is accepted only if its ``resource_id`` and its
   ``identifier`` both appear in the local text of that file. OCR noise allowed, as character
   classes: separators ``_ - . ,`` / space / none; ``o``/``0``; ``i``/``l``/``1``/``|`` (Tesseract
   reads "gmail" as "gmall"). Other digits must match. Every dropped row is listed with a reason.
4. Accepted rows become observations with assertion ``vision_row`` (resolver tier "vision",
   below parsed text rows). ``UNREADABLE`` rows are dropped.

A PDF without a text layer cannot be grounded, so it is not sent (listed in the report).
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

import config
import safety
from evidence.common import (ABSENT, ACTIVE, ANONYMIZED, BLOCKED, DISABLED, IDENTIFIABLE, OPEN, PRESENT, REDACTED,
                             RE_EMAIL, RE_HASH, RE_USER_ID, VISION_ROW, Identifiers, Observation)
from llm_client import LLMClient, render_prompt
from loaders import EvidenceFile, normalize_email, normalize_phone
from schema import RawState, VisionExtraction, VisionRow

PROMPT = config.PROMPT_VERSIONS["vision"]
SEP = r"[_\-\s.,]?"
CONFUSABLE = str.maketrans({"o": "0", "l": "1", "i": "1", "|": "1", "!": "1"})


@dataclass
class FileReport:
    file_id: str
    path: str
    status: str = ""                 # ok | injection_screened | fallback:<flag> | unreadable | no_text_layer
    returned: int = 0
    grounded: int = 0
    dropped: list[dict] = field(default_factory=list)
    injection_suspected: bool = False
    screen_hits: list[str] = field(default_factory=list)


def _ocr_norm(text: str) -> str:
    return text.lower().translate(CONFUSABLE)


def _token_pattern(token: str) -> str:
    """Regex for an id inside normalized OCR text: separators may be _ - . , space or missing."""
    parts = [re.escape(_ocr_norm(p)) for p in re.split(r"[_\-.]", token) if p]
    return SEP.join(parts)


def grounded(value: str, text: str) -> bool:
    """True when ``value`` (a resource id or identifier) appears in the OCR/PDF ``text``."""
    if not value:
        return False
    norm = _ocr_norm(text)
    if RE_HASH.fullmatch(value):
        return value.lower() in text.lower()
    digits = re.sub(r"\D", "", value)
    if not RE_EMAIL.search(value) and not RE_USER_ID.fullmatch(value) and len(digits) >= 7 \
            and re.fullmatch(r"\+?[\d\s().-]+", value):
        return digits in re.sub(r"[\s().+-]", "", text)
    if "@" in value:
        local, _, domain = value.lower().partition("@")
        # An email may follow a stray OCR digit ("4g.silva76"): only a letter before it blocks a match.
        pattern = r"(?<![a-z])" + _token_pattern(local) + r"\s?@\s?" + _token_pattern(domain)
    else:
        pattern = r"(?<![a-z0-9])" + _token_pattern(value)
    return re.search(pattern + r"(?![0-9a-z])", norm) is not None


def _identifiers(value: str | None) -> Identifiers:
    ids = Identifiers()
    if not value:
        return ids
    value = value.strip()
    if "@" in value:
        ids.emails.update(normalize_email(e) for e in RE_EMAIL.findall(value))
    elif RE_USER_ID.fullmatch(value):
        ids.user_ids.add(value)
    elif RE_HASH.fullmatch(value):
        ids.hashes.add(value.lower())
    elif len(re.sub(r"\D", "", value)) >= 7:
        ids.phones.add(normalize_phone(value))
    return ids


def state_fields(s: RawState, category: str) -> dict | None:
    """RawState -> resolver fields. None for UNREADABLE."""
    if s == RawState.UNREADABLE:
        return None
    if s in (RawState.FOUND, RawState.PRESENT):
        return {"exists": PRESENT}
    if s in (RawState.NOT_FOUND, RawState.ABSENT):
        return {"exists": ABSENT}
    if s == RawState.IDENTIFIABLE:
        return {"exists": PRESENT, "treatment": IDENTIFIABLE}
    if s == RawState.REDACTED:
        return {"exists": PRESENT, "treatment": REDACTED}
    if s == RawState.ANONYMIZED:
        return {"exists": PRESENT, "treatment": ANONYMIZED}
    if category == "DATA_FLOW" and s in (RawState.ACTIVE, RawState.DISABLED):
        return {"exists": PRESENT, "flow_state": ACTIVE if s == RawState.ACTIVE else DISABLED}
    if category == "BACKUP_ARCHIVE" and s in (RawState.ACTIVE, RawState.BLOCKED):
        return {"exists": PRESENT, "restore_state": OPEN if s == RawState.ACTIVE else BLOCKED}
    return {"exists": PRESENT}   # an "active" / "disabled" account or a blocked user is still present


def to_observation(ev: EvidenceFile, row: VisionRow, n: int, category: str) -> Observation | None:
    fields = state_fields(row.observed_state, category)
    if fields is None:
        return None
    link = _identifiers(row.identifier)
    exposed = None
    if fields.get("exists") == PRESENT and link.direct():
        exposed = Identifiers(emails=set(link.emails), phones=set(link.phones), hashes=set(link.hashes))
    # A screenshot shows each record's state at capture time; a row time (created, modified) is kept
    # as a field only.
    shown_at = row.observed_at.isoformat() if row.observed_at else ""
    return Observation(
        obs_id=f"{ev.file_id}#v{n}", file_id=ev.file_id, source_kind="vision", family="vision_png",
        available_at=ev.captured_at, state_observed_at=ev.captured_at, system_id=row.system_id,
        resource_id=row.resource_id, assertion=VISION_ROW, record_type=row.category or "",
        link_ids=link, exposed_ids=exposed, fields={"source_text": row.source_text, "row_time": shown_at,
                                                    "observed_state": row.observed_state.value},
        detail="vision row", **fields)


def _messages(ev: EvidenceFile, image: bytes, known_systems, known_categories) -> list[dict]:
    system, user = render_prompt(
        PROMPT, FILE_ID=ev.file_id, ORIGIN=ev.origin, CAPTURED_AT=ev.captured_at.strftime("%Y-%m-%dT%H:%M:%S"),
        SCHEMA=__import__("json").dumps(VisionExtraction.model_json_schema(), sort_keys=True),
        KNOWN_SYSTEMS=", ".join(sorted(known_systems)), KNOWN_CATEGORIES=", ".join(sorted(known_categories)))
    data_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
    return [{"role": "system", "content": system},
            {"role": "user", "content": [{"type": "text", "text": user},
                                         {"type": "image_url", "image_url": {"url": data_url}}]}]


def extract(ev: EvidenceFile, path, local_text: str | None, client: LLMClient, known_systems: set[str],
            known_categories: set[str], system_category: dict[str, str]) -> tuple[list[Observation], FileReport]:
    report = FileReport(ev.file_id, ev.file_path)
    if not local_text or not local_text.strip():
        report.status = "no_text_layer"   # nothing to ground against: not sent
        return [], report
    report.screen_hits = safety.screen(local_text)
    if report.screen_hits:
        report.status = "injection_screened"
        return [], report
    context = {"file_id": ev.file_id, "known_systems": known_systems, "known_categories": known_categories}
    result = client.structured("vision", ev.file_id, _messages(ev, path.read_bytes(), known_systems,
                                                                 known_categories),
                               VisionExtraction, context, PROMPT)
    if result.value is None:
        report.status = f"fallback:{result.flag}"
        return [], report
    extraction: VisionExtraction = result.value
    report.injection_suspected = extraction.injection_suspected
    report.returned = len(extraction.rows)
    if extraction.unreadable:
        report.status = "unreadable"
        return [], report
    out: list[Observation] = []
    for n, row in enumerate(extraction.rows, start=1):
        reason = ""
        if not grounded(row.resource_id, local_text):
            reason = "resource_id not in OCR text"
        elif row.identifier and not grounded(row.identifier, local_text):
            reason = "identifier not in OCR text"
        elif safety.screen(row.source_text):
            reason = "injection pattern in source_text"
        obs = None
        if not reason:
            obs = to_observation(ev, row, n, row.category or system_category.get(row.system_id, ""))
            if obs is None:
                reason = "unreadable state"
        if reason:
            report.dropped.append({"resource_id": row.resource_id, "identifier": row.identifier, "reason": reason})
            continue
        out.append(obs)
    report.grounded = len(out)
    report.status = "ok"
    return out, report
