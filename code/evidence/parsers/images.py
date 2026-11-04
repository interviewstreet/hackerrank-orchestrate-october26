"""Parser for PNG screenshots of internal admin consoles (OCR).

OCR engine: RapidOCR (ONNX runtime, pip-installable, no system binary).
OCR is slow (seconds per image), so results are cached as JSON under
``code/evidence/ocr_cache/`` keyed by the image's SHA-256. A cache entry is
only reused when the image bytes are identical, so a changed image is always
re-read. ``ocr_mode``:

* ``"auto"``       use cache, run OCR on a miss and store the result (default)
* ``"cache_only"`` never run the engine; a miss is reported as a ParseIssue
* ``"force"``      always run the engine and refresh the cache

Layout handling: OCR boxes are grouped into visual rows. A resource id is
linked to identifiers on its own row; page-wide identifiers are attached only
when the screen shows a single subject (<=1 email, <=1 phone, <=1 user id).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from ..models import PRESENT, ParseIssue
from ..normalize import (
    PHONE_RE,
    RESOURCE_PREFIX_SYSTEM,
    default_category_for_resource,
    extract_emails,
    extract_file_names,
    extract_phones,
    extract_resource_ids,
    extract_user_ids,
    system_for_resource,
)
from .common import ParseResult, make_record

FMT = "png"
CACHE_DIR = Path(__file__).resolve().parent.parent / "ocr_cache"
ENGINE_NAME = "rapidocr_onnxruntime"

_prefix_alt = "|".join(re.escape(p) for p, _ in RESOURCE_PREFIX_SYSTEM)
_OCR_DIGIT_FIX_RE = re.compile(rf"(?<![A-Za-z_])({_prefix_alt})([0-9oO]*[0-9][0-9oO]*|[oO]+[0-9oO]*)(?![A-Za-z_])", re.I)
_engine = None


class OCRUnavailable(RuntimeError):
    pass


def fix_ocr_text(text: str) -> str:
    """Normalise common OCR confusions inside resource ids (``audit_record_oo3``)."""
    text = text.replace("�", " · ")
    return _OCR_DIGIT_FIX_RE.sub(lambda m: m.group(1) + m.group(2).replace("o", "0").replace("O", "0"), text)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path(path: Path, digest: str) -> Path:
    # Content-addressed: changed image bytes -> different file name -> cache miss.
    return CACHE_DIR / f"{path.stem}.{digest[:16]}.json"


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise OCRUnavailable(f"{ENGINE_NAME} not installed ({exc})") from exc
        _engine = RapidOCR()
    return _engine


def run_ocr(path: Path) -> list[dict]:
    engine = _get_engine()
    result, _ = engine(str(path))
    items = []
    for box, text, conf in result or []:
        items.append({"text": str(text), "conf": round(float(conf), 4),
                      "box": [[int(round(x)), int(round(y))] for x, y in box]})
    return items


def load_ocr(path: Path, mode: str = "auto") -> tuple[list[dict], str]:
    """Return (ocr items, source) where source is 'cache' or 'engine'."""
    digest = _sha256(path)
    cpath = _cache_path(path, digest)
    if mode != "force" and cpath.is_file():
        items = _read_cache(cpath, digest)
        if items is not None:
            return items, "cache"
        # corrupt / mismatched entry: treat as a miss (re-run OCR unless cache_only)
    if mode == "cache_only":
        raise OCRUnavailable(f"no valid OCR cache entry for {path.name} and ocr_mode=cache_only")
    items = run_ocr(path)
    _write_cache(cpath, {"file": path.name, "sha256": digest, "engine": ENGINE_NAME, "items": items})
    return items, "engine"


def _read_cache(cpath: Path, digest: str) -> Optional[list[dict]]:
    """Return cached items, or None if the entry is unreadable or belongs to other bytes."""
    try:
        data = json.loads(cpath.read_text(encoding="utf-8"))
        items = data["items"]
        if data.get("sha256") != digest or not isinstance(items, list):
            return None
        if not all(isinstance(i, dict) and isinstance(i.get("text"), str) and isinstance(i.get("box"), list) for i in items):
            return None
        return items
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_cache(cpath: Path, payload: dict) -> None:
    """Atomic write; a read-only cache directory must not lose a successful OCR run."""
    try:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        tmp = cpath.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(cpath)
    except OSError:
        pass


def _rows(items: list[dict]) -> list[list[dict]]:
    """Group OCR boxes into visual rows by vertical centre."""
    boxes = []
    for it in items:
        ys = [p[1] for p in it["box"]]
        xs = [p[0] for p in it["box"]]
        boxes.append((sum(ys) / len(ys), max(ys) - min(ys), min(xs), it))
    boxes.sort(key=lambda b: (b[0], b[2]))
    rows: list[list[tuple]] = []
    for b in boxes:
        if rows:
            last = rows[-1]
            yc = sum(x[0] for x in last) / len(last)
            tol = max(8.0, 0.6 * max(b[1], max(x[1] for x in last)))
            if abs(b[0] - yc) <= tol:
                last.append(b)
                continue
        rows.append([b])
    return [[b[3] for b in sorted(r, key=lambda b: b[2])] for r in rows]


def _identifiers(text: str) -> dict:
    raw_phones = [m.group(0) for m in PHONE_RE.finditer(text)]
    return {
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "raw_phones": raw_phones,
        "users": extract_user_ids(text),
    }


def parse_image(ev, ocr_mode: str = "auto") -> ParseResult:
    res = ParseResult()
    try:
        items, source = load_ocr(ev.absolute_path, ocr_mode)
    except OCRUnavailable as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"OCR unavailable: {exc}"))
        return res
    except Exception as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"OCR failed: {type(exc).__name__}: {exc}"))
        return res
    res.bump(f"ocr_{source}")
    for it in items:
        it["text"] = fix_ocr_text(it["text"])
    page_text = " \n".join(it["text"] for it in items)
    if not page_text.strip():
        res.issues.append(ParseIssue(ev.file_id, "warning", "OCR produced no text"))
        return res

    page = _identifiers(page_text)
    single_subject = len(page["emails"]) <= 1 and len(page["phones"]) <= 1 and len(page["users"]) <= 1
    file_names = extract_file_names(page_text)
    low = page_text.lower()

    def terms_of(ids: dict) -> set:
        return ({("email", e) for e in ids["emails"]} | {("phone", p) for p in ids["phones"]}
                | {("user_id", u) for u in ids["users"]})

    def pii_of(ids: dict) -> dict:
        out = {}
        if ids["emails"]:
            out["email"] = ids["emails"][0] if len(ids["emails"]) == 1 else ids["emails"]
        if ids["raw_phones"]:
            out["phone"] = ids["raw_phones"][0] if len(ids["raw_phones"]) == 1 else ids["raw_phones"]
        return out

    seen: dict[str, dict] = {}
    for ri, row in enumerate(_rows(items)):
        row_text = " | ".join(it["text"] for it in row)
        for rid in extract_resource_ids(row_text):
            entry = seen.setdefault(rid, {"rows": [], "emails": [], "phones": [], "raw_phones": [], "users": []})
            entry["rows"].append(row_text)
            ids = _identifiers(row_text)
            for k in ("emails", "phones", "raw_phones", "users"):
                entry[k] += [v for v in ids[k] if v not in entry[k]]

    for rid, entry in seen.items():
        ids = entry
        if single_subject:
            ids = {k: list(dict.fromkeys(entry[k] + page[k])) for k in ("emails", "phones", "raw_phones", "users")}
        category = default_category_for_resource(rid)
        if category is None and rid.startswith("support_"):
            category = "SUPPORT_ATTACHMENT" if "attachment" in low else "SUPPORT_MESSAGE"
        payload = {"resource_id": rid, "ocr_rows": entry["rows"]}
        if ids["users"] and len(ids["users"]) == 1:
            payload["subject_reference"] = ids["users"][0]
        res.records.append(make_record(
            ev, system_id=system_for_resource(rid) or ev.origin, resource_id=rid, observed_at=ev.captured_at,
            presence=PRESENT, payload=payload, claim_only=False, source_format=FMT,
            locator=f"ocr rows: {len(entry['rows'])}", data_category=category,
            raw_extra={"ocr_source": source, "single_subject_screen": single_subject},
            extra_terms=terms_of(ids), pii_override=pii_of(ids),
        ))
        res.bump("resource_mentions")

    if not seen:
        # Screen without platform resource ids (e.g. reference registry, object browser).
        rid = page["users"][0] if len(page["users"]) == 1 else ev.absolute_path.stem
        category = "ACCOUNT_TOMBSTONE" if ("retained reference" in low or "deleted" in low) and page["users"] else None
        terms = terms_of(page) if single_subject else set()
        terms |= {("file_name", f) for f in file_names}
        payload = {"screen_reference": rid, "file_names": file_names}
        if single_subject and page["users"]:
            payload["subject_reference"] = page["users"][0]
        res.records.append(make_record(
            ev, system_id=ev.origin, resource_id=rid, observed_at=ev.captured_at, presence=PRESENT,
            payload=payload, claim_only=False, source_format=FMT, locator="screen", data_category=category,
            raw_extra={"ocr_source": source, "single_subject_screen": single_subject},
            extra_terms=terms, pii_override=pii_of(page) if single_subject else {},
        ))
        res.bump("screens")

    # Keep the full OCR text on every record from this image for auditability.
    for r in res.records:
        r.raw_state["ocr_text"] = page_text
    return res
