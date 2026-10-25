"""system_activity.csv -> claim facts + identity-link events.

Activity rows are claims (reported_result is not proof). We keep them in the
store with is_claim=True for debug/risk analysis, but the state
reconstructor never uses a claim to prove a resource state. The exception is
discovery metadata: LINK_RESOURCE_IDENTITY rows name a resource's owner, and
CLASSIFY_REQUEST rows cross-check intent classification.
"""
import re

from .config import PREFIX_MAP
from .identity import norm_email
from .loaders import parse_ts

_LINK_RE = re.compile(r"linked\s+\S+\s+\([^)]*\)\s+to\s+(\S+)\s+and\s+(user_\d+)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def system_for_resource(resource_id, fallback=""):
    for prefix in sorted(PREFIX_MAP, key=len, reverse=True):
        if str(resource_id).startswith(prefix + "_"):
            return PREFIX_MAP[prefix][0]
    return fallback or ""


def category_for_resource(resource_id):
    for prefix in sorted(PREFIX_MAP, key=len, reverse=True):
        if str(resource_id).startswith(prefix + "_"):
            return PREFIX_MAP[prefix][1]
    return ""


def load_activity(store, activity_rows):
    """Add claim facts; return (link_events, classify_events)."""
    links = []      # (observed_at, resource_id, email, user_id, activity_id)
    classify = []   # (observed_at, resource_id, activity_id)
    for row in activity_rows:
        ts = parse_ts(row.get("event_time"))
        resource_id = row.get("resource_id", "")
        system = system_for_resource(resource_id, row.get("target_system", ""))
        category = category_for_resource(resource_id)
        store.add(row["activity_id"], "activity", ts, system, resource_id,
                  category, "UNKNOWN", is_claim=True,
                  detail=row.get("event_type", ""))
        if row.get("event_type") == "LINK_RESOURCE_IDENTITY":
            details = row.get("details", "")
            m = _LINK_RE.search(details)
            email = None
            user_id = None
            found = _EMAIL_RE.search(details)
            if found:
                email = norm_email(found.group(0))
            if m:
                email = norm_email(m.group(1)) if "@" in m.group(1) else email
                user_id = m.group(2)
            else:
                um = re.search(r"\b(user_\d+)\b", details)
                user_id = um.group(1) if um else None
            links.append((ts, resource_id, email, user_id, row["activity_id"]))
        elif row.get("event_type") == "CLASSIFY_REQUEST":
            classify.append((ts, resource_id, row["activity_id"]))
    return links, classify
