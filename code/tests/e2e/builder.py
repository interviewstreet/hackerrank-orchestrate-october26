"""Writes a miniature participant dataset (same file contracts as dataset/) for end-to-end scenarios.

Scenarios are written black-box from the public contract: the builder only knows the CSV columns and the
evidence formats participants see. Expected outputs are written by hand in scenarios.py.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

RULES = [
    ("rule_01", "USER_PROFILE", "Always", "DELETE"),
    ("rule_02", "SECONDARY_IDENTIFIER", "Always", "DELETE"),
    ("rule_03", "SEARCH_INDEX_ENTRY", "Always", "DELETE"),
    ("rule_04", "CACHE_ENTRY", "Always", "DELETE"),
    ("rule_05", "SUPPORT_MESSAGE", "Conversation contains shared customer, agent, or order context that must be retained", "REDACT"),
    ("rule_06", "SUPPORT_ATTACHMENT", "Attachment belongs only to the deletion subject", "DELETE"),
    ("rule_07", "ANALYTICS_PROFILE", "Record is still attributable to a user", "ANONYMIZE"),
    ("rule_08", "PRODUCT_TELEMETRY", "Record is still attributable to a user", "ANONYMIZE"),
    ("rule_09", "USER_EXPORT", "Always", "DELETE"),
    ("rule_10", "MARKETING_PROFILE", "Always", "DELETE"),
    ("rule_11", "EMAIL_DELIVERY_LOG", "Log contains a user email address", "REDACT"),
    ("rule_12", "SECURITY_AUDIT_LOG", "Record is within the supplied retention period", "RETAIN"),
    ("rule_13", "LEGAL_HOLD_RECORD", "A supplied legal hold is active", "RETAIN"),
    ("rule_14", "BACKUP_ARCHIVE", "Restore access can be blocked", "RETAIN"),
    ("rule_15", "ACCOUNT_TOMBSTONE", "Account is deleted and only a stable internal user_id is needed to preserve references to retained records", "REDACT"),
]
DELETE_TEXT = "Please permanently delete the account associated with this email address."


def sha(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


@dataclass
class MiniDataset:
    users: list = field(default_factory=list)
    history: list = field(default_factory=list)
    requests: list = field(default_factory=list)
    activity: list = field(default_factory=list)
    files: list = field(default_factory=list)   # (file_id, relpath, origin, captured_at, content)

    # ---------- people and requests ----------
    def user(self, uid: str, name: str, email: str, phone: str, updated_at: str = "2026-01-01T00:00:00Z"):
        self.users.append((uid, name, email, phone, sha(email), updated_at))
        return self

    def change(self, uid: str, field_name: str, old: str, new: str, at: str):
        self.history.append((f"audit_{len(self.history) + 1:02d}", uid, at, field_name, old, new))
        return self

    def request(self, case_id: str, email: str, requested: str, reported: str, audit: str,
                text: str = DELETE_TEXT, status: str = "COMPLETE"):
        self.requests.append((case_id, email, requested, status, reported, audit, text))
        return self

    def act(self, time: str, event_type: str, source: str, target: str, rid: str, result: str, details: str):
        self.activity.append((f"activity_{len(self.activity) + 1:02d}", time, event_type, source, target, rid, result, details))
        return self

    def evidence(self, relpath: str, captured: str, content: str, origin: str = "test_capture") -> str:
        fid = f"evidence_{len(self.files) + 1:02d}"
        self.files.append((fid, relpath, origin, captured, content))
        return fid

    # ---------- evidence renderers (participant-visible formats) ----------
    def readback_log(self, captured: str, lines: list[tuple]) -> str:
        """lines: (ts, service, event_prefix, resource_id, lookup_key, completed_kv) -> two trace-joined lines."""
        out = [f"{captured} level=INFO service=readback_collector event=export_started target_count={len(lines)} mode=point_in_time"]
        for i, (ts, service, prefix, rid, key, kv) in enumerate(lines, start=1):
            tr = f"rb-{i:06d}"
            out.append(f"{ts} level=DEBUG service={service} trace_id={tr} event={prefix}_started resource_id={rid} lookup_key={key}")
            out.append(f"{ts} level=INFO service={service} trace_id={tr} event={prefix}_completed resource_id={rid} {kv}")
        return self.evidence(f"evidence/logs/resource_lookup_trace_{captured[:10].replace('-', '')}.log", captured, "\n".join(out) + "\n")

    def split_trace_log(self, captured: str, ts: str, service: str, key: str, rid: str, result_kv: str) -> str:
        """JSON-per-line log where the lookup key and the resource sit on different lines of one trace."""
        a = {"severity": "DEBUG", "service": service, "trace_id": "tr-1000001", "event": "index_query_started", "match_key": key}
        b = {"severity": "INFO", "service": service, "trace_id": "tr-1000001", "event": "cache_lookup", "result": "miss"}
        c = {"severity": "INFO", "service": service, "trace_id": "tr-1000001", "resource_id": rid, "event": "index_query_completed"}
        c.update(dict(kv.split("=", 1) for kv in result_kv.split()))
        body = "\n".join(f"{ts} {json.dumps(x)}" for x in (a, b, c)) + "\n"
        return self.evidence(f"evidence/logs/structured_service_events_{captured[:10].replace('-', '')}.log", captured, body,
                             "central_observability_export")

    def inventory_sql(self, captured: str, scope: list[str], inserts: list[str], name: str = "inventory") -> str:
        ddl = """CREATE TABLE snapshot_scope (origin_system TEXT PRIMARY KEY, captured_at TEXT NOT NULL);
CREATE TABLE customer_profiles (resource_id TEXT PRIMARY KEY, customer_reference TEXT, full_name TEXT, email TEXT, phone TEXT, email_hash TEXT, account_status TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE customer_search_documents (resource_id TEXT PRIMARY KEY, customer_reference TEXT, display_name TEXT, email TEXT, phone TEXT, email_hash TEXT, index_name TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE customer_analytics_profiles (resource_id TEXT PRIMARY KEY, customer_reference TEXT, email TEXT, phone TEXT, email_hash TEXT, audience_cohort TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE support_records (resource_id TEXT PRIMARY KEY, customer_reference TEXT, requester_name TEXT, requester_email TEXT, requester_phone TEXT, message_excerpt TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE customer_exports (resource_id TEXT PRIMARY KEY, customer_reference TEXT, owner_email TEXT, owner_phone TEXT, object_key TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE connector_subscriptions (resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, connector_name TEXT NOT NULL, enabled INTEGER NOT NULL, last_delivery_status TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE backup_restore_entries (resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, archive_key TEXT NOT NULL, restore_allowed INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE security_audit_records (resource_id TEXT PRIMARY KEY, subject_reference TEXT NOT NULL, event_code TEXT NOT NULL, retention_until TEXT NOT NULL, updated_at TEXT NOT NULL);
"""
        body = "BEGIN TRANSACTION;\n" + ddl
        body += "".join(f"INSERT INTO snapshot_scope VALUES ('{s}', '{captured}');\n" for s in scope)
        body += "".join(i.rstrip(";") + ";\n" for i in inserts) + "COMMIT;\n"
        return self.evidence(f"evidence/databases/customer_data_{name}_{captured[:10].replace('-', '')}.sql", captured, body,
                             "customer_data_inventory_capture")

    def failover_sql(self, captured: str, primary: list[tuple], failover: list[tuple]) -> str:
        cols = "resource_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, full_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, account_status TEXT NOT NULL, updated_at TEXT NOT NULL"
        body = "BEGIN TRANSACTION;\n"
        for table, rows in (("customer_profiles_primary", primary), ("customer_profiles_failover_replica", failover)):
            body += f"CREATE TABLE {table} ({cols});\n"
            for r in rows:
                body += f"INSERT INTO \"{table}\" VALUES(" + ",".join(f"'{v}'" for v in r) + ");\n"
        body += "COMMIT;\n"
        return self.evidence(f"evidence/databases/customer_accounts_failover_replica_{captured[:10].replace('-', '')}.sql",
                             captured, body, "customer_account_failover_replica_capture")

    def json_table_sql(self, captured: str, rows: list[tuple[str, str, str, dict]]) -> str:
        """JSON-in-table snapshot (customer_data_primary): (resource_id, origin_system, collection, document)."""
        body = ("BEGIN TRANSACTION;\nCREATE TABLE customer_data_primary (resource_id TEXT PRIMARY KEY, origin_system TEXT NOT NULL, "
                "collection_name TEXT NOT NULL, record_json TEXT NOT NULL, updated_at TEXT NOT NULL);\n")
        for rid, system, collection, doc in rows:
            body += (f"INSERT INTO \"customer_data_primary\" VALUES('{rid}','{system}','{collection}',"
                     f"'{json.dumps(doc, ensure_ascii=False)}','{captured}');\n")
        body += "COMMIT;\n"
        return self.evidence(f"evidence/databases/customer_data_json_{captured[:10].replace('-', '')}.sql", captured, body,
                             "customer_data_inventory_capture")

    def bundle_json(self, captured: str, snapshots: list[tuple[str, str, list[dict]]]) -> str:
        data = {"exported_at": captured, "source": "records_assurance_service",
                "snapshots": [{"captured_at": captured, "data_store": ds, "collection": col, "records": recs}
                              for ds, col, recs in snapshots]}
        return self.evidence(f"evidence/records/customer_data_snapshot_bundle_{captured[:10].replace('-', '')}.json",
                             captured, json.dumps(data, indent=2), "records_assurance_snapshot_bundle")

    def service_export_json(self, captured: str, exports: dict) -> str:
        data = {"exported_at": captured, "region": "global", "service_exports": exports, "source": "records_assurance_gateway"}
        return self.evidence(f"evidence/records/service_resource_export_{captured[:10].replace('-', '')}.json",
                             captured, json.dumps(data, indent=2), "service_resource_export")

    def handover_txt(self, captured: str, rows: list[tuple]) -> str:
        lines = ["CUSTOMER PLATFORM - SHIFT HANDOVER", f"Snapshot: {captured}", "", "Checks:", ""]
        lines += [f"- {captured} | {s} | {r} | {cat} | {res} | {ref}" for s, r, cat, res, ref in rows]
        return self.evidence(f"evidence/records/customer_account_handover_{captured[:10].replace('-', '')}.txt",
                             captured, "\n".join(lines) + "\n", "customer_account_service")

    # ---------- write ----------
    def write(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True)

        def w(name, header, rows):
            with open(root / name, "w", newline="", encoding="utf-8") as fh:
                wr = csv.writer(fh, lineterminator="\n")
                wr.writerow(header)
                wr.writerows(rows)

        w("user_identities.csv", ["user_id", "name", "email", "phone", "email_hash", "updated_at"], self.users)
        w("user_audit_log.csv", ["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"], self.history)
        w("deletion_requests.csv", ["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"], self.requests)
        w("system_activity.csv", ["activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id", "reported_result", "details"], self.activity)
        w("deletion_rules.csv", ["rule_id", "data_category", "condition", "required_action"], RULES)
        w("evidence_files.csv", ["file_id", "file_path", "origin", "captured_at"], [(f, p, o, c) for f, p, o, c, _ in self.files])
        for _, rel, _, _, content in self.files:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root
