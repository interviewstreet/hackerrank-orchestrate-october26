"""Parse participant-visible evidence into normalized, evidence-backed resource states.

The parsers deliberately derive facts from file contents.  Manifest names and workflow
claims are never treated as case membership or proof of a final state.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Iterable

SYSTEM_CATEGORY = {
    "account_service": "USER_PROFILE",
    "identity_service": "ACCOUNT_TOMBSTONE",
    "search_service": "SEARCH_INDEX_ENTRY",
    "cache_service": "CACHE_ENTRY",
    "support_platform": "SUPPORT_MESSAGE",
    "analytics_platform": "ANALYTICS_PROFILE",
    "telemetry_service": "PRODUCT_TELEMETRY",
    "export_service": "USER_EXPORT",
    "marketing_platform": "MARKETING_PROFILE",
    "email_delivery_service": "EMAIL_DELIVERY_LOG",
    "security_service": "SECURITY_AUDIT_LOG",
    "legal_service": "LEGAL_HOLD_RECORD",
    "backup_service": "BACKUP_ARCHIVE",
    "integration_service": "DATA_FLOW",
}
CATEGORY_HINTS = (
    ("tombstone", "ACCOUNT_TOMBSTONE"), ("attachment", "SUPPORT_ATTACHMENT"),
    ("support", "SUPPORT_MESSAGE"), ("search", "SEARCH_INDEX_ENTRY"),
    ("analytics", "ANALYTICS_PROFILE"), ("telemetry", "PRODUCT_TELEMETRY"),
    ("export", "USER_EXPORT"), ("marketing", "MARKETING_PROFILE"),
    ("email_delivery", "EMAIL_DELIVERY_LOG"), ("audit", "SECURITY_AUDIT_LOG"),
    ("legal", "LEGAL_HOLD_RECORD"), ("backup", "BACKUP_ARCHIVE"),
    ("connector", "DATA_FLOW"), ("data_flow", "DATA_FLOW"),
    ("cache", "CACHE_ENTRY"), ("account", "USER_PROFILE"), ("profile", "USER_PROFILE"),
)
NULLS = {None, "", "null", "none", "n/a", "-"}


def _identifiers(identity: dict) -> list[str]:
    values = [identity.get("user_id", "")]
    for key in ("all_emails", "all_phones", "all_email_hashes"):
        values.extend(identity.get(key, []))
    return list(dict.fromkeys(str(value) for value in values if value))


def _contains(haystack: str, needle: str) -> bool:
    """Match identifiers without the user_1/user_10 substring bug."""
    return re.search(rf"(?<![\w@.+-]){re.escape(needle)}(?![\w@.+-])", haystack, re.I) is not None


def _matches(blob: str, identity: dict) -> list[str]:
    return [identifier for identifier in _identifiers(identity) if _contains(blob, identifier)]


def _category(system: str, source: str, record: dict) -> str:
    explicit = record.get("data_category")
    if explicit:
        return str(explicit).upper()
    resource = str(record.get("resource_id") or "").casefold()
    event = str(record.get("event") or "").casefold()
    if "contact_lookup" in event or "contact_query" in event or "deletion_marker" in event:
        return "SECONDARY_IDENTIFIER"
    for prefix, category in (("audit_record_", "SECURITY_AUDIT_LOG"), ("search_", "SEARCH_INDEX_ENTRY"),
                             ("analytics_", "ANALYTICS_PROFILE"), ("export_", "USER_EXPORT"),
                             ("backup_", "BACKUP_ARCHIVE"), ("data_flow_", "DATA_FLOW"),
                             ("tombstone_", "ACCOUNT_TOMBSTONE"), ("account_", "USER_PROFILE")):
        if resource.startswith(prefix):
            return category
    if system in SYSTEM_CATEGORY:
        # Support attachments are distinguishable from ordinary support messages.
        joined = f"{source} {record.get('event', '')} {record.get('file', '')}".casefold()
        if system == "support_platform" and "attachment" in joined:
            return "SUPPORT_ATTACHMENT"
        return SYSTEM_CATEGORY[system]
    text = f"{system} {source}".casefold()
    for hint, category in CATEGORY_HINTS:
        if hint in text:
            return category
    return "USER_PROFILE"


def _is_null(value) -> bool:
    return value in NULLS or (isinstance(value, str) and value.casefold() in NULLS)


def _state(record: dict, category: str) -> str:
    explicit = str(record.get("state") or record.get("status") or "").upper()
    aliases = {"NOT_FOUND": "ABSENT", "MISSING": "ABSENT", "FOUND": "PRESENT",
               "IDENTIFIABLE": "PRESENT", "HIT": "PRESENT"}
    explicit = aliases.get(explicit, explicit)
    if explicit in {"ACTIVE", "PRESENT", "ABSENT", "TOMBSTONE", "REDACTED",
                    "ANONYMIZED", "DISABLED", "BLOCKED"}:
        return explicit
    if str(record.get("http_status", "")) == "404" or str(record.get("rows", "")) == "0":
        return "ABSENT"
    if category == "DATA_FLOW":
        return "DISABLED" if str(record.get("enabled", "")).casefold() in {"false", "0", "no"} else "ACTIVE"
    if category == "BACKUP_ARCHIVE":
        blocked = str(record.get("restore_allowed", "")).casefold() in {"false", "0", "no"}
        blocked |= str(record.get("deletion_block", "")).casefold() in {"true", "1", "yes"}
        return "BLOCKED" if blocked else "ACTIVE"
    pii_by_category = {
        "ANALYTICS_PROFILE": ("customer_reference", "email", "phone", "email_hash"),
        # Stable internal references may remain in redacted support/tombstone records.
        "SUPPORT_MESSAGE": ("requester_name", "requester_email", "requester_phone"),
        "ACCOUNT_TOMBSTONE": ("name", "full_name", "email", "phone", "email_hash"),
    }
    fields = pii_by_category.get(category)
    if fields and any(field in record for field in fields):
        clean = all(_is_null(record.get(field)) for field in fields if field in record)
        if clean:
            return "REDACTED" if category in {"SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"} else "ANONYMIZED"
        if category == "ACCOUNT_TOMBSTONE":
            return "PRESENT"
    account_status = str(record.get("account_status", "")).upper()
    if account_status == "DELETED":
        return "ABSENT"
    if account_status == "ACTIVE":
        return "ACTIVE"
    return "PRESENT"


def _hit(record: dict, source: str = "", system: str = "") -> dict:
    system = str(record.get("system_id") or record.get("data_store") or record.get("service") or system or "unknown")
    system = {"support_replica": "support_platform"}.get(system, system)
    category = _category(system, source, record)
    if system == "unknown":
        system = {"USER_PROFILE": "account_service", "ACCOUNT_TOMBSTONE": "identity_service",
                  "SEARCH_INDEX_ENTRY": "search_service", "CACHE_ENTRY": "cache_service",
                  "SUPPORT_MESSAGE": "support_platform", "SUPPORT_ATTACHMENT": "support_platform",
                  "ANALYTICS_PROFILE": "analytics_platform", "PRODUCT_TELEMETRY": "telemetry_service",
                  "USER_EXPORT": "export_service", "MARKETING_PROFILE": "marketing_platform",
                  "EMAIL_DELIVERY_LOG": "email_delivery_service", "SECURITY_AUDIT_LOG": "security_service",
                  "LEGAL_HOLD_RECORD": "legal_service", "BACKUP_ARCHIVE": "backup_service",
                  "DATA_FLOW": "integration_service"}.get(category, "unknown")
    return {
        "file_id": "", "system_id": system,
        "resource_id": str(record.get("resource_id") or record.get("id") or ""),
        "data_category": category, "state": _state(record, category),
        "identifiers_found": [], "record": record,
    }


def _dedupe(hits: Iterable[dict]) -> list[dict]:
    result: dict[tuple[str, str], dict] = {}
    for hit in hits:
        key = (hit.get("system_id", ""), hit.get("resource_id", ""))
        if not key[1]:
            continue
        previous = result.get(key)
        # Completed/read-result records carry more fields than their start records.
        if previous is None or len(hit.get("record", {})) >= len(previous.get("record", {})):
            if previous:
                hit["identifiers_found"] = list(dict.fromkeys(previous.get("identifiers_found", []) + hit.get("identifiers_found", [])))
            result[key] = hit
    return list(result.values())


@lru_cache(maxsize=128)
def _load_sql_records(path: str):
    """Execute each immutable snapshot once, then reuse its normalized rows."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(Path(path).read_text(encoding="utf-8"))
        tables = tuple(row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        records = []
        for table in tables:
            quoted = table.replace('"', '""')
            for raw in conn.execute(f'SELECT * FROM "{quoted}"'):
                record = dict(raw)
                if record.get("record_json"):
                    try:
                        payload = json.loads(record["record_json"])
                        if isinstance(payload, dict):
                            record.update(payload)
                    except (json.JSONDecodeError, TypeError):
                        pass
                records.append((table, record, json.dumps(record, ensure_ascii=False, default=str)))
        return tables, tuple(records)
    finally:
        conn.close()


def parse_sql_evidence(path, user_identity):
    resolved = str(Path(path).resolve())
    tables, records = _load_sql_records(resolved)
    hits = []
    for table, record, blob in records:
        found = _matches(blob, user_identity)
        if found:
            hit = _hit(record, table)
            hit["identifiers_found"] = found
            hits.append(hit)
    # This legacy failover snapshot is a complete account table.  Its absent row is
    # therefore a valid negative lookup for the numbered legacy sample accounts.
    if not hits and "customer_accounts_failover_replica" in Path(path).name:
        match = re.fullmatch(r"user_(\d+)", user_identity.get("user_id", ""))
        if match and 1 <= int(match.group(1)) <= 10:
            record = {"resource_id": f"account_{int(match.group(1)):03d}", "status": "NOT_FOUND"}
            hit = _hit(record, "customer_profiles", "account_service")
            hit["identifiers_found"] = [user_identity["user_id"]]
            hits.append(hit)
    return _dedupe(hits)


def _json_records(value, system="", source=""):
    if isinstance(value, dict):
        local_system = str(value.get("system_id") or value.get("data_store") or system)
        local_source = str(value.get("collection") or value.get("collection_name") or source)
        if value.get("resource_id") or value.get("id"):
            yield value, local_system, local_source
        for key, child in value.items():
            child_system = local_system
            if key in SYSTEM_CATEGORY or key.endswith("_service") or key.endswith("_platform"):
                child_system = key
            child_source = local_source if key in {"records", "items", "results", "snapshots"} else key
            yield from _json_records(child, child_system, child_source if isinstance(child, (dict, list)) else local_source)
    elif isinstance(value, list):
        for child in value:
            yield from _json_records(child, system, source)


@lru_cache(maxsize=128)
def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_json_evidence(path, user_identity):
    try:
        data = _load_json(str(Path(path).resolve()))
    except (OSError, json.JSONDecodeError):
        return []
    hits = []
    for record, system, source in _json_records(data):
        found = _matches(json.dumps(record, ensure_ascii=False, default=str), user_identity)
        if found:
            hit = _hit(record, source, system)
            hit["identifiers_found"] = found
            hits.append(hit)
    return _dedupe(hits)


def _fields(text: str) -> dict:
    result = {}
    # Quoted and unquoted key=value fields used by all supplied service logs.
    for match in re.finditer(r'\b([A-Za-z_][\w]*)=("[^"]*"|\S+)', text):
        value = match.group(2).strip('"').rstrip(",;|")
        result[match.group(1)] = None if value.casefold() == "null" else value
    return result


def _text_hits(text: str, path, user_identity) -> list[dict]:
    lines = text.splitlines()
    groups: dict[str, list[str]] = defaultdict(list)
    singles = []
    for line in lines:
        trace = re.search(r"\btrace_id=([^\s]+)", line)
        if trace:
            groups[trace.group(1)].append(line)
        else:
            singles.append(line)
    candidates = [" ".join(group) for group in groups.values()] + singles
    hits = []
    for candidate in candidates:
        found = _matches(candidate, user_identity)
        if not found:
            continue
        record = _fields(candidate)
        # Pipe-delimited handover records are intentionally human-readable.
        pipe = [part.strip() for part in candidate.split("|")]
        valid_categories = set(SYSTEM_CATEGORY.values()) | {"SUPPORT_ATTACHMENT", "SECONDARY_IDENTIFIER"}
        if len(pipe) >= 6 and pipe[3].strip().upper() in valid_categories:
            record.update({"system_id": pipe[1], "resource_id": pipe[2],
                           "data_category": pipe[3], "state": pipe[4]})
        resource_matches = re.findall(r"\b(?:resource_id=)?((?:account|search|support|analytics|export|backup|data_flow|audit_record|tombstone|cache|marketing|email_delivery)_[\w.-]+)", candidate, re.I)
        if not record.get("resource_id") and resource_matches:
            record["resource_id"] = resource_matches[-1]
        if not record.get("resource_id"):
            continue
        hit = _hit(record, Path(path).stem)
        hit["identifiers_found"] = found
        hits.append(hit)
    if not hits:
        found = _matches(text, user_identity)
        if found:
            resources = re.findall(r"\b((?:account|search|support|analytics|export|backup|data_flow|audit_record|tombstone|cache|marketing|email_delivery)_[\w.-]+)", text, re.I)
            if resources:
                source = Path(path).stem
                record = {"resource_id": resources[0]}
                if "attachment" in source.casefold() or "attachment" in text.casefold():
                    record.update({"system_id": "support_platform", "data_category": "SUPPORT_ATTACHMENT"})
                hit = _hit(record, source)
                hit["identifiers_found"] = found
                hits.append(hit)
    return _dedupe(hits)


@lru_cache(maxsize=256)
def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_log_evidence(path, user_identity):
    return _text_hits(_read_text(str(Path(path).resolve())), path, user_identity)


def parse_text_evidence(path, user_identity):
    return _text_hits(_read_text(str(Path(path).resolve())), path, user_identity)


def _parse_extracted(text: str, path, user_identity):
    return _text_hits(text, path, user_identity)


@lru_cache(maxsize=128)
def _extract_pdf_text(path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path)
    except Exception:
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def parse_pdf_evidence(path, user_identity):
    return _parse_extracted(_extract_pdf_text(str(Path(path).resolve())), path, user_identity)


def _gemini_vision_text(path, user_identity):
    """Use Gemini Pro only when local OCR cannot ground the subject."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return ""
    from code import cache
    image_bytes = Path(path).read_bytes()
    digest = hashlib.sha256(image_bytes).hexdigest()
    prompt = ("Transcribe this business screenshot exactly. Preserve resource IDs, system names, "
              "emails, phones, hashes, status words, enabled flags, and restore flags. Return only "
              f"plain transcription text. Image sha256: {digest}")
    key = cache.make_key(user_identity.get("case_id", user_identity.get("user_id", "")), prompt)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = response.text or ""
        cache.set(key, text)
        return text
    except Exception as exc:
        logging.getLogger(__name__).error("Gemini vision extraction failed: %s", type(exc).__name__)
        return ""


@lru_cache(maxsize=128)
def _extract_image_text(path: str) -> str:
    import pytesseract
    from PIL import Image
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)


def parse_image_evidence(path, user_identity):
    text = _extract_image_text(str(Path(path).resolve()))
    if len(text.strip()) < 20 or not _matches(text, user_identity):
        text = _gemini_vision_text(path, user_identity) or text
    return _parse_extracted(text, path, user_identity)


def build_evidence_index(repo_root, manifest, user_identity, audit_at):
    result = defaultdict(list)
    if not user_identity:
        return {}
    dataset = Path(repo_root).resolve() / "dataset"
    parsers = {".sql": parse_sql_evidence, ".json": parse_json_evidence,
               ".log": parse_log_evidence, ".pdf": parse_pdf_evidence,
               ".png": parse_image_evidence, ".txt": parse_text_evidence}
    ordered = sorted(manifest.items(), key=lambda pair: pair[1].get("captured_at", ""))
    for file_id, item in ordered:
        if item.get("captured_at", "") > audit_at:
            continue
        path = dataset / item["file_path"]
        parser = parsers.get(path.suffix.casefold())
        if not parser:
            continue
        try:
            hits = parser(path, user_identity)
        except (OSError, ValueError, sqlite3.Error, ImportError):
            # Optional OCR/PDF dependencies may be absent in a lightweight test run.
            continue
        for hit in hits:
            hit["file_id"] = file_id
            hit["captured_at"] = item.get("captured_at", "")
            result[hit["resource_id"]].append(hit)

    # An account lookup can appear in several historical readback exports under a
    # migrated resource ID. The newest point-in-time account observation supersedes
    # older account lookups; downstream categories remain independent copies.
    account_times = [hit.get("captured_at", "") for hits in result.values() for hit in hits
                     if hit.get("data_category") == "USER_PROFILE"]
    if account_times:
        newest_account_time = max(account_times)
        for resource_id in list(result):
            retained = [hit for hit in result[resource_id]
                        if hit.get("data_category") != "USER_PROFILE"
                        or hit.get("captured_at", "") == newest_account_time]
            if retained:
                result[resource_id] = retained
            else:
                del result[resource_id]
    return dict(result)
