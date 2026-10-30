"""Local OCR for PNG/PDF evidence (VISION_SPEC steps 2-3): a grounding check on what the vision model read, and
a findings-only fallback when no vision result exists.

Text comes from `pdftotext` (PDF text layer), else `pdftoppm` + `tesseract` (raster pages, PNG/JPG). Both are
optional system tools, called through their CLIs. Results are cached by the file's sha256 in the committed
`code/cache/ocr_cache.jsonl`, so a clean run reproduces the same checks without the tools installed. Missing
tools and a cache miss mean "no OCR text": the guard is then skipped, never applied to an empty text.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from ..config import CACHE_DIR
from ..loaders import EMAIL_RE, normalize_text, parse_ts
from ..models import EvidenceFile
from .records import RawRecord, system_for

log = logging.getLogger(__name__)
CACHE_PATH = CACHE_DIR / "ocr_cache.jsonl"
LANGS = "eng+rus"
TIMEOUT_S = 120

ID_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d{3,}\b(?!\.\w)", re.I)
PHONE_RE = re.compile(r"\+\d[\d\s().-]{6,}\d")
STATUS_WORDS = ("PRESENT", "ACTIVE", "ENABLED", "FOUND", "AVAILABLE", "RESTORABLE", "RETAINED")
ID_FIELDS = ("email", "requester_email", "owner_email", "customer_email", "uploaded_by")
PHONE_FIELDS = ("phone", "requester_phone", "owner_phone")


class OCRCache:
    """Append-only JSONL: one line per file content hash."""

    def __init__(self, path: Path | None = None):
        # GDA_OCR_CACHE: another OCR cache file (experiments and tests must not touch the committed one)
        self.path = path or Path(os.environ.get("GDA_OCR_CACHE") or CACHE_PATH)
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = json.loads(line)
                    self._entries.setdefault(e["sha256"], e)

    def get(self, sha: str) -> dict | None:
        return self._entries.get(sha)

    def put(self, entry: dict) -> None:
        with self._lock:
            if entry["sha256"] in self._entries:
                return
            self._entries[entry["sha256"]] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


_CACHE: OCRCache | None = None


def cache() -> OCRCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = OCRCache()
    return _CACHE


def engine_available() -> bool:
    return shutil.which("tesseract") is not None


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, check=True).stdout


def _tesseract(image: Path) -> str:
    return _run(["tesseract", str(image), "stdout", "-l", LANGS])


def _live_text(path: Path) -> tuple[str, str] | None:
    """(text, engine) or None when no tool can read the file."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            if shutil.which("pdftotext"):
                text = _run(["pdftotext", "-layout", str(path), "-"])
                if text.strip():
                    return text, "pdftotext"
            if shutil.which("pdftoppm") and engine_available():
                with tempfile.TemporaryDirectory(prefix="gda_ocr_") as tmp:
                    _run(["pdftoppm", "-r", "200", "-png", str(path), str(Path(tmp) / "page")])
                    pages = sorted(Path(tmp).glob("page*.png"))
                    return "\n".join(_tesseract(p) for p in pages), f"pdftoppm+tesseract:{LANGS}"
            return None
        if engine_available():
            return _tesseract(path), f"tesseract:{LANGS}"
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("OCR failed for %s: %s", path.name, exc)
    return None


def ocr_text(path: Path) -> str | None:
    """OCR text of a visual file: committed cache first, then the local tools (and cache the result)."""
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    hit = cache().get(sha)
    if hit is not None:
        return hit["text"]
    live = _live_text(path)
    if live is None:
        return None
    text, engine = live
    cache().put({"sha256": sha, "file": path.name, "engine": engine, "text": text})
    return text


# ---------------------------------------------------------------- grounding (step 2)
# Latin look-alikes the eng+rus model returns for Latin text (Баскир_9288 for backup_9288)
HOMOGLYPHS = str.maketrans({
    "а": "a", "б": "b", "в": "b", "г": "r", "д": "d", "е": "e", "ё": "e", "з": "3", "и": "u", "й": "u", "к": "k",
    "л": "n", "м": "m", "н": "h", "о": "o", "п": "n", "р": "p", "с": "c", "т": "t", "у": "y", "ф": "f", "х": "x",
    "ц": "u", "ч": "4", "ш": "w", "щ": "w", "ы": "b", "ь": "b", "э": "e", "ю": "o", "я": "r",
})


def squash(text: str) -> str:
    """Comparison form: NFKC + casefold, Cyrillic look-alikes as Latin, separators dropped (OCR loses `_` and `.`)."""
    return re.sub(r"[^a-z0-9@+]", "", normalize_text(text).translate(HOMOGLYPHS))


def _fuzzy_in(needle: str, hay: str, limit: int) -> bool:
    """Is `needle` a substring of `hay` with at most `limit` edits (Sellers' approximate matching)?"""
    if needle in hay:
        return True
    prev = [0] * (len(hay) + 1)
    for i, c in enumerate(needle, 1):
        cur = [i] + [0] * len(hay)
        for j, h in enumerate(hay, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (c != h))
        prev = cur
    return min(prev) <= limit


def _found(value: str, hay: str, digits: str) -> bool:
    v = squash(value)
    if not v:
        return True
    if re.fullmatch(r"[+\d\s().-]+", value.strip()):
        d = re.sub(r"\D", "", value)
        return len(d) >= 6 and d in digits
    return _fuzzy_in(v, hay, 1 if len(v) < 12 else 2)  # a misread character or two (S/5, O/0, l/1)


def mentions(text: str, values) -> bool:
    """Does the OCR text show any of these values (emails, phones, hashes, ids), with the same OCR tolerance?"""
    hay, digits = squash(text), re.sub(r"\D", "", text)
    return any(_found(str(v), hay, digits) for v in values if v)


class Grounding:
    """Counts what the guard checked; read by the evaluation report and the `visual_grounding` invariant."""

    def __init__(self):
        self.files: dict[str, dict] = {}

    def check(self, ef: EvidenceFile, records: list[RawRecord], text: str | None) -> list[RawRecord]:
        """Drop records whose resource id the OCR text does not show, and identifiers it does not show.
        With no OCR text (unreadable image, no tool, no cache) nothing is dropped."""
        stat = {"records": len(records), "grounded": 0, "dropped": [], "fields_removed": [], "ocr": text is not None}
        self.files[ef.file_id] = stat
        if text is None or not text.strip():
            stat["grounded"] = len(records)
            return records
        hay, digits = squash(text), re.sub(r"\D", "", text)
        kept = []
        for r in records:
            shown = r.fields.get("file") if r.resource_id.startswith("file:") else r.resource_id
            if not _found(str(shown), hay, digits):
                stat["dropped"].append(r.resource_id)
                log.warning("%s: %s not visible in the OCR text; dropped as a possible misreading", ef.file_id, r.resource_id)
                continue
            for k in (*ID_FIELDS, *PHONE_FIELDS):
                v = r.fields.get(k)
                if isinstance(v, str) and v.strip() and not _found(v, hay, digits):
                    stat["fields_removed"].append(f"{r.resource_id}.{k}")
                    r.fields[k] = None
            stat["grounded"] += 1
            kept.append(r)
        return kept

    def summary(self) -> dict:
        checked = [s for s in self.files.values() if s["ocr"]]
        n = sum(s["records"] for s in checked)
        g = sum(s["grounded"] for s in checked)
        return {"files": len(self.files), "files_with_ocr": len(checked), "records": n, "grounded": g,
                "agreement": (g / n) if n else 1.0,
                "dropped": sorted(f"{f}:{r}" for f, s in self.files.items() for r in s["dropped"]),
                "fields_removed": sorted(f"{f}:{x}" for f, s in self.files.items() for x in s["fields_removed"])}


GROUNDING = Grounding()


# ---------------------------------------------------------------- fallback (step 3)
def fallback_records(ef: EvidenceFile, text: str, known_files=()) -> list[RawRecord]:
    """One record per OCR line that shows a resource id or a file name, with the emails / phones / status words
    on that line. File names are the ones the data catalog links to a resource (matched with OCR tolerance), so a
    misread name cannot invent a resource. `source_format="ocr"`: these can only show that something is still
    there, never absence."""
    out: list[RawRecord] = []
    seen: set[str] = set()
    for line in text.splitlines():
        ids = [m.group(0).lower() for m in ID_RE.finditer(line) if system_for(m.group(0).lower()) != "unknown"]
        hay = squash(line)
        files = [f"file:{n}" for n in sorted(known_files)
                 if len(squash(n)) >= 6 and _fuzzy_in(squash(n), hay, max(1, len(squash(n)) // 8))]
        if files:
            ids = [i for i in ids if not any(squash(i) in squash(f) for f in files)]
        for rid in ids + files:
            if rid in seen:
                continue
            seen.add(rid)
            fields: dict = {"resource_id": rid}
            if rid.startswith("file:"):
                fields["file"] = rid[5:]
                fields["result"] = "FOUND"  # a listed file is a stored file (as in the vision listing pass)
            emails = EMAIL_RE.findall(line)
            if emails:
                fields["email"] = emails[0]
            phone = PHONE_RE.search(line)
            if phone:
                fields["phone"] = phone.group(0)
            status = next((w for w in STATUS_WORDS if re.search(rf"\b{w}\b", line, re.I)), None)
            if status:
                fields["result"] = status
            ts = next((t for t in (parse_ts(x) for x in re.findall(r"\d{4}-\d{2}-\d{2}T[\d:]+Z", line)) if t), None)
            out.append(RawRecord(ef.file_id, ef.captured_at, rid, fields, ts or ef.captured_at,
                                 "object_storage" if rid.startswith("file:") else system_for(rid),
                                 "visual", "ocr_fallback", "ocr"))
    return out
