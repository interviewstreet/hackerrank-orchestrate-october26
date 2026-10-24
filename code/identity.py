"""Current and historical identity resolution."""
from __future__ import annotations


def _unique(values):
    return list(dict.fromkeys(v for v in values if v))


def resolve_identity(email: str, requested_at: str, data: dict) -> dict | None:
    del requested_at  # history is needed even when changes followed the request
    needle = (email or "").casefold()
    current = data.get("user_identities_by_email", {}).get(needle)
    user_id = current.get("user_id") if current else None
    if not user_id:
        for candidate, events in data["user_audit_log"].items():
            if any(e.get("field_name") == "email" and needle in {
                (e.get("old_value") or "").casefold(), (e.get("new_value") or "").casefold()
            } for e in events):
                user_id = candidate
                break
    if not user_id:
        return None
    current = data["user_identities"].get(user_id, {})
    values = {"email": [], "phone": [], "email_hash": []}
    for event in data["user_audit_log"].get(user_id, []):
        field = event.get("field_name")
        if field in values:
            values[field].extend([event.get("old_value"), event.get("new_value")])
    historical_emails = _unique(v for v in values["email"] if v != current.get("email"))
    historical_phones = _unique(v for v in values["phone"] if v != current.get("phone"))
    historical_hashes = _unique(v for v in values["email_hash"] if v != current.get("email_hash"))
    return {
        "user_id": user_id,
        "current_email": current.get("email", ""), "current_name": current.get("name", ""),
        "current_phone": current.get("phone", ""), "current_email_hash": current.get("email_hash", ""),
        "historical_emails": historical_emails, "historical_phones": historical_phones,
        "historical_email_hashes": historical_hashes,
        "all_emails": _unique([current.get("email"), *historical_emails]),
        "all_phones": _unique([current.get("phone"), *historical_phones]),
        "all_email_hashes": _unique([current.get("email_hash"), *historical_hashes]),
    }
