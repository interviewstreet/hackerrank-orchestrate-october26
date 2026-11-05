"""
lineage.py — data for the website's "data lineage map". Display only.

Nothing here is used for any deletion decision. system_activity.csv rows
are *claims* (a workflow saying what it did), not proof of state, so the
website labels every edge "reported activity (claims)".

For one case:
  * nodes come from the case's evidence hits (P2), one per
    (system_id, resource_id, replica_or_table), put in a column by
    node_group(): primary systems -> copies -> backups and archives.
  * edges come from system_activity.csv rows that
      - are about one of the case's resources: the row's resource_id, or a
        resource named in its details ("... repopulated downstream resource
        search_1934"), and
      - happened at or before the case's audit_at, and
      - are a movement (sync, index, export, cache refresh, restore) or a
        claim about a flow / backup (flow check, flow disabled, restore
        blocked, restore-access check).
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from utils import parse_ts

# Data is copied or recreated somewhere else -> drawn as an arrow
MOVEMENT_EVENTS = {
    "SYNC_RECORD": "sync",
    "INDEX_RECORD": "index",
    "CREATE_EXPORT": "export",
    "REFRESH_CACHE": "cache",
    "RESTORE_BACKUP": "restore",
}
# A claim about whether a flow or a backup can still copy data back ->
# shown on the flow / backup box, not as an arrow
CONTROL_EVENTS = {
    "CHECK_DATA_FLOW": "flow check",
    "DISABLE_DATA_FLOW": "flow disabled",
    "BLOCK_RESTORE": "restore blocked",
    "CHECK_RESTORE_ACCESS": "restore-access check",
}

PRIMARY, COPY, BACKUP = "primary", "copy", "backup"
GROUP_ORDER = (PRIMARY, COPY, BACKUP)

# Systems of record (the original copy of the user's data)
_PRIMARY_SYSTEMS = {"account_service", "identity_service", "profile_service"}
# Backups, archives and legal / retention stores
_BACKUP_HINTS = ("backup", "archive", "legal", "retention")

_RESOURCE_TOKEN = re.compile(r"\b[a-z]+(?:_[a-z]+)*_\d+\b", re.IGNORECASE)


def node_group(system_id: str, origins: Iterable[str] = (),
               replica_or_table: Optional[str] = None) -> str:
    """
    primary  the system of record (account_service, identity_service,
             profile_service), primary copy only
    backup   backups, archives, legal / retention stores (by system_id or
             the evidence file's origin)
    copy     everything else: replicas, search indexes, analytics, exports,
             logs, support, integrations, caches
    """
    system = (system_id or "").lower()
    origin_text = " ".join(o.lower() for o in origins if o)
    if any(h in system for h in _BACKUP_HINTS) or any(h in origin_text for h in _BACKUP_HINTS):
        return BACKUP
    is_replica = bool(replica_or_table) or "replica" in system or "replica" in origin_text
    if system in _PRIMARY_SYSTEMS and not is_replica:
        return PRIMARY
    return COPY


@dataclass(frozen=True)
class LineageEdge:
    activity_id: str
    event_time: str
    event_type: str
    kind: str                 # "movement" or "control"
    label: str                # e.g. "sync", "flow check"
    source_system: str
    source_resource_id: str
    target_system: str
    target_resource_id: str
    reported_result: str      # SUCCESS / FAILED / PARTIAL — a claim
    details: str


def _mentions(row: dict) -> set[str]:
    """Lower-cased resource ids a row is about: resource_id + ids named in details."""
    found = {m.lower() for m in _RESOURCE_TOKEN.findall(row.get("details") or "")}
    if row.get("resource_id"):
        found.add(row["resource_id"].lower())
    return found


def edge_from_row(row: dict, case_resources: set[str]) -> Optional[LineageEdge]:
    """Turn one activity row into an edge for a case, or None if not relevant."""
    etype = row.get("event_type", "")
    if etype in MOVEMENT_EVENTS:
        kind, label = "movement", MOVEMENT_EVENTS[etype]
    elif etype in CONTROL_EVENTS:
        kind, label = "control", CONTROL_EVENTS[etype]
    else:
        return None
    rid = (row.get("resource_id") or "").strip()
    named = sorted(_mentions(row) - {rid.lower()})
    if rid.lower() not in case_resources and not (set(named) & case_resources):
        return None
    # A movement whose details name a downstream resource ends at that resource
    # ("connector data_flow_2528 repopulated search_1934"); otherwise source and
    # target share the row's resource_id (e.g. a replication sync).
    target_rid = rid
    if kind == "movement":
        downstream = [n for n in named if n in case_resources] or named
        if downstream:
            target_rid = downstream[0]
    return LineageEdge(
        activity_id=row.get("activity_id", ""), event_time=row.get("event_time", ""),
        event_type=etype, kind=kind, label=label,
        source_system=row.get("source_system", ""), source_resource_id=rid,
        target_system=row.get("target_system", ""), target_resource_id=target_rid,
        reported_result=row.get("reported_result", ""), details=row.get("details", ""),
    )


def extract_edges(activity_rows: Iterable[dict], case_resources: Iterable[str],
                  audit_at: Optional[datetime]) -> list[LineageEdge]:
    """
    Edges for one case: relevant rows at or before *audit_at*, oldest first
    (ties by activity_id). With no audit_at nothing is returned, because
    nothing can be shown without a cut-off.
    """
    if audit_at is None:
        return []
    resources = {r.lower() for r in case_resources if r}
    if not resources:
        return []
    edges = []
    for row in activity_rows:
        ts = parse_ts(row.get("event_time"), context=f"activity {row.get('activity_id', '?')}")
        if ts is None or ts > audit_at:
            continue
        edge = edge_from_row(row, resources)
        if edge is not None:
            edges.append(edge)
    edges.sort(key=lambda e: (e.event_time, e.activity_id))
    return edges


class LineageSource:
    """Loads system_activity.csv and evidence_files.csv once for the whole run."""

    def __init__(self, dataset_dir: Path | str):
        dataset_dir = Path(dataset_dir)
        with open(dataset_dir / "system_activity.csv", newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        # index rows by every resource they mention, so each case only
        # looks at the rows about its own resources
        self._by_resource: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            for rid in _mentions(row):
                self._by_resource[rid].append(row)
        with open(dataset_dir / "evidence_files.csv", newline="", encoding="utf-8") as fh:
            self.file_origins: dict[str, str] = {r["file_id"]: r.get("origin", "")
                                                 for r in csv.DictReader(fh)}

    def edges_for(self, case_resources: Iterable[str],
                  audit_at: Optional[datetime]) -> list[LineageEdge]:
        resources = {r.lower() for r in case_resources if r}
        candidates = {id(r): r for rid in resources for r in self._by_resource.get(rid, [])}
        return extract_edges(candidates.values(), resources, audit_at)


def case_resources(evidence: Optional[dict]) -> list[str]:
    """Resource ids in P2's evidence['records'] (what the map's nodes are built from)."""
    out: list[str] = []
    for rec in (evidence or {}).get("records", []) or []:
        rid = getattr(rec, "resource_id", "") or ""
        if rid and rid not in out:
            out.append(rid)
    return out
