"""Ground subject-to-resource lineage from participant-visible catalog events."""
from __future__ import annotations

import re

RESOURCE_PATTERN = re.compile(
    r"\b(?:account|search|support|analytics|export|backup|data_flow|audit_record|"
    r"tombstone|cache|marketing|email_delivery|object)_[A-Za-z0-9.-]+\b",
    re.IGNORECASE,
)


def catalog_resource_ids(events: list[dict]) -> list[str]:
    """Return resources explicitly linked to the resolved subject by the data catalog.

    The caller must pass identity- and audit-time-filtered events. Workflow operation
    claims are intentionally excluded: only explicit catalog lineage events are trusted.
    """
    resources = []
    for event in events:
        if event.get("event_type", "").upper() != "LINK_RESOURCE_IDENTITY":
            continue
        resource_id = event.get("resource_id", "")
        if resource_id:
            resources.append(resource_id)
        resources.extend(RESOURCE_PATTERN.findall(event.get("details", "")))
    return list(dict.fromkeys(resources))


def augment_identity_lineage(identity: dict | None, events: list[dict]) -> dict | None:
    if identity is None:
        return None
    resources = catalog_resource_ids(events)
    identity["lineage_resource_ids"] = list(
        dict.fromkeys([*identity.get("lineage_resource_ids", []), *resources])
    )
    # Invalidate the evidence matcher cache if a caller augments an identity twice.
    identity.pop("_match_identifiers", None)
    return identity
