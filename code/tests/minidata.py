"""A tiny, fully self-contained dataset used by the tests (no dependency on the real dataset/).

Every expected result in test_mini_dataset.py was derived by hand from deletion_rules.csv and the problem statement,
before the engine was run on it. Names and emails are invented.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

RULES = 'rule_id,data_category,condition,required_action\nrule_01,USER_PROFILE,Always,DELETE\nrule_02,SECONDARY_IDENTIFIER,Always,DELETE\nrule_03,SEARCH_INDEX_ENTRY,Always,DELETE\nrule_04,CACHE_ENTRY,Always,DELETE\nrule_05,SUPPORT_MESSAGE,"Conversation contains shared customer, agent, or order context that must be retained",REDACT\nrule_06,SUPPORT_ATTACHMENT,Attachment belongs only to the deletion subject,DELETE\nrule_07,ANALYTICS_PROFILE,Record is still attributable to a user,ANONYMIZE\nrule_08,PRODUCT_TELEMETRY,Record is still attributable to a user,ANONYMIZE\nrule_09,USER_EXPORT,Always,DELETE\nrule_10,MARKETING_PROFILE,Always,DELETE\nrule_11,EMAIL_DELIVERY_LOG,Log contains a user email address,REDACT\nrule_12,SECURITY_AUDIT_LOG,Record is within the supplied retention period,RETAIN\nrule_13,LEGAL_HOLD_RECORD,A supplied legal hold is active,RETAIN\nrule_14,BACKUP_ARCHIVE,Restore access can be blocked,RETAIN\nrule_15,ACCOUNT_TOMBSTONE,Account is deleted and only a stable internal user_id is needed to preserve references to retained records,REDACT\n'

USERS = [  # user_id, name, email, phone
    ("user_91", "Ada Example", "ada@example.com", "+1 555 0100"),
    ("user_92", "Ben Example", "ben@example.com", "+1 555 0101"),
    ("user_93", "Cara Example", "cara@example.com", "+1 555 0102"),
    ("user_94", "Dana Example", "dana@example.com", "+1 555 0103"),
]

DELETE = "Please permanently delete my account and all personal data."
KEEP = "Please do not delete my account. I only want to update my phone number."

#            case_id, email,              requested_at,           reported_status, reported_at,           audit_at, text
REQUESTS = [
    ("mini_01", "ada@example.com",  "2026-08-30T09:00:00Z", "COMPLETE", "2026-08-31T09:00:00Z", "2026-09-05T12:00:00Z", DELETE),
    ("mini_02", "cara@example.com", "2026-08-30T09:00:00Z", "COMPLETE", "2026-08-31T09:00:00Z", "2026-09-05T12:00:00Z", DELETE),
    ("mini_03", "ada@examp1e.com",  "2026-08-30T09:00:00Z", "COMPLETE", "2026-08-31T09:00:00Z", "2026-09-05T12:00:00Z", DELETE),
    ("mini_04", "ada@example.com",  "2026-08-30T09:00:00Z", "COMPLETE", "2026-08-31T09:00:00Z", "2026-09-05T12:00:00Z", KEEP),
    ("mini_05", "dana@example.com", "2026-08-01T09:00:00Z", "COMPLETE", "2026-08-06T09:00:00Z", "2026-08-25T12:00:00Z", DELETE),
    ("mini_06", "ada@example.com",  "2026-08-30T09:00:00Z", "COMPLETE", "2026-08-31T09:00:00Z", "2026-08-31T10:00:00Z", DELETE),
]

EVIDENCE = [  # file_id, path, origin, captured_at
    ("evidence_01", "evidence/databases/customer_data_inventory_20260901.sql", "inventory", "2026-09-01T10:00:00Z"),
    ("evidence_02", "evidence/databases/customer_data_inventory_20260805.sql", "inventory", "2026-08-05T10:00:00Z"),
    ("evidence_03", "evidence/databases/customer_data_inventory_20260820.sql", "inventory", "2026-08-20T10:00:00Z"),
]

DDL = {
    "customer_profiles": "resource_id TEXT PRIMARY KEY, customer_reference TEXT, full_name TEXT, email TEXT, phone TEXT, email_hash TEXT, account_status TEXT NOT NULL, updated_at TEXT NOT NULL",
    "customer_search_documents": "resource_id TEXT PRIMARY KEY, customer_reference TEXT, display_name TEXT, email TEXT, phone TEXT, email_hash TEXT, index_name TEXT NOT NULL, updated_at TEXT NOT NULL",
    "connector_subscriptions": "resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, connector_name TEXT NOT NULL, enabled INTEGER NOT NULL, last_delivery_status TEXT NOT NULL, updated_at TEXT NOT NULL",
    "backup_restore_entries": "resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, archive_key TEXT NOT NULL, restore_allowed INTEGER NOT NULL, updated_at TEXT NOT NULL",
    "security_audit_records": "resource_id TEXT PRIMARY KEY, subject_reference TEXT NOT NULL, event_code TEXT NOT NULL, retention_until TEXT NOT NULL, updated_at TEXT NOT NULL",
}


def _sql(ts: str, scope: list, inserts: dict) -> str:
    out = ["PRAGMA foreign_keys=ON;", "BEGIN TRANSACTION;", "CREATE TABLE snapshot_scope (origin_system TEXT PRIMARY KEY, captured_at TEXT NOT NULL);"]
    for t in inserts:
        out.append(f"CREATE TABLE {t} ({DDL[t]});")
    for s in scope:
        out.append(f"INSERT INTO snapshot_scope VALUES ('{s}', '{ts}');")
    for t, rows in inserts.items():
        for r in rows:
            out.append(f"INSERT INTO {t} VALUES ({', '.join('NULL' if v is None else repr(v) for v in r)});")
    out += ["COMMIT;", f"-- snapshot_completed_at={ts}", ""]
    return "\n".join(out)


def build_mini_dataset(root: Path) -> Path:
    d = Path(root)
    (d / "evidence" / "databases").mkdir(parents=True, exist_ok=True)

    def write_csv(name, header, rows):
        with open(d / name, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n"); w.writerow(header); w.writerows(rows)

    write_csv("user_identities.csv", ["user_id", "name", "email", "phone", "email_hash", "updated_at"],
              [(u, n, e, p, hashlib.sha256(e.encode()).hexdigest(), "2026-01-01T00:00:00Z") for u, n, e, p in USERS])
    write_csv("deletion_requests.csv", ["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"], REQUESTS)
    write_csv("sample_deletion_requests.csv", ["case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"], REQUESTS)
    (d / "deletion_rules.csv").write_text(RULES, encoding="utf-8")
    write_csv("system_activity.csv", ["activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id", "reported_result", "details"], [])
    write_csv("user_audit_log.csv", ["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"], [])
    write_csv("evidence_files.csv", ["file_id", "file_path", "origin", "captured_at"], EVIDENCE)
    write_csv("sample_output.csv", ["case_id", "deletion_status", "steps_json"], [])

    all_scope = ["account_service", "search_service", "integration_service", "backup_service", "security_service"]
    # evidence_01 (2026-09-01): Ada has a search entry, a restorable backup and a retained audit record; Cara has an active connector
    (d / EVIDENCE[0][1]).write_text(_sql("2026-09-01T10:00:00Z", all_scope, {
        "customer_search_documents": [("search_100", None, None, "ada@example.com", None, None, "customer_directory_v3", "2026-09-01T09:00:00Z")],
        "backup_restore_entries": [("backup_300", None, "ada@example.com", "archive/backup_300.tar.zst", 1, "2026-09-01T09:00:00Z")],
        "security_audit_records": [("audit_record_400", "user_91", "ACCOUNT_DELETION_RECORDED", "2031-12-31T23:59:59Z", "2026-09-01T09:00:00Z")],
        "connector_subscriptions": [("data_flow_200", None, "cara@example.com", "customer_events_connector", 1, "delivered", "2026-09-01T09:00:00Z")],
        "customer_profiles": [("account_999", None, "Someone Else", "other@example.com", None, None, "ACTIVE", "2026-09-01T09:00:00Z")],
    }), encoding="utf-8")
    # evidence_02 (2026-08-05): Dana's profile still exists, plus her retained audit record
    (d / EVIDENCE[1][1]).write_text(_sql("2026-08-05T10:00:00Z", all_scope, {
        "customer_profiles": [("account_500", None, "Dana Example", "dana@example.com", "+1 555 0103", None, "ACTIVE", "2026-08-05T09:00:00Z")],
        "security_audit_records": [("audit_record_410", "user_94", "IDENTITY_CHANGE_RECORDED", "2031-12-31T23:59:59Z", "2026-08-05T09:00:00Z")],
    }), encoding="utf-8")
    # evidence_03 (2026-08-20): later full account snapshot without Dana's profile
    (d / EVIDENCE[2][1]).write_text(_sql("2026-08-20T10:00:00Z", ["account_service"], {
        "customer_profiles": [("account_501", None, "Eve Example", "eve@example.com", None, None, "ACTIVE", "2026-08-20T09:00:00Z")],
    }), encoding="utf-8")
    return d


def step(no, phase, system, resource, op, state, ev):
    return {"step_no": no, "phase": phase, "system_id": system, "resource_id": resource, "operation": op, "state": state, "evidence_id": ev}


# Hand-derived expectations (phase order, then operation order, then system_id, then resource_id).
EXPECTED = {
    "mini_01": ("INCOMPLETE", [
        step(1, "FINDING", "search_service", "search_100", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_01"),
        step(2, "FINDING", "backup_service", "backup_300", "REPORT_RESTORE_RISK", "ACTIVE", "evidence_01"),
        step(3, "REMEDIATION", "backup_service", "backup_300", "BLOCK_RESTORE", "BLOCKED", ""),
        step(4, "REMEDIATION", "search_service", "search_100", "DELETE_RECORD", "ABSENT", ""),
        step(5, "VERIFICATION", "search_service", "search_100", "VERIFY_RECORD_ABSENT", "ABSENT", ""),
        step(6, "VERIFICATION", "security_service", "audit_record_400", "VERIFY_RECORD_PRESENT", "PRESENT", ""),
        step(7, "VERIFICATION", "backup_service", "backup_300", "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""),
    ]),
    "mini_02": ("INCOMPLETE", [
        step(1, "FINDING", "integration_service", "data_flow_200", "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", "evidence_01"),
        step(2, "REMEDIATION", "integration_service", "data_flow_200", "DISABLE_DATA_FLOW", "DISABLED", ""),
        step(3, "VERIFICATION", "integration_service", "data_flow_200", "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""),
    ]),
    "mini_03": ("INCOMPLETE", []),          # lookalike address: no such customer, nothing may be invented
    "mini_04": ("NOT_APPLICABLE", []),
    "mini_05": ("COMPLETE", [
        step(1, "VERIFICATION", "account_service", "account_500", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_03"),
        step(2, "VERIFICATION", "security_service", "audit_record_410", "VERIFY_RECORD_PRESENT", "PRESENT", "evidence_02"),
    ]),
    "mini_06": ("INCOMPLETE", []),          # audited before any evidence existed: nothing can be proven
}
