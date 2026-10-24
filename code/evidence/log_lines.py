"""Log line dispatcher: one parser per line shape, all returning a ``LogLine``.

Shapes found in ``dataset/evidence/logs`` (plan section 5):

* ``kv``       ``TS level=INFO service=S trace_id=T event=E k=v k="v"``
               (also ``TS INFO service=S event=E ...`` with a bare level word)
* ``bracket``  ``TS [LEVEL] [service] [trace] event: k="v" ...``
* ``pipe``     ``TS | LEVEL | service | trace | event | k="v" ...``
* ``json``     ``TS {"severity": ..., "service": ..., "event": ..., ...}``
* ``syslog``   ``TS <PRI>1 host service trace - - level=L k="v" ...``
* ``cloud``    ``TS requestId=T level=L function=S message="k=\\"v\\" event=\\"E\\" ..."``

A line that matches no shape raises ``ShapeError`` (parse_coverage reports it).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from evidence.common import ShapeError
from loaders import require_ts

RE_KV = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')
RE_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+(.*)$")
RE_BRACKET = re.compile(r"^\[(\w+)\]\s+\[([\w.-]+)\]\s+\[([^\]]+)\]\s+([\w.-]+):\s*(.*)$")
RE_SYSLOG = re.compile(r"^<\d+>\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s+(.*)$")
RE_BARE_LEVEL = re.compile(r"^(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\s+(.*)$")
NULLS = {"null", "none", ""}


@dataclass
class LogLine:
    at: datetime
    shape: str
    service: str
    trace_id: str
    event: str
    level: str = ""
    fields: dict = field(default_factory=dict)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def parse_kv(text: str) -> dict:
    """``k=v`` / ``k="v"`` pairs. The whole text must be pairs (else ShapeError)."""
    pairs = {}
    rest = RE_KV.sub("", text).strip()
    if rest:
        raise ShapeError(f"unparsed text {rest[:40]!r}")
    for key, value in RE_KV.findall(text):
        pairs[key] = _unquote(value)
    return pairs


def _clean(fields: dict) -> dict:
    out = {}
    for k, v in fields.items():
        if isinstance(v, str) and v.strip().lower() in NULLS:
            v = None
        out[k] = v
    return out


def parse_line(line: str) -> LogLine:
    m = RE_TS.match(line.strip())
    if not m:
        raise ShapeError(f"no leading timestamp: {line[:60]!r}")
    at, rest = require_ts(m.group(1)), m.group(2)

    if rest.startswith("{"):
        try:
            data = json.loads(rest)
        except json.JSONDecodeError as exc:
            raise ShapeError(f"bad JSON payload: {exc}") from exc
        if not isinstance(data, dict) or "event" not in data:
            raise ShapeError("JSON payload without event")
        data = {k: (str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in data.items()}
        return LogLine(at, "json", data.get("service") or data.get("logger", ""), data.get("trace_id", ""),
                       data["event"], data.get("severity", ""), _clean(data))

    if m2 := RE_BRACKET.match(rest):
        level, service, trace, event, tail = m2.groups()
        return LogLine(at, "bracket", service, trace, event, level, _clean(parse_kv(tail)))

    if rest.startswith("|") or re.match(r"^[A-Z]+\s+\|", rest):
        parts = [p.strip() for p in rest.strip("| ").split("|")]
        if len(parts) != 5:
            raise ShapeError(f"pipe line with {len(parts)} fields")
        level, service, trace, event, tail = parts
        return LogLine(at, "pipe", service, trace, event, level, _clean(parse_kv(tail)))

    if m2 := RE_SYSLOG.match(rest):
        _host, service, trace, tail = m2.groups()
        data = parse_kv(tail)
        if "event" not in data:
            raise ShapeError("syslog line without event")
        return LogLine(at, "syslog", service, trace, data["event"], data.get("level", ""), _clean(data))

    level = ""
    if m2 := RE_BARE_LEVEL.match(rest):
        level, rest = m2.groups()
    data = parse_kv(rest)
    if "requestId" in data and "message" in data:
        inner = parse_kv(data["message"])
        if "event" not in inner:
            raise ShapeError("cloud message without event")
        return LogLine(at, "cloud", data.get("function", ""), data["requestId"], inner["event"],
                       data.get("level", ""), _clean(inner))
    if "event" not in data or "service" not in data:
        raise ShapeError(f"key=value line without service/event: {rest[:60]!r}")
    return LogLine(at, "kv", data["service"], data.get("trace_id", ""), data["event"],
                   level or data.get("level", ""), _clean(data))
