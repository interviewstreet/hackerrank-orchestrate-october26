"""Parser for SQLite-compatible SQL snapshot dumps under ``evidence/databases/``.

Each dump is executed in a private in-memory SQLite database (safer than
regex-parsing INSERT statements with escaped JSON). Three table families:

* JSON-blob tables  (resource_id, origin_system, collection_name, record_json, updated_at)
  in primary / read / regional / reporting / failover replica topologies.
* Inventory tables  (customer_profiles, support_records, ...) with a
  ``snapshot_scope`` table naming which systems were captured.
* Typed tables      (customer_profiles_primary / _failover_replica, search_documents_primary).

Replica identity is preserved: ``replica_or_table`` is None for the primary /
system-of-record table and the replica table name otherwise.
"""

from __future__ import annotations

import json
import re
import sqlite3

from ..models import COMPLETE, INFERRED, PRESENT, EvidenceFile, ParseIssue, SnapshotScope
from ..normalize import (
    COLLECTION_CATEGORY,
    INVENTORY_TABLE_SYSTEM,
    category_for,
    norm_resource_id,
    parse_ts,
    system_for_resource,
)
from .common import ParseResult, make_record

FMT = "sql"
BOOL_COLUMNS = {"enabled", "restore_allowed", "archive_present", "download_available", "available"}
HEADER_RE = re.compile(r"^--\s*([A-Za-z ]+?):\s*(.+?)\s*$")
FOOTER_RE = re.compile(r"^--\s*snapshot_completed_at=(\S+)", re.M)


def replica_name(table: str) -> str | None:
    """None for a primary table, else the replica table name."""
    t = table.lower()
    if t.endswith("_primary") or t == "primary":
        return None
    if "replica" in t or "failover" in t:
        return table
    return None


def _typed_table_system(table: str, rows: list[dict]) -> str | None:
    for r in rows:
        s = system_for_resource(str(r.get("resource_id") or ""))
        if s:
            return s
    t = table.lower()
    if t.startswith("customer_profiles"):
        return "account_service"
    if t.startswith("search_documents"):
        return "search_service"
    return None


def _typed_category(table: str) -> str | None:
    t = table.lower()
    if t in COLLECTION_CATEGORY:
        return COLLECTION_CATEGORY[t]
    base = re.sub(r"_(primary|failover_replica|read_replica|reporting_replica|replica(_\w+)?)$", "", t)
    if base.startswith("search_documents"):
        return "SEARCH_INDEX_ENTRY"
    return COLLECTION_CATEGORY.get(base)


def parse_sql(ev: EvidenceFile) -> ParseResult:
    res = ParseResult()
    try:
        text = ev.absolute_path.read_text(encoding="utf-8")
    except OSError as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"cannot read: {exc}"))
        return res

    header = {}
    for line in text.splitlines()[:12]:
        m = HEADER_RE.match(line)
        if m:
            header[m.group(1).strip().lower()] = m.group(2).strip()
    footer = FOOTER_RE.search(text)
    file_ts = (
        parse_ts(header.get("captured at"))
        or (parse_ts(footer.group(1)) if footer else None)
        or ev.captured_at
    )
    topology = header.get("database topology")

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    # Evidence SQL is data: never let it ATTACH (and so create/read) files on disk.
    con.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_ATTACH else sqlite3.SQLITE_OK)
    try:
        con.executescript(text)
    except sqlite3.Error as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"SQLite execution failed: {exc}"))
        con.close()
        return res

    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        data: dict[str, list[dict]] = {}
        cols: dict[str, list[str]] = {}
        for t in tables:
            cols[t] = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
            rows = []
            for row in con.execute(f'SELECT rowid AS __rowid__, * FROM "{t}"'):
                d = dict(row)
                for c in BOOL_COLUMNS & set(d):
                    if d[c] in (0, 1, "0", "1"):
                        d[c] = bool(int(d[c]))
                rows.append(d)
            data[t] = rows
    finally:
        con.close()

    scope_times: dict[str, object] = {}
    if "snapshot_scope" in data:
        for r in data["snapshot_scope"]:
            scope_times[str(r["origin_system"])] = parse_ts(r["captured_at"]) or file_ts

    blob_tables = [t for t in tables if {"record_json", "origin_system", "collection_name"} <= set(cols[t])]
    # Every (system, collection) present anywhere in a topology dump is
    # considered covered by *each* of its tables (that is how drift is shown).
    blob_pairs: set[tuple[str, str]] = set()
    for t in blob_tables:
        for r in data[t]:
            blob_pairs.add((str(r["origin_system"]), str(r["collection_name"])))

    for t in tables:
        if t == "snapshot_scope":
            continue
        rows = data[t]
        replica = replica_name(t)
        base_extra = {"table": t, "topology": topology}

        if t in blob_tables:
            ids_by_pair: dict[tuple[str, str], list[str]] = {p: [] for p in blob_pairs}
            for r in rows:
                try:
                    payload = json.loads(r["record_json"])
                except (TypeError, ValueError) as exc:
                    res.issues.append(ParseIssue(ev.file_id, "warning", f"{t} rowid {r['__rowid__']}: bad record_json ({exc})"))
                    payload = {}
                rid = str(r["resource_id"])
                system, coll = str(r["origin_system"]), str(r["collection_name"])
                ids_by_pair.setdefault((system, coll), []).append(norm_resource_id(rid))
                res.records.append(make_record(
                    ev, system_id=system, resource_id=rid, observed_at=file_ts, presence=PRESENT,
                    payload=payload if isinstance(payload, dict) else {"record_json": payload},
                    claim_only=False, source_format=FMT, locator=f"{t}#rowid={r['__rowid__']}",
                    collection=coll, replica_or_table=replica,
                    raw_extra=base_extra | {"updated_at": r.get("updated_at")},
                ))
                res.bump("sql_rows")
            for (system, coll), ids in ids_by_pair.items():
                inferred = not ids  # this table holds no rows of the collection; seen only in a sibling table
                res.scopes.append(SnapshotScope(
                    evidence_id=ev.file_id, system_id=system, data_category=category_for(coll, None),
                    collection=coll, replica_or_table=replica, captured_at=file_ts,
                    resource_ids=frozenset(ids),
                    scope_source="sql_sibling_inference" if inferred else "sql_table",
                    completeness=INFERRED if inferred else COMPLETE,
                    limitations=(f"table {t} holds no {system}/{coll} rows; coverage is inferred from "
                                 f"sibling tables in the same dump",) if inferred else ()))
            continue

        if t in INVENTORY_TABLE_SYSTEM and "snapshot_scope" in data:
            system = INVENTORY_TABLE_SYSTEM[t]
            observed = scope_times.get(system, file_ts)
            for r in rows:
                payload = {k: v for k, v in r.items() if k != "__rowid__"}
                res.records.append(make_record(
                    ev, system_id=system, resource_id=str(r["resource_id"]), observed_at=observed,
                    presence=PRESENT, payload=payload, claim_only=False, source_format=FMT,
                    locator=f"{t}#rowid={r['__rowid__']}", collection=t, replica_or_table=replica,
                    raw_extra=base_extra,
                ))
                res.bump("sql_rows")
            if system in scope_times:
                res.scopes.append(SnapshotScope(
                    evidence_id=ev.file_id, system_id=system, data_category=category_for(t, None),
                    collection=t, replica_or_table=replica, captured_at=scope_times[system],
                    resource_ids=frozenset(norm_resource_id(str(r["resource_id"])) for r in rows),
                    scope_source="inventory_snapshot_scope"))
            continue

        if "resource_id" in cols[t]:
            system = _typed_table_system(t, rows)
            if system is None:
                res.issues.append(ParseIssue(ev.file_id, "warning", f"table {t}: cannot determine system; rows skipped"))
                continue
            category = _typed_category(t)
            if category is None:
                res.issues.append(ParseIssue(ev.file_id, "warning", f"table {t}: unknown data category"))
            for r in rows:
                payload = {k: v for k, v in r.items() if k != "__rowid__"}
                res.records.append(make_record(
                    ev, system_id=system, resource_id=str(r["resource_id"]), observed_at=file_ts,
                    presence=PRESENT, payload=payload, claim_only=False, source_format=FMT,
                    locator=f"{t}#rowid={r['__rowid__']}", collection=t, replica_or_table=replica,
                    data_category=category, raw_extra=base_extra,
                ))
                res.bump("sql_rows")
            res.scopes.append(SnapshotScope(
                evidence_id=ev.file_id, system_id=system, data_category=category, collection=t,
                replica_or_table=replica, captured_at=file_ts,
                resource_ids=frozenset(norm_resource_id(str(r["resource_id"])) for r in rows),
                scope_source="sql_table"))
            continue

        res.issues.append(ParseIssue(ev.file_id, "unsupported", f"table {t}: no resource_id column"))
    return res
