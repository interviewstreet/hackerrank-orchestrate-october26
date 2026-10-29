"""
Identity resolution and evidence indexing utilities for Stage 2.

Provides:
- resolve_user_ids(email, identities, audit_log) → set[user_id]
- get_user_audit_entries(user_id, audit_log, cutoff_iso) → list[dict]
- filter_system_activity(cutoff_iso, activity) → list[dict]
- filter_evidence(cutoff_iso, evidence_files) → list[dict]

All functions are pure, side‑effect free and operate on data already loaded
by `code.load.load_dataset`.
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Dict, Set

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_iso(ts: str) -> _dt.datetime:
    """Parse an ISO‑8601 timestamp ending with 'Z' (UTC)."""
    try:
        return _dt.datetime.strptime(ts, ISO_FORMAT).replace(tzinfo=_dt.timezone.utc)
    except Exception as exc:
        raise ValueError(f"Invalid timestamp '{ts}': {exc}") from exc


def resolve_user_ids(
    email: str,
    identities: List[Dict[str, str]],
    audit_log: List[Dict[str, str]],
) -> Set[str]:
    """Return all user_ids that could correspond to the supplied email.

    Matching is performed against:
    * the current `email` column in `user_identities.csv`
    * any historical `old_value` or `new_value` where `field_name` == "email"
    in `user_audit_log.csv`.

    The comparison is case‑insensitive and whitespace‑trimmed.
    """
    target = email.strip().lower()
    matched: Set[str] = set()

    # Current snapshot
    for row in identities:
        cur_email = row.get("email", "").strip().lower()
        if cur_email == target and row.get("user_id"):
            matched.add(row["user_id"])

    # Historical audit entries
    for row in audit_log:
        if row.get("field_name", "").strip().lower() != "email":
            continue
        for col in ("old_value", "new_value"):
            val = row.get(col, "").strip().lower()
            if val == target and row.get("user_id"):
                matched.add(row["user_id"])

    return matched


def get_user_audit_entries(
    user_id: str,
    audit_log: List[Dict[str, str]],
    cutoff_iso: str,
) -> List[Dict[str, str]]:
    """Return audit log rows for ``user_id`` with ``event_time`` <= ``cutoff_iso``.
    ``cutoff_iso`` must be an ISO‑8601 UTC string.
    """
    cutoff = _parse_iso(cutoff_iso)
    result: List[Dict[str, str]] = []
    for row in audit_log:
        if row.get("user_id") != user_id:
            continue
        ev = row.get("event_time")
        if not ev:
            continue
        try:
            ev_dt = _parse_iso(ev)
        except ValueError:
            # Skip malformed timestamps – they are considered invalid evidence
            continue
        if ev_dt <= cutoff:
            result.append(row)
    return result


def filter_system_activity(
    activity: List[Dict[str, str]],
    cutoff_iso: str,
) -> List[Dict[str, str]]:
    """Return system activity rows with ``event_time`` <= ``cutoff_iso``.
    No additional linking is performed here – callers can further filter by
    ``resource_id`` or other identifiers as needed.
    """
    cutoff = _parse_iso(cutoff_iso)
    filtered: List[Dict[str, str]] = []
    for row in activity:
        ev = row.get("event_time")
        if not ev:
            continue
        try:
            ev_dt = _parse_iso(ev)
        except ValueError:
            continue
        if ev_dt <= cutoff:
            filtered.append(row)
    return filtered


def filter_evidence(
    evidence_files: List[Dict[str, str]],
    cutoff_iso: str,
) -> List[Dict[str, str]]:
    """Return evidence file records captured at or before ``cutoff_iso``.
    ``captured_at`` must be ISO‑8601 UTC.
    """
    cutoff = _parse_iso(cutoff_iso)
    filtered: List[Dict[str, str]] = []
    for row in evidence_files:
        cap = row.get("captured_at")
        if not cap:
            continue
        try:
            cap_dt = _parse_iso(cap)
        except ValueError:
            continue
        if cap_dt <= cutoff:
            filtered.append(row)
    return filtered

