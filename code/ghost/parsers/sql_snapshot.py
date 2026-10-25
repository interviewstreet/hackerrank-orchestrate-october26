"""SQL snapshot exports, executed once into an in-memory SQLite database.

Three shapes occur:
  inventory   flat tables named after the data (customer_profiles, support_records, ...)
              plus snapshot_scope(origin_system, captured_at)
  replica     tables of (resource_id, origin_system, collection_name, record_json, updated_at),
              one primary table and one or more replica tables; drift = rows that differ
  one-off     flat tables with a topology suffix (customer_profiles_primary, ..._failover_replica)
Every table is read with a single SELECT.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

from ..errors import ParseError
from .base import COLLECTION_CATEGORY, ParseResult, state_for, system_for

log = logging.getLogger(__name__)

_TOPOLOGY_SUFFIX = re.compile(r"_(primary|failover_replica|read_replica|reporting_replica|replica(_[a-z_]+)?)$")
_CATEGORY_SYSTEM = {
    "USER_PROFILE": "account_service", "SEARCH_INDEX_ENTRY": "search_service",
    "ANALYTICS_PROFILE": "analytics_platform", "SUPPORT_MESSAGE": "support_platform",
    "SUPPORT_ATTACHMENT": "support_platform", "USER_EXPORT": "export_service",
    "DATA_FLOW": "integration_service", "BACKUP_ARCHIVE": "backup_service",
    "SECURITY_AUDIT_LOG": "security_service", "ACCOUNT_TOMBSTONE": "identity_service",
    "LEGAL_HOLD_RECORD": "legal_service",
}


def parse(path: Path, evidence_id: str, captured_at: str) -> ParseResult:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(path.read_text(encoding="utf-8"))
    except (sqlite3.Error, UnicodeDecodeError) as exc:
        con.close()
        raise ParseError(evidence_id, f"cannot execute SQL: {exc}") from exc

    out = ParseResult()
    try:
        tables = [t for (t,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        declared_scope = "snapshot_scope" in tables
        if declared_scope:
            for system, at in con.execute("SELECT origin_system, captured_at FROM snapshot_scope"):
                out.scope.add((system, at or captured_at))

        for table in tables:
            if table == "snapshot_scope":
                continue
            cur = con.execute(f'SELECT * FROM "{table}"')
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            if "record_json" in cols:
                _replica_rows(out, rows, table, evidence_id, captured_at)
                continue
            category = COLLECTION_CATEGORY.get(_TOPOLOGY_SUFFIX.sub("", table))
            if category is None:
                log.warning("%s: table %s not recognised, %d rows skipped", evidence_id, table, len(rows))
                out.skipped += len(rows)
                continue
            if not declared_scope:
                out.scope.add((_CATEGORY_SYSTEM[category], captured_at))
            for row in rows:
                rid = row.get("resource_id")
                if not rid:
                    out.skipped += 1
                    continue
                result, subjects = state_for(category, row)
                out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=captured_at,
                        system_id=system_for(rid, _CATEGORY_SYSTEM[category]), resource_id=rid,
                        category=category, result=result, subjects=subjects,
                        retention_until=row.get("retention_until") or row.get("retained_until"),
                        raw_ref=table)
    finally:
        con.close()
    return out


def _replica_rows(out: ParseResult, rows: list[dict], table: str, evidence_id: str,
                  captured_at: str) -> None:
    for row in rows:
        rid = row.get("resource_id")
        category = COLLECTION_CATEGORY.get(row.get("collection_name") or "")
        if not rid or category is None:
            out.skipped += 1
            continue
        try:
            record = json.loads(row["record_json"])
        except (TypeError, json.JSONDecodeError):
            log.warning("%s: %s/%s has invalid record_json", evidence_id, table, rid)
            out.skipped += 1
            continue
        system = system_for(rid, row.get("origin_system") or "")
        out.scope.add((row.get("origin_system") or system, captured_at))
        result, subjects = state_for(category, record)
        out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=captured_at,
                system_id=system, resource_id=rid, category=category, result=result,
                subjects=subjects,
                retention_until=record.get("retention_until") or record.get("retained_until"),
                raw_ref=table)
