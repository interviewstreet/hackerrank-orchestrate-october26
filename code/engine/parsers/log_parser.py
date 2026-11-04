"""Log parser: key=value service logs, message="..."-wrapped logs, and readback traces."""
from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from ..contracts import Coverage, Observation
from ..util import extract_identifiers
from .common import RESULT_TO_STATE, make_obs, truthy

KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s")


def _unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v.replace('\\"', '"')


BRACKET_RE = re.compile(r"^(\S+Z)\s+\[(\w+)\]\s+\[([\w\-]+)\]\s+\[([^\]]*)\]\s+(\w+):\s*(.*)$")
PIPE_RE = re.compile(r"^(\S+Z)\s+\|\s+(\w+)\s+\|\s+([\w\-]+)\s+\|\s+([^|]*?)\s+\|\s+(\w+)\s+\|\s*(.*)$")


def parse_line(line: str) -> Dict[str, str]:
    """Return a flat dict of a log line's fields. Handles four layouts:
    key=value, message="..."-wrapped, JSON-lines, [LEVEL] [service] [trace] event: k="v", and pipe-delimited."""
    line = line.rstrip("\n")
    ts = TS_RE.match(line)
    fields: Dict[str, str] = {"_ts": ts.group(1) if ts else ""}

    rest = line[len(fields["_ts"]):].lstrip() if fields["_ts"] else line
    if rest.startswith("{"):                                    # JSON lines
        try:
            for k, v in json.loads(rest).items():
                fields[k] = "" if v is None else str(v)
            return fields
        except ValueError:
            pass
    for rx in (BRACKET_RE, PIPE_RE):
        m = rx.match(line)
        if m:
            _, level, service, trace, event, tail = m.groups()
            fields.update({"level": level, "service": service, "trace_id": trace, "event": event})
            for k, v in KV_RE.findall(tail):
                fields.setdefault(k, _unquote(v))
            return fields

    m = re.search(r'message="(.*)"\s*$', line)
    head = line
    if m:
        inner = m.group(1).replace('\\"', '"')
        head = line[:m.start()]
        for k, v in KV_RE.findall(inner):
            fields[k] = _unquote(v)
    for k, v in KV_RE.findall(head):
        fields.setdefault(k, _unquote(v))
    return fields


def _clean(v):
    return None if v is None or v.strip().lower() in ("", "null", "none", "[redacted]") else v


def _event_to_obs_inner(evidence_id, captured_at, f, lineno):
    ev = f.get("event", "")
    rid = f.get("resource_id", "")
    ts = f.get("_ts") or captured_at
    rec = {k: v for k, v in f.items() if not k.startswith("_")}
    loc = f"line {lineno}"
    kw = dict(observed_at=ts, source_format="log", locator=loc)
    state = None
    ident = {}

    if ev == "record_lookup":                                   # explicit result row
        state = RESULT_TO_STATE.get(str(f.get("result", "")).upper())
        return make_obs(evidence_id, captured_at, {k: v for k, v in rec.items() if k not in ("result", "system", "record_type", "event", "seq", "service")},
                        system_id=f.get("system", ""), category=f.get("record_type", ""), state=state or "", **kw,
                        extra_attrs={"result": f.get("result"), "event": ev}) if state and rid else None
    if not rid:
        return None
    if ev == "profile_lookup_completed":
        code = f.get("http_status") or f.get("status_code")
        state = "ABSENT" if str(code) == "404" or f.get("rows") == "0" else "PRESENT"
    elif ev == "index_query_completed":
        state = "PRESENT" if f.get("result") == "hit" else "ABSENT"
    elif ev in ("message_pii_scan", "attachment_pii_scan", "analytics_identity_scan"):
        state = "PRESENT"
        rec["identifiable"] = True
    elif ev == "analytics_profile_read":
        state = "PRESENT"
        rec["identifiable"] = str(f.get("direct_identifiers", "0")) not in ("0", "")
    elif ev == "message_read":
        state = "PRESENT"
        rec["redacted"] = "[REDACTED]" in rec.get("message_text", "")
    elif ev in ("audit_record_read_completed", "contact_lookup_completed", "contact_query_completed",
                "support_ticket_read_completed", "analytics_profile_read_completed"):
        state = "PRESENT" if f.get("rows", "1") != "0" else "ABSENT"
        if ev == "analytics_profile_read_completed":
            rec["identifiable"] = any(_clean(f.get(k)) for k in ("email", "phone", "email_hash", "customer_reference"))
    elif ev == "restore_authorization_completed":
        state = "BLOCKED" if f.get("decision") == "deny" else "ACTIVE"
    elif ev == "restore_candidate_evaluated":
        ok = truthy(f.get("eligible")) and not truthy(f.get("deletion_block"))
        state = "ACTIVE" if ok else "BLOCKED"
    elif ev == "restore_policy_read_completed":
        ra = truthy(f.get("restore_allowed"))
        state = ("ACTIVE" if ra else "BLOCKED") if ra is not None else None
    elif ev == "connector_heartbeat":
        en = truthy(f.get("enabled"))
        state = ("ACTIVE" if (en and truthy(f.get("scheduler_registered")) is not False) else "DISABLED") if en is not None else None
    elif ev in ("connector_config_loaded", "connector_config_read_completed"):
        en = truthy(f.get("enabled"))
        state = ("ACTIVE" if en else "DISABLED") if en is not None else None
    elif ev in ("export_download_check_completed", "export_metadata_read_completed"):
        state = "PRESENT" if truthy(f.get("available")) else "ABSENT"
    elif ev == "deletion_marker_check":
        state = "PRESENT"
    if not state:
        return None
    cat = {"attachment_pii_scan": "SUPPORT_ATTACHMENT", "contact_query_completed": "SUPPORT_ATTACHMENT",
           "contact_lookup_completed": "MARKETING_PROFILE", "message_pii_scan": "SUPPORT_MESSAGE",
           "message_read": "SUPPORT_MESSAGE", "support_ticket_read_completed": "SUPPORT_MESSAGE"}.get(ev, "")
    for k in ("correlation_key", "match_key", "lookup_key", "matched_value", "subject_ref", "subject_reference",
              "customer_email", "requester_email", "owner_email", "email"):
        pass  # identifiers are harvested generically below
    return make_obs(evidence_id, captured_at, {k: v for k, v in rec.items() if k != "resource_id"} | {"resource_id": rid},
                    state=state, category=cat, **kw, extra_attrs={"event": ev})



LOOKUP_KEYS = ("lookup_key", "match_key", "subject_key", "correlation_key", "subject_ref")


def _event_to_obs(evidence_id, captured_at, f, lineno):
    """Lookup keys say which subject was queried (a LINK); they are not data stored in the record."""
    lookup = {k: f[k] for k in LOOKUP_KEYS if k in f}
    f2 = {k: v for k, v in f.items() if k not in LOOKUP_KEYS}
    o = _event_to_obs_inner(evidence_id, captured_at, f2, lineno)
    if o:
        ids = extract_identifiers(lookup)
        o.links = {"emails": list(ids["emails"]), "user_refs": list(ids["user_refs"]), "hashes": list(ids["hashes"])}
        o.attrs["lookup"] = lookup
    return o


# fields that carry a subject identifier (email / user ref / hash) rather than a resource id
IDENT_KEYS = ("lookup_key", "match_key", "subject_key", "correlation_key", "matched_value", "subject_ref",
              "subject_reference", "customer_email", "requester_email", "owner_email", "email", "customer_reference",
              "user_id", "requester_phone")


def parse_log(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    """Parse a log. Events of one trace (same trace_id) describe one lookup: the 'started' event carries the key that
    was looked up (an email), the 'completed' event carries the resource id. Identifiers are therefore shared across
    a trace so the resource can be tied to the subject."""
    events = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                events.append((n, parse_line(line)))

    trace_ids: Dict[str, Dict[str, List[str]]] = {}
    for _, f in events:
        tid = f.get("trace_id") or f.get("requestId")
        if not tid:
            continue
        ids = extract_identifiers({k: f[k] for k in IDENT_KEYS if k in f})
        bucket = trace_ids.setdefault(tid, {"emails": [], "user_refs": [], "hashes": []})
        for kind in bucket:
            for v in ids[kind]:
                if v not in bucket[kind]:
                    bucket[kind].append(v)

    obs: List[Observation] = []
    for n, f in events:
        o = _event_to_obs(evidence_id, captured_at, f, n)
        if not o:
            continue
        tid = f.get("trace_id") or f.get("requestId")
        shared = trace_ids.get(tid)
        if shared:
            for kind in ("emails", "user_refs", "hashes"):
                bucket = o.links.setdefault(kind, [])
                for v in shared[kind]:
                    if v not in bucket:
                        bucket.append(v)
            o.attrs["trace_id"] = tid
        obs.append(o)
    return obs, []
