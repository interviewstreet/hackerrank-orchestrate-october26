"""PNG evidence: OCR (tesseract via pytesseract, or the tesseract CLI),
cached on disk. Extracted text is then parsed like a document.

Screenshots are single-subject admin consoles. In addition to resource ids
visible in the text, status words ("Ready", archives, connector lists) are
kept in the extracted text for the document-style extractor. If OCR is not
available the parser returns no facts instead of failing the whole run.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from ..config import CACHE_DIR
from .pdf_parser import facts_from_document_text

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover
    pytesseract = None
    Image = None


def _cache_path():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "ocr_cache.json"


def ocr_image(path):
    key = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    cache_file = _cache_path()
    cache = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    if key in cache:
        return cache[key]
    text = ""
    if pytesseract is not None and Image is not None:
        try:
            text = pytesseract.image_to_string(Image.open(path))
        except Exception:
            text = ""
    if not text:
        try:
            out = subprocess.run(["tesseract", str(path), "stdout"],
                                 capture_output=True, text=True, timeout=60)
            text = out.stdout or ""
        except Exception:
            text = ""
    cache[key] = text
    try:
        cache_file.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass
    return text


# Screenshot-specific patterns: "<Name> / user_NN - resource_id - email",
# plus label/value pairs tesseract commonly mangles are handled by the
# generic email/user/resource regexes in the document extractor.
_EXTRA_PATTERNS = [
    re.compile(r"(backup_\d+).*?restore", re.I | re.S),
]


def parse_image_file(path, source_id, store, manifest_ts):
    text = ocr_image(path)
    before = len(store.facts)
    facts_from_document_text(text, source_id, store, manifest_ts,
                             subject_only=True)
    # Consoles whose subject resource is named without a system prefix word
    # nearby still yield facts via document extraction; backup/connector/
    # marketing/search consoles need their category fixed by filename-free
    # content cues:
    low = text.lower()
    from ..facts import EMAIL_RE, USER_RE
    # A screenshot is a single-subject console: lists/tables on it name other
    # customers too. Only the first email/user (the opened subject) may link
    # the screenshot's resources; taking every address would cross-link them.
    _all_emails = [m.group(0).lower() for m in EMAIL_RE.finditer(text)]
    _all_users = USER_RE.findall(text)
    emails = {_all_emails[0]} if _all_emails else set()
    users = {_all_users[0]} if _all_users else set()
    full_ids = sorted(set(re.findall(
        r"\b(?:account|search|analytics|support|export|data_flow|backup|"
        r"audit_record|tombstone|legal_hold|marketing|cache|email_delivery|"
        r"object)_[\w\-]+\b", text)))
    existing = {f.resource_id for f in store.facts[before:]}
    for resource_id in full_ids:
        if resource_id in existing:
            continue
        if resource_id.startswith("marketing_"):
            cat, sys_id = "MARKETING_PROFILE", "marketing_platform"
        elif resource_id.startswith("search_"):
            cat, sys_id = "SEARCH_INDEX_ENTRY", "search_service"
        elif resource_id.startswith("analytics_"):
            cat, sys_id = "ANALYTICS_PROFILE", "analytics_platform"
        elif resource_id.startswith("backup_"):
            cat, sys_id = "BACKUP_ARCHIVE", "backup_service"
        elif resource_id.startswith("data_flow"):
            cat, sys_id = "DATA_FLOW", "integration_service"
        elif resource_id.startswith("export_"):
            cat, sys_id = "USER_EXPORT", "export_service"
        elif resource_id.startswith("tombstone"):
            cat, sys_id = "ACCOUNT_TOMBSTONE", "identity_service"
        elif resource_id.startswith("object_"):
            cat, sys_id = "SUPPORT_ATTACHMENT", "object_storage"
        else:
            continue
        enabled = True if ("enabled" in low or "healthy" in low) else None
        store.add(source_id, "evidence", manifest_ts, sys_id, resource_id,
                  cat, "PRESENT",
                  record={"email": next(iter(emails), None)} if emails else None,
                  emails=emails or None, user_ids=users or None,
                  exposed=bool(emails), attributable=bool(emails or users),
                  enabled=enabled)
    return len(store.facts) - before
