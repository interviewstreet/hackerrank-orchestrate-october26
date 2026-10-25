"""Log evidence: several dialects, one extraction strategy.

Each line is reduced to (timestamp, system, trace_id, event, {key=value}).
``*_started`` lines only contribute their lookup subject to the trace
context; the matching ``*_completed`` / scan / heartbeat line then emits the
fact, linked through that subject but with exposure judged solely from the
completed record's own fields.
"""
import json
import re

from ..loaders import parse_ts

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_KV_RE = re.compile(r'(\w+)=\\?"([^"\\]*(?:\\.[^"\\]*)*)\\?"|(\w+)=([^\s]+)')
_BRACKET_RE = re.compile(
    r"^\S+\s+\[[A-Z]+\]\s+\[([a-z_]+)\]\s+\[([^\]]+)\]\s+(\w+):")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

SYSTEM_ALIASES = {
    "profile_service": "account_service",
    "support_replica": "support_platform",
    "search_index_service": "search_service",
    "attachment_preview": "support_platform",
}

CONTEXT_KEYS = ("lookup_key", "match_key", "subject_key", "subject_ref",
                "owner_key", "scan_key", "correlation_key", "query",
                "subject_reference", "customer_email")

COMPLETED_SUFFIXES = ("_completed", "_scan", "_read", "_evaluated", "_loaded",
                      "_heartbeat", "_check")


def _clean(value):
    if value is None:
        return None
    s = str(value).strip().strip('"')
    if s.lower() in ("null", "none", ""):
        return None
    return s


def _parse_line(line):
    ts_m = _TS_RE.search(line)
    ts = parse_ts(ts_m.group(0)) if ts_m else None
    kv = {}
    # JSON dialect
    brace = line.find("{")
    if brace >= 0:
        try:
            obj = json.loads(line[brace:])
            if isinstance(obj, dict):
                kv.update({str(k): v for k, v in obj.items()})
        except ValueError:
            pass
    unescaped = line.replace('\\"', '"').replace("\\'", "'")
    for m in _KV_RE.finditer(unescaped):
        key = m.group(1) or m.group(3)
        val = m.group(2) if m.group(2) is not None else m.group(4)
        kv.setdefault(key, val)
    system = None
    trace = None
    event = _clean(kv.get("event"))
    bracket = _BRACKET_RE.match(line.strip())
    if bracket:
        system, trace, event = bracket.group(1), bracket.group(2), bracket.group(3)
    parts = [p.strip() for p in line.split(" | ")]
    if len(parts) >= 5 and _TS_RE.match(parts[0]):
        system = system or parts[2]
        trace = trace or parts[3]
        event = event or parts[4]
    system = system or _clean(kv.get("service")) or _clean(kv.get("logger")) \
        or _clean(kv.get("function"))
    trace = trace or _clean(kv.get("trace_id")) or _clean(kv.get("requestId")) \
        or _clean(kv.get("request_id"))
    if trace is None:
        # syslog-style dialect: bare "tr-..." token, preceded by the bare
        # service name (e.g. `node-9 search_service tr-5482781 - -`).
        bare = re.search(r"\b([a-z]+(?:_[a-z]+)+)\s+(tr-[A-Za-z0-9]+)\b", line)
        if bare:
            system = system or bare.group(1)
            trace = bare.group(2)
        else:
            bare_trace = re.search(r"\b(tr-[A-Za-z0-9]+)\b", line)
            if bare_trace:
                trace = bare_trace.group(1)
    if system in SYSTEM_ALIASES:
        system = SYSTEM_ALIASES[system]
    return ts, system, trace, event, kv


def _context_ids(kv_or_ctx):
    emails, users, hashes = set(), set(), set()
    for key in CONTEXT_KEYS:
        v = _clean(kv_or_ctx.get(key))
        if not v:
            continue
        if "@" in v:
            emails.add(v.lower())
        elif v.startswith("user_"):
            users.add(v)
        elif _HEX64.match(v.lower()):
            hashes.add(v.lower())
    return emails, users, hashes


def parse_log_text(text, source_id, store, manifest_ts):
    before = len(store.facts)
    traces = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        ts, system, trace, event, kv = _parse_line(line)
        if not event:
            continue
        observed = ts or manifest_ts
        resource_id = _clean(kv.get("resource_id"))
        if trace and (event.endswith("_started") or event.endswith("_query_started")
                      or event.endswith("_scan_started") or "started" in event):
            ctx = traces.setdefault(trace, {})
            for key in CONTEXT_KEYS:
                if _clean(kv.get(key)):
                    ctx[key] = kv[key]
            if resource_id:
                ctx.setdefault("resource_id", resource_id)
            continue
        if event == "export_started" or (event == "export_completed" and not resource_id):
            continue
        ctx = traces.get(trace, {}) if trace else {}
        ctx_emails, ctx_users, ctx_hashes = _context_ids(ctx)
        kv_emails, kv_users, kv_hashes = _context_ids(kv)
        emails = ctx_emails | kv_emails
        users = ctx_users | kv_users
        hashes = ctx_hashes | kv_hashes
        if not resource_id:
            resource_id = ctx.get("resource_id")
        if not resource_id:
            continue
        sys_id = system or ""
        record = {k: _clean(v) for k, v in kv.items()
                  if k in ("email", "customer_reference", "customer_email",
                           "owner_email", "requester_email", "requester_name",
                           "requester_phone", "phone", "email_hash",
                           "subject_reference", "full_name", "display_name",
                           "user_id", "message_text")}
        record = {k: v for k, v in record.items() if v is not None}

        def emit(category, presence, rec=None, exposed=None, attributable=None,
                 enabled=None, restore=None, retention=None):
            store.add(source_id, "evidence", observed,
                      _clean(kv.get("system")) or sys_id, resource_id, category,
                      presence, record=rec,
                      emails=emails or None, user_ids=users or None,
                      hashes=hashes or None, exposed=exposed,
                      attributable=attributable, enabled=enabled,
                      restore_allowed=restore, retention_until=retention)

        if event == "record_lookup":
            _emit_lookup(store, source_id, observed, kv, resource_id, emails, users)
        elif event == "profile_lookup_completed":
            rows = _clean(kv.get("rows"))
            status = _clean(kv.get("http_status"))
            if rows == "0" or status == "404":
                emit("USER_PROFILE", "ABSENT", rec=None)
            else:
                emit("USER_PROFILE", "PRESENT", rec=record)
        elif event == "index_query_completed":
            result = (_clean(kv.get("result")) or "").lower()
            total = _clean(kv.get("total_hits")) or _clean(kv.get("total"))
            if result in ("no_hit", "miss", "not_found") or total == "0":
                emit("SEARCH_INDEX_ENTRY", "ABSENT", rec=None)
            else:
                emit("SEARCH_INDEX_ENTRY", "PRESENT", rec=record)
        elif event in ("analytics_profile_read_completed", "analytics_profile_read"):
            emit("ANALYTICS_PROFILE", "PRESENT", rec=record)
        elif event == "analytics_identity_scan":
            matched = _clean(kv.get("matched_value"))
            emit("ANALYTICS_PROFILE", "PRESENT",
                 rec={"email": matched} if matched and "@" in matched else record,
                 exposed=True, attributable=True)
        elif event == "contact_lookup_completed":
            emit("SECONDARY_IDENTIFIER", "PRESENT", rec=None,
                 exposed=True, attributable=True)
        elif event in ("connector_config_read_completed", "connector_config_loaded",
                       "connector_heartbeat"):
            enabled = _clean(kv.get("enabled"))
            emit("DATA_FLOW", "PRESENT", rec=record,
                 enabled=(enabled.lower() == "true" if enabled else None))
        elif event == "restore_policy_read_completed":
            restore = _clean(kv.get("restore_allowed"))
            emit("BACKUP_ARCHIVE", "PRESENT", rec=record,
                 restore=(restore.lower() == "true" if restore else None))
        elif event == "restore_candidate_evaluated":
            blocked = (_clean(kv.get("deletion_block")) or "").lower() == "true"
            eligible = (_clean(kv.get("eligible")) or "").lower() == "true"
            emit("BACKUP_ARCHIVE", "PRESENT", rec=record,
                 restore=(eligible and not blocked))
        elif event == "restore_authorization_completed":
            emit("BACKUP_ARCHIVE", "PRESENT", rec=record,
                 restore=(_clean(kv.get("decision")) or "").lower() != "deny")
        elif event == "audit_record_read_completed":
            rows = _clean(kv.get("rows"))
            if rows == "0":
                emit("SECURITY_AUDIT_LOG", "ABSENT", rec=None)
            else:
                emit("SECURITY_AUDIT_LOG", "PRESENT", rec=record,
                     retention=parse_ts(_clean(kv.get("retention_until"))))
        elif event == "support_ticket_read_completed":
            emit("SUPPORT_MESSAGE", "PRESENT", rec=record)
        elif event == "message_pii_scan":
            matched = _clean(kv.get("matched_value"))
            rec = {"email": matched} if matched and "@" in matched else record
            emit("SUPPORT_MESSAGE", "PRESENT", rec=rec, exposed=True,
                 attributable=True)
        elif event == "attachment_pii_scan":
            matched = _clean(kv.get("matched_value"))
            rec = {"email": matched} if matched and "@" in matched else \
                {"phone": matched} if matched else record
            emit("SUPPORT_ATTACHMENT", "PRESENT", rec=rec, exposed=True,
                 attributable=True)
        elif event == "message_read":
            emit("SUPPORT_MESSAGE", "PRESENT", rec=record)
        elif event == "contact_query_completed":
            rows = _clean(kv.get("rows"))
            if rows == "0":
                emit("SUPPORT_ATTACHMENT", "ABSENT", rec=None)
            else:
                # legacy contact index in the support replica: a contact
                # record, treated for deletion (not a retained conversation)
                emit("SUPPORT_ATTACHMENT", "PRESENT", rec=None,
                     exposed=True, attributable=True)
        elif event == "deletion_marker_check":
            if (_clean(kv.get("marker_found")) or "").lower() == "false":
                emit("SUPPORT_ATTACHMENT", "PRESENT", rec=None,
                     exposed=True, attributable=True)
        elif event in ("export_metadata_read_completed",
                       "export_download_check_completed"):
            avail = _clean(kv.get("available"))
            if avail and avail.lower() == "false":
                emit("USER_EXPORT", "ABSENT", rec=None)
            else:
                emit("USER_EXPORT", "PRESENT", rec=record)
        # all other events (lookups, cache, retries, collector) are noise
    return len(store.facts) - before


def _emit_lookup(store, source_id, observed, kv, resource_id, emails, users):
    result = (_clean(kv.get("result")) or "").upper()
    system = _clean(kv.get("system")) or ""
    record_type = _clean(kv.get("record_type")) or ""
    subject = _clean(kv.get("subject_reference")) or ""
    if "@" in subject:
        emails = set(emails) | {subject.lower()}
    elif subject.startswith("user_"):
        users = set(users) | {subject}
    presence = "ABSENT" if result == "NOT_FOUND" else "PRESENT"
    enabled = (result == "ACTIVE") if record_type == "DATA_FLOW" else None
    restore = (result == "ACTIVE") if record_type == "BACKUP_ARCHIVE" else None
    exposed = result == "IDENTIFIABLE"
    store.add(source_id, "evidence", observed, system, resource_id, record_type,
              presence, record={"subject_reference": subject} if presence == "PRESENT" and not exposed else ({"email": subject} if exposed and "@" in subject else None),
              emails=emails or None, user_ids=users or None,
              enabled=enabled, restore_allowed=restore,
              exposed=exposed if presence == "PRESENT" else False,
              attributable=exposed if presence == "PRESENT" else False)
