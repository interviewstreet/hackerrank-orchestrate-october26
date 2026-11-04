"""
utils.py — small helpers shared by every pipeline stage.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Optional


def warn(msg: str) -> None:
    """Print a warning to stderr (keeps stdout clean for the summary)."""
    print(f"WARNING: {msg}", file=sys.stderr)


def to_utc(dt: datetime) -> datetime:
    """Return *dt* as an aware UTC datetime. A naive datetime is assumed UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_ts(value: Optional[str], context: str = "") -> Optional[datetime]:
    """
    Parse an ISO-8601 timestamp into an aware UTC datetime.

    Accepts "2026-09-26T11:00:00Z", "...+02:00", "2026-09-26 11:00:00",
    "2026-09-26" and fractional seconds. A missing timezone means UTC.

    Returns None (and prints a warning naming *context*) for an empty or
    missing value. Raises ValueError with a clear message if the value is
    present but cannot be parsed.
    """
    where = f" ({context})" if context else ""
    if value is None or not str(value).strip():
        warn(f"empty timestamp{where}")
        return None
    text = str(value).strip()
    if text[-1] in "Zz":
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"cannot parse timestamp {value!r}{where}") from None
    return to_utc(dt)
