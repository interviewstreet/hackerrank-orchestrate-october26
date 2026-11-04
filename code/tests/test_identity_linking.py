"""Regression tests for cross-references (A), identity conflicts (B), name-only
matching (C) and the file-name linking fix. Isolated fixtures + real corpus."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from evidence import LINKED, STRONG, WEAK, ResourceReference, SubjectIdentifiers
from identity_helper import identifiers_for, identifiers_for_email
from test_independent_validation import MiniDataset, snap

AT = datetime(2026, 10, 1, tzinfo=timezone.utc)
A = SubjectIdentifiers(user_id="user_1", emails=frozenset({"a@x.io"}), names=frozenset({"Alex Morgan"}))
B = SubjectIdentifiers(user_id="user_2", emails=frozenset({"b@x.io"}))


def search_doc(rid, email, ref, **extra):
    return {"resource_id": rid, "index_name": "customer_directory_v3",
            "document": {"email": email}, "source_resource_id": ref, **extra}


# ==========================================================================
# A. Explicit resource cross-references
# ==========================================================================
@pytest.fixture
def xref_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("own", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [search_doc("search_10", "a@x.io", "account_61")])])
    ds.bundle("other", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [search_doc("search_20", "b@x.io", "account_62")])])
    ds.bundle("future", "2026-11-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-11-01T00:00:00Z",
              [search_doc("search_30", "a@x.io", "account_64")])])
    ledger = {"exported_at": "2026-09-02T00:00:00Z", "origin": "t", "record_count": 1, "records": [
        {"recorded_at": "2026-09-02T00:00:00Z", "system": "search_service", "resource_id": "search_40",
         "record_type": "SEARCH_INDEX_ENTRY", "result": "FOUND", "subject_reference": "a@x.io",
         "source_resource_id": "account_63"}]}
    ds.add("evidence/records/ledger.json", json.dumps(ledger), "2026-09-02T00:00:00Z")
    # account_63 *has* an observation (no identifiers), so a wrongly followed claim would surface it
    ds.bundle("acct63", "2026-09-03T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-03T00:00:00Z",
              [{"resource_id": "account_63", "email": None}])])
    return ds.scanner()


def test_A_valid_same_subject_cross_reference(xref_ds):
    refs = xref_ds.referenced_resources(A, AT)
    assert refs == [ResourceReference(
        resource_id="account_61", system_id="account_service", source_evidence_id="evidence_01",
        source_locator="snapshots[0].records[0]", source_system_id="search_service",
        source_resource_id="search_10", source_field="source_resource_id",
        source_observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        source_captured_at=datetime(2026, 9, 1, tzinfo=timezone.utc), has_observations=False)]
    # pointer only: no ObservedRecord is fabricated for the referenced resource
    assert "account_61" not in {h.resource_id for h in xref_ds.find_records(A, AT)}
    assert xref_ds.records_for_resource("account_61", AT) == []
    # P3 can ask for absence proofs on it (the acct63 snapshot covers account_service profiles)
    assert [p.evidence_id for p in xref_ds.absence_proofs("account_service", refs[0].resource_id, AT)] == ["evidence_05"]


def test_A_future_dated_cross_reference_rejected(xref_ds):
    assert "account_64" not in {r.resource_id for r in xref_ds.referenced_resources(A, AT)}
    later = datetime(2026, 11, 2, tzinfo=timezone.utc)
    assert "account_64" in {r.resource_id for r in xref_ds.referenced_resources(A, later)}


def test_A_unrelated_subject_cross_reference_rejected(xref_ds):
    assert "account_62" not in {r.resource_id for r in xref_ds.referenced_resources(A, AT)}
    assert [r.resource_id for r in xref_ds.referenced_resources(B, AT)] == ["account_62"]


def test_A_claim_only_cross_reference_rejected(xref_ds):
    hits = {h.resource_id: h for h in xref_ds.find_records(A, AT)}
    assert hits["search_40"].claim_only  # the claim itself is still returned
    assert "account_63" not in {r.resource_id for r in xref_ds.referenced_resources(A, AT)}
    # ...and its cross-reference is not followed into account_63's observation
    assert "account_63" not in hits


def test_A_has_observations_respects_cutoff(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("own", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [search_doc("search_10", "a@x.io", "account_61")])])
    ds.bundle("late", "2026-12-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-12-01T00:00:00Z",
              [{"resource_id": "account_61"}])])
    s = ds.scanner()
    [r] = s.referenced_resources(A, AT)
    assert r.has_observations is False
    [r] = s.referenced_resources(A, datetime(2026, 12, 2, tzinfo=timezone.utc))
    assert r.has_observations is True


def test_A_real_corpus_case_06_account_006(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "jonas.berg@outlook.com")
    refs = scanner.referenced_resources(ids, "2026-09-10T09:15:00Z")
    assert [(r.resource_id, r.source_evidence_id, r.source_field) for r in refs] == [
        ("account_006", "evidence_57", "source_resource_id")]
    # the namesakes' references in the same file (Jonas Berglund, Joana Berg) are not reported
    assert not {"account_8814", "account_4203"} & {r.resource_id for r in refs}
    assert scanner.absence_proofs("account_service", "account_006", "2026-09-10T09:15:00Z")


# ==========================================================================
# B. Identity conflict detection
# ==========================================================================
@pytest.fixture
def conflict_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("c", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [
        {"resource_id": "account_1", "email": "a@x.io", "customer_reference": "user_2"},   # conflicting
        {"resource_id": "account_2", "email": "a@x.io", "customer_reference": "user_1"},   # consistent
        {"resource_id": "account_3", "email": "a@x.io", "customer_reference": "user_2",
         "linked_resource": "search_99"},                                                   # conflicting + xref
    ])])
    ds.bundle("s", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [{"resource_id": "search_99", "document": {"email": None}}])])
    return ds.scanner()


def test_B_conflicting_email_and_user_id(conflict_ds):
    hits = {h.resource_id: h for h in conflict_ds.find_records(A, AT)}
    c = hits["account_1"]
    assert c.identity_conflict is True and not c.is_confirmed
    assert c.conflict_details == ("record references user_2, subject is user_1",)
    assert c.match_strength == STRONG and c.identifiers_matched == ["email:a@x.io"]
    # provenance and the original observation are untouched
    assert (c.evidence_id, c.locator, c.subject_reference, c.raw_state["customer_reference"]) == (
        "evidence_01", "snapshots[0].records[0]", "user_2", "user_2")
    # the stored corpus record is not mutated
    assert all(not r.identity_conflict for r in conflict_ds.records)


def test_B_conflict_seen_from_the_other_subject_too(conflict_ds):
    hits = {h.resource_id: h for h in conflict_ds.find_records(B, AT)}
    c = hits["account_1"]  # B's user_id but A's email
    assert c.identity_conflict
    assert c.conflict_details == ("record carries subject's user_id but a different email: a@x.io",)


def test_B_conflict_is_not_confirmed_for_either_subject(conflict_ds):
    for subj in (A, B):
        assert ("account_service", "account_1", None) not in conflict_ds.latest_by_resource(subj, AT)
        assert ("account_service", "account_1", None) in conflict_ds.latest_by_resource(subj, AT, include_unconfirmed=True)


def test_B_conflicting_record_does_not_seed_links(conflict_ds):
    hits = {h.resource_id for h in conflict_ds.find_records(A, AT)}
    assert "search_99" not in hits
    assert "search_99" not in {r.resource_id for r in conflict_ds.referenced_resources(A, AT)}


def test_B_correct_identity_match_without_conflict(conflict_ds):
    ok = {h.resource_id: h for h in conflict_ds.find_records(A, AT)}["account_2"]
    assert (ok.identity_conflict, ok.conflict_details, ok.match_strength, ok.is_confirmed) == ((False), (), STRONG, True)
    assert ("account_service", "account_2", None) in conflict_ds.latest_by_resource(A, AT)


def test_B_missing_information_is_not_a_conflict(conflict_ds):
    # subject without user_id: the record's reference cannot be compared
    hits = conflict_ds.find_records(SubjectIdentifiers(emails=frozenset({"a@x.io"})), AT)
    assert hits and all(not h.identity_conflict for h in hits)


def test_B_real_corpus_has_no_conflicts_for_sample_subjects(scanner, dataset_dir):
    import csv
    for row in csv.DictReader((dataset_dir / "sample_deletion_requests.csv").open(encoding="utf-8")):
        ids = identifiers_for_email(dataset_dir, row["email"])
        assert not [h for h in scanner.find_records(ids, row["audit_at"]) if h.identity_conflict], row["case_id"]


# ==========================================================================
# C. Name-only matching
# ==========================================================================
@pytest.fixture
def name_ds(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("n", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [
        {"resource_id": "account_70", "full_name": "Alex Morgan"},                          # name only
        {"resource_id": "account_71", "full_name": "Alex Morgan", "email": "a@x.io"},      # name + email
        {"resource_id": "account_72", "full_name": "Alex Morgan", "email": "namesake@x.io"},  # namesake
    ])])
    # a later de-identified copy of account_70: must not be linked through a name-only match
    ds.bundle("n2", "2026-09-02T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-02T00:00:00Z",
              [{"resource_id": "account_70", "full_name": None}])])
    return ds.scanner()


def test_C_name_only_is_weak(name_ds):
    hits = name_ds.find_records(SubjectIdentifiers(names=frozenset({"alex  MORGAN"})), AT)
    assert {h.resource_id for h in hits} == {"account_70", "account_71", "account_72"}
    assert all(h.match_strength == WEAK and not h.is_confirmed for h in hits)
    assert name_ds.latest_by_resource(SubjectIdentifiers(names=frozenset({"Alex Morgan"})), AT) == {}


def test_C_name_only_match_does_not_expand_links(name_ds):
    hits = name_ds.find_records(SubjectIdentifiers(names=frozenset({"Alex Morgan"})), AT)
    assert [h.evidence_id for h in hits if h.resource_id == "account_70"] == ["evidence_01"]  # not the n2 copy


def test_C_name_plus_email_is_strong(name_ds):
    hits = {h.resource_id: h for h in name_ds.find_records(A, AT)}
    h = hits["account_71"]
    assert h.match_strength == STRONG and h.is_confirmed
    assert h.identifiers_matched == ["email:a@x.io", "name:alex morgan"]


def test_C_shared_name_collision(name_ds):
    hits = {h.resource_id: h for h in name_ds.find_records(A, AT)}
    # the namesake's record matches on name only -> WEAK, never confirmed as A's
    assert hits["account_72"].match_strength == WEAK and not hits["account_72"].is_confirmed
    assert hits["account_70"].match_strength == WEAK
    assert set(name_ds.latest_by_resource(A, AT)) == {("account_service", "account_71", None)}
    assert {r.resource_id for r in name_ds.referenced_resources(A, AT)} == set()


def test_C_real_corpus_shared_names_are_never_strong_alone(scanner, dataset_dir):
    # three full names are shared by two users each in user_identities.csv
    for name in ("Gabriel Costa", "Thandiwe Ndlovu", "Mateo Rios"):
        hits = scanner.find_records(SubjectIdentifiers(names=frozenset({name})), "2026-12-31T00:00:00Z")
        assert all(h.match_strength == WEAK for h in hits)


def test_C_real_corpus_exact_name_still_corroborates(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "leila.haddad@yahoo.com")
    [h] = [h for h in scanner.find_records(ids, "2026-09-08T13:40:00Z") if h.resource_id == "account_005"]
    assert "name:leila haddad" in h.identifiers_matched and h.match_strength == STRONG


# ==========================================================================
# Historical identifiers, audit_at, LINKED provenance (existing behaviour)
# ==========================================================================
def test_historical_identity_is_strong(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "nadia.ionescu@yahoo.com")
    hits = [h for h in scanner.find_records(ids, "2026-09-18T12:25:00Z") if h.resource_id == "support_002"]
    assert len(hits) == 2  # contact_query_completed + deletion_marker_check in evidence_61
    for h in hits:
        assert h.match_strength == STRONG and h.is_confirmed and h.identifiers_matched == ["email:nadia.ionescu@yahoo.com"]


def test_audit_at_cutoff_applies_to_links_and_references(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "jonas.berg@outlook.com")
    # evidence_57 is captured 2026-09-10T08:45Z: before that, no reference
    assert scanner.referenced_resources(ids, "2026-09-10T08:44:59Z") == []
    assert scanner.referenced_resources(ids, "2026-09-10T08:45:00Z")


def test_linked_records_carry_provenance(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "l.fontaine46@yahoo.com", resource_ids={"analytics_9406"})
    [h] = [h for h in scanner.find_records(ids, "2026-09-26T11:00:00Z") if h.resource_id == "analytics_9406"]
    assert h.match_strength == STRONG  # matched directly by the supplied resource id
    # user_26: account_5684's identifier-less 404 read-back (evidence_92) is reached
    # from the confirmed evidence_02 snapshot row that carries the subject's email
    linked = [h for h in scanner.find_records(identifiers_for(dataset_dir, "user_26"), "2026-12-31T00:00:00Z")
              if h.match_strength == LINKED]
    [h] = [h for h in linked if h.resource_id == "account_5684"]
    assert (h.evidence_id, h.identifiers_matched, h.linked_via) == (
        "evidence_92", ["linked_resource_id:account_5684"], ("evidence_02@snapshots[0].records[0]",))
    for h in linked:
        assert h.linked_via and h.identifiers_matched[0].startswith("linked_")
        for prov in h.linked_via:
            eid, loc = prov.split("@", 1)
            assert scanner.is_valid_evidence_id(eid) and loc


# ==========================================================================
# File-name linking fix (found by B on the real corpus)
# ==========================================================================
def test_shared_backup_segment_does_not_link_users(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("b", "2026-09-01T00:00:00Z", [snap("backup_service", "backup_catalog", "2026-09-01T00:00:00Z", [
        {"resource_id": "backup_1", "archive_path": "s3://b/weekly/segment-31.tar.zst", "subject_reference": "a@x.io"},
        {"resource_id": "backup_2", "archive_path": "s3://b/weekly/segment-31.tar.zst", "subject_reference": "user_2"},
    ])])
    s = ds.scanner()
    assert {h.resource_id for h in s.find_records(A, AT)} == {"backup_1"}
    assert all(t[0] != "file_name" for r in s.records for t in r.linked_terms)


def test_attachment_file_name_still_links(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("t", "2026-09-01T00:00:00Z", [snap("support_platform", "ticket_attachments", "2026-09-01T00:00:00Z", [
        {"resource_id": "support_5", "file_name": "delivery_confirmation_77.pdf", "uploaded_by": "a@x.io"}])])
    ds.bundle("o", "2026-09-02T00:00:00Z", [snap("support_platform", "ticket_attachments", "2026-09-02T00:00:00Z", [
        {"resource_id": "support_6", "file_name": "delivery_confirmation_77.pdf"}])])
    s = ds.scanner()
    hits = {h.resource_id: h for h in s.find_records(A, AT)}
    assert hits["support_6"].match_strength == LINKED
    assert hits["support_6"].linked_via == ("evidence_01@snapshots[0].records[0]",)


def test_real_corpus_backup_segment_false_links_removed(scanner, dataset_dir):
    for uid, foreign in (("user_55", "backup_4863"), ("user_121", "backup_838"), ("user_73", "backup_161")):
        rids = {h.resource_id for h in scanner.find_records(identifiers_for(dataset_dir, uid), "2026-12-31T00:00:00Z")}
        assert foreign not in rids, uid
