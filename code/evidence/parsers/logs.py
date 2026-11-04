"""Parser for the log families under ``evidence/logs/``.

Syntax is detected per line, so a file mixing syntaxes still parses:

=================  ==========================================================
syntax             example
=================  ==========================================================
json               ``ts {"severity":..,"service":..,"event":..}``
cloud_runtime      ``ts requestId=.. level=.. function=svc message="k=\\"v\\" .."``
syslog             ``ts <pri>1 node svc trace - - k="v" ..``
app_trace          ``ts [LEVEL] [svc] [trace] event: k="v" ..``
ops_stream         ``ts | LEVEL | svc | trace | event | k="v" ..``
kv                 ``ts [LEVEL] level=.. service=.. event=.. k=v ..``
=================  ==========================================================

``kv`` covers service_events, resource_lookup_trace, support_replica and the
lookup-ledger logs (``event=record_lookup``), giving eight file families.

Identifiers usually sit on the ``*_started`` line of a trace while the state
sits on the ``*_completed`` line, so lines are correlated by trace id.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from ..models import ABSENT, PRESENT, UNKNOWN, EvidenceFile, ParseIssue
from ..normalize import (
    CANONICAL_SYSTEMS,
    default_category_for_resource,
    is_nullish,
    norm_email,
    norm_hash,
    norm_phone,
    norm_user_id,
    parse_ts,
    system_for_resource,
)
from .common import ParseResult, clean_value, ledger_presence, make_record

FMT = "log"
KV_RE = re.compile(r'([A-Za-z_][\w.]*)=("(?:[^"\\]|\\.)*"|\S+)')
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+(.*)$")
CLOUD_RE = re.compile(r'^requestId=(\S+)\s+level=(\S+)\s+function=(\S+)\s+message="(.*)"\s*$')
SYSLOG_RE = re.compile(r"^<(\d+)>1\s+(\S+)\s+(\S+)\s+(\S+)\s+-\s+-\s*(.*)$")
APP_RE = re.compile(r"^\[(\w+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]\s+(\w+):\s*(.*)$")
OPS_RE = re.compile(r"^\|?\s*(\w+)\s+\|\s+(\S+)\s+\|\s+(\S+)\s+\|\s+(\w+)\s+\|\s*(.*)$")
BARE_LEVEL_RE = re.compile(r"^(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\s+(.*)$")

ENVELOPE_KEYS = {"severity", "logger", "level", "instance", "pod", "region", "trace_id",
                 "service", "event", "attempt"}
TRACE_KEY_FIELDS = ("lookup_key", "match_key", "subject_key", "subject_ref", "scan_key", "owner_key", "correlation_key")

FAMILIES = (
    "structured_service_events", "service_events", "syslog_archive", "application_trace",
    "operations_stream", "cloud_runtime_export", "resource_lookup_trace", "lookup_ledger",
    "support_replica",
)


def family_of(file_path: str) -> str:
    name = file_path.rsplit("/", 1)[-1]
    for fam in FAMILIES:
        if name.startswith(fam):
            return fam
    if name.startswith(("search_index_diagnostic", "notification_delivery")):
        return "lookup_ledger"
    return "unknown"


@dataclass
class LogLine:
    lineno: int
    ts: object
    syntax: str
    level: Optional[str]
    service: Optional[str]
    trace: Optional[str]
    event: Optional[str]
    fields: dict = field(default_factory=dict)


def _unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return v


def _kv(text: str) -> dict:
    return {k: _unquote(v) for k, v in KV_RE.findall(text)}


def parse_line(lineno: int, line: str) -> Optional[LogLine]:
    m = TS_RE.match(line.strip())
    if not m:
        return None
    ts = parse_ts(m.group(1))
    rest = m.group(2)
    if rest.startswith("{"):
        try:
            obj = json.loads(rest)
        except ValueError:
            return None
        f = {k: (str(v) if not isinstance(v, str) else v) for k, v in obj.items()}
        return LogLine(lineno, ts, "json", f.get("severity") or f.get("level"), f.get("service") or f.get("logger"),
                       f.get("trace_id"), f.get("event"), f)
    m2 = CLOUD_RE.match(rest)
    if m2:
        body = m2.group(4).replace('\\"', '"')
        f = _kv(body)
        return LogLine(lineno, ts, "cloud_runtime", m2.group(2), m2.group(3), m2.group(1), f.get("event"), f)
    m2 = SYSLOG_RE.match(rest)
    if m2:
        f = _kv(m2.group(5))
        return LogLine(lineno, ts, "syslog", f.get("level"), m2.group(3), m2.group(4), f.get("event"), f)
    m2 = APP_RE.match(rest)
    if m2:
        f = _kv(m2.group(5))
        return LogLine(lineno, ts, "app_trace", m2.group(1), m2.group(2), m2.group(3), m2.group(4), f)
    m2 = OPS_RE.match(rest)
    if m2:
        f = _kv(m2.group(5))
        return LogLine(lineno, ts, "ops_stream", m2.group(1), m2.group(2), m2.group(3), m2.group(4), f)
    level = None
    m2 = BARE_LEVEL_RE.match(rest)
    if m2:
        level, rest = m2.group(1), m2.group(2)
    f = _kv(rest)
    if not f:
        return None
    return LogLine(lineno, ts, "kv", f.get("level") or level, f.get("service"), f.get("trace_id"), f.get("event"), f)


# ---------------------------------------------------------------------------
# Semantics
# ---------------------------------------------------------------------------

EVENT_CATEGORY = [
    ("record_lookup", None),  # uses record_type
    ("contact_lookup", "MARKETING_PROFILE"),
    ("profile_lookup", "USER_PROFILE"),
    ("index_query", "SEARCH_INDEX_ENTRY"),
    ("analytics_", "ANALYTICS_PROFILE"),
    ("attachment_", "SUPPORT_ATTACHMENT"),
    ("message_", "SUPPORT_MESSAGE"),
    ("support_ticket", "SUPPORT_MESSAGE"),
    ("contact_query", "SUPPORT_MESSAGE"),
    ("deletion_marker", None),
    ("audit_record", "SECURITY_AUDIT_LOG"),
    ("restore_", "BACKUP_ARCHIVE"),
    ("export_", "USER_EXPORT"),
    ("connector_", "DATA_FLOW"),
    ("retained_order", "LEGAL_HOLD_RECORD"),
]
STATE_EVENT_SUFFIXES = ("_completed", "_read", "_scan", "_loaded", "_heartbeat", "_evaluated")


def event_category(event: str) -> Optional[str]:
    for prefix, cat in EVENT_CATEGORY:
        if event.startswith(prefix):
            return cat
    return None


def _presence(event: str, f: dict) -> str:
    rows = f.get("rows")
    if rows is not None and str(rows).lstrip("-").isdigit():
        return PRESENT if int(rows) > 0 else ABSENT
    status = f.get("http_status")
    if status is not None and str(status).isdigit():
        s = int(status)
        if s in (404, 410):
            return ABSENT
        if 200 <= s < 300:
            return PRESENT
    total = f.get("total_hits")
    if total is not None and str(total).isdigit() and int(total) == 0:
        return ABSENT
    result = f.get("result")
    if result is not None:
        r = str(result).lower()
        if r in ("hit", "found"):
            return PRESENT
        if r in ("miss", "not_found"):
            return ABSENT
    ap = clean_value(f.get("archive_present"))
    if ap is False:
        return ABSENT
    if event.endswith(STATE_EVENT_SUFFIXES):
        return PRESENT
    return UNKNOWN


def _system(line: LogLine, rid: str) -> tuple[str, Optional[str]]:
    """(system_id, replica_or_table) for an observation line."""
    svc = line.service or ""
    if svc in CANONICAL_SYSTEMS:
        return svc, None
    inferred = system_for_resource(rid) or svc or "unknown_system"
    replica = svc if "replica" in svc else None
    return inferred, replica


def _trace_terms(values: list[str]) -> set[tuple[str, str]]:
    out = set()
    for v in values:
        if is_nullish(v):
            continue
        for kind, fn in (("email", norm_email), ("user_id", norm_user_id), ("email_hash", norm_hash)):
            n = fn(v)
            if n:
                out.add((kind, n))
                break
        else:
            p = norm_phone(v) if str(v).startswith("+") else None
            if p:
                out.add(("phone", p))
    return out


def parse_log(ev: EvidenceFile) -> ParseResult:
    res = ParseResult()
    family = family_of(ev.file_path)
    try:
        text = ev.absolute_path.read_text(encoding="utf-8")
    except OSError as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"cannot read: {exc}"))
        return res

    lines: list[LogLine] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        ll = parse_line(i, raw)
        if ll is None or ll.ts is None:
            res.issues.append(ParseIssue(ev.file_id, "warning", f"line {i}: unparsed log line"))
            res.bump("unparsed_lines")
            continue
        lines.append(ll)
        res.bump(f"syntax_{ll.syntax}")
    res.bump("lines", len(lines))

    # Pass 1: per-trace lookup keys and connection pools.
    trace_keys: dict[str, list[str]] = {}
    trace_pool: dict[str, str] = {}
    for ll in lines:
        if not ll.trace:
            continue
        for k in TRACE_KEY_FIELDS:
            if ll.fields.get(k):
                trace_keys.setdefault(ll.trace, []).append(ll.fields[k])
        if ll.fields.get("pool"):
            trace_pool[ll.trace] = ll.fields["pool"]

    # Pass 2: observations.
    trace_category: dict[str, str] = {}
    for ll in lines:
        f = ll.fields
        event = ll.event or ""
        rid = f.get("resource_id")
        if not rid or is_nullish(rid):
            res.bump("noise_lines")
            continue
        if event.endswith("_started"):
            res.bump("started_lines")
            continue
        payload = {k: v for k, v in f.items() if k not in ENVELOPE_KEYS}
        raw_extra = {
            "log_family": family,
            "log_syntax": ll.syntax,
            "level": ll.level,
            "event": event,
            "logged_service": ll.service,
            "trace_id": ll.trace,
        }
        if ll.trace and ll.trace in trace_pool:
            raw_extra["pool"] = trace_pool[ll.trace]
        extra_terms = _trace_terms(trace_keys.get(ll.trace, [])) if ll.trace else set()
        extra_terms |= _trace_terms([f[k] for k in TRACE_KEY_FIELDS if f.get(k)])

        if event == "record_lookup" and f.get("system"):
            rec = make_record(
                ev, system_id=f["system"], resource_id=rid, observed_at=ll.ts,
                presence=ledger_presence(f.get("result")), payload=payload, claim_only=True,
                source_format=FMT, locator=f"line {ll.lineno}", data_category=f.get("record_type") or None,
                raw_extra=raw_extra, extra_terms=extra_terms, pii_override={},
            )
            res.records.append(rec)
            res.bump("ledger_records")
            continue

        system, replica = _system(ll, rid)
        category = event_category(event)
        if category is None and ll.trace:
            category = trace_category.get(ll.trace)
        if category is None and (ll.service or "").startswith("attachment"):
            category = "SUPPORT_ATTACHMENT"
        if category is None:
            category = default_category_for_resource(rid)
        if category and ll.trace:
            trace_category.setdefault(ll.trace, category)
        rec = make_record(
            ev, system_id=system, resource_id=rid, observed_at=ll.ts, presence=_presence(event, f),
            payload=payload, claim_only=False, source_format=FMT, locator=f"line {ll.lineno}",
            replica_or_table=replica, data_category=category, raw_extra=raw_extra,
            extra_terms=extra_terms,
        )
        res.records.append(rec)
        res.bump("observations")
    return res
