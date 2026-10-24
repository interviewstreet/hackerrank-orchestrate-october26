"""system_activity.csv -> typed observations.

Each row is typed by what it asserts (decision D4):

* ``ownership_link``   - LINK_RESOURCE_IDENTITY: a catalog links a resource to identifiers.
* ``activity_readback`` - CHECK_DATA_FLOW / CHECK_RESTORE_ACCESS: a status check read back
                         the live state ("remains enabled", "can still be restored").
* ``sync_fact``        - a connector or restore job repopulated a downstream resource.
* ``operation_claim``  - everything else ("worker reported success"). Never proof of state.
"""

from __future__ import annotations

import re

from evidence.common import (
    ACTIVE,
    ACTIVITY_READBACK,
    BLOCKED,
    DISABLED,
    OPEN,
    OPERATION_CLAIM,
    OWNERSHIP_LINK,
    Extraction,
    Identifiers,
    Observation,
    scan_identifiers,
)
from loaders import Activity

SYNC_FACT = "sync_fact"
RE_FLOW_ACTIVE = re.compile(r"\b(?:remains|is still|still) (?:enabled|active)\b", re.I)
RE_FLOW_OFF = re.compile(r"\b(?:is|was|remains) (?:disabled|inactive|stopped)\b", re.I)
RE_RESTORE_OPEN = re.compile(r"\bcan still be restored\b", re.I)
RE_RESTORE_BLOCKED = re.compile(r"\b(?:cannot|can no longer) be restored\b|\brestore (?:is )?blocked\b", re.I)
RE_REPOPULATED = re.compile(r"\brepopulated downstream resource\b", re.I)
RE_EXCLUSIVE = re.compile(r"\bbelongs only to\b|\bno other subject\b", re.I)


def extract(rows: list[Activity]) -> Extraction:
    out = Extraction(family="activity")
    for a in rows:
        state: dict = {}
        fields: dict[str, object] = {"event_type": a.event_type, "source_system": a.source_system,
                  "reported_result": a.reported_result, "details": a.details}
        if a.event_type == "LINK_RESOURCE_IDENTITY":
            assertion = OWNERSHIP_LINK
            fields["exclusive"] = bool(RE_EXCLUSIVE.search(a.details))
        elif a.event_type == "CHECK_DATA_FLOW" and (RE_FLOW_ACTIVE.search(a.details) or RE_FLOW_OFF.search(a.details)):
            assertion = ACTIVITY_READBACK
            state = {"flow_state": ACTIVE if RE_FLOW_ACTIVE.search(a.details) else DISABLED}
        elif a.event_type == "CHECK_RESTORE_ACCESS" and (RE_RESTORE_OPEN.search(a.details)
                                                         or RE_RESTORE_BLOCKED.search(a.details)):
            assertion = ACTIVITY_READBACK
            state = {"restore_state": OPEN if RE_RESTORE_OPEN.search(a.details) else BLOCKED}
        elif RE_REPOPULATED.search(a.details):
            assertion = SYNC_FACT
        else:
            assertion = OPERATION_CLAIM
        ids = scan_identifiers(a.details) if assertion == OWNERSHIP_LINK else None
        out.observations.append(Observation(
            obs_id=a.activity_id, file_id=a.activity_id, source_kind="activity", family="activity",
            available_at=a.event_time, state_observed_at=a.event_time, system_id=a.target_system,
            resource_id=a.resource_id, assertion=assertion, fields=fields, detail=a.event_type,
            link_ids=ids if ids is not None else Identifiers(), **state))
        out.rows_parsed += 1
    return out
