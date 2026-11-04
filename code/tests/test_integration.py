"""Integration tests for evidence.integration (P1 identity bundle -> P2 findings dict).

P1's IdentityBundle / IdentityChange are represented by test-only fakes that
implement exactly the fields and the as_subject_kwargs() mapping documented in
P1's code/README_identity.md (no P1 import, no second resolver).
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from evidence import STRONG, WEAK, ResourceReference, SubjectIdentifiers
from evidence.integration import (
    CURRENT,
    HISTORICAL,
    case_audit_at,
    find_case_evidence,
    find_evidence,
    get_scanner,
    identifier_provenance,
)
from test_independent_validation import MiniDataset, snap

KEYS = ["records", "latest_by_resource", "referenced_resources", "absence_proofs", "identifier_provenance"]


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --------------------------------------------------------------------------
# Fakes mirroring P1's documented models
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FakeChange:  # P1 IdentityChange
    audit_id: str
    field_name: str
    old_value: str
    new_value: str
    event_time: str


@dataclass
class FakeIdentity:  # P1 IdentityBundle
    user_id: str
    current_email: str
    current_name: str
    current_phone: str
    current_email_hash: str
    historical_emails: list = field(default_factory=list)
    historical_phones: list = field(default_factory=list)
    historical_email_hashes: list = field(default_factory=list)
    request_email: str = ""
    history: list = field(default_factory=list)

    def all_emails(self):
        out = [self.current_email.lower()]
        out += [e.lower() for e in self.historical_emails if e.lower() not in out]
        return out

    def all_phones(self):
        return [self.current_phone] + [p for p in self.historical_phones if p != self.current_phone]

    def all_email_hashes(self):
        return [self.current_email_hash] + [h for h in self.historical_email_hashes if h != self.current_email_hash]

    def as_subject_kwargs(self):  # mapping table in README_identity.md "For P2 and P3 – adapter"
        fs = lambda vals: frozenset(v for v in vals if v and v.strip())
        return {"user_id": self.user_id or None, "emails": fs(self.all_emails()), "phones": fs(self.all_phones()),
                "email_hashes": fs(self.all_email_hashes()), "names": fs([self.current_name]),
                "resource_ids": frozenset()}


def sha(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


# case_43 exactly as printed in README_identity.md section 6
CASE_43 = FakeIdentity(
    user_id="user_41", current_email="javier.r9408@outlook.com", current_name="Javier Ríos",
    current_phone="+34 695 783 595",
    current_email_hash="5e3b9b928e5c07b78012b06e451a02a26789e1639766588b7b706b8bbecf89bd",
    historical_emails=["javier.r940897@outlook.com"],
    historical_email_hashes=["2e0aabf7d2e6c922c1d59fe49b69d3d9874d2f83ccaf826538f48e84e0ef9515"],
    request_email="javier.r940897@outlook.com",
    history=[FakeChange("audit_293", "email", "javier.r940897@outlook.com", "javier.r9408@outlook.com",
                        "2026-05-28T19:48:13Z"),
             FakeChange("audit_294", "email_hash",
                        "2e0aabf7d2e6c922c1d59fe49b69d3d9874d2f83ccaf826538f48e84e0ef9515",
                        "5e3b9b928e5c07b78012b06e451a02a26789e1639766588b7b706b8bbecf89bd",
                        "2026-05-28T19:48:13Z")])
CASE_43_AT = ts("2026-09-26T11:00:00Z")


def bundle_from_dataset(dataset_dir: Path, email: str, audit_at: datetime) -> FakeIdentity:
    """Test scaffolding: assemble a bundle with P1's documented field semantics
    (no changes after audit_at exist in this dataset, so no roll-back is needed)."""
    d = Path(dataset_dir)
    users = list(csv.DictReader((d / "user_identities.csv").open(encoding="utf-8")))
    audit = list(csv.DictReader((d / "user_audit_log.csv").open(encoding="utf-8")))
    e = email.lower()
    uid = next((u["user_id"] for u in users if u["email"].lower() == e), None) or next(
        a["user_id"] for a in audit if a["field_name"] == "email" and a["old_value"].lower() == e)
    u = next(x for x in users if x["user_id"] == uid)
    rows = sorted((a for a in audit if a["user_id"] == uid and ts(a["event_time"]) <= audit_at),
                  key=lambda a: (a["event_time"], a["audit_id"]))
    hist = [FakeChange(a["audit_id"], a["field_name"], a["old_value"], a["new_value"], a["event_time"]) for a in rows]
    h_emails = [c.old_value.lower() for c in hist if c.field_name == "email" and c.old_value]
    h_hashes = [c.old_value for c in hist if c.field_name == "email_hash" and c.old_value]
    h_hashes += [sha(x) for x in h_emails if sha(x) not in h_hashes]
    return FakeIdentity(uid, u["email"], u["name"], u["phone"], u["email_hash"], h_emails,
                        [c.old_value for c in hist if c.field_name == "phone" and c.old_value], h_hashes,
                        email, hist)


@pytest.fixture(scope="module")
def real_scanner(dataset_dir):
    return get_scanner(dataset_dir, ocr_mode="cache_only")


def case_row(dataset_dir, case_id):
    return next(r for r in csv.DictReader((dataset_dir / "sample_deletion_requests.csv").open(encoding="utf-8"))
                if r["case_id"] == case_id)


def real_case(dataset_dir, real_scanner, case_id):
    row = case_row(dataset_dir, case_id)
    at = ts(row["audit_at"])
    identity = bundle_from_dataset(dataset_dir, row["email"], at)
    return identity, at, find_evidence(identity, at, scanner=real_scanner)


# ==========================================================================
# Adapter round trip and output shape
# ==========================================================================
def test_p1_adapter_round_trip(real_scanner):
    kw = CASE_43.as_subject_kwargs()
    ids = SubjectIdentifiers(**kw)
    assert (ids.user_id, ids.emails, ids.phones, ids.names, ids.resource_ids) == (
        "user_41", frozenset({"javier.r940897@outlook.com", "javier.r9408@outlook.com"}),
        frozenset({"+34 695 783 595"}), frozenset({"Javier Ríos"}), frozenset())
    assert len(ids.email_hashes) == 2
    out = find_evidence(CASE_43, CASE_43_AT, scanner=real_scanner)
    assert list(out) == KEYS
    assert isinstance(out["records"], list) and isinstance(out["latest_by_resource"], dict)
    assert isinstance(out["referenced_resources"], list) and isinstance(out["absence_proofs"], dict)
    assert isinstance(out["identifier_provenance"], dict)


def test_scanner_results_are_passed_through_unchanged(dataset_dir, real_scanner):
    identity, at, out = real_case(dataset_dir, real_scanner, "case_11")
    ids = SubjectIdentifiers(**identity.as_subject_kwargs())
    assert out["records"] == real_scanner.find_records(ids, at)
    assert out["latest_by_resource"] == real_scanner.latest_by_resource(ids, at)
    assert out["referenced_resources"] == real_scanner.referenced_resources(ids, at)


# ==========================================================================
# Provenance
# ==========================================================================
def test_current_identifier_provenance():
    prov = identifier_provenance(CASE_43, SubjectIdentifiers(**CASE_43.as_subject_kwargs()), CASE_43_AT)
    assert prov[("email", "javier.r9408@outlook.com")] == [
        {"source": CURRENT, "audit_id": "audit_293", "event_time": ts("2026-05-28T19:48:13Z"), "basis": "history.new_value"}]
    assert prov[("email_hash", CASE_43.current_email_hash)] == [
        {"source": CURRENT, "audit_id": "audit_294", "event_time": ts("2026-05-28T19:48:13Z"), "basis": "history.new_value"}]
    snapshot = [{"source": CURRENT, "audit_id": None, "event_time": None, "basis": "snapshot"}]
    assert prov[("phone", "34695783595")] == snapshot
    assert prov[("user_id", "user_41")] == snapshot
    assert prov[("name", "javier rios")] == snapshot
    assert set(prov) == {("email", "javier.r9408@outlook.com"), ("email", "javier.r940897@outlook.com"),
                         ("email_hash", CASE_43.current_email_hash),
                         ("email_hash", CASE_43.historical_email_hashes[0]),
                         ("phone", "34695783595"), ("user_id", "user_41"), ("name", "javier rios")}


def test_historical_email_phone_and_hash_provenance():
    ident = FakeIdentity(
        user_id="user_9", current_email="new@x.io", current_name="Pat Lee", current_phone="+44 7700 900002",
        current_email_hash=sha("new@x.io"), historical_emails=["old@x.io"], historical_phones=["+44 7700 900001"],
        historical_email_hashes=[sha("old@x.io")],
        history=[FakeChange("audit_1", "phone", "+44 7700 900001", "+44 7700 900002", "2026-02-01T10:00:00Z"),
                 FakeChange("audit_2", "email", "old@x.io", "new@x.io", "2026-03-01T10:00:00Z"),
                 FakeChange("audit_3", "email_hash", sha("old@x.io"), sha("new@x.io"), "2026-03-01T10:00:00Z")])
    prov = identifier_provenance(ident, SubjectIdentifiers(**ident.as_subject_kwargs()), ts("2026-09-01T00:00:00Z"))
    hist = lambda aid, t: [{"source": HISTORICAL, "audit_id": aid, "event_time": ts(t), "basis": "history.old_value"}]
    assert prov[("phone", "447700900001")] == hist("audit_1", "2026-02-01T10:00:00Z")
    assert prov[("email", "old@x.io")] == hist("audit_2", "2026-03-01T10:00:00Z")
    assert prov[("email_hash", sha("old@x.io"))] == hist("audit_3", "2026-03-01T10:00:00Z")
    assert prov[("phone", "447700900002")][0]["audit_id"] == "audit_1"  # became current at that change


def test_case_43_historical_audit_ids_and_event_times():
    prov = identifier_provenance(CASE_43, SubjectIdentifiers(**CASE_43.as_subject_kwargs()), CASE_43_AT)
    assert prov[("email", "javier.r940897@outlook.com")] == [
        {"source": HISTORICAL, "audit_id": "audit_293", "event_time": ts("2026-05-28T19:48:13Z"),
         "basis": "history.old_value"}]
    assert prov[("email_hash", CASE_43.historical_email_hashes[0])][0]["audit_id"] == "audit_294"


def test_computed_historical_email_hash_has_no_invented_audit_id():
    ident = FakeIdentity(
        user_id="user_9", current_email="new@x.io", current_name="", current_phone="",
        current_email_hash=sha("new@x.io"), historical_emails=["old@x.io"],
        historical_email_hashes=[sha("old@x.io")],  # computed by P1: no email_hash row exists
        history=[FakeChange("audit_2", "email", "old@x.io", "new@x.io", "2026-03-01T10:00:00Z")])
    prov = identifier_provenance(ident, SubjectIdentifiers(**ident.as_subject_kwargs()), ts("2026-09-01T00:00:00Z"))
    assert prov[("email_hash", sha("old@x.io"))] == [
        {"source": HISTORICAL, "audit_id": None, "event_time": None, "basis": "computed_sha256_of_historical_email"}]
    # empty name/phone are not searched and get no provenance
    assert not any(k[0] in ("name", "phone") for k in prov)


def test_empty_event_time_is_kept_as_unknown_time():
    ident = FakeIdentity("user_9", "new@x.io", "", "", sha("new@x.io"), ["old@x.io"], [], [sha("old@x.io")], "",
                         [FakeChange("audit_2", "email", "old@x.io", "new@x.io", ""),
                          FakeChange("audit_3", "email_hash", sha("old@x.io"), sha("new@x.io"), "")])
    prov = identifier_provenance(ident, SubjectIdentifiers(**ident.as_subject_kwargs()), ts("2026-09-01T00:00:00Z"))
    assert prov[("email", "old@x.io")] == [{"source": HISTORICAL, "audit_id": "audit_2", "event_time": None,
                                            "basis": "history.old_value"}]


def test_value_both_current_and_historical_gets_two_entries():
    ident = FakeIdentity("user_9", "a@x.io", "", "", sha("a@x.io"), ["a@x.io", "b@x.io"], [], [], "",
                         [FakeChange("audit_1", "email", "a@x.io", "b@x.io", "2026-01-01T00:00:00Z"),
                          FakeChange("audit_2", "email", "b@x.io", "a@x.io", "2026-02-01T00:00:00Z")])
    ids = SubjectIdentifiers(**{**ident.as_subject_kwargs(), "email_hashes": frozenset({sha("a@x.io"), sha("b@x.io")})})
    prov = identifier_provenance(ident, ids, ts("2026-09-01T00:00:00Z"))
    assert [(e["source"], e["audit_id"]) for e in prov[("email", "a@x.io")]] == [(HISTORICAL, "audit_1"), (CURRENT, "audit_2")]


def test_historical_evidence_captured_after_identifier_change_is_kept(dataset_dir, real_scanner):
    identity, at, out = real_case(dataset_dir, real_scanner, "case_10")
    [entry] = out["identifier_provenance"][("email", "nadia.ionescu@yahoo.com")]
    assert (entry["source"], entry["audit_id"]) == (HISTORICAL, "audit_121")
    recs = [r for r in out["records"] if r.resource_id == "support_002"]
    assert recs and all(r.observed_at > entry["event_time"] for r in recs)  # seen long after the change
    assert all("email:nadia.ionescu@yahoo.com" in r.identifiers_matched for r in recs)
    assert ("support_platform", "support_002", "support_replica") in out["latest_by_resource"]


def test_history_row_after_audit_at_raises(real_scanner):
    with pytest.raises(ValueError, match="different cutoff"):
        find_evidence(CASE_43, ts("2026-05-01T00:00:00Z"), scanner=real_scanner)


def test_unexplained_identifier_raises(real_scanner):
    bad = FakeIdentity("user_9", "a@x.io", "", "", sha("a@x.io"))
    bad.as_subject_kwargs = lambda: {"user_id": "user_9", "emails": frozenset({"a@x.io", "ghost@x.io"}),
                                     "phones": frozenset(), "email_hashes": frozenset({sha("a@x.io")}),
                                     "names": frozenset(), "resource_ids": frozenset()}
    with pytest.raises(ValueError, match="not explained"):
        find_evidence(bad, CASE_43_AT, scanner=real_scanner)


# ==========================================================================
# audit_at validation and cutoffs
# ==========================================================================
@pytest.mark.parametrize("bad,exc", [
    (None, ValueError),
    (datetime(2026, 9, 26, 11, 0), ValueError),
    ("2026-09-26T11:00:00Z", TypeError),
    (1790000000, TypeError),
])
def test_audit_at_validation(real_scanner, bad, exc):
    with pytest.raises(exc):
        find_evidence(CASE_43, bad, scanner=real_scanner)


@pytest.mark.parametrize("case_id", ["case_05", "case_06", "case_10", "case_11", "case_21", "case_31"])
def test_every_output_respects_audit_at(dataset_dir, real_scanner, case_id):
    identity, at, out = real_case(dataset_dir, real_scanner, case_id)
    for r in out["records"] + list(out["latest_by_resource"].values()):
        assert r.observed_at <= at and r.captured_at <= at
        assert real_scanner.get_file(r.evidence_id).captured_at <= at
    for ref in out["referenced_resources"]:
        assert ref.source_observed_at <= at and ref.source_captured_at <= at
    for proofs in out["absence_proofs"].values():
        for p in proofs:
            assert p.captured_at <= at and real_scanner.get_file(p.evidence_id).captured_at <= at
    for entries in out["identifier_provenance"].values():
        assert all(e["event_time"] is None or e["event_time"] <= at for e in entries)


def test_equivalent_timezones_give_identical_results(dataset_dir, real_scanner):
    from datetime import timedelta
    a = find_evidence(CASE_43, CASE_43_AT, scanner=real_scanner)
    b = find_evidence(CASE_43, CASE_43_AT.astimezone(timezone(timedelta(hours=9))), scanner=real_scanner)
    assert a == b


# ==========================================================================
# Matching safeguards
# ==========================================================================
AT = ts("2026-10-01T00:00:00Z")
A = FakeIdentity("user_1", "a@x.io", "Alex Morgan", "", sha("a@x.io"))


def test_name_only_observations_remain_weak(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("n", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [
        {"resource_id": "account_70", "full_name": "Alex Morgan", "linked": "search_70"},
        {"resource_id": "account_72", "full_name": "Alex Morgan", "email": "namesake@x.io"}])])
    ds.bundle("s", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [{"resource_id": "search_70"}])])
    out = find_evidence(A, AT, scanner=ds.scanner())
    assert {r.resource_id: r.match_strength for r in out["records"]} == {"account_70": WEAK, "account_72": WEAK}
    assert out["latest_by_resource"] == {} and out["referenced_resources"] == []
    assert out["absence_proofs"] == {}  # no confirmed observation, so nothing to prove


def test_conflicting_observation_not_in_confirmed_latest(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("c", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [
        {"resource_id": "account_1", "email": "a@x.io", "customer_reference": "user_2", "linked": "search_9"},
        {"resource_id": "account_2", "email": "a@x.io", "customer_reference": "user_1"}])])
    out = find_evidence(A, AT, scanner=ds.scanner())
    recs = {r.resource_id: r for r in out["records"]}
    assert recs["account_1"].identity_conflict and recs["account_1"].match_strength == STRONG
    assert recs["account_1"].conflict_details == ("record references user_2, subject is user_1",)
    assert set(out["latest_by_resource"]) == {("account_service", "account_2", None)}
    assert "search_9" not in {r.resource_id for r in out["referenced_resources"]}
    assert ("account_service", "account_1") not in out["absence_proofs"]


def test_claim_only_distinction_and_provenance_preserved(dataset_dir, real_scanner):
    identity, at, out = real_case(dataset_dir, real_scanner, "case_11")
    claims = [r for r in out["records"] if r.claim_only]
    assert claims and all(r.evidence_id == "evidence_03" for r in claims)
    assert not any(r.claim_only for r in out["latest_by_resource"].values())
    labels = {f"{k}:{v}" for (k, v) in out["identifier_provenance"]}
    for r in out["records"]:
        assert all(m in labels or m.startswith("linked_") for m in r.identifiers_matched)
        if r.match_strength == "LINKED":
            assert r.linked_via


# ==========================================================================
# References and absence proofs
# ==========================================================================
def test_explicit_resource_reference_and_its_proofs(dataset_dir, real_scanner):
    identity, at, out = real_case(dataset_dir, real_scanner, "case_06")
    [ref] = out["referenced_resources"]
    assert (ref.resource_id, ref.source_evidence_id, ref.source_field) == ("account_006", "evidence_57", "source_resource_id")
    proofs = out["absence_proofs"][("account_service", "account_006")]
    assert {p.evidence_id for p in proofs} >= {"evidence_54", "evidence_90"}
    assert all(p.is_valid_proof for p in proofs)


def test_proofs_for_resources_found_through_confirmed_observations(dataset_dir, real_scanner):
    identity, at, out = real_case(dataset_dir, real_scanner, "case_05")
    proofs = out["absence_proofs"][("account_service", "account_005")]
    primary = [p for p in proofs if p.evidence_id == "evidence_54"]
    assert [p.replica_or_table for p in primary] == [None]  # absent from the primary, present on failover
    assert all(p.is_valid_proof for p in proofs)
    # keys come only from confirmed, authoritative records or references, deduplicated
    confirmed = {(r.system_id, r.resource_id) for r in out["records"] if r.is_confirmed and not r.claim_only}
    assert set(out["absence_proofs"]) == confirmed | {(x.system_id, x.resource_id) for x in out["referenced_resources"]}
    assert len(out["absence_proofs"]) == len({(s, r.lower()) for s, r in out["absence_proofs"]})


def test_unknown_system_id_produces_no_proof(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("s", "2026-09-01T00:00:00Z", [snap("search_service", "customer_search_documents", "2026-09-01T00:00:00Z",
              [{"resource_id": "search_1", "document": {"email": "a@x.io"}}])])
    scanner = ds.scanner()
    orphan = ResourceReference("thing_1", None, "evidence_01", "x", "search_service", "search_1", None, AT, AT, False)
    scanner.referenced_resources = lambda ids, at: [orphan]  # instance-level stub; scanner code unchanged
    out = find_evidence(A, AT, scanner=scanner)
    assert out["referenced_resources"] == [orphan]
    assert not any(rid == "thing_1" for (_, rid) in out["absence_proofs"])


def test_claim_only_references_do_not_establish_absence(tmp_path):
    ds = MiniDataset(tmp_path)
    ledger = {"exported_at": "2026-09-02T00:00:00Z", "origin": "t", "record_count": 1, "records": [
        {"recorded_at": "2026-09-02T00:00:00Z", "system": "search_service", "resource_id": "search_40",
         "record_type": "SEARCH_INDEX_ENTRY", "result": "NOT_FOUND", "subject_reference": "a@x.io",
         "source_resource_id": "account_63"}]}
    ds.add("evidence/records/ledger.json", json.dumps(ledger), "2026-09-02T00:00:00Z")
    ds.bundle("p", "2026-09-03T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-03T00:00:00Z", [])])
    out = find_evidence(A, AT, scanner=ds.scanner())
    assert [r.claim_only for r in out["records"]] == [True]
    assert out["referenced_resources"] == []
    assert out["absence_proofs"] == {}  # neither the claim's resource nor its cross-reference


def test_contradicted_proofs_are_not_returned(tmp_path):
    ds = MiniDataset(tmp_path)
    ds.bundle("old", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z",
              [{"resource_id": "account_8"}])])
    export = {"exported_at": "2026-09-05T00:00:00Z", "region": "t", "source": "t", "service_exports": {
        "account_service": {"profile_lookups": [{"observed_at": "2026-09-05T00:00:00Z", "resource_id": "account_7",
                                                 "status_code": 200, "profile": {"email": "a@x.io"}}]}}}
    ds.add("evidence/records/service_resource_export_t.json", json.dumps(export), "2026-09-05T00:00:00Z")
    scanner = ds.scanner()
    out = find_evidence(A, AT, scanner=scanner)
    # the 09-01 snapshot lacks account_7 but account_7 is PRESENT later in the same copy
    assert [p.contradicted_by for p in scanner.absence_proofs("account_service", "account_7", AT)] != [()]
    assert out["absence_proofs"][("account_service", "account_7")] == []


# ==========================================================================
# Scanner lifecycle
# ==========================================================================
def test_get_scanner_caches_per_dataset_and_ocr_mode(tmp_path, monkeypatch):
    ds = MiniDataset(tmp_path)
    ds.bundle("x", "2026-09-01T00:00:00Z", [snap("account_service", "customer_profiles", "2026-09-01T00:00:00Z", [])])
    ds.scanner()  # writes the manifest
    loads = []
    real_load = __import__("evidence.scanner", fromlist=["EvidenceScanner"]).EvidenceScanner.load
    monkeypatch.setattr("evidence.scanner.EvidenceScanner.load", lambda self: (loads.append(1), real_load(self))[1])
    a = get_scanner(ds.root, ocr_mode="cache_only")
    b = get_scanner(str(ds.root / "." / "evidence" / ".."), ocr_mode="cache_only")  # same resolved directory
    c = get_scanner(ds.root, ocr_mode="force")
    assert a is b and a is not c and len(loads) == 2
    for _ in range(5):
        find_evidence(A, AT, dataset_dir=ds.root, ocr_mode="cache_only")
    assert len(loads) == 2  # never reloaded per case


# ==========================================================================
# Case-row entry point: find_case_evidence(identity, case)
# ==========================================================================
def test_case_entry_point_accepts_a_raw_csv_row(dataset_dir, real_scanner):
    row = case_row(dataset_dir, "case_10")          # straight from csv.DictReader: audit_at is a str
    assert isinstance(row["audit_at"], str)
    identity = bundle_from_dataset(dataset_dir, row["email"], ts(row["audit_at"]))
    out = find_case_evidence(identity, row, scanner=real_scanner)
    assert list(out) == KEYS
    assert out == find_evidence(identity, ts(row["audit_at"]), scanner=real_scanner)


@pytest.mark.parametrize("value,expected", [
    ("2026-09-26T11:00:00Z", "2026-09-26T11:00:00+00:00"),
    ("2026-09-26T13:00:00+02:00", "2026-09-26T11:00:00+00:00"),
    ("2026-09-26T06:00:00-0500", "2026-09-26T11:00:00+00:00"),
    (datetime(2026, 9, 26, 11, tzinfo=timezone.utc), "2026-09-26T11:00:00+00:00"),
])
def test_case_audit_at_valid_forms(value, expected):
    got = case_audit_at({"case_id": "case_x", "audit_at": value})
    assert got.isoformat() == expected and got.tzinfo is not None


@pytest.mark.parametrize("case,exc", [
    ({"case_id": "c"}, ValueError),                                     # missing key
    ({"case_id": "c", "audit_at": None}, ValueError),                   # missing value
    ({"case_id": "c", "audit_at": "   "}, ValueError),                  # empty string
    ({"case_id": "c", "audit_at": "2026-09-26T11:00:00"}, ValueError),  # no offset
    ({"case_id": "c", "audit_at": "2026-09-26"}, ValueError),           # date only
    ({"case_id": "c", "audit_at": "not a dateZ"}, ValueError),          # offset-looking garbage
    ({"case_id": "c", "audit_at": datetime(2026, 9, 26, 11)}, ValueError),  # naive datetime
    ({"case_id": "c", "audit_at": 1790000000}, TypeError),              # epoch int
    ({"case_id": "c", "audit_at": 1790000000.0}, TypeError),
    (["2026-09-26T11:00:00Z"], TypeError),                              # not a mapping
])
def test_case_audit_at_rejections(real_scanner, case, exc):
    with pytest.raises(exc):
        case_audit_at(case)
    with pytest.raises(exc):
        find_case_evidence(CASE_43, case, scanner=real_scanner)


def test_case_entry_point_keeps_history_cutoff_check(real_scanner):
    # CASE_43's history rows are 2026-05-28; a case cut off before that is a mismatched bundle
    with pytest.raises(ValueError, match="different cutoff"):
        find_case_evidence(CASE_43, {"case_id": "case_43", "audit_at": "2026-05-01T00:00:00Z"}, scanner=real_scanner)


def test_case_entry_point_on_every_sample_row(dataset_dir, real_scanner):
    for row in csv.DictReader((dataset_dir / "sample_deletion_requests.csv").open(encoding="utf-8")):
        identity = bundle_from_dataset(dataset_dir, row["email"], ts(row["audit_at"]))
        out = find_case_evidence(identity, row, scanner=real_scanner)
        at = ts(row["audit_at"])
        assert list(out) == KEYS
        assert all(r.observed_at <= at and r.captured_at <= at for r in out["records"])
        assert all(r.is_confirmed and not r.claim_only for r in out["latest_by_resource"].values())
        assert all(p.is_valid_proof for ps in out["absence_proofs"].values() for p in ps)
