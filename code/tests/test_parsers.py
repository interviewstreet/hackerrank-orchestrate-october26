"""Parser unit tests on tiny inline fixtures (no dependency on dataset/)."""
import json

from engine.parsers.json_parser import parse_json
from engine.parsers.log_parser import parse_line, parse_log
from engine.parsers.record_parser import parse_txt
from engine.parsers.sql_parser import parse_sql
from minidata import build_mini_dataset


def test_sql_snapshot_rows_and_coverage(tmp_path):
    d = build_mini_dataset(tmp_path)
    obs, cov = parse_sql("evidence_01", "2026-09-01T10:00:00Z", str(d / "evidence/databases/customer_data_inventory_20260901.sql"))
    by = {o.resource_id: o for o in obs}
    assert by["search_100"].emails == ["ada@example.com"] and by["search_100"].state == "PRESENT"
    assert by["backup_300"].state == "ACTIVE"                      # restore_allowed=1 -> restore risk
    assert by["data_flow_200"].state == "ACTIVE"                   # enabled=1
    assert by["audit_record_400"].user_refs == ["user_91"]
    assert {c.system_id for c in cov} >= {"account_service", "search_service"}
    assert all(c.replica == "primary" for c in cov)


def test_sql_disabled_flow_and_blocked_restore(tmp_path):
    sql = tmp_path / "s.sql"
    sql.write_text(
        "CREATE TABLE snapshot_scope (origin_system TEXT PRIMARY KEY, captured_at TEXT NOT NULL);\n"
        "INSERT INTO snapshot_scope VALUES ('integration_service','2026-01-01T00:00:00Z');\n"
        "CREATE TABLE connector_subscriptions (resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, connector_name TEXT NOT NULL, enabled INTEGER NOT NULL, last_delivery_status TEXT NOT NULL, updated_at TEXT NOT NULL);\n"
        "INSERT INTO connector_subscriptions VALUES ('data_flow_1', NULL, 'x@example.com', 'c', 0, 'ok', '2026-01-01T00:00:00Z');\n"
        "CREATE TABLE backup_restore_entries (resource_id TEXT PRIMARY KEY, customer_reference TEXT, customer_email TEXT, archive_key TEXT NOT NULL, restore_allowed INTEGER NOT NULL, updated_at TEXT NOT NULL);\n"
        "INSERT INTO backup_restore_entries VALUES ('backup_1', NULL, 'x@example.com', 'k', 0, '2026-01-01T00:00:00Z');\n", encoding="utf-8")
    obs, _ = parse_sql("evidence_09", "2026-01-01T00:00:00Z", str(sql))
    states = {o.resource_id: o.state for o in obs}
    assert states == {"data_flow_1": "DISABLED", "backup_1": "BLOCKED"}


def test_json_lookup_404_is_absent_and_200_is_present(tmp_path):
    f = tmp_path / "export.json"
    f.write_text(json.dumps({"exported_at": "2026-09-15T11:44:55Z", "service_exports": {"account_service": {"profile_lookups": [
        {"observed_at": "2026-09-15T09:00:00Z", "profile": None, "resource_id": "account_1", "status_code": 404},
        {"observed_at": "2026-09-15T09:05:00Z", "profile": {"email": "a@example.com"}, "resource_id": "account_2", "status_code": 200}]}}}),
        encoding="utf-8")
    obs, cov = parse_json("evidence_09", "2026-09-15T11:44:55Z", str(f))
    st = {o.resource_id: o.state for o in obs}
    assert st["account_1"] == "ABSENT" and st["account_2"] == "PRESENT"
    assert all(c.source_format != "sql" for c in cov)               # a lookup export is not a full snapshot


def test_log_layouts_parse_to_the_same_fields():
    kv = parse_line('2026-09-26T08:57:37Z level=INFO service=account_service trace_id=t1 event=profile_lookup_completed resource_id=account_7 http_status=404')
    br = parse_line('2026-09-26T08:57:37Z [INFO] [account_service] [t1] profile_lookup_completed: resource_id="account_7" http_status="404"')
    for rec in (kv, br):
        assert rec.get("resource_id") == "account_7"
        assert str(rec.get("http_status")) == "404"


def test_log_lookup_404_becomes_absent(tmp_path):
    f = tmp_path / "a.log"
    f.write_text("2026-09-26T08:57:37Z level=DEBUG service=account_service trace_id=t1 event=profile_lookup_started resource_id=account_7 lookup_key=a@example.com\n"
                 "2026-09-26T08:57:37Z level=INFO service=account_service trace_id=t1 event=profile_lookup_completed resource_id=account_7 rows=0 http_status=404\n",
                 encoding="utf-8")
    obs, _ = parse_log("evidence_09", "2026-09-26T10:00:00Z", str(f))
    o = [x for x in obs if x.resource_id == "account_7"][-1]
    assert o.state == "ABSENT" and o.observed_at == "2026-09-26T08:57:37Z"
    assert "a@example.com" not in o.emails                           # lookup keys are links, not stored data


def test_txt_handover_rows(tmp_path):
    f = tmp_path / "h.txt"
    f.write_text("- 2026-09-01T09:00:00Z | search_service | search_5 | SEARCH_INDEX_ENTRY | FOUND | user_12\n", encoding="utf-8")
    obs, _ = parse_txt("evidence_09", "2026-09-01T10:00:00Z", str(f))
    assert len(obs) == 1 and obs[0].state == "PRESENT" and obs[0].user_refs == ["user_12"]
