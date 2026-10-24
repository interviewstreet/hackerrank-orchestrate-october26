"""SQLite-compatible SQL snapshot exports -> observations and scopes.

Each file runs in its own in-memory SQLite database. Two families:

* replica snapshots (``customer_data_<copy>``, ``customer_profiles_<copy>``,
  ``search_documents_<copy>``): every table is a full copy, so the file is a full-scope
  listing of every system it contains, per physical copy.
* inventory snapshots (``snapshot_scope`` + one table per service): the listing is
  complete only for the systems in ``snapshot_scope`` and only for the subjects that
  appear in the file (see ``Scope.subjects``).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from evidence.common import (PRIMARY, SNAPSHOT_ROW, Extraction, Identifiers, Observation, Scope,
                             ShapeError, record_state, resource_refs, scan_identifiers)
from loaders import EvidenceFile, parse_ts

RE_COPY = re.compile(r"^(?P<base>.+?)_(?P<copy>primary|failover_replica|read_replica|reporting_replica|replica_[a-z_]+)$")

# Inventory / replica tables whose rows are not record_json documents.
TABLE_SYSTEMS = {
    "customer_profiles": "account_service",
    "customer_search_documents": "search_service",
    "search_documents": "search_service",
    "customer_analytics_profiles": "analytics_platform",
    "support_records": "support_platform",
    "customer_exports": "export_service",
    "connector_subscriptions": "integration_service",
    "backup_restore_entries": "backup_service",
    "security_audit_records": "security_service",
}
RECORD_JSON_BASES = {"customer_data"}
UPDATED_KEYS = ("updated_at", "indexed_at")


def _rows(con: sqlite3.Connection, table: str) -> list[dict]:
    cur = con.execute(f'SELECT * FROM "{table}"')
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def extract(ev: EvidenceFile, path: Path) -> Extraction:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(path.read_text(encoding="utf-8"))
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if "snapshot_scope" in tables:
            return _inventory(ev, con, tables)
        return _replicas(ev, con, tables)
    finally:
        con.close()


def _observation(ev, family, n, system_id, copy, collection, record, observed_at, detail) -> Observation:
    ids = scan_identifiers(record)
    updated = next((record[k] for k in UPDATED_KEYS if record.get(k)), None)
    rid = record.get("resource_id")
    if not rid:
        raise ShapeError(f"{ev.file_id}: row without resource_id in {detail}")
    return Observation(
        obs_id=f"{ev.file_id}#{n}", file_id=ev.file_id, source_kind="sql", family=family,
        available_at=ev.captured_at, state_observed_at=observed_at, system_id=system_id,
        resource_id=rid, assertion=SNAPSHOT_ROW, physical_copy=copy, collection=collection,
        record_updated_at=parse_ts(updated) if updated else None,
        link_ids=ids, exposed_ids=ids, fields=record, refs=resource_refs(record), detail=detail,
        **record_state(system_id, record),
    )


def _replicas(ev: EvidenceFile, con, tables) -> Extraction:
    out = Extraction(family="sql_replica_snapshot")
    origin_systems: set[str] = set()   # systems seen in any record_json copy table
    table_copies: list[tuple[str, str]] = []
    n = 0
    for table in tables:
        match = RE_COPY.match(table)
        if not match:
            raise ShapeError(f"{ev.file_id}: table {table!r} has no known copy suffix")
        base, copy = match.group("base"), match.group("copy")
        if base not in RECORD_JSON_BASES and base not in TABLE_SYSTEMS:
            raise ShapeError(f"{ev.file_id}: unknown table {table!r}")
        table_copies.append((base, copy))
        for row in _rows(con, table):
            n += 1
            if base in RECORD_JSON_BASES:
                if "record_json" not in row or "origin_system" not in row:
                    raise ShapeError(f"{ev.file_id}: {table} lacks record_json/origin_system")
                record = json.loads(row["record_json"])
                record.setdefault("updated_at", row.get("updated_at"))
                if record.get("resource_id") != row.get("resource_id"):
                    raise ShapeError(f"{ev.file_id}: resource_id mismatch in {table}")
                system, collection = row["origin_system"], row.get("collection_name", "")
                origin_systems.add(system)
            else:
                record, system, collection = row, TABLE_SYSTEMS[base], base
            out.observations.append(_observation(ev, out.family, n, system, copy, collection, record,
                                                 ev.captured_at, table))
            out.rows_parsed += 1
    # Each copy table is a full copy. A record_json copy mirrors every origin system of the
    # file, so a system missing from one copy (replication drift) is ABSENT there.
    seen = set()
    for base, copy in table_copies:
        systems = sorted(origin_systems) if base in RECORD_JSON_BASES else [TABLE_SYSTEMS[base]]
        for system in systems:
            if (system, copy) not in seen:
                seen.add((system, copy))
                out.scopes.append(Scope(ev.file_id, out.family, system, copy, ev.captured_at, ev.captured_at))
    return out


def _inventory(ev: EvidenceFile, con, tables) -> Extraction:
    out = Extraction(family="sql_inventory")
    scope_rows = _rows(con, "snapshot_scope")
    scope_at = {r["origin_system"]: parse_ts(r["captured_at"]) for r in scope_rows}
    if not scope_at:
        raise ShapeError(f"{ev.file_id}: empty snapshot_scope")
    subjects = Identifiers()
    n = 0
    for table in tables:
        if table == "snapshot_scope":
            continue
        if table not in TABLE_SYSTEMS:
            raise ShapeError(f"{ev.file_id}: unknown inventory table {table!r}")
        system = TABLE_SYSTEMS[table]
        for row in _rows(con, table):
            n += 1
            if system not in scope_at:
                out.skip(f"row outside snapshot_scope ({system})")
                continue
            obs = _observation(ev, out.family, n, system, PRIMARY, table, row, scope_at[system], table)
            subjects.update(obs.link_ids)
            out.observations.append(obs)
            out.rows_parsed += 1
    for system, at in sorted(scope_at.items()):
        out.scopes.append(Scope(ev.file_id, out.family, system, PRIMARY, ev.captured_at, at,
                                subjects=subjects))
    return out
