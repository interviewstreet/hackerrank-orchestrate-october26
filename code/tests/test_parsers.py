"""Per-format parser tests against the real corpus."""

import collections
import os
from datetime import datetime, timezone

import pytest

from evidence.manifest import load_manifest
from evidence.models import ABSENT, PRESENT
from evidence.parsers import parse_file
from evidence.parsers.images import fix_ocr_text
from evidence.parsers.logs import parse_line


@pytest.fixture(scope="module")
def parsed(dataset_dir):
    rep = load_manifest(dataset_dir)
    return {ev.file_id: (ev, parse_file(ev, ocr_mode="cache_only")) for ev in rep.files}


def test_every_file_parses_without_errors(parsed):
    problems = [(fid, i.severity, i.message) for fid, (_, r) in parsed.items() for i in r.issues]
    assert problems == []
    assert len(parsed) == 94


@pytest.mark.parametrize("ext", ["json", "sql", "log", "pdf", "png", "txt"])
def test_each_extension_yields_observations(parsed, ext):
    files = [(ev, r) for ev, r in parsed.values() if ev.extension == ext]
    assert files
    assert sum(len(r.records) for _, r in files) > 0
    for ev, r in files:
        for rec in r.records:
            assert rec.evidence_id == ev.file_id
            assert rec.source_format == ext
            assert rec.captured_at == ev.captured_at
            assert rec.system_id and rec.resource_id and rec.observed_at.tzinfo is not None


def test_only_empty_inventory_has_no_records(parsed):
    empty = [fid for fid, (_, r) in parsed.items() if not r.records]
    assert empty == ["evidence_90"]
    # ...but it still proves the account_service table was empty
    scopes = parsed["evidence_90"][1].scopes
    assert len(scopes) == 1 and scopes[0].system_id == "account_service" and not scopes[0].resource_ids


def test_all_log_families_parse_every_line(parsed):
    families = collections.Counter()
    for ev, r in parsed.values():
        if ev.extension != "log":
            continue
        assert r.stats.get("unparsed_lines", 0) == 0, ev.file_path
        for rec in r.records:
            families[rec.raw_state.get("log_family")] += 1
    assert set(families) == {
        "structured_service_events", "service_events", "syslog_archive", "application_trace",
        "operations_stream", "cloud_runtime_export", "resource_lookup_trace", "lookup_ledger",
        "support_replica",
    }


def test_log_syntaxes_detected(parsed):
    syntaxes = collections.Counter()
    for ev, r in parsed.values():
        for k, v in r.stats.items():
            if k.startswith("syntax_"):
                syntaxes[k[7:]] += v
    assert set(syntaxes) == {"json", "cloud_runtime", "syslog", "app_trace", "ops_stream", "kv"}


@pytest.mark.parametrize("line,service,event,field,value", [
    ('2026-09-10T08:56:20Z {"severity":"DEBUG","service":"account_service","trace_id":"tr-1","resource_id":"account_6633","event":"profile_lookup_completed","rows":"1"}',
     "account_service", "profile_lookup_completed", "rows", "1"),
    ('2026-06-08T06:52:09Z requestId=tr-1 level=INFO function=search_service message="resource_id=\\"search_021\\" event=\\"index_query_completed\\" correlation_key=\\"a@b.io\\""',
     "search_service", "index_query_completed", "correlation_key", "a@b.io"),
    ('2026-08-22T10:51:17Z <15>1 node-1 account_service tr-4973247 - - level=DEBUG resource_id="account_1785" event="profile_lookup_completed" rows="1"',
     "account_service", "profile_lookup_completed", "resource_id", "account_1785"),
    ('2026-07-28T05:51:21Z [INFO] [account_service] [tr-6074163] profile_lookup_completed: resource_id="account_7947" rows="0" http_status="404"',
     "account_service", "profile_lookup_completed", "http_status", "404"),
    ('2026-07-03T07:51:32Z | DEBUG | security_service | tr-5156005 | audit_record_read_completed | resource_id="audit_record_4413" rows="1"',
     "security_service", "audit_record_read_completed", "resource_id", "audit_record_4413"),
    ('2026-09-26T07:49:50Z level=INFO service=account_service trace_id=rb-1 event=profile_lookup_completed resource_id=account_2064 rows=0 http_status=404',
     "account_service", "profile_lookup_completed", "rows", "0"),
    ('2026-09-06T07:00:00Z INFO service=search_index_service event=record_lookup seq=2 system="account_service" resource_id="account_2387" result="NOT_FOUND"',
     "search_index_service", "record_lookup", "system", "account_service"),
])
def test_parse_line_each_syntax(line, service, event, field, value):
    ll = parse_line(1, line)
    assert ll is not None
    assert ll.service == service and ll.event == event and ll.fields[field] == value


def test_trace_correlation_links_started_key_to_completed_line(parsed):
    # evidence_01: index_query_started match_key=g.silva76.jr@gmail.com -> completed resource_id=search_1874
    recs = [r for r in parsed["evidence_01"][1].records if r.resource_id == "search_1874"]
    assert recs and recs[0].presence == PRESENT
    assert ("email", "g.silva76.jr@gmail.com") in recs[0].linked_terms
    assert recs[0].pii_fields == {}  # the lookup key is not stored PII


def test_sql_replica_identity_preserved(parsed):
    recs = parsed["evidence_54"][1].records
    keys = {(r.resource_id, r.replica_or_table) for r in recs}
    assert ("account_005", "customer_profiles_failover_replica") in keys
    assert ("account_005", None) not in keys  # absent from the primary table
    assert ("account_8741", None) in keys and ("account_8741", "customer_profiles_failover_replica") in keys


def test_sql_json_blob_tables(parsed):
    recs = parsed["evidence_05"][1].records
    replicas = {r.replica_or_table for r in recs}
    assert replicas == {None, "customer_data_read_replica"}
    a = next(r for r in recs if r.resource_id == "analytics_4440")
    assert a.pii_fields["email"] == "seoyeon-han@gmail.com" and a.subject_reference == "user_51"


def test_inventory_booleans_and_scope(parsed):
    recs = {r.resource_id: r for r in parsed["evidence_93"][1].records}
    assert recs["backup_4978"].raw_state["restore_allowed"] is True
    assert recs["data_flow_6846"].raw_state["enabled"] is False
    systems = {s.system_id for s in parsed["evidence_93"][1].scopes}
    assert len(systems) == 8


def test_json_readback_presence(parsed):
    recs = {r.resource_id: r for r in parsed["evidence_92"][1].records}
    assert recs["account_3136"].presence == ABSENT
    assert recs["account_5334"].presence == PRESENT
    assert recs["analytics_1895"].presence == PRESENT and recs["analytics_1895"].pii_fields == {}


def test_tombstones_with_null_pii_are_kept(parsed):
    recs = {r.resource_id: r for r in parsed["evidence_51"][1].records}
    t = recs["tombstone_440"]
    assert t.presence == PRESENT and t.data_category == "ACCOUNT_TOMBSTONE"
    assert t.pii_fields == {} and t.subject_reference == "user_541"
    assert t.raw_state["email"] is None and t.raw_state["account_status"] == "DELETED"
    exposed = recs["tombstone_9178"]
    assert set(exposed.pii_fields) == {"name", "email", "phone", "email_hash"}


def test_claim_only_classification(parsed):
    for fid in ("evidence_03", "evidence_08", "evidence_13", "evidence_36", "evidence_41", "evidence_50"):
        assert all(r.claim_only for r in parsed[fid][1].records), fid
    for fid in ("evidence_05", "evidence_54", "evidence_92", "evidence_94", "evidence_58", "evidence_04"):
        assert not any(r.claim_only for r in parsed[fid][1].records), fid


def test_txt_handover(parsed):
    recs = {r.resource_id: r for r in parsed["evidence_03"][1].records}
    assert len(recs) == 41
    assert recs["search_052"].presence == PRESENT and recs["search_052"].data_category == "SEARCH_INDEX_ENTRY"
    assert recs["account_4248"].presence == ABSENT
    assert recs["analytics_2034"].raw_state["result"] == "IDENTIFIABLE"
    assert ("email", "choi.jihoon94@gmail.com") in recs["account_1810"].linked_terms  # mixed case source


def test_pdf_documents(parsed):
    att = parsed["evidence_58"][1].records
    assert [(r.resource_id, r.data_category) for r in att] == [("support_001", "SUPPORT_ATTACHMENT")]
    assert att[0].pii_fields["email"] == "priya.raman@gmail.com"
    reg = parsed["evidence_27"][1].records
    assert len(reg) == 6 and all(r.data_category == "LEGAL_HOLD_RECORD" for r in reg)
    # multi-subject register rows are not cross-linked
    assert {u for r in reg for k, u in r.linked_terms if k == "user_id"} == {"user_08", "user_12", "user_17", "user_21", "user_24", "user_29"}
    assert all(len([t for t in r.linked_terms if t[0] == "user_id"]) == 1 for r in reg)
    sec = parsed["evidence_55"][1].records
    assert sec[0].resource_id == "audit_record_003" and sec[0].subject_reference == "user_03"


def test_png_ocr_records(parsed):
    rows = {(r.evidence_id, r.resource_id): r for ev, res in parsed.values() if ev.extension == "png" for r in res.records}
    assert rows[("evidence_04", "account_5762")].pii_fields["email"] == "haruka.s1838@zoho.com"
    assert rows[("evidence_04", "account_5762")].subject_reference == "user_11"
    assert ("evidence_37", "audit_record_003") in rows  # OCR read "audit_record_oo3"
    assert ("email", "lucia-torres@gmail.com") in rows[("evidence_14", "data_flow_9846")].linked_terms
    # multi-person screen: each backup row keeps only its own email
    b = rows[("evidence_32", "backup_9287")]
    assert {v for k, v in b.linked_terms if k == "email"} == {"areed1433@gmail.com"}
    assert rows[("evidence_42", "user_17")].data_category == "ACCOUNT_TOMBSTONE"
    m = rows[("evidence_60", "marketing_001")]
    assert m.pii_fields["email"] == "sj.park@naver.com"


def test_ocr_text_fixups():
    assert "audit_record_003" in fix_ocr_text("audit_record_oo3-Rawevent")
    assert "support_on" in fix_ocr_text("support_on")  # not a resource id; untouched


def test_ocr_cache_miss_is_reported(tmp_path):
    from PIL import Image
    from evidence.models import EvidenceFile

    p = tmp_path / "blank.png"
    Image.new("RGB", (40, 20), "white").save(p)
    ev = EvidenceFile("evidence_x", "evidence/images/blank.png", "test", datetime(2026, 1, 1, tzinfo=timezone.utc), p)
    r = parse_file(ev, ocr_mode="cache_only")
    assert r.records == [] and r.issues and r.issues[0].severity == "error"


@pytest.mark.ocr
@pytest.mark.skipif(os.environ.get("RUN_OCR_TESTS") != "1", reason="set RUN_OCR_TESTS=1 to run the live OCR engine")
def test_live_ocr_matches_cache(dataset_dir):
    from evidence.parsers.images import load_ocr, run_ocr

    path = dataset_dir / "evidence/images/deleted_account_reference_20260310.png"
    cached, _ = load_ocr(path, "cache_only")
    live = run_ocr(path)
    assert [i["text"] for i in live] == [i["text"] for i in cached]
