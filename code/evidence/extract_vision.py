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
   State grounding (``row_block``): one OCR block (Tesseract layout block, or one text line)
   must hold the resource id (or its visible catalog alias) with the state cue - on the id's own
   line when the block lists other records - and at least half of the ``source_text`` words.
   The identifier must be in that block, or anywhere on a page that shows no other record.
4. Accepted rows become observations with assertion ``vision_row`` (resolver tier "vision",
   below parsed text rows). ``UNREADABLE`` rows are dropped.

A PDF without a text layer cannot be grounded, so it is not sent (listed in the report).
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

import config
import safety
from evidence.common import (
    ABSENT,
    ACTIVE,
    ANONYMIZED,
    BLOCKED,
    DISABLED,
    IDENTIFIABLE,
    OPEN,
    PRESENT,
    RE_EMAIL,
    RE_HASH,
    RE_USER_ID,
    REDACTED,
    VISION_ROW,
    Identifiers,
    Observation,
)
from llm_client import LLMClient, render_prompt
from loaders import EvidenceFile, normalize_email, normalize_phone
from schema import RawState, VisionExtraction, VisionRow

PROMPT = config.PROMPT_VERSIONS["vision"]
SEP = r"[_\-\s.,]?"
CONFUSABLE = str.maketrans({"o": "0", "l": "1", "i": "1", "|": "1", "!": "1"})
MIN_SOURCE_SHARE = 0.5   # share of source_text words that must be in the grounding OCR block
RE_RECORD = re.compile(r"\b[a-z]+(?:_[a-z]+)*_\d+\b")   # a record name: resource id or file stem
# State cue words, shared with the agent acceptance check (agent/loop.py).
NEGATIVE = r"not[ _]found|absent|deleted|removed|missing|no results|\b404\b|rows=\"?0\b|purged"
STATE_WORDS = {
    RawState.FOUND: r"\bfound\b|present|exists|available|listed|retained|rows=\"?[1-9]|\b200\b",
    RawState.PRESENT: r"\bfound\b|present|exists|available|listed|retained|rows=\"?[1-9]|\b200\b",
    RawState.NOT_FOUND: NEGATIVE,
    RawState.ABSENT: NEGATIVE,
    RawState.IDENTIFIABLE: r"identifiable|@|\+\d",
    RawState.REDACTED: r"redact|masked|\*\*\*",
    RawState.ANONYMIZED: r"anonymi[sz]",
    RawState.ACTIVE: r"\bactive\b|enabled|running|enabled=\"?true",
    RawState.DISABLED: r"disabled|paused|stopped|inactive|enabled=\"?false",
    RawState.BLOCKED: r"blocked|denied|not allowed|restore_allowed=\"?false",
}


@dataclass(frozen=True)
class Alias:
    """A catalog display name (file name, statement number) for one resource id (``facts.catalog_alias_rows``)."""
    name: str
    system_id: str
    resource_id: str
    at: datetime


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


def to_observation(ev: EvidenceFile, row: VisionRow, n: int, category: str,
                   available_at: datetime | None = None) -> Observation | None:
    """``available_at``: later than ``captured_at`` when the row was read through a catalog alias
    published after the capture (the reading cannot exist before its alias)."""
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
        available_at=max(ev.captured_at, available_at or ev.captured_at), state_observed_at=ev.captured_at,
        system_id=row.system_id,
        resource_id=row.resource_id, assertion=VISION_ROW, record_type=row.category or "",
        link_ids=link, exposed_ids=exposed, fields={"source_text": row.source_text, "row_time": shown_at,
                                                    "observed_state": row.observed_state.value},
        detail="vision row", **fields)


def _alias_table(aliases: list[Alias]) -> str:
    lines = sorted({f"- `{a.name}` -> system `{a.system_id}`, resource `{a.resource_id}`" for a in aliases})
    return "\n".join(lines) or "(empty)"


def _messages(ev: EvidenceFile, image: bytes, known_systems, known_categories, aliases: list[Alias]) -> list[dict]:
    system, user = render_prompt(
        PROMPT, FILE_ID=ev.file_id, ORIGIN=ev.origin, CAPTURED_AT=ev.captured_at.strftime("%Y-%m-%dT%H:%M:%S"),
        SCHEMA=json.dumps(VisionExtraction.model_json_schema(), sort_keys=True),
        KNOWN_SYSTEMS=", ".join(sorted(known_systems)), KNOWN_CATEGORIES=", ".join(sorted(known_categories)),
        ALIASES=_alias_table(aliases))
    data_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
    return [{"role": "system", "content": system},
            {"role": "user", "content": [{"type": "text", "text": user},
                                         {"type": "image_url", "image_url": {"url": data_url}}]}]


def _grounding_time(row: VisionRow, text: str, aliases: list[Alias]) -> tuple[bool, datetime | None]:
    """(grounded, alias time): the id itself is in the OCR text, or a catalog alias of it is."""
    if grounded(row.resource_id, text):
        return True, None
    times = [a.at for a in aliases if (a.system_id, a.resource_id) == (row.system_id, row.resource_id)
             and grounded(a.name, text)]
    return (True, min(times)) if times else (False, None)


def _source_tokens(source_text: str) -> list[str]:
    """Words of ``source_text`` (table separators and edge punctuation removed)."""
    tokens = (t.strip("|:;,()[]{}\"'") for t in source_text.split())
    return [t for t in tokens if re.search(r"[0-9A-Za-z]", t)]


def state_cue(state: RawState, line: str) -> bool:
    """The OCR line supports ``state``. A listed row with no negative word shows a present record
    (a file listing or console row is itself the cue); every other state needs its own cue word
    (IDENTIFIABLE: an email or phone on the line)."""
    low = line.lower()
    if state in (RawState.FOUND, RawState.PRESENT):
        return re.search(NEGATIVE, low) is None
    return re.search(STATE_WORDS[state], low) is not None if state in STATE_WORDS else False


def layout_blocks(tsv: str | None) -> list[list[str]]:
    """Lines of each Tesseract TSV block (``--psm 3``), in reading order."""
    if not tsv:
        return []
    lines: dict[tuple[int, int, int], list[str]] = {}
    for rec in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if rec.get("level") == "5" and (rec.get("text") or "").strip():
            key = (int(rec["block_num"]), int(rec["par_num"]), int(rec["line_num"]))
            lines.setdefault(key, []).append(rec["text"])
    blocks: dict[int, list[str]] = {}
    for (block, _, _), words in sorted(lines.items()):
        blocks.setdefault(block, []).append(" ".join(words))
    return list(blocks.values())


def _other_record(text: str, names: list[str]) -> bool:
    """``text`` names a record other than ``names`` (the row's id and its aliases): a token shaped
    like a resource id or a file stem (``name_123``). User ids are identifiers, not records."""
    for m in RE_RECORD.finditer(text.lower()):
        token = m.group(0)
        if not RE_USER_ID.fullmatch(token) and not any(grounded(token, n) or grounded(n, token) for n in names):
            return True
    return False


def _cue(row: VisionRow, scope: str, region: str) -> bool:
    """The state cue is in ``scope``. An IDENTIFIABLE row is also supported by its own direct
    identifier (email, phone, hash) visible in the record's region: that identifier is the exposure."""
    if state_cue(row.observed_state, scope):
        return True
    return (row.observed_state == RawState.IDENTIFIABLE and bool(_identifiers(row.identifier).direct())
            and grounded(row.identifier or "", region))


def row_block(row: VisionRow, text: str, layout: str | None, aliases: list[Alias]) -> str | None:
    """The OCR block that grounds the row, or None.

    Candidate blocks: every ``--psm 3`` layout block, and every ``--psm 6`` text line as a block of
    its own (two segmentations of the same image). A block grounds the row when:

    - a line of it holds the resource id (or a visible catalog alias);
    - the state cue is in the block, or only on that line when the block lists other records (a
      table: the state must come from the record's own row);
    - the identifier is in the block, or in the record's region: the whole page when the page
      names no other record (a single-record view such as a ticket page with an email card);
    - at least ``MIN_SOURCE_SHARE`` of the ``source_text`` words are in the block (OCR misreads
      sizes and dates, so not all of them).
    """
    tokens = _source_tokens(row.source_text)
    if not tokens:
        return None
    names = [row.resource_id] + [a.name for a in aliases
                                 if (a.system_id, a.resource_id) == (row.system_id, row.resource_id)]
    single_record_page = not _other_record(text, names)
    for lines in [*layout_blocks(layout), *([ln] for ln in text.splitlines() if ln.strip())]:
        block = "\n".join(lines)
        if sum(grounded(t, block) for t in tokens) < MIN_SOURCE_SHARE * len(tokens):
            continue
        listing = _other_record(block, names)
        region = text if single_record_page else block
        if row.identifier and not grounded(row.identifier, region):
            continue
        for line in lines:
            if any(grounded(n, line) for n in names) and _cue(row, line if listing else block, region):
                return block
    return None


def extract(ev: EvidenceFile, path, local_text: str | None, client: LLMClient, known_systems: set[str],
            known_categories: set[str], system_category: dict[str, str],
            aliases: Sequence[Alias] = (), layout: str | None = None) -> tuple[list[Observation], FileReport]:
    """``aliases``: catalog display names (file names, statement numbers) for resource ids.
    ``layout``: the Tesseract TSV of the image (``--psm 3``), for block grounding."""
    aliases = list(aliases)
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
                                                                 known_categories, aliases),
                               VisionExtraction, context, PROMPT)
    if not isinstance(result.value, VisionExtraction):
        report.status = f"fallback:{result.flag}"
        return [], report
    extraction = result.value
    report.injection_suspected = extraction.injection_suspected
    report.returned = len(extraction.rows)
    if extraction.unreadable:
        report.status = "unreadable"
        return [], report
    out: list[Observation] = []
    for n, row in enumerate(extraction.rows, start=1):
        reason = ""
        ok, alias_at = _grounding_time(row, local_text, aliases)
        if not ok:
            reason = "resource_id not in OCR text"
        elif row.identifier and not grounded(row.identifier, local_text):
            reason = "identifier not in OCR text"
        elif row_block(row, local_text, layout, aliases) is None:
            reason = "no OCR block holds the id with its state cue, identifier and source_text"
        elif safety.screen(row.source_text):
            reason = "injection pattern in source_text"
        obs = None
        if not reason:
            obs = to_observation(ev, row, n, row.category or system_category.get(row.system_id, ""), alias_at)
            if obs is None:
                reason = "unreadable state"
        if reason or obs is None:
            report.dropped.append({"resource_id": row.resource_id, "identifier": row.identifier, "reason": reason})
            continue
        out.append(obs)
    report.grounded = len(out)
    report.status = "ok"
    return out, report
