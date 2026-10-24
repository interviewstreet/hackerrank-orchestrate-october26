"""Log files -> typed read-back observations (plan section 5, milestone 3).

Lines are parsed by ``log_lines.parse_line`` (six shapes). Then each event is typed by a
table: every event name must be in exactly one table, else ``ShapeError``.

* ``STATE_EVENTS``  - a read-back of one resource (rows / http_status / result / enabled ...).
* ``START_EVENTS``  - opens a trace and carries the lookup key (the subject identifier).
* ``CLAIM_EVENTS``  - "operation succeeded" style lines: typed as operation claims, never proof.
* ``NOISE_EVENTS``  - infrastructure lines with no resource state (counted, not used).

Within one trace (same file, same trace id) the lookup keys of the start lines link the
subject to the resources read later in that trace; a ``connection_acquired`` pool names the
physical copy (``account_service_primary`` -> ``primary``). Logs never declare a scope: an
unmentioned resource is not absent (D9); only an explicit 404 / miss / rows=0 is.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from evidence.common import (
    ABSENT,
    ACTIVE,
    BLOCKED,
    DISABLED,
    IDENTIFIABLE,
    OPEN,
    OPERATION_CLAIM,
    PRESENT,
    PRIMARY,
    RE_EMAIL,
    RE_HASH,
    RE_RESOURCE_ID,
    RE_USER_ID,
    REDACTED,
    STATE_READBACK,
    Extraction,
    Identifiers,
    Observation,
    ShapeError,
    result_state,
)
from evidence.log_lines import LogLine, parse_line
from loaders import EvidenceFile, normalize_email, normalize_phone, parse_ts

LOOKUP_KEYS = ("lookup_key", "subject_key", "match_key", "subject_ref", "owner_key", "scan_key",
               "correlation_key", "subject_reference")
# Fields that hold the record's own content (exposure), as opposed to the query key.
CONTENT_KEYS = ("email", "phone", "email_hash", "customer_email", "customer_reference", "owner_email",
                "requester_email", "requester_phone", "requester_name", "matched_value")
NAME_FIELDS = {"requester_name"}
SERVICE_SYSTEM = {"profile_service": "account_service", "support_replica": "support_platform"}
SERVICE_COPY = {"support_replica": "replica"}
RE_PHONE = re.compile(r"^\+?[\d][\d\s().-]{6,}$")


def _true(value) -> bool | None:
    if value is None:
        return None
    return str(value).strip().lower() in ("true", "1", "yes", "allow", "allowed")


def _rows_state(f: dict) -> dict:
    if f.get("rows") is not None:
        return {"exists": PRESENT if int(f["rows"]) > 0 else ABSENT}
    if f.get("http_status") is not None:
        return {"exists": PRESENT if f["http_status"].startswith("2") else ABSENT}
    raise ShapeError("lookup without rows/http_status")


def _hit_state(f: dict) -> dict:
    if f.get("total_hits") is not None:
        return {"exists": PRESENT if int(f["total_hits"]) > 0 else ABSENT}
    result = (f.get("result") or "").lower()
    if result not in ("hit", "miss"):
        raise ShapeError(f"index result {result!r}")
    return {"exists": PRESENT if result == "hit" else ABSENT}


def _identifiable(f: dict) -> dict:
    state = {"exists": PRESENT}
    if f.get("direct_identifiers") is not None:
        if int(f["direct_identifiers"]) > 0:
            state["treatment"] = IDENTIFIABLE
    elif f.get("matched_value"):
        state["treatment"] = IDENTIFIABLE
    return state


def _flow(f: dict) -> dict:
    enabled = _true(f.get("enabled"))
    if enabled is None:
        raise ShapeError("connector line without enabled")
    return {"exists": PRESENT, "flow_state": ACTIVE if enabled else DISABLED}


def _restore_decision(f: dict) -> dict:
    return {"exists": PRESENT, "restore_state": OPEN if _true(f.get("decision")) else BLOCKED}


def _restore_candidate(f: dict) -> dict:
    open_ = _true(f.get("eligible")) and not _true(f.get("deletion_block"))
    return {"exists": PRESENT, "restore_state": OPEN if open_ else BLOCKED}


def _restore_policy(f: dict) -> dict:
    if _true(f.get("archive_present")) is False:
        return {"exists": ABSENT}
    allowed = _true(f.get("restore_allowed"))
    return {"exists": PRESENT, **({} if allowed is None else {"restore_state": OPEN if allowed else BLOCKED})}


def _available(f: dict) -> dict:
    return {"exists": PRESENT if _true(f.get("available")) else ABSENT}


def _message_read(f: dict) -> dict:
    text = (f.get("message_text") or "").strip()
    return {"exists": PRESENT, **({"treatment": REDACTED} if text.upper() == "[REDACTED]" else {})}


def _marker(f: dict) -> dict:
    found = _true(f.get("marker_found"))
    if found is None:
        raise ShapeError("deletion_marker_check without marker_found")
    return {"exists": ABSENT if found else PRESENT}


def _record_lookup(f: dict) -> dict:
    return result_state(f.get("result") or "", f.get("record_type") or "")


def _present(_f: dict) -> dict:
    return {"exists": PRESENT}


# event -> (state function, record_type stated by the event, or "")
STATE_EVENTS = {
    "profile_lookup_completed": (_rows_state, ""),
    "index_query_completed": (_hit_state, ""),
    "analytics_identity_scan": (_identifiable, ""),
    "analytics_profile_read": (_identifiable, ""),
    "analytics_profile_read_completed": (_present, ""),
    # A contact record that stores a marketing opt-in flag is marketing data (rule_10), not an
    # analytics profile: category from content, not from the id prefix (plan 9.5).
    "contact_lookup_completed": (_rows_state, "MARKETING_PROFILE"),
    "restore_authorization_completed": (_restore_decision, ""),
    "restore_candidate_evaluated": (_restore_candidate, ""),
    "restore_policy_read_completed": (_restore_policy, ""),
    "export_download_check_completed": (_available, ""),
    "export_metadata_read_completed": (_available, ""),
    "connector_config_loaded": (_flow, ""),
    "connector_heartbeat": (_flow, ""),
    "connector_config_read_completed": (_flow, ""),
    "retained_order_loaded": (_present, "LEGAL_HOLD_RECORD"),
    "audit_record_read_completed": (_rows_state, ""),
    "attachment_pii_scan": (_identifiable, "SUPPORT_ATTACHMENT"),
    "message_pii_scan": (_identifiable, "SUPPORT_MESSAGE"),
    "message_read": (_message_read, "SUPPORT_MESSAGE"),
    "support_ticket_read_completed": (_present, "SUPPORT_MESSAGE"),
    # A contact-index row maps a contact identifier to a record: a secondary identifier (rule_02).
    "contact_query_completed": (_rows_state, "SECONDARY_IDENTIFIER"),
    "deletion_marker_check": (_marker, ""),
    "record_lookup": (_record_lookup, None),   # record_type comes from the line
}
START_EVENTS = frozenset({
    "profile_lookup_started", "index_query_started", "analytics_profile_read_started",
    "analytics_profile_scan_started", "restore_policy_check_started", "restore_policy_read_started",
    "export_download_check_started", "export_metadata_read_started", "connector_config_read_started",
    "retained_order_query_started", "audit_record_query_started", "audit_record_read_started",
    "attachment_scan_started", "message_scan_started", "support_ticket_read_started", "contact_query_started",
})
RE_CLAIM_EVENT = re.compile(r"^(?:delete|deletion|purge|erase|anonymi[sz]e|redact)\w*_(?:completed|succeeded|done|ok)$")
NOISE_EVENTS = frozenset({
    "cache_lookup", "connection_acquired", "dependency_recovered", "dependency_retry", "certificate_checked",
    "checkpoint_saved", "slow_call_rate", "cache_refresh", "flag_snapshot_loaded", "connection_pool_pressure",
    "telemetry_flushed", "consumer_lag", "properties_reloaded", "lease_renewed", "lease_extended", "timer_tick",
    "pool_sample", "delivery_abandoned", "batch_started", "export_started", "export_completed", "disk_latency",
    # names a resource but states nothing about it (a preview render failed)
    "thumbnail_failed",
})


def field_ids(fields: dict, keys) -> Identifiers:
    ids = Identifiers()
    for key in keys:
        value = fields.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        if key in NAME_FIELDS:
            ids.names.add(value)
        elif "@" in value:
            ids.emails.update(normalize_email(e) for e in RE_EMAIL.findall(value))
        elif RE_USER_ID.fullmatch(value):
            ids.user_ids.add(value)
        elif RE_HASH.fullmatch(value):
            ids.hashes.add(value.lower())
        elif "phone" in key or RE_PHONE.match(value):
            ids.phones.add(normalize_phone(value))
    return ids


def _copy(lines: list[LogLine], service: str) -> str:
    for ll in lines:
        pool = ll.fields.get("pool")
        if ll.event == "connection_acquired" and pool:
            for system in (service, SERVICE_SYSTEM.get(service, service)):
                if pool.startswith(system + "_"):
                    return pool[len(system) + 1:]
            return pool.rsplit("_", 1)[-1]
    return SERVICE_COPY.get(service, PRIMARY)


def extract(ev: EvidenceFile, path: Path) -> Extraction:
    out = Extraction(family="log")
    parsed: list[tuple[int, LogLine]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            ll = parse_line(raw)
        except ShapeError as exc:
            raise ShapeError(f"{ev.file_id}:{line_no}: {exc}") from exc
        known = (ll.event in STATE_EVENTS or ll.event in START_EVENTS or ll.event in NOISE_EVENTS
                 or RE_CLAIM_EVENT.match(ll.event))
        if not known:
            raise ShapeError(f"{ev.file_id}:{line_no}: unknown event {ll.service}/{ll.event}")
        parsed.append((line_no, ll))
        out.rows_parsed += 1

    traces: dict[str, list[LogLine]] = defaultdict(list)
    for line_no, ll in parsed:
        traces[ll.trace_id or f"line{line_no}"].append(ll)

    for line_no, ll in parsed:
        if ll.event in NOISE_EVENTS:
            out.skip(f"noise:{ll.event}")
            continue
        if ll.event in START_EVENTS:
            continue
        trace = traces[ll.trace_id or f"line{line_no}"]
        rid = ll.fields.get("resource_id")
        if not rid or not RE_RESOURCE_ID.fullmatch(rid):
            raise ShapeError(f"{ev.file_id}:{line_no}: {ll.event} without a resource id")
        keys = Identifiers()
        for other in trace:
            if other.event in START_EVENTS or other is ll:
                keys.update(field_ids(other.fields, LOOKUP_KEYS))
        content = field_ids(ll.fields, CONTENT_KEYS)
        link = Identifiers()
        link.update(keys)
        link.update(content)
        system = ll.fields.get("system") if ll.event == "record_lookup" else SERVICE_SYSTEM.get(ll.service, ll.service)
        common = dict(obs_id=f"{ev.file_id}#{line_no}", file_id=ev.file_id, source_kind="log", family=out.family,
                      available_at=ev.captured_at, state_observed_at=ll.at, system_id=system, resource_id=rid,
                      physical_copy=_copy(trace, ll.service), link_ids=link, fields=dict(ll.fields),
                      detail=f"{ll.shape}:{ll.event}")
        if RE_CLAIM_EVENT.match(ll.event):
            out.observations.append(Observation(assertion=OPERATION_CLAIM, **common))
            continue
        state_fn, record_type = STATE_EVENTS[ll.event]
        state = state_fn(ll.fields)
        if record_type is None:
            record_type = ll.fields.get("record_type") or ""
        exposed = content if any(k in ll.fields for k in CONTENT_KEYS) else None
        if state.get("exists") == ABSENT:
            exposed = None
        retention = ll.fields.get("retention_until")
        if retention and parse_ts(retention) is None:
            raise ShapeError(f"{ev.file_id}:{line_no}: bad retention_until {retention!r}")
        out.observations.append(Observation(assertion=STATE_READBACK, record_type=record_type,
                                            exposed_ids=exposed, **common, **state))
    return out
