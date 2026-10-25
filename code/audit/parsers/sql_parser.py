"""SQL evidence: SQLite snapshots, executed in memory.

Three table styles occur:
* typed inventory tables (customer_profiles, customer_search_documents, ...)
* generic replica tables (customer_data_primary / *_replica) whose rows carry
  ``origin_system``, ``collection_name`` and a JSON ``record_json``
* simple profile/search tables (customer_profiles_primary, ...)

A row's presence proves PRESENT. Absence is *never* inferred from a missing
row in these sparse snapshots (explicit lookups elsewhere prove absence).
"""
import json
import re
import sqlite3

from ..config import COLLECTION_CATEGORY
from ..loaders import parse_ts

TABLE_SYSTEM_CATEGORY = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_profiles": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "connector_subscriptions": ("integration_service", "DATA_FLOW"),
    "backup_restore_entries": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_records": ("security_service", "SECURITY_AUDIT_LOG"),
}

_HEADER_CAPTURED = re.compile(r"--\s*Captured at:\s*(\S+)")


def parse_sql_text(text, source_id, store, manifest_ts):
    captured = manifest_ts
    m = _HEADER_CAPTURED.search(text)
    if m:
        captured = parse_ts(m.group(1)) or manifest_ts
    before = len(store.facts)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    try:
        con.executescript(text)
    except sqlite3.Error:
        # Tolerate a partial script: run statements one by one.
        for stmt in text.split(";\n"):
            try:
                con.execute(stmt)
            except sqlite3.Error:
                continue
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        if table == "snapshot_scope":
            continue
        try:
            rows = [dict(r) for r in con.execute(f'SELECT * FROM "{table}"')]
        except sqlite3.Error:
            continue
        for row in rows:
            _parse_row(store, source_id, captured, table, row)
    con.close()
    return len(store.facts) - before


def _parse_row(store, source_id, captured, table, row):
    # Generic replica style: record_json holds the real record.
    if "record_json" in row and row.get("record_json"):
        try:
            record = json.loads(row["record_json"])
        except (ValueError, TypeError):
            return
        if not isinstance(record, dict):
            return
        record.setdefault("resource_id", row.get("resource_id"))
        system = row.get("origin_system", "")
        collection = row.get("collection_name", "")
        category = COLLECTION_CATEGORY.get(collection, "")
        observed = parse_ts(row.get("updated_at")) or captured
        store.add(source_id, "evidence", observed, system,
                  record.get("resource_id"), category, "PRESENT",
                  record=record, enabled=record.get("enabled"),
                  restore_allowed=record.get("restore_allowed"),
                  retention_until=parse_ts(record.get("retention_until")
                                           or record.get("retained_until")))
        return
    resource_id = row.get("resource_id")
    if not resource_id:
        return
    if table in TABLE_SYSTEM_CATEGORY:
        system, category = TABLE_SYSTEM_CATEGORY[table]
    elif "search" in table:
        system, category = "search_service", "SEARCH_INDEX_ENTRY"
        # search_documents_primary uses source_resource_id/display_name
    elif "profile" in table:
        system, category = "account_service", "USER_PROFILE"
    else:
        return
    observed = parse_ts(row.get("updated_at") or row.get("indexed_at")) or captured
    store.add(source_id, "evidence", observed, system, resource_id, category,
              "PRESENT", record=row, enabled=row.get("enabled"),
              restore_allowed=(None if row.get("restore_allowed") is None
                               else str(row.get("restore_allowed")).lower()
                               in ("1", "true")),
              retention_until=parse_ts(row.get("retention_until")))
