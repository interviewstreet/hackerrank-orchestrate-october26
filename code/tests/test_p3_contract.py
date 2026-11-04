"""Tests for the API contract agreed with P3.

1. find_records(identifiers, audit_at) -> list[ObservedRecord]: every matching
   observation, nothing collapsed.
2. absence_proofs(system_id, resource_id, audit_at) -> list[AbsenceProof]: scope,
   completeness, verification time, errors, limitations; no proof from
   incomplete or out-of-scope evidence.
3. latest_by_resource(identifiers, audit_at): latest *authoritative*
   observation per (system_id, resource_id, replica_or_table).
"""

from __future__ import annotations

import json
import typing
from datetime import datetime, timedelta, timezone

import pytest

from evidence import (
    ABSENT,
    COMPLETE,
    INCOMPLETE,
    INFERRED,
    PRESENT,
    AbsenceProof,
    EvidenceScanner,
    ObservedRecord,
    SubjectIdentifiers,
)
from test_independent_validation import BLOB_TABLE, SQL_HEADER, MiniDataset, blob_insert, snap

AT = datetime(2026, 10, 1, tzinfo=timezone.utc)


# ==========================================================================
# 1. find_records
# ==========================================================================
def test_find_records_signature():
    hints = typing.get_type_hints(EvidenceScanner.find_records)
    assert hints["identifiers"] is SubjectIdentifiers
    assert hints["audit_at"] is datetime
    assert hints["return"] == list[ObservedRecord]


@pytest.mark.parametrize("email,at", [
    ("leila.haddad@yahoo.com", "2026-09-08T13:40:00Z"),
    ("novak.tomasz@icloud.com", "2026-10-01T12:00:00Z"),
    ("e.varga90@yahoo.com", "2026-09-15T12:00:00Z"),
    ("marek.zielinski@gmail.com", "2026-09-30T00:00:00Z"),
])
def test_find_for_subject_is_backward_compatible_alias(scanner, email, at):
    ids = SubjectIdentifiers(emails=frozenset({email}))
    a = scanner.find_records(ids, datetime.fromisoformat(at.replace("Z", "+00:00")))
    b = scanner.find_for_subject(ids, at)
    assert a == b and a


@pytest.fixture
def conflict_ds(tmp_path):
    """One resource observed many ways: two snapshots, a replica copy, a 404 read-back and a claim."""
    ds = MiniDataset(tmp_path)
    ds.bundle("s1", "2026-09-01T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z",
             [{"resource_id": "account_77", "email": "c@x.io"}])])
    ds.bundle("s2", "2026-09-03T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-03T00:00:00Z",
             [{"resource_id": "account_77", "email": "c@x.io", "account_status": "DELETION_PENDING"}])])
    sql = SQL_HEADER.format(captured="2026-09-04T00:00:00Z") + BLOB_TABLE.format(t="customer_data_primary") \
        + BLOB_TABLE.format(t="customer_data_read_replica")
    sql += blob_insert("customer_data_primary", "account_88", "account_service", "customer_profiles",
                       {"resource_id": "account_88", "email": "other@x.io"}, "2026-09-04T00:00:00Z")
    sql += blob_insert("customer_data_read_replica", "account_77", "account_service", "customer_profiles",
                       {"resource_id": "account_77", "email": "c@x.io"}, "2026-09-04T00:00:00Z")
    sql += "COMMIT;\n"
    ds.add("evidence/databases/customer_data_read_replica_c.sql", sql, "2026-09-04T00:00:00Z")
    export = {"exported_at": "2026-09-05T00:00:00Z", "region": "t", "source": "t", "service_exports": {
        "account_service": {"profile_lookups": [
            {"observed_at": "2026-09-05T00:00:00Z", "resource_id": "account_77", "status_code": 404, "profile": None}]}}}
    ds.add("evidence/records/service_resource_export_c.json", json.dumps(export), "2026-09-05T00:00:00Z")
    ds.add("evidence/records/handover.txt",
           "- 2026-09-06T00:00:00Z | account_service | account_77 | USER_PROFILE | FOUND | c@x.io\n",
           "2026-09-06T00:00:00Z")
    return ds.scanner()


def test_find_records_returns_every_observation(conflict_ds):
    hits = conflict_ds.find_records(SubjectIdentifiers(emails=frozenset({"c@x.io"})), AT)
    rows = [(h.evidence_id, h.replica_or_table, h.presence, h.claim_only, h.observed_at.day) for h in hits
            if h.resource_id == "account_77"]
    assert rows == [
        ("evidence_01", None, PRESENT, False, 1),
        ("evidence_02", None, PRESENT, False, 3),
        ("evidence_03", "customer_data_read_replica", PRESENT, False, 4),
        ("evidence_04", None, ABSENT, False, 5),
        ("evidence_05", None, PRESENT, True, 6),
    ]
    # the decoy in the same SQL file is not matched
    assert "account_88" not in {h.resource_id for h in hits}


def test_find_records_preserves_timestamps_and_state(conflict_ds):
    hits = conflict_ds.find_records(SubjectIdentifiers(resource_ids=frozenset({"account_77"})), AT)
    for h in hits:
        assert h.captured_at == conflict_ds.get_file(h.evidence_id).captured_at
        assert h.observed_at <= AT and h.captured_at <= AT
    s2 = next(h for h in hits if h.evidence_id == "evidence_02")
    assert s2.raw_state["account_status"] == "DELETION_PENDING"


def test_find_records_cutoff_drops_later_observations_only(conflict_ds):
    at = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
    hits = conflict_ds.find_records(SubjectIdentifiers(resource_ids=frozenset({"account_77"})), at)
    assert [h.evidence_id for h in hits] == ["evidence_01", "evidence_02", "evidence_03"]


# ==========================================================================
# Timestamp validation (all query methods)
# ==========================================================================
QUERIES = [
    lambda s, at: s.find_records(SubjectIdentifiers(emails=frozenset({"c@x.io"})), at),
    lambda s, at: s.find_for_subject(SubjectIdentifiers(emails=frozenset({"c@x.io"})), at),
    lambda s, at: s.latest_by_resource(SubjectIdentifiers(emails=frozenset({"c@x.io"})), at),
    lambda s, at: s.absence_proofs("account_service", "account_77", at),
    lambda s, at: s.records_for_resource("account_77", at),
    lambda s, at: s.snapshot_scopes(at),
]


@pytest.mark.parametrize("query", QUERIES)
@pytest.mark.parametrize("bad,exc", [
    (datetime(2026, 10, 1), ValueError),            # naive datetime
    ("2026-10-01T00:00:00", ValueError),            # string without offset
    ("2026-10-01", ValueError),                     # date only, no offset
    ("yesterday", ValueError),
    (1790000000, TypeError),                        # epoch int
    (None, TypeError),
])
def test_invalid_audit_at_is_rejected(conflict_ds, query, bad, exc):
    with pytest.raises(exc):
        query(conflict_ds, bad)


@pytest.mark.parametrize("query", QUERIES)
def test_equivalent_audit_at_forms_agree(conflict_ds, query):
    forms = [
        datetime(2026, 9, 5, tzinfo=timezone.utc),
        datetime(2026, 9, 5, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        "2026-09-05T00:00:00Z",
        "2026-09-04T20:00:00-04:00",
    ]
    results = [query(conflict_ds, f) for f in forms]
    assert all(r == results[0] for r in results)


# ==========================================================================
# 3. latest_by_resource: authoritative only
# ==========================================================================
def test_latest_by_resource_signature():
    hints = typing.get_type_hints(EvidenceScanner.latest_by_resource)
    assert hints["audit_at"] is datetime
    assert hints["return"] == dict[tuple[str, str, typing.Optional[str]], ObservedRecord]


def test_latest_excludes_newer_claim(conflict_ds):
    ids = SubjectIdentifiers(emails=frozenset({"c@x.io"}))
    latest = conflict_ds.latest_by_resource(ids, AT)
    assert set(latest) == {("account_service", "account_77", None),
                           ("account_service", "account_77", "customer_data_read_replica")}
    primary = latest[("account_service", "account_77", None)]
    # the 09-06 FOUND handover claim is newer, but the 09-05 404 read-back is the latest authoritative state
    assert (primary.evidence_id, primary.presence, primary.claim_only) == ("evidence_04", ABSENT, False)
    replica = latest[("account_service", "account_77", "customer_data_read_replica")]
    assert (replica.evidence_id, replica.presence) == ("evidence_03", PRESENT)
    # claims are still reachable
    assert any(h.claim_only for h in conflict_ds.find_records(ids, AT))
    assert conflict_ds.latest_by_resource(ids, AT, include_claims=True)[
        ("account_service", "account_77", None)].evidence_id == "evidence_05"


def test_latest_never_returns_claims_on_real_corpus(scanner, dataset_dir):
    from identity_helper import identifiers_for_email

    for email, at in [("novak.tomasz@icloud.com", "2026-10-01T12:00:00Z"),
                      ("y.tanaka32@gmail.com", "2026-10-01T12:00:00Z"),
                      ("leila.haddad@yahoo.com", "2026-09-08T13:40:00Z")]:
        ids = identifiers_for_email(dataset_dir, email)
        latest = scanner.latest_by_resource(ids, at)
        assert all(not r.claim_only for r in latest.values())
        authoritative = [h for h in scanner.find_records(ids, at) if not h.claim_only]
        assert set(latest) == {h.latest_key for h in authoritative}


# ==========================================================================
# 2. absence_proofs: scope, completeness, errors, limitations
# ==========================================================================
def test_absence_proofs_signature():
    hints = typing.get_type_hints(EvidenceScanner.absence_proofs)
    assert hints["audit_at"] is datetime and hints["return"] == list[AbsenceProof]


@pytest.fixture
def proof_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    # SQL dump: account_service rows exist only in the replica -> primary coverage is INFERRED
    sql = SQL_HEADER.format(captured="2026-09-01T00:00:00Z") + BLOB_TABLE.format(t="customer_data_primary") \
        + BLOB_TABLE.format(t="customer_data_read_replica")
    sql += blob_insert("customer_data_primary", "search_1", "search_service", "customer_search_documents",
                       {"resource_id": "search_1"}, "2026-09-01T00:00:00Z")
    sql += blob_insert("customer_data_read_replica", "account_5", "account_service", "customer_profiles",
                       {"resource_id": "account_5"}, "2026-09-01T00:00:00Z")
    sql += "COMMIT;\n"
    inferred = ds.add("evidence/databases/customer_data_read_replica_p.sql", sql, "2026-09-01T00:00:00Z")
    # bundle with a record lacking resource_id -> scope INCOMPLETE
    broken = ds.bundle("broken", "2026-09-02T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-02T00:00:00Z", [{"email": "no-id@x.io"}])])
    # clean declared snapshot -> COMPLETE
    clean = ds.bundle("clean", "2026-09-03T00:00:00Z", [
        snap("account_service", "customer_profiles", "2026-09-03T00:00:00Z", [{"resource_id": "account_9"}])])
    # later authoritative PRESENT read-back of account_404 in the primary copy
    export = {"exported_at": "2026-09-04T00:00:00Z", "region": "t", "source": "t", "service_exports": {
        "account_service": {"profile_lookups": [
            {"observed_at": "2026-09-04T00:00:00Z", "resource_id": "account_404", "status_code": 200,
             "profile": {"email": "late@x.io"}}]}}}
    ds.add("evidence/records/service_resource_export_p.json", json.dumps(export), "2026-09-04T00:00:00Z")
    return ds.scanner(), inferred, broken, clean


def test_default_proofs_are_complete_only(proof_ds):
    s, inferred, broken, clean = proof_ds
    proofs = s.absence_proofs("account_service", "account_1", AT)
    # clean primary snapshot + the dump's replica table (which really holds account rows)
    assert [(p.evidence_id, p.replica_or_table, p.completeness) for p in proofs] == [
        (clean, None, COMPLETE), (inferred, "customer_data_read_replica", COMPLETE)]
    p = proofs[0]
    assert (p.scope_source, p.scope_record_count, p.errors, p.contradicted_by) == ("collection_snapshot", 1, (), ())
    assert p.verified_at == datetime(2026, 9, 3, tzinfo=timezone.utc) and p.is_valid_proof


def test_unverified_candidates_are_marked(proof_ds):
    s, inferred, broken, clean = proof_ds
    proofs = {p.evidence_id: p for p in s.absence_proofs("account_service", "account_1", AT, include_unverified=True)}
    assert set(proofs) == {inferred, broken, clean}
    inf = proofs[inferred]
    assert (inf.completeness, inf.scope_source, inf.replica_or_table, inf.is_valid_proof) == (
        INFERRED, "sql_sibling_inference", None, False)
    assert any("inferred from sibling tables" in lim for lim in inf.limitations)
    br = proofs[broken]
    assert br.completeness == INCOMPLETE and not br.is_valid_proof
    assert br.errors and "record without resource_id" in br.errors[0]
    assert any("could not be listed" in lim for lim in br.limitations)
    # the replica table of the same dump genuinely holds account rows -> COMPLETE for that copy
    replica = [p for p in s.absence_proofs("account_service", "account_1", AT, include_unverified=True)
               if p.replica_or_table == "customer_data_read_replica"]
    assert [(p.evidence_id, p.completeness) for p in replica] == [(inferred, COMPLETE)]


def test_copy_limitation_is_stated(proof_ds):
    s, inferred, broken, clean = proof_ds
    for p in s.absence_proofs("account_service", "account_1", AT, include_unverified=True):
        expected = ("covers the primary copy only; replica copies are not covered" if p.replica_or_table is None
                    else f"covers replica copy '{p.replica_or_table}' only; the primary copy is not covered")
        assert expected in p.limitations


def test_contradicted_by_later_present_observation(proof_ds):
    s, inferred, broken, clean = proof_ds
    proofs = s.absence_proofs("account_service", "account_404", AT)
    [p] = [p for p in proofs if p.evidence_id == clean]
    assert p.contradicted_by == ("evidence_04@service_exports.account_service.profile_lookups[0]",)
    assert p.completeness == COMPLETE and not p.is_valid_proof
    assert any("observed PRESENT" in lim for lim in p.limitations)
    # a primary-copy read-back does not contradict the replica-copy proof
    [rep] = [p for p in proofs if p.replica_or_table == "customer_data_read_replica"]
    assert rep.contradicted_by == () and rep.is_valid_proof
    # before the read-back the primary proof is uncontradicted
    early = s.absence_proofs("account_service", "account_404", datetime(2026, 9, 3, 12, tzinfo=timezone.utc))
    [e] = [p for p in early if p.evidence_id == clean]
    assert e.contradicted_by == () and e.is_valid_proof


def test_out_of_scope_never_returned(proof_ds):
    s, *_ = proof_ds
    for unverified in (False, True):
        assert s.absence_proofs("billing_service", "account_1", AT, include_unverified=unverified) == []
        assert s.absence_proofs("account_service", "account_1", "2026-08-31T00:00:00Z",
                                include_unverified=unverified) == []
        assert s.absence_proofs("account_service", "account_1", AT, data_category="SEARCH_INDEX_ENTRY",
                                include_unverified=unverified) == []
        assert s.absence_proofs("account_service", "account_5", AT, include_unverified=unverified) == [
            p for p in s.absence_proofs("account_service", "account_5", AT, include_unverified=unverified)
            if p.replica_or_table != "customer_data_read_replica"]  # the replica that lists it is excluded


def test_real_corpus_sample_proofs_still_valid(scanner):
    # case_01: account_001 absent from evidence_54; case_31: account_4857 absent from evidence_51
    for rid, at, eid in [("account_001", "2026-09-03T11:30:00Z", "evidence_54"),
                         ("account_4857", "2026-09-15T12:00:00Z", "evidence_51")]:
        proofs = [p for p in scanner.absence_proofs("account_service", rid, at) if p.evidence_id == eid]
        assert proofs and all(p.completeness == COMPLETE and p.errors == () for p in proofs)


def test_real_corpus_inferred_coverage_is_not_default_proof(scanner):
    at = "2026-10-01T12:00:00Z"
    default = scanner.absence_proofs("account_service", "account_none_1", at)
    everything = scanner.absence_proofs("account_service", "account_none_1", at, include_unverified=True)
    assert all(p.completeness == COMPLETE for p in default)
    inferred = [p for p in everything if p.completeness == INFERRED]
    assert inferred and all(p.scope_source == "sql_sibling_inference" for p in inferred)
    assert {(p.evidence_id, p.collection, p.replica_or_table) for p in default}.isdisjoint(
        {(p.evidence_id, p.collection, p.replica_or_table) for p in inferred})
    assert not [p for p in everything if p.completeness == INCOMPLETE]  # corpus has no parse issues
