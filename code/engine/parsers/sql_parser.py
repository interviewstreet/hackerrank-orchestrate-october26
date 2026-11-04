"""SQLite-compatible snapshot parser. Executes each export in memory and reads every table."""
from __future__ import annotations

import json
import re
import sqlite3
from typing import List, Tuple

from ..contracts import Coverage, Observation
from ..util import category_for_resource
from .common import COLLECTION_CATEGORY, make_obs

# typed (non record_json) tables -> (system_id, data_category)
TYPED_TABLES = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_profiles_primary": ("account_service", "USER_PROFILE"),
    "customer_profiles_failover_replica": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "search_documents_primary": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_profiles": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "connector_subscriptions": ("integration_service", "DATA_FLOW"),
    "backup_restore_entries": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_records": ("security_service", "SECURITY_AUDIT_LOG"),
}


def _rows(con: sqlite3.Connection, table: str):
    cur = con.execute(f'SELECT * FROM "{table}"')
    cols = [c[0] for c in cur.description]
    for row in cur.fetchall():
        yield dict(zip(cols, row))


def parse_sql(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    text = open(path, encoding="utf-8").read()
    topo = re.search(r"Database topology:\s*(\S+)", text)
    topology = topo.group(1) if topo else "inventory"
    header_ts = re.search(r"Captured at:\s*(\S+)", text)
    snap_ts = header_ts.group(1) if header_ts else captured_at

    con = sqlite3.connect(":memory:")
    con.executescript(text)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    obs: List[Observation] = []
    cov: List[Coverage] = []
    covered = set()

    for table in tables:
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
        if table == "snapshot_scope":
            for r in _rows(con, table):
                key = (r["origin_system"], r["captured_at"])
                if key not in covered:
                    covered.add(key)
                    cov.append(Coverage(evidence_id, r["captured_at"], r["origin_system"], "", "sql", table))
            continue
        if "record_json" in cols:
            for r in _rows(con, table):
                rec = json.loads(r["record_json"])
                rec.setdefault("resource_id", r["resource_id"])
                coll = r["collection_name"]
                system, cat = COLLECTION_CATEGORY.get(coll, (r["origin_system"], ""))
                system = r["origin_system"] or system
                o = make_obs(evidence_id, snap_ts, rec, system_id=system, category=cat, observed_at=r["updated_at"],
                             source_format="sql", locator=f"{table}/{r['resource_id']}",
                             extra_attrs={"table": table, "topology": topology, "collection": coll})
                if o:
                    obs.append(o)
                key = (system, snap_ts)
                if key not in covered:
                    covered.add(key)
                    cov.append(Coverage(evidence_id, snap_ts, system, coll, "sql", table))
            continue
        if table in TYPED_TABLES:
            system, cat = TYPED_TABLES[table]
            for r in _rows(con, table):
                rec = dict(r)
                if table == "search_documents_primary":
                    # search entries carry the originating account in source_resource_id
                    rec["source_account"] = rec.get("source_resource_id")
                o = make_obs(evidence_id, snap_ts, rec, system_id=system, category=cat,
                             observed_at=r.get("updated_at") or r.get("indexed_at") or snap_ts,
                             source_format="sql", locator=f"{table}/{r['resource_id']}",
                             extra_attrs={"table": table, "topology": topology})
                if o:
                    obs.append(o)
            key = (system, snap_ts)
            if key not in covered:
                covered.add(key)
                cov.append(Coverage(evidence_id, snap_ts, system, "", "sql", table))
    con.close()
    return obs, cov
