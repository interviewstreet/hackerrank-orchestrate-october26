"""Service logs in five layouts (logfmt, JSON-per-line, bracketed, pipe-delimited, RFC5424 syslog, and the
cloud-runtime wrapper with an escaped `message="k=\\"v\\""` payload) -> RawRecords.

Lookup keys and the resource/result usually sit on different lines of the same trace, so lines are grouped
by trace id and merged before a record is emitted for each resource the trace mentions.
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict

from ..loaders import parse_ts
from ..models import EvidenceFile
from .records import REFERENCE_FIELDS, RawRecord, system_for

KV_RE = re.compile(r'([A-Za-z_][\w.]*)=("(?:[^"\\]|\\.)*"|\S+)')
BRACKET_RE = re.compile(r"^\[(?P<level>\w+)\]\s+\[(?P<service>[\w.-]+)\](?:\s+\[(?P<trace>[\w.-]+)\])?\s+(?P<event>\w+):")
PIPE_RE = re.compile(r"^\|\s*(?P<level>\w+)\s*\|\s*(?P<service>[\w.-]+)\s*\|\s*(?P<trace>[\w.-]+)\s*\|\s*(?P<event>\w+)\s*\|")
SYSLOG_RE = re.compile(r"^<\d+>\d+\s+\S+\s+(?P<service>[\w.-]+)\s+(?P<trace>[\w.-]+)\s+-\s+-\s")
TRACE_PREFIXES = ("tr-", "rb-")


def _unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v.replace('\\"', '"')


def parse_line(line: str) -> dict | None:
    line = line.rstrip("\n")
    if not line.strip():
        return None
    ts_str, _, rest = line.partition(" ")
    ts = parse_ts(ts_str)
    if ts is None:
        return None
    rest = rest.strip()
    fields: dict = {}
    if rest.startswith("{"):
        try:
            fields = {k: (None if v is None else str(v)) for k, v in json.loads(rest).items()}
        except json.JSONDecodeError:
            return None
        if "logger" in fields and "service" not in fields:
            fields["service"] = fields["logger"]
    else:
        for rx in (BRACKET_RE, PIPE_RE, SYSLOG_RE):
            m = rx.match(rest)
            if m:
                fields.update({k: v for k, v in m.groupdict().items() if v})
                if "trace" in fields:
                    fields["trace_id"] = fields.pop("trace")
                rest = rest[m.end():]
                break
        for k, v in KV_RE.findall(rest):
            fields[k] = _unquote(v)
        if "message" in fields and "=" in fields["message"]:
            for k, v in KV_RE.findall(fields.pop("message")):
                fields[k] = _unquote(v)
        if "requestId" in fields:
            fields.setdefault("trace_id", fields.pop("requestId"))
        if "function" in fields:
            fields.setdefault("service", fields.pop("function"))
    for k, v in list(fields.items()):
        if isinstance(v, str) and v.lower() == "null":
            fields[k] = None
    fields["_ts"] = ts
    return fields


def extract(ef: EvidenceFile) -> tuple[list[RawRecord], set[tuple[str, str]]]:
    lines = [p for p in (parse_line(l) for l in ef.path.read_text(encoding="utf-8").splitlines()) if p]
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for i, f in enumerate(lines):
        trace = f.get("trace_id") or ""
        key = trace if trace.startswith(TRACE_PREFIXES) else f"__line{i}"
        groups.setdefault(key, []).append(f)

    records: list[RawRecord] = []
    for key, group in groups.items():
        rids = list(dict.fromkeys(f["resource_id"] for f in group if f.get("resource_id")))
        # lines without a resource (lookup started, cache/connection noise) only contribute who was looked up;
        # their own result fields (e.g. a cache "miss") say nothing about the resource
        shared = {}
        for f in group:
            if not f.get("resource_id"):
                for k, v in f.items():
                    if (k in REFERENCE_FIELDS or k in {"service", "trace_id"}) and (v is not None or k not in shared):
                        shared[k] = v
        for rid in rids:
            merged = dict(shared)
            last_ts = None
            for f in group:
                if f.get("resource_id") == rid:
                    for k, v in f.items():
                        if v is not None or k not in merged:
                            merged[k] = v
                    last_ts = f["_ts"]
            ts = merged.pop("_ts", None)
            service = merged.get("service")
            records.append(RawRecord(
                evidence_id=ef.file_id,
                captured_at=ef.captured_at,
                resource_id=rid,
                fields=merged,
                observed_at=last_ts or ts,
                system_hint=merged.get("system") if merged.get("system") else system_for(rid, service),
                location="log",
                collection=str(merged.get("event") or ""),
                source_format="log",
            ))
    return records, set()
