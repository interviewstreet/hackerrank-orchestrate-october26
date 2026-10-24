"""Temporal boundary and activity reconstruction helpers."""
from __future__ import annotations


def filter_events(activity_list: list[dict], user_identity: dict, audit_at: str) -> list[dict]:
    if not user_identity:
        return []
    identifiers = [user_identity.get("user_id", "")]
    for key in ("all_emails", "all_phones", "all_email_hashes"):
        identifiers.extend(user_identity.get(key, []))
    needles = [str(v).casefold() for v in identifiers if v]
    result = []
    for event in activity_list:
        if event.get("event_time", "") > audit_at:
            continue
        haystack = f"{event.get('resource_id', '')} {event.get('details', '')}".casefold()
        if any(v in haystack for v in needles):
            result.append(event)
    return sorted(result, key=lambda e: e.get("event_time", ""))


def get_latest_state(events_for_resource: list[dict]) -> tuple[str, str] | None:
    if not events_for_resource:
        return None
    latest = max(events_for_resource, key=lambda e: e.get("event_time", ""))
    return latest.get("event_type", ""), latest.get("reported_result", "")
