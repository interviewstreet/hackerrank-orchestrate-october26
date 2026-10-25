"""Table 3: what the workers claimed, from system_activity.csv."""
from __future__ import annotations

import logging

from ..config import ACTIVITY_CSV
from ..dataset_io import read_csv
from ..models import Activity

log = logging.getLogger(__name__)

_COLUMNS = ("activity_id", "event_time", "event_type", "source_system",
            "target_system", "resource_id", "reported_result")


def build_activities() -> list[Activity]:
    rows = read_csv(ACTIVITY_CSV, _COLUMNS)
    acts = [
        Activity(
            activity_id=r["activity_id"],
            event_time=r["event_time"],
            event_type=r["event_type"],
            source_system=r["source_system"],
            target_system=r["target_system"],
            resource_id=r["resource_id"],
            result=r["reported_result"],
        )
        for r in rows  # the free-text details column is intentionally dropped
    ]
    acts.sort(key=lambda a: (a.event_time, a.activity_id))
    log.info("activities: %d rows", len(acts))
    return acts
