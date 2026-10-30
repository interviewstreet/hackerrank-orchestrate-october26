"""SQLite-compatible snapshot exports -> RawRecords (+ the systems each snapshot fully covers)."""
from __future__ import annotations

import json
import re
import sqlite3

from ..loaders import parse_ts
from ..models import EvidenceFile
from .records import RawRecord, system_for

TABLE_SYSTEM = {
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
LOCATION_SUFFIX = re.compile(r"_(primary|failover_replica|read_replica|reporting_replica|replica_[a-z_]+)$")


def _split_table(name: str) -> tuple[str, str]:
    m = LOCATION_SUFFIX.search(name)
    if m:
        return name[: m.start()], m.group(1)
    return name, "primary"


def extract(ef: EvidenceFile) -> tuple[list[RawRecord], set[tuple[str, str]]]:
    """Returns records and the coverage set {(system_id, location)} this snapshot asserts is complete."""
    sql = ef.path.read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        records: list[RawRecord] = []
        coverage: set[tuple[str, str]] = set()
        scoped = "snapshot_scope" in tables
        if scoped:
            for (origin,) in conn.execute("SELECT origin_system FROM snapshot_scope ORDER BY origin_system"):
                coverage.add((origin, "*"))
        for table in tables:
            if table == "snapshot_scope":
                continue
            base, location = _split_table(table)
            cur = conn.execute(f'SELECT * FROM "{table}" ORDER BY resource_id')
            cols = [d[0] for d in cur.description]
            table_system = TABLE_SYSTEM.get(base)
            if not scoped and table_system:
                coverage.add((table_system, location))
            for row in cur.fetchall():
                f = dict(zip(cols, row))
                collection = base
                if "record_json" in f:
                    try:
                        inner = json.loads(f.pop("record_json"))
                    except (TypeError, json.JSONDecodeError):
                        inner = {}
                    collection = f.get("collection_name") or base
                    f = {**f, **_flatten(inner)}
                rid = str(f.get("resource_id") or "")
                if not rid:
                    continue
                hint = f.get("origin_system") or table_system
                records.append(RawRecord(
                    evidence_id=ef.file_id,
                    captured_at=ef.captured_at,
                    resource_id=rid,
                    fields=f,
                    observed_at=parse_ts(str(f.get("updated_at") or "")) or ef.captured_at,
                    system_hint=hint or system_for(rid),
                    location=location,
                    collection=collection,
                    source_format="sql",
                ))
        if not scoped:
            # JSON-in-table topologies (customer_data_<location>) are full copies of every origin system they hold
            for r in records:
                if r.collection and r.source_format == "sql" and r.location:
                    coverage.add((system_for(r.resource_id, r.system_hint), r.location))
        return records, coverage
    finally:
        conn.close()


def _flatten(obj: dict, prefix: str = "") -> dict:
    """Flatten nested documents ({"document": {"email": ..}} -> {"email": ..}); lists are kept as JSON text."""
    out: dict = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out.update(_flatten(v, prefix))
        elif isinstance(v, list):
            out[prefix + k] = json.dumps(v, sort_keys=True)
        else:
            out.setdefault(prefix + k, v)
    return out
