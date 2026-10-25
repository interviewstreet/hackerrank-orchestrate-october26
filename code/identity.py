"""Current and historical identity resolution at a case audit boundary."""
from __future__ import annotations


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))


def _snapshot_as_of(user_id: str, audit_at: str, data: dict) -> dict:
    current = dict(data["user_identities"].get(user_id, {}))
    if not audit_at:
        return current
    # The snapshot is the newest known state. Reverse changes that occurred after the
    # audit cutoff so future identifiers cannot leak into an earlier investigation.
    events = data["user_audit_log"].get(user_id, [])
    for event in reversed(events):
        if event.get("event_time", "") <= audit_at:
            continue
        field = event.get("field_name")
        if field in {"email", "phone", "email_hash", "name"}:
            current[field] = event.get("old_value", "")
    return current


def resolve_identity(email: str, audit_at: str, data: dict) -> dict | None:
    needle = (email or "").casefold()
    user_id = None
    as_of_snapshots = {}
    for candidate in data["user_identities"]:
        snapshot = _snapshot_as_of(candidate, audit_at, data)
        as_of_snapshots[candidate] = snapshot
        if (snapshot.get("email") or "").casefold() == needle:
            user_id = candidate
            break
        eligible = [event for event in data["user_audit_log"].get(candidate, [])
                    if not audit_at or event.get("event_time", "") <= audit_at]
        if any(event.get("field_name") == "email" and needle in {
            (event.get("old_value") or "").casefold(),
            (event.get("new_value") or "").casefold(),
        } for event in eligible):
            user_id = candidate
            break
    if not user_id:
        return None

    current = as_of_snapshots.get(user_id) or _snapshot_as_of(user_id, audit_at, data)
    values = {"email": [], "phone": [], "email_hash": []}
    eligible_events = [
        event for event in data["user_audit_log"].get(user_id, [])
        if not audit_at or event.get("event_time", "") <= audit_at
    ]
    for event in eligible_events:
        field = event.get("field_name")
        if field in values:
            values[field].extend([event.get("old_value"), event.get("new_value")])
    historical_emails = _unique(value for value in values["email"] if value != current.get("email"))
    historical_phones = _unique(value for value in values["phone"] if value != current.get("phone"))
    historical_hashes = _unique(value for value in values["email_hash"] if value != current.get("email_hash"))
    return {
        "user_id": user_id,
        "current_email": current.get("email", ""),
        "current_name": current.get("name", ""),
        "current_phone": current.get("phone", ""),
        "current_email_hash": current.get("email_hash", ""),
        "historical_emails": historical_emails,
        "historical_phones": historical_phones,
        "historical_email_hashes": historical_hashes,
        "all_emails": _unique([current.get("email"), *historical_emails]),
        "all_phones": _unique([current.get("phone"), *historical_phones]),
        "all_email_hashes": _unique([current.get("email_hash"), *historical_hashes]),
    }
