"""Service logs in six line formats (key=value, JSON body, syslog, pipe, bracket, cloud runtime).

Each line is reduced to (timestamp, trace_id, event, fields). Lines are grouped by trace so the
identifier on a '*_started' line (lookup_key, match_key, subject_ref, ...) links the person to the
resource reported on the matching '*_completed' line, even when that record is gone (404).
Only events listed in EVENTS produce observations; everything else is noise.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Callable

from ..errors import ParseError
from .base import (ParseResult, classify_record, flag, is_null, ledger_result, norm_subject,
                   system_for)

log = logging.getLogger(__name__)

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
_KV = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|[^\s"|]+)')
_TRACE = re.compile(r"\b(?:tr|rb)-[0-9A-Za-z-]+")
_TOKEN = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")
# Fields that carry an identifier linking a trace to a person.
_SUBJECT_KEYS = ("lookup_key", "match_key", "scan_key", "subject_key", "owner_key", "correlation_key",
                 "subject_ref", "subject_reference", "matched_value", "lookup_value")
_IDENTITY_FIELDS = ("email", "phone", "email_hash", "customer_reference", "customer_email",
                    "requester_email", "requester_name", "requester_phone", "owner_email",
                    "subject_reference", "subject_ref", "user_id")

Handler = Callable[[dict], "tuple[str, str] | None"]


def _exists(kv: dict) -> str:
    """IDENTIFIABLE / REFERENCED / ANONYMIZED from whatever identity fields the line reports."""
    fields = {k: kv[k] for k in _IDENTITY_FIELDS if k in kv}
    if not fields:
        return "IDENTIFIABLE"  # the record exists; the line just does not echo its fields
    return classify_record(fields)[0]


def _rows_zero(kv: dict) -> bool:
    return str(kv.get("rows", "")).strip() == "0" or str(kv.get("http_status", "")) == "404"


def _profile(kv):   return ("USER_PROFILE", "NOT_FOUND" if _rows_zero(kv) else _exists(kv))
def _search(kv):
    miss = str(kv.get("result", "")).lower() in ("miss", "none", "0") or str(kv.get("total_hits", "")) == "0"
    return ("SEARCH_INDEX_ENTRY", "NOT_FOUND" if miss else _exists(kv))
def _ticket(kv):    return ("SUPPORT_MESSAGE", "NOT_FOUND" if _rows_zero(kv) else _exists(kv))
def _msg_read(kv):
    redacted = "[REDACTED]" in str(kv.get("message_text", ""))
    return ("SUPPORT_MESSAGE", "REDACTED" if redacted else _exists(kv))
def _analytics(kv):
    if _rows_zero(kv):
        return ("ANALYTICS_PROFILE", "NOT_FOUND")
    if str(kv.get("direct_identifiers", "")).strip() not in ("", "0"):
        return ("ANALYTICS_PROFILE", "IDENTIFIABLE")
    return ("ANALYTICS_PROFILE", _exists(kv) if any(k in kv for k in _IDENTITY_FIELDS) else "ANONYMIZED")
def _audit(kv):     return ("SECURITY_AUDIT_LOG", "NOT_FOUND" if _rows_zero(kv) else "REFERENCED")
def _connector(kv):
    enabled = flag(kv.get("enabled"))
    return None if enabled is None else ("DATA_FLOW", "ACTIVE" if enabled else "DISABLED")
def _restore_policy(kv):
    if flag(kv.get("archive_present")) is False:
        return ("BACKUP_ARCHIVE", "NOT_FOUND")
    allowed = flag(kv.get("restore_allowed"))
    return None if allowed is None else ("BACKUP_ARCHIVE", "RESTORE_ALLOWED" if allowed else "RESTORE_BLOCKED")
def _restore_auth(kv):
    allowed = flag(kv.get("decision"))
    return None if allowed is None else ("BACKUP_ARCHIVE", "RESTORE_ALLOWED" if allowed else "RESTORE_BLOCKED")
def _restore_candidate(kv):
    eligible, blocked = flag(kv.get("eligible")), flag(kv.get("deletion_block"))
    if eligible is None:
        return None
    return ("BACKUP_ARCHIVE", "RESTORE_ALLOWED" if eligible and not blocked else "RESTORE_BLOCKED")
def _export(kv):
    available = flag(kv.get("available"))
    return None if available is None else ("USER_EXPORT", _exists(kv) if available else "NOT_FOUND")
# The support replica's legacy contact index is a secondary copy of the person's contact
# details, not a conversation: rule_02 SECONDARY_IDENTIFIER (always DELETE) applies.
def _contact(kv):   return ("SECONDARY_IDENTIFIER", "NOT_FOUND" if _rows_zero(kv) else "IDENTIFIABLE")
def _marketing(kv): return ("MARKETING_PROFILE", "NOT_FOUND" if _rows_zero(kv) else "IDENTIFIABLE")
def _marker(kv):
    found = flag(kv.get("marker_found"))
    return ("SECONDARY_IDENTIFIER", "IDENTIFIABLE") if found is False else None


EVENTS: dict[str, Handler] = {
    "profile_lookup_completed": _profile,
    "index_query_completed": _search,
    "support_ticket_read_completed": _ticket,
    "message_pii_scan": lambda kv: ("SUPPORT_MESSAGE", "IDENTIFIABLE"),
    "attachment_pii_scan": lambda kv: ("SUPPORT_ATTACHMENT", "IDENTIFIABLE"),
    "message_read": _msg_read,
    "analytics_profile_read": _analytics,
    "analytics_profile_read_completed": _analytics,
    "analytics_identity_scan": lambda kv: ("ANALYTICS_PROFILE", "IDENTIFIABLE"),
    "audit_record_read_completed": _audit,
    "connector_config_read_completed": _connector,
    "connector_config_loaded": _connector,
    "connector_heartbeat": _connector,
    "restore_policy_read_completed": _restore_policy,
    "restore_authorization_completed": _restore_auth,
    "restore_candidate_evaluated": _restore_candidate,
    "export_metadata_read_completed": _export,
    "export_download_check_completed": _export,
    "contact_query_completed": _contact,
    "contact_lookup_completed": _marketing,
    "deletion_marker_check": _marker,
}


def parse_line(line: str) -> tuple[str, str | None, str | None, dict] | None:
    m = _TS.match(line)
    if not m:
        return None
    ts, body = m.group(1), line[m.end():]
    kv: dict[str, str] = {}
    brace = body.find("{")
    if brace >= 0 and body.rstrip().endswith("}"):
        try:
            kv.update({k: ("null" if v is None else str(v)) for k, v in json.loads(body[brace:]).items()})
        except json.JSONDecodeError:
            pass
    flat = body.replace('message="', " ", 1) if 'message="' in body else body  # cloud runtime nesting
    for k, v in _KV.findall(flat.replace('\\"', '"')):
        kv.setdefault(k, v[1:-1] if v.startswith('"') and v.endswith('"') else v)
    event = kv.get("event")
    if event is None:  # bracket and pipe formats carry the event as a bare token
        event = next((t for t in _TOKEN.findall(body) if t in EVENTS or t.endswith("_started")), None)
    trace = kv.get("trace_id") or kv.get("requestId")
    if not trace:
        t = _TRACE.search(body)
        trace = t.group(0) if t else None
    return ts, trace, event, kv


def _subjects(kv: dict) -> set[str]:
    out: set[str] = set()
    for key in (*_SUBJECT_KEYS, *_IDENTITY_FIELDS):
        value = kv.get(key)
        if value is not None and not is_null(value):
            s = norm_subject(key, value)
            if s:
                out.add(s)
    return out


def parse(path: Path, evidence_id: str, captured_at: str) -> ParseResult:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ParseError(evidence_id, f"not UTF-8 text: {exc}") from exc

    parsed = [(n, p) for n, line in enumerate(lines, start=1) if (p := parse_line(line))]
    trace_subjects: dict[str, set[str]] = defaultdict(set)
    for _, (_, trace, _, kv) in parsed:
        if trace:
            trace_subjects[trace] |= _subjects(kv)

    out = ParseResult()
    for n, (ts, trace, event, kv) in parsed:
        rid = kv.get("resource_id")
        if not rid or is_null(rid):
            continue
        if event == "record_lookup" or ("record_type" in kv and "result" in kv and "system" in kv):
            subj = norm_subject("subject", kv.get("subject_reference", "")) if kv.get("subject_reference") else None
            result = ledger_result(kv["record_type"], kv["result"], subj)
            if result is None:
                out.skipped += 1
                continue
            out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=ts,
                    system_id=kv.get("system") or system_for(rid), resource_id=rid,
                    category=kv["record_type"], result=result, subjects=(subj,) if subj else (),
                    raw_ref=f"line {n}")
            continue
        handler = EVENTS.get(event or "")
        if handler is None:
            continue
        verdict = handler(kv)
        if verdict is None:
            out.skipped += 1
            continue
        category, result = verdict
        subjects = _subjects(kv) | (trace_subjects.get(trace, set()) if trace else set())
        out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=ts,
                system_id=system_for(rid), resource_id=rid, category=category, result=result,
                subjects=tuple(sorted(subjects)), retention_until=kv.get("retention_until"),
                raw_ref=f"line {n} {event}")
    return out
