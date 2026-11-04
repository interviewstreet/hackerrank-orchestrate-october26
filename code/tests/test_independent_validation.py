"""Independent validation of the Evidence Discovery module.

Every test here builds its own isolated dataset in ``tmp_path`` (manifest +
evidence files in the real formats) and drives it through the *existing*
parsers and scanner, or checks the real corpus read-only. No other team
member's module is used; identity resolution is replaced by hand-written
SubjectIdentifiers. Test names are prefixed V<n>_ to map to the review list.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import typing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from evidence import (
    ABSENT,
    PRESENT,
    UNKNOWN,
    AbsenceProof,
    EvidenceFile,
    EvidenceScanner,
    ObservedRecord,
    ParseIssue,
    SnapshotScope,
    SubjectIdentifiers,
)

UTC = timezone.utc


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --------------------------------------------------------------------------
# Isolated dataset builder (writes real-format files; parsing is production code)
# --------------------------------------------------------------------------
class MiniDataset:
    def __init__(self, root: Path):
        self.root = root / "dataset"
        (self.root / "evidence").mkdir(parents=True)
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, rel: str, content: str, captured_at: str, origin: str = "test_origin") -> str:
        fid = f"evidence_{len(self.rows) + 1:02d}"
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self.rows.append((fid, rel, origin, captured_at))
        return fid

    def bundle(self, name: str, captured_at: str, snapshots: list[dict]) -> str:
        doc = {"exported_at": captured_at, "source": "test", "snapshots": snapshots}
        return self.add(f"evidence/records/{name}.json", json.dumps(doc), captured_at)

    def scanner(self) -> EvidenceScanner:
        with (self.root / "evidence_files.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["file_id", "file_path", "origin", "captured_at"])
            w.writerows(self.rows)
        s = EvidenceScanner(self.root, ocr_mode="cache_only")
        s.load()
        return s


def snap(store, collection, captured_at, records):
    return {"captured_at": captured_at, "data_store": store, "collection": collection, "records": records}


SQL_HEADER = """-- Ghost Data Still Exists: point-in-time database snapshot
-- Dialect: SQLite-compatible SQL
-- Captured at: {captured}
-- Database topology: read_replica

BEGIN TRANSACTION;
"""
BLOB_TABLE = """CREATE TABLE {t} (resource_id TEXT PRIMARY KEY, origin_system TEXT NOT NULL,
 collection_name TEXT NOT NULL, record_json TEXT NOT NULL CHECK (json_valid(record_json)), updated_at TEXT NOT NULL);
"""


def blob_insert(table, rid, system, coll, record, updated):
    rj = json.dumps(record).replace("'", "''")
    return f"INSERT INTO \"{table}\" VALUES('{rid}','{system}','{coll}','{rj}','{updated}');\n"


# ==========================================================================
# V1  Public API and return types
# ==========================================================================
@pytest.fixture
def api_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("b1", "2026-09-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z",
             [{"resource_id": "account_1", "email": "a@x.io", "full_name": "Ann Ex"}]),
    ])
    return ds.scanner()


def test_V1_api_return_types(api_ds):
    s = api_ds
    ids = SubjectIdentifiers(emails=frozenset({"a@x.io"}))
    at = "2026-09-02T00:00:00Z"

    assert EvidenceScanner(s.dataset_dir).load() is None
    files = s.files()
    assert isinstance(files, list) and all(isinstance(f, EvidenceFile) for f in files)
    assert isinstance(s.get_file("evidence_01"), EvidenceFile)
    with pytest.raises(KeyError):
        s.get_file("evidence_99")
    assert s.is_valid_evidence_id("evidence_01") is True and s.is_valid_evidence_id("evidence_99") is False

    hits = s.find_for_subject(ids, at)
    assert isinstance(hits, list) and hits and all(isinstance(h, ObservedRecord) for h in hits)

    latest = s.latest_by_resource(ids, at)
    assert isinstance(latest, dict) and latest
    for k, v in latest.items():
        assert isinstance(k, tuple) and len(k) == 3 and isinstance(v, ObservedRecord)
        assert isinstance(k[0], str) and isinstance(k[1], str) and (k[2] is None or isinstance(k[2], str))

    proofs = s.absence_proofs("account_service", "account_2", at)
    assert isinstance(proofs, list) and all(isinstance(p, AbsenceProof) for p in proofs) and proofs
    assert all(isinstance(x, ObservedRecord) for x in s.records_for_resource("account_1", at))
    assert all(isinstance(x, SnapshotScope) for x in s.snapshot_scopes(at))
    assert isinstance(s.summary(), dict) and isinstance(s.file_stats(), dict)
    assert isinstance(s.issues, list) and all(isinstance(i, ParseIssue) for i in s.issues)


def test_V1_api_accepts_str_and_datetime_and_rejects_bad_audit_at(api_ds):
    ids = SubjectIdentifiers(emails=frozenset({"a@x.io"}))
    a = api_ds.find_for_subject(ids, "2026-09-02T00:00:00Z")
    b = api_ds.find_for_subject(ids, datetime(2026, 9, 2, tzinfo=UTC))
    c = api_ds.find_for_subject(ids, datetime(2026, 9, 2, 2, tzinfo=timezone(timedelta(hours=2))))  # same instant
    assert [r.locator for r in a] == [r.locator for r in b] == [r.locator for r in c]
    with pytest.raises(ValueError):
        api_ds.find_for_subject(ids, "not a date")
    # contract: naive datetimes are rejected rather than silently assumed UTC
    with pytest.raises(ValueError):
        api_ds.find_for_subject(ids, datetime(2026, 9, 2))


def test_V1_api_requires_load(tmp_path):
    s = EvidenceScanner(tmp_path)
    for call in (lambda: s.files(), lambda: s.get_file("evidence_01"),
                 lambda: s.find_for_subject(SubjectIdentifiers(), "2026-01-01T00:00:00Z"),
                 lambda: s.absence_proofs("a", "b", "2026-01-01T00:00:00Z")):
        with pytest.raises(RuntimeError):
            call()


def test_V1_dataclass_contracts():
    def fields(cls):
        return [f.name for f in dataclasses.fields(cls)]

    assert fields(EvidenceFile) == ["file_id", "file_path", "origin", "captured_at", "absolute_path"]
    assert fields(SubjectIdentifiers) == ["user_id", "emails", "phones", "email_hashes", "names", "resource_ids"]
    assert fields(ObservedRecord)[:13] == [
        "evidence_id", "system_id", "resource_id", "data_category", "collection", "replica_or_table",
        "observed_at", "captured_at", "presence", "pii_fields", "identifiers_matched", "raw_state", "claim_only"]
    assert fields(AbsenceProof) == ["evidence_id", "system_id", "resource_id", "data_category", "collection",
                                    "replica_or_table", "captured_at", "scope_source", "completeness",
                                    "scope_record_count", "limitations", "errors", "contradicted_by"]
    for frozen in (EvidenceFile, SubjectIdentifiers, SnapshotScope, AbsenceProof, ParseIssue):
        assert frozen.__dataclass_params__.frozen
    hints = typing.get_type_hints(EvidenceScanner.find_for_subject)
    assert hints["return"] == list[ObservedRecord]


# ==========================================================================
# V2  Each SubjectIdentifiers field independently
# ==========================================================================
@pytest.fixture
def ident_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("ids", "2026-09-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [
            {"resource_id": "account_u", "customer_reference": "user_901", "email": None, "phone": None},
            {"resource_id": "account_e", "email": "only.email@x.io"},
            {"resource_id": "account_p", "phone": "+44 7700 900123"},
            {"resource_id": "account_h", "email_hash": "ab" * 32},
            {"resource_id": "account_n", "full_name": "Zoë  Example"},
        ]),
        snap("analytics_platform", "customer_analytics_reports", "2026-09-01T00:00:00Z", [
            {"resource_id": "analytics_r", "user_id": None, "email": None, "phone": None, "email_hash": None,
             "metrics": {"sessions_30d": 3}},
        ]),
    ])
    return ds.scanner()


@pytest.mark.parametrize("ids,expected,matched", [
    (SubjectIdentifiers(user_id="USER_901"), "account_u", "user_id:user_901"),
    (SubjectIdentifiers(emails=frozenset({"ONLY.Email@X.io"})), "account_e", "email:only.email@x.io"),
    (SubjectIdentifiers(phones=frozenset({"+44 (0)7700-900123".replace("(0)", "")})), "account_p", "phone:447700900123"),
    (SubjectIdentifiers(email_hashes=frozenset({"AB" * 32})), "account_h", "email_hash:" + "ab" * 32),
    (SubjectIdentifiers(names=frozenset({"zoe example"})), "account_n", "name:zoe example"),
    (SubjectIdentifiers(resource_ids=frozenset({"analytics_r"})), "analytics_r", "resource_id:analytics_r"),
])
def test_V2_each_identifier_field_alone(ident_ds, ids, expected, matched):
    hits = ident_ds.find_for_subject(ids, "2026-09-02T00:00:00Z")
    assert [h.resource_id for h in hits] == [expected]
    assert hits[0].identifiers_matched == [matched]


def test_V2_resource_id_only_record_has_no_identifiers(ident_ds):
    [h] = ident_ds.find_for_subject(SubjectIdentifiers(resource_ids=frozenset({"analytics_r"})), "2026-09-02T00:00:00Z")
    assert h.presence == PRESENT and h.pii_fields == {} and h.subject_reference is None
    assert {k for k, _ in h.linked_terms} == {"resource_id"}


def test_V2_empty_identifiers_return_nothing(ident_ds):
    assert ident_ds.find_for_subject(SubjectIdentifiers(), "2026-09-02T00:00:00Z") == []
    assert ident_ds.latest_by_resource(SubjectIdentifiers(), "2026-09-02T00:00:00Z") == {}


def test_V2_partial_values_do_not_match(ident_ds):
    at = "2026-09-02T00:00:00Z"
    assert ident_ds.find_for_subject(SubjectIdentifiers(user_id="user_90"), at) == []
    assert ident_ds.find_for_subject(SubjectIdentifiers(names=frozenset({"Zoe"})), at) == []
    assert ident_ds.find_for_subject(SubjectIdentifiers(emails=frozenset({"email@x.io"})), at) == []
    assert ident_ds.find_for_subject(SubjectIdentifiers(phones=frozenset({"7700900123"})), at) == []


def test_V2_resource_ids_on_real_corpus_without_email_or_phone(scanner):
    # case_25 / case_21 resources that carry no identifiers in any evidence
    ids = SubjectIdentifiers(resource_ids=frozenset({"account_3136", "analytics_1895", "analytics_5335"}))
    got = {(h.resource_id, h.evidence_id, h.presence) for h in scanner.find_for_subject(ids, "2026-09-15T12:00:00Z")}
    assert ("account_3136", "evidence_92", ABSENT) in got
    assert ("analytics_1895", "evidence_92", PRESENT) in got
    assert ("analytics_5335", "evidence_92", PRESENT) in got


# ==========================================================================
# V3  Case-insensitive matching, original resource-id casing preserved
# ==========================================================================
def test_V3_case_insensitive_match_preserves_casing(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("case", "2026-09-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z",
             [{"resource_id": "Account_ABC7", "email": "Mixed.Case@Example.COM"}]),
    ])
    s = ds.scanner()
    at = "2026-09-02T00:00:00Z"
    for q in ("account_abc7", "ACCOUNT_ABC7", "Account_ABC7"):
        [h] = s.find_for_subject(SubjectIdentifiers(resource_ids=frozenset({q})), at)
        assert h.resource_id == "Account_ABC7"
    [h] = s.find_for_subject(SubjectIdentifiers(emails=frozenset({"mixed.case@example.com"})), at)
    assert h.resource_id == "Account_ABC7" and h.pii_fields["email"] == "Mixed.Case@Example.COM"
    assert list(s.latest_by_resource(SubjectIdentifiers(resource_ids=frozenset({"account_abc7"})), at)) == [
        ("account_service", "Account_ABC7", None)]
    assert [r.resource_id for r in s.records_for_resource("ACCOUNT_abc7", at)] == ["Account_ABC7"]
    # the snapshot contains it regardless of query casing -> no absence proof
    assert s.absence_proofs("account_service", "ACCOUNT_ABC7", at, data_category="USER_PROFILE") == []


def test_V3_real_corpus_mixed_case_email_and_register_id(scanner):
    hits = scanner.find_for_subject(SubjectIdentifiers(emails=frozenset({"Sipho.Mokoena@Gmail.com"})), "2026-10-01T12:00:00Z")
    assert ("evidence_03", "account_2381") in {(h.evidence_id, h.resource_id) for h in hits}  # file has SIPHO.MOKOENA@GMAIL.COM
    reg = scanner.find_for_subject(SubjectIdentifiers(resource_ids=frozenset({"ord-20264118"})), "2026-06-01T00:00:00Z")
    assert [h.resource_id for h in reg] == ["ORD-20264118"]


# ==========================================================================
# V4  audit_at filtering on captured_at and observed_at
# ==========================================================================
@pytest.fixture
def time_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    # file A captured 09-01; one record observed 09-05 (after file capture, possible in exports)
    export = {"exported_at": "2026-09-01T00:00:00Z", "region": "t", "source": "t", "service_exports": {
        "account_service": {"profile_lookups": [
            {"observed_at": "2026-08-31T10:00:00Z", "resource_id": "account_t1", "status_code": 200,
             "profile": {"email": "t@x.io"}},
            {"observed_at": "2026-09-05T10:00:00Z", "resource_id": "account_t1", "status_code": 404, "profile": None},
        ]}}}
    a = ds.add("evidence/records/service_resource_export_a.json", json.dumps(export), "2026-09-01T00:00:00Z")
    # file B captured later (09-10), observation timestamp early (08-01)
    b = ds.bundle("late_file", "2026-09-10T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-08-01T00:00:00Z",
             [{"resource_id": "account_t2", "email": "t@x.io"}]),
    ])
    return ds.scanner(), a, b


def test_V4_captured_at_cutoff(time_ds):
    s, a, b = time_ds
    ids = SubjectIdentifiers(emails=frozenset({"t@x.io"}))
    # observation in B is dated 08-01, but B was only captured 09-10
    assert b not in {h.evidence_id for h in s.find_for_subject(ids, "2026-09-09T23:59:59Z")}
    assert b in {h.evidence_id for h in s.find_for_subject(ids, "2026-09-10T00:00:00Z")}  # inclusive
    assert s.absence_proofs("account_service", "account_x", "2026-09-09T00:00:00Z") == []  # B's scope hidden
    assert [p.evidence_id for p in s.absence_proofs("account_service", "account_x", "2026-09-10T00:00:00Z")] == [b]


def test_V4_observed_at_cutoff_inside_available_file(time_ds):
    s, a, b = time_ds
    ids = SubjectIdentifiers(resource_ids=frozenset({"account_t1"}))
    early = s.find_for_subject(ids, "2026-09-02T00:00:00Z")
    assert [(h.evidence_id, h.presence) for h in early] == [(a, PRESENT)]  # 09-05 404 not visible yet
    late = s.find_for_subject(ids, "2026-09-05T10:00:00Z")
    assert [h.presence for h in late] == [PRESENT, ABSENT]
    assert s.latest_by_resource(ids, "2026-09-05T10:00:00Z")[("account_service", "account_t1", None)].presence == ABSENT
    assert s.latest_by_resource(ids, "2026-09-05T09:59:59Z")[("account_service", "account_t1", None)].presence == PRESENT


def test_V4_links_are_not_followed_through_future_records(tmp_path):
    ds = MiniDataset(tmp_path)
    # the only record that links email -> search_l1 is captured after audit_at
    ds.bundle("future", "2026-09-20T00:00:00Z", [
        snap("search_service", "customer_search_documents", "2026-09-20T00:00:00Z",
             [{"resource_id": "search_l1", "document": {"email": "f@x.io"}}])])
    ds.bundle("past", "2026-09-01T00:00:00Z", [
        snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
             [{"resource_id": "search_l1", "document": {"email": None}}])])
    s = ds.scanner()
    assert s.find_for_subject(SubjectIdentifiers(emails=frozenset({"f@x.io"})), "2026-09-10T00:00:00Z") == []


def test_V4_real_corpus_no_result_after_audit_at(scanner):
    for at in ("2026-03-01T00:00:00Z", "2026-07-01T00:00:00Z", "2026-09-15T12:00:00Z"):
        cutoff = ts(at)
        ids = SubjectIdentifiers(user_id="user_21", emails=frozenset({"amara-okeke@proton.me", "ingrid.dahl@outlook.com"}))
        for h in scanner.find_for_subject(ids, at):
            assert h.captured_at <= cutoff and h.observed_at <= cutoff
        for p in scanner.absence_proofs("account_service", "account_6440", at):
            assert p.captured_at <= cutoff and scanner.get_file(p.evidence_id).captured_at <= cutoff


# ==========================================================================
# V5  Primary vs replica drift
# ==========================================================================
@pytest.fixture
def drift_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    sql = SQL_HEADER.format(captured="2026-09-01T00:00:00Z")
    sql += BLOB_TABLE.format(t="customer_data_primary") + BLOB_TABLE.format(t="customer_data_read_replica")
    shared = {"resource_id": "account_s", "email": "shared@x.io"}
    ghost = {"resource_id": "account_g", "email": "ghost@x.io", "full_name": "Gus Host"}
    sql += blob_insert("customer_data_primary", "account_s", "account_service", "customer_profiles", shared, "2026-09-01T00:00:00Z")
    sql += blob_insert("customer_data_read_replica", "account_s", "account_service", "customer_profiles", shared, "2026-09-01T00:00:00Z")
    sql += blob_insert("customer_data_read_replica", "account_g", "account_service", "customer_profiles", ghost, "2026-09-01T00:00:00Z")
    sql += "COMMIT;\n"
    fid = ds.add("evidence/databases/customer_data_read_replica_x.sql", sql, "2026-09-01T00:00:00Z")
    return ds.scanner(), fid


def test_V5_replica_only_record_keeps_replica_key(drift_ds):
    s, fid = drift_ds
    latest = s.latest_by_resource(SubjectIdentifiers(emails=frozenset({"ghost@x.io"})), "2026-09-02T00:00:00Z")
    assert list(latest) == [("account_service", "account_g", "customer_data_read_replica")]
    rec = latest[("account_service", "account_g", "customer_data_read_replica")]
    assert rec.presence == PRESENT and rec.evidence_id == fid and rec.raw_state["table"] == "customer_data_read_replica"


def test_V5_record_in_both_copies_is_two_keys(drift_ds):
    s, _ = drift_ds
    latest = s.latest_by_resource(SubjectIdentifiers(emails=frozenset({"shared@x.io"})), "2026-09-02T00:00:00Z")
    assert set(latest) == {("account_service", "account_s", None),
                           ("account_service", "account_s", "customer_data_read_replica")}


def test_V5_absence_only_from_primary(drift_ds):
    s, fid = drift_ds
    proofs = s.absence_proofs("account_service", "account_g", "2026-09-02T00:00:00Z")
    assert proofs == [AbsenceProof(fid, "account_service", "account_g", "USER_PROFILE", "customer_profiles",
                                   None, ts("2026-09-01T00:00:00Z"), scope_source="sql_table",
                                   completeness="COMPLETE", scope_record_count=1,
                                   limitations=("covers the primary copy only; replica copies are not covered",))]


def test_V5_real_corpus_account_005(scanner):
    latest = scanner.latest_by_resource(SubjectIdentifiers(emails=frozenset({"leila.haddad@yahoo.com"})), "2026-09-08T13:40:00Z")
    assert ("account_service", "account_005", "customer_profiles_failover_replica") in latest
    assert ("account_service", "account_005", None) not in latest
    primary = [p for p in scanner.absence_proofs("account_service", "account_005", "2026-09-08T13:40:00Z")
               if p.evidence_id == "evidence_54"]
    assert [(p.collection, p.replica_or_table) for p in primary] == [("customer_profiles_primary", None)]


# ==========================================================================
# V6  PRESENT / ABSENT / UNKNOWN
# ==========================================================================
@pytest.fixture
def state_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    log = (
        "2026-09-01T10:00:00Z level=INFO service=account_service trace_id=t1 event=profile_lookup_started lookup_key=st@x.io\n"
        "2026-09-01T10:00:01Z level=INFO service=account_service trace_id=t1 resource_id=account_a event=profile_lookup_completed rows=0 http_status=404\n"
        "2026-09-01T10:00:02Z level=INFO service=search_service trace_id=t2 event=index_query_started match_key=st@x.io\n"
        "2026-09-01T10:00:03Z level=INFO service=search_service trace_id=t2 resource_id=search_a event=index_query_completed result=hit\n"
        "2026-09-01T10:00:04Z level=WARN service=support_platform trace_id=t3 event=message_scan_started subject_key=st@x.io\n"
        "2026-09-01T10:00:05Z level=WARN service=support_platform trace_id=t3 resource_id=support_a event=deletion_marker_check marker_found=false\n"
        "2026-09-01T10:00:06Z level=INFO service=search_service trace_id=t4 event=index_query_started match_key=st@x.io\n"
        "2026-09-01T10:00:07Z level=INFO service=search_service trace_id=t4 resource_id=search_b event=index_query_completed result=miss total_hits=0\n"
    )
    ds.add("evidence/logs/service_events_states.log", log, "2026-09-01T12:00:00Z")
    return ds.scanner()


def test_V6_three_presence_states(state_ds):
    hits = {h.resource_id: h for h in state_ds.find_for_subject(SubjectIdentifiers(emails=frozenset({"st@x.io"})), "2026-09-02T00:00:00Z")}
    assert hits["account_a"].presence == ABSENT
    assert hits["search_a"].presence == PRESENT
    assert hits["search_b"].presence == ABSENT
    assert hits["support_a"].presence == UNKNOWN
    assert {h.presence for h in hits.values()} == {PRESENT, ABSENT, UNKNOWN}


def test_V6_unknown_never_overrides_known_state(tmp_path):
    ds = MiniDataset(tmp_path)
    log = (
        "2026-09-01T10:00:00Z level=INFO service=support_platform trace_id=t1 resource_id=support_k event=support_ticket_read_completed requester_email=k@x.io\n"
        "2026-09-01T11:00:00Z level=WARN service=support_platform trace_id=t2 resource_id=support_k event=deletion_marker_check marker_found=false\n"
    )
    ds.add("evidence/logs/service_events_k.log", log, "2026-09-01T12:00:00Z")
    s = ds.scanner()
    ids = SubjectIdentifiers(emails=frozenset({"k@x.io"}))
    hits = s.find_for_subject(ids, "2026-09-02T00:00:00Z")
    assert [h.presence for h in hits] == [PRESENT, UNKNOWN]  # both returned, newest is UNKNOWN
    assert s.latest_by_resource(ids, "2026-09-02T00:00:00Z")[("support_platform", "support_k", None)].presence == PRESENT


def test_V6_real_corpus_states(scanner):
    pres = {r.presence for r in scanner.records}
    assert pres == {PRESENT, ABSENT, UNKNOWN}
    [r] = [r for r in scanner.records if r.evidence_id == "evidence_61" and r.raw_state.get("event") == "deletion_marker_check"]
    assert r.presence == UNKNOWN and r.raw_state["marker_found"] is False


# ==========================================================================
# V7  claim_only vs authoritative store state
# ==========================================================================
@pytest.fixture
def claim_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.add("evidence/records/handover.txt",
           "HANDOVER\nSnapshot: 2026-09-01T10:00:00Z\n\n"
           "- 2026-09-01T10:00:00Z | account_service | account_31 | USER_PROFILE | NOT_FOUND | claim@x.io\n",
           "2026-09-01T10:00:00Z")
    ds.bundle("store", "2026-09-01T10:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T10:00:00Z",
             [{"resource_id": "account_31", "email": "claim@x.io"}])])
    ledger = {"exported_at": "2026-09-01T09:00:00Z", "origin": "t", "record_count": 1, "records": [
        {"recorded_at": "2026-09-01T09:00:00Z", "system": "search_service", "resource_id": "search_31",
         "record_type": "SEARCH_INDEX_ENTRY", "result": "FOUND", "subject_reference": "claim@x.io"}]}
    ds.add("evidence/records/ledger.json", json.dumps(ledger), "2026-09-01T09:00:00Z")
    return ds.scanner()


def test_V7_claim_flags(claim_ds):
    hits = claim_ds.find_for_subject(SubjectIdentifiers(emails=frozenset({"claim@x.io"})), "2026-09-02T00:00:00Z")
    flags = {(h.source_format, h.resource_id): h.claim_only for h in hits}
    assert flags == {("txt", "account_31"): True, ("json", "account_31"): False, ("json", "search_31"): True}
    for h in hits:
        if h.claim_only:
            assert h.pii_fields == {}  # lookup subject is a query key, not stored PII
            assert "result" in h.raw_state


def test_V7_store_state_wins_tie_against_claim(claim_ds):
    # same observed_at: the store snapshot (PRESENT) must beat the handover claim (NOT_FOUND)
    latest = claim_ds.latest_by_resource(SubjectIdentifiers(emails=frozenset({"claim@x.io"})), "2026-09-02T00:00:00Z")
    rec = latest[("account_service", "account_31", None)]
    assert rec.claim_only is False and rec.presence == PRESENT


def test_V7_malformed_handover_row_is_reported_not_silently_dropped(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.add("evidence/records/handover.txt",
           "- 2026-09-01T10:00:00Z | account_service | account_c | USER_PROFILE | NOT_FOUND | x@x.io\n",
           "2026-09-01T10:00:00Z")
    s = ds.scanner()
    assert s.records == []
    assert [(i.severity, i.message) for i in s.issues] == [
        ("warning", "line 1: unrecognised resource id 'account_c'"),
        ("unsupported", "no recognisable checklist rows")]


def test_V7_claims_never_create_scopes(claim_ds):
    assert {s.evidence_id for s in claim_ds.scopes} == {"evidence_02"}


def test_V7_real_corpus_claim_sources(scanner):
    claims = {r.evidence_id for r in scanner.records if r.claim_only}
    assert {"evidence_03", "evidence_08", "evidence_13", "evidence_36", "evidence_41", "evidence_50"} <= claims
    store = {r.evidence_id for r in scanner.records if not r.claim_only}
    assert {"evidence_05", "evidence_54", "evidence_57", "evidence_58", "evidence_92", "evidence_94"} <= store
    assert all(r.source_format != "sql" for r in scanner.records if r.claim_only)


# ==========================================================================
# V8  absence_proofs(): exact structure and validity conditions
# ==========================================================================
@pytest.fixture
def absence_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    old = ds.bundle("old", "2026-08-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-08-01T00:00:00Z", [{"resource_id": "account_z"}]),
        snap("support_platform", "support_conversations", "2026-08-01T00:00:00Z", [{"resource_id": "support_m"}]),
    ])
    new = ds.bundle("new", "2026-09-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", []),
        snap("support_platform", "ticket_attachments", "2026-09-01T00:00:00Z", [{"resource_id": "support_att"}]),
    ])
    future = ds.bundle("future", "2026-12-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-12-01T00:00:00Z", [])])
    # a lookup ledger saying NOT_FOUND must not become an absence proof
    ledger = {"exported_at": "2026-09-02T00:00:00Z", "origin": "t", "record_count": 1, "records": [
        {"recorded_at": "2026-09-02T00:00:00Z", "system": "export_service", "resource_id": "export_q",
         "record_type": "USER_EXPORT", "result": "NOT_FOUND", "subject_reference": "q@x.io"}]}
    ds.add("evidence/records/ledger.json", json.dumps(ledger), "2026-09-02T00:00:00Z")
    return ds.scanner(), old, new, future


def test_V8_exact_output_structure(absence_ds):
    s, old, new, future = absence_ds
    proofs = s.absence_proofs("account_service", "Account_Z", "2026-10-01T00:00:00Z")
    assert proofs == [AbsenceProof(evidence_id=new, system_id="account_service", resource_id="Account_Z",
                                   data_category="USER_PROFILE", collection="customer_profiles",
                                   replica_or_table=None, captured_at=ts("2026-09-01T00:00:00Z"),
                                   scope_source="collection_snapshot", completeness="COMPLETE",
                                   scope_record_count=0,
                                   limitations=("covers the primary copy only; replica copies are not covered",),
                                   errors=(), contradicted_by=())]
    p = proofs[0]
    assert dataclasses.asdict(p).keys() == {"evidence_id", "system_id", "resource_id", "data_category",
                                            "collection", "replica_or_table", "captured_at", "scope_source",
                                            "completeness", "scope_record_count", "limitations", "errors",
                                            "contradicted_by"}
    assert p.verified_at == p.captured_at and p.is_valid_proof
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.evidence_id = "x"


def test_V8_scope_containing_resource_is_not_proof(absence_ds):
    s, old, new, _ = absence_ds
    # at 08-15 only the old snapshot exists, and it contains account_z
    assert s.absence_proofs("account_service", "account_z", "2026-08-15T00:00:00Z") == []


def test_V8_newest_first_and_cutoff(absence_ds):
    s, old, new, future = absence_ds
    proofs = s.absence_proofs("account_service", "account_never", "2026-10-01T00:00:00Z")
    assert [p.evidence_id for p in proofs] == [new, old]
    assert future not in {p.evidence_id for p in proofs}
    assert [p.evidence_id for p in s.absence_proofs("account_service", "account_never", "2026-12-01T00:00:00Z")] == [future, new, old]


def test_V8_category_and_system_must_match(absence_ds):
    s, old, new, _ = absence_ds
    at = "2026-10-01T00:00:00Z"
    # an attachment that was observed: only the ticket_attachments scope can prove its absence
    assert s.absence_proofs("support_platform", "support_att", at) == []  # it is in that scope
    att = s.absence_proofs("support_platform", "support_x", at, data_category="SUPPORT_ATTACHMENT")
    assert [(p.evidence_id, p.collection) for p in att] == [(new, "ticket_attachments")]
    msg = s.absence_proofs("support_platform", "support_x", at, data_category="SUPPORT_MESSAGE")
    assert [(p.evidence_id, p.collection) for p in msg] == [(old, "support_conversations")]
    # unknown category (support_* is ambiguous, never observed) -> no guess
    assert s.absence_proofs("support_platform", "support_x", at) == []
    # wrong system -> nothing
    assert s.absence_proofs("search_service", "account_never", at) == []


def test_V8_observed_category_is_used_by_default(absence_ds):
    s, old, new, _ = absence_ds
    # support_m was observed in support_conversations -> SUPPORT_MESSAGE scopes only
    proofs = s.absence_proofs("support_platform", "support_m", "2026-10-01T00:00:00Z")
    assert proofs == []  # the only SUPPORT_MESSAGE scope (old) contains it


def test_V8_claims_are_not_absence_proofs(absence_ds):
    s, *_ = absence_ds
    assert s.absence_proofs("export_service", "export_q", "2026-10-01T00:00:00Z") == []
    assert all(sc.system_id != "export_service" for sc in s.scopes)


def test_V8_every_proof_matches_a_real_scope(scanner):
    at = "2026-10-01T12:00:00Z"
    for system, rid in [("account_service", "account_001"), ("search_service", "search_001"),
                        ("analytics_platform", "analytics_9406"), ("backup_service", "backup_4978"),
                        ("identity_service", "tombstone_440"), ("security_service", "audit_record_003")]:
        for p in scanner.absence_proofs(system, rid, at):
            matching = [sc for sc in scanner.scopes if (sc.evidence_id, sc.system_id, sc.collection,
                        sc.replica_or_table, sc.captured_at) == (p.evidence_id, p.system_id, p.collection,
                        p.replica_or_table, p.captured_at)]
            assert matching and all(not sc.contains(rid) for sc in matching)
            assert p.system_id == system and p.resource_id == rid


# ==========================================================================
# V9  Tombstones with empty PII remain PRESENT
# ==========================================================================
def test_V9_tombstone_null_pii_is_present(tmp_path):
    ds = MiniDataset(tmp_path)
    fid = ds.bundle("tomb", "2026-09-01T00:00:00Z", [
        snap("identity_service", "deleted_customer_references", "2026-09-01T00:00:00Z", [
            {"resource_id": "tombstone_1", "subject_reference": "user_777", "name": None, "email": None,
             "phone": None, "email_hash": None, "account_status": "DELETED"}])])
    s = ds.scanner()
    [h] = s.find_for_subject(SubjectIdentifiers(user_id="user_777"), "2026-09-02T00:00:00Z")
    assert (h.presence, h.data_category, h.pii_fields, h.subject_reference) == (PRESENT, "ACCOUNT_TOMBSTONE", {}, "user_777")
    assert h.raw_state["email"] is None and h.raw_state["account_status"] == "DELETED"
    assert h.evidence_id == fid
    assert s.absence_proofs("identity_service", "tombstone_1", "2026-09-02T00:00:00Z") == []


def test_V9_real_corpus_tombstone(scanner):
    [h] = [x for x in scanner.find_for_subject(SubjectIdentifiers(user_id="user_541"), "2026-09-15T12:00:00Z")
           if x.resource_id == "tombstone_440"]
    assert h.presence == PRESENT and h.pii_fields == {} and h.evidence_id == "evidence_51"


# ==========================================================================
# V10 Evidence IDs against the manifest (read independently with csv)
# ==========================================================================
def test_V10_all_ids_in_manifest(scanner, dataset_dir):
    with (dataset_dir / "evidence_files.csv").open(encoding="utf-8", newline="") as fh:
        manifest = {r["file_id"]: r for r in csv.DictReader(fh)}
    assert len(manifest) == 94
    assert {f.file_id for f in scanner.files()} == set(manifest)
    for f in scanner.files():
        assert f.file_path == manifest[f.file_id]["file_path"]
        assert f.captured_at == ts(manifest[f.file_id]["captured_at"])
    assert {r.evidence_id for r in scanner.records} <= set(manifest)
    assert {s.evidence_id for s in scanner.scopes} <= set(manifest)
    for r in scanner.records:
        assert r.captured_at == ts(manifest[r.evidence_id]["captured_at"])
    for rid in ("account_001", "search_9999", "audit_record_1"):
        assert {p.evidence_id for p in scanner.absence_proofs(
            "account_service" if rid.startswith("account") else "search_service" if rid.startswith("search") else "security_service",
            rid, "2026-12-31T00:00:00Z")} <= set(manifest)
