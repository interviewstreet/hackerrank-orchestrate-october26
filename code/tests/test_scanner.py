"""Integration tests for the public EvidenceScanner API."""

import csv
from datetime import datetime, timezone

import pytest

from evidence import ABSENT, PRESENT, EvidenceScanner, SubjectIdentifiers
from identity_helper import identifiers_for, identifiers_for_email


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ------------------------------------------------------------------ corpus
def test_full_corpus_scan(scanner):
    s = scanner.summary()
    assert s["manifest_entries"] == 94
    assert s["files_parsed_without_error"] == 94
    assert s["missing_on_disk"] == [] and s["unlisted_on_disk"] == []
    assert s["issues_by_severity"] == {}
    assert set(s["observations_by_extension"]) == {"json", "sql", "log", "pdf", "png", "txt"}
    assert s["observations"] > 2500


def test_load_is_idempotent(scanner):
    n = len(scanner.records)
    scanner.load()
    assert len(scanner.records) == n


def test_query_before_load_raises(dataset_dir):
    with pytest.raises(RuntimeError):
        EvidenceScanner(dataset_dir).find_for_subject(SubjectIdentifiers(), "2026-09-01T00:00:00Z")


def test_files_and_get_file(scanner):
    assert len(scanner.files()) == 94
    f = scanner.get_file("evidence_94")
    assert f.file_path.endswith("resource_lookup_trace_20260926_103856.log")
    with pytest.raises(KeyError):
        scanner.get_file("evidence_95")


def test_every_cited_evidence_id_is_valid(scanner):
    valid = {f.file_id for f in scanner.files()}
    assert {r.evidence_id for r in scanner.records} <= valid
    assert {s.evidence_id for s in scanner.scopes} <= valid


def test_sample_output_evidence_ids_exist(scanner, dataset_dir):
    import json
    for row in csv.DictReader((dataset_dir / "sample_output.csv").open(encoding="utf-8")):
        for step in json.loads(row["steps_json"]):
            if step["evidence_id"]:
                assert scanner.is_valid_evidence_id(step["evidence_id"])


# ----------------------------------------------------------- replica drift
def test_replica_drift_account_005(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "leila.haddad@yahoo.com")
    latest = scanner.latest_by_resource(ids, "2026-09-08T13:40:00Z")
    key = ("account_service", "account_005", "customer_profiles_failover_replica")
    assert latest[key].presence == PRESENT and latest[key].evidence_id == "evidence_54"
    assert ("account_service", "account_005", None) not in latest  # primary copy not observed
    proofs = scanner.absence_proofs("account_service", "account_005", "2026-09-08T13:40:00Z")
    primary = [p for p in proofs if p.evidence_id == "evidence_54"]
    assert [p.replica_or_table for p in primary] == [None]  # absent only from the primary table


def test_absence_proof_for_resource_with_no_identifiers(scanner):
    # case_01: account_001 is linked to the subject only via system_activity.
    proofs = scanner.absence_proofs("account_service", "account_001", "2026-09-03T11:30:00Z")
    assert {p.evidence_id for p in proofs} >= {"evidence_54"}
    # an empty collection snapshot is also proof (case_31, evidence_51)
    proofs = scanner.absence_proofs("account_service", "account_4857", "2026-09-15T12:00:00Z")
    assert "evidence_51" in {p.evidence_id for p in proofs}


def test_absence_proofs_respect_category(scanner):
    # support_001 is an attachment; support *message* tables are not proof of its absence
    proofs = scanner.absence_proofs("support_platform", "support_001", "2026-09-12T08:00:00Z")
    assert all(p.data_category in (None, "SUPPORT_ATTACHMENT") for p in proofs)


def test_present_resource_has_no_absence_proof_from_its_own_snapshot(scanner):
    proofs = scanner.absence_proofs("account_service", "account_8741", "2026-09-03T00:00:00Z")
    assert "evidence_54" not in {p.evidence_id for p in proofs}


# --------------------------------------------- identifiers and false positives
def test_historical_email_finds_records(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "nadia.ionescu@yahoo.com")  # historical address of user_10
    assert ids.user_id == "user_10" and len(ids.emails) > 1
    hits = scanner.find_for_subject(ids, "2026-09-18T12:25:00Z")
    sup = [h for h in hits if h.resource_id == "support_002"]
    assert sup and sup[0].replica_or_table == "support_replica" and sup[0].evidence_id == "evidence_61"
    # decoy: nadia.popescu@yahoo.com (support_5914) in the same file
    assert "support_5914" not in {h.resource_id for h in hits}


def test_mixed_case_emails_match(scanner):
    ids = SubjectIdentifiers(emails=frozenset({"choi.jihoon94@gmail.com"}))
    hits = scanner.find_for_subject(ids, "2026-10-01T12:00:00Z")
    got = {(h.evidence_id, h.resource_id) for h in hits}
    assert ("evidence_03", "account_1810") in got  # written CHOI.JIHOON94@GMAIL.COM
    upper = SubjectIdentifiers(emails=frozenset({"CHOI.JIHOON94@GMAIL.COM"}))
    assert {(h.evidence_id, h.resource_id) for h in scanner.find_for_subject(upper, "2026-10-01T12:00:00Z")} == got


def test_similar_names_are_not_matched(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "jonas.berg@outlook.com")
    hits = scanner.find_for_subject(ids, "2026-09-10T09:15:00Z")
    rids = {h.resource_id for h in hits}
    assert "search_001" in rids
    assert "search_8814" not in rids  # Jonas Berglund
    assert "search_4203" not in rids  # Joana Berg


def test_similar_person_decoys_excluded(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "priya.raman@gmail.com")
    rids = {h.resource_id for h in scanner.find_for_subject(ids, "2026-09-12T08:00:00Z")}
    assert "support_001" in rids
    assert "account_7204" not in rids  # Priya Ramanathan


def test_name_matching_is_exact_only(scanner):
    hits = scanner.find_for_subject(SubjectIdentifiers(names=frozenset({"Jonas"})), "2026-12-31T00:00:00Z")
    assert hits == []


def test_user_id_matching_is_exact(scanner):
    # user_05 must not match user_052 / user_5xx
    hits = scanner.find_for_subject(SubjectIdentifiers(user_id="user_05"), "2026-12-31T00:00:00Z")
    assert hits and all("user_id:user_05" in h.identifiers_matched for h in hits)


def test_email_hash_matching(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "minjun.kim@gmail.com")
    hits = scanner.find_for_subject(ids, "2026-09-15T12:00:00Z")
    a = [h for h in hits if h.resource_id == "analytics_9914"]
    assert a and a[0].evidence_id == "evidence_01" and any(m.startswith("email_hash:") for m in a[0].identifiers_matched)


def test_resource_id_linking_reaches_deidentified_copies(scanner, dataset_dir):
    # analytics_9406 carries no identifiers; the auditor supplies it from system_activity.
    ids = identifiers_for_email(dataset_dir, "l.fontaine46@yahoo.com", resource_ids={"analytics_9406"})
    latest = scanner.latest_by_resource(ids, "2026-09-26T11:00:00Z")
    rec = latest[("analytics_platform", "analytics_9406", None)]
    assert rec.evidence_id == "evidence_94" and rec.presence == PRESENT and rec.pii_fields == {}


def test_pdf_and_png_are_found_for_subject(scanner, dataset_dir):
    hits = scanner.find_for_subject(identifiers_for_email(dataset_dir, "priya.raman@gmail.com"), "2026-09-12T08:00:00Z")
    assert ("evidence_58", "support_001") in {(h.evidence_id, h.resource_id) for h in hits}
    hits = scanner.find_for_subject(identifiers_for(dataset_dir, "user_17"), "2026-03-11T00:00:00Z")
    assert "evidence_42" in {h.evidence_id for h in hits}


# -------------------------------------------------------------- time cutoffs
def test_evidence_captured_after_audit_at_is_excluded(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "leila.haddad@yahoo.com")
    before = scanner.find_for_subject(ids, "2026-09-02T22:59:59Z")
    assert "evidence_54" not in {h.evidence_id for h in before}
    after = scanner.find_for_subject(ids, "2026-09-02T23:00:00Z")  # inclusive cutoff
    assert "evidence_54" in {h.evidence_id for h in after}
    assert "evidence_54" not in {p.evidence_id for p in scanner.absence_proofs("account_service", "account_001", "2026-09-02T22:00:00Z")}


def test_no_returned_record_is_after_audit_at(scanner, dataset_dir):
    audit_at = utc("2026-09-15T12:00:00Z")
    for email in ("lucia-torres@gmail.com", "e.varga90@yahoo.com", "minjun.kim@gmail.com"):
        for h in scanner.find_for_subject(identifiers_for_email(dataset_dir, email), audit_at):
            assert h.observed_at <= audit_at and h.captured_at <= audit_at
            assert scanner.get_file(h.evidence_id).captured_at <= audit_at


def test_observation_after_audit_at_inside_earlier_file(scanner):
    # evidence_13 is captured 2026-08-12, but records[38] (account_1417) is recorded 2026-08-14.
    ids = SubjectIdentifiers(resource_ids=frozenset({"account_1417"}))
    hits = scanner.find_for_subject(ids, "2026-08-13T00:00:00Z")
    assert all(h.observed_at <= utc("2026-08-13T00:00:00Z") for h in hits)
    assert ("evidence_13", "records[38]") not in {(h.evidence_id, h.locator) for h in hits}
    hits = scanner.find_for_subject(ids, "2026-08-15T00:00:00Z")
    assert ("evidence_13", "records[38]") in {(h.evidence_id, h.locator) for h in hits}


def test_line_after_audit_at_in_synthetic_log(tmp_path):
    ds = tmp_path / "dataset"
    (ds / "evidence/logs").mkdir(parents=True)
    (ds / "evidence/logs/service_events_test.log").write_text(
        "2026-09-01T10:00:00Z level=INFO service=account_service trace_id=t1 event=profile_lookup_started lookup_key=a@b.io\n"
        "2026-09-01T10:00:01Z level=INFO service=account_service trace_id=t1 resource_id=account_9 event=profile_lookup_completed rows=1 http_status=200\n"
        "2026-09-03T10:00:00Z level=INFO service=account_service trace_id=t2 event=profile_lookup_started lookup_key=a@b.io\n"
        "2026-09-03T10:00:01Z level=INFO service=account_service trace_id=t2 resource_id=account_9 event=profile_lookup_completed rows=0 http_status=404\n",
        encoding="utf-8")
    (ds / "evidence_files.csv").write_text(
        "file_id,file_path,origin,captured_at\nevidence_01,evidence/logs/service_events_test.log,test,2026-09-01T12:00:00Z\n",
        encoding="utf-8")
    s = EvidenceScanner(ds)
    s.load()
    ids = SubjectIdentifiers(emails=frozenset({"A@B.io"}))
    # file captured 09-01 but contains a later line; with audit_at 09-02 only the 09-01 line counts
    latest = s.latest_by_resource(ids, "2026-09-02T00:00:00Z")
    assert latest[("account_service", "account_9", None)].presence == PRESENT
    latest = s.latest_by_resource(ids, "2026-09-04T00:00:00Z")
    assert latest[("account_service", "account_9", None)].presence == ABSENT


# --------------------------------------------------------- multiple observations
def test_multiple_observations_latest_wins(scanner):
    # evidence_08: account_8473 FOUND on 2026-08-31, NOT_FOUND on 2026-09-06
    ids = SubjectIdentifiers(emails=frozenset({"marek.zielinski@gmail.com"}))
    hits = [h for h in scanner.find_for_subject(ids, "2026-09-30T00:00:00Z") if h.resource_id == "account_8473"]
    assert len(hits) >= 2
    key = ("account_service", "account_8473", None)
    # evidence_08 is a lookup ledger (claim_only): not authoritative, so not in latest_by_resource...
    assert all(h.claim_only for h in hits)
    assert key not in scanner.latest_by_resource(ids, "2026-09-30T00:00:00Z")
    # ...but both conflicting claims stay available, and include_claims picks the newest
    found = [h for h in hits if h.evidence_id == "evidence_08"]
    assert {h.presence for h in found} == {PRESENT, ABSENT}
    assert scanner.latest_by_resource(ids, "2026-09-30T00:00:00Z", include_claims=True)[key].presence == ABSENT
    # evidence_08 is captured 2026-09-06: before that even its 08-31 line is unavailable
    assert key not in scanner.latest_by_resource(ids, "2026-09-01T00:00:00Z", include_claims=True)


def test_latest_by_resource_keys_are_unique_and_sorted(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "novak.tomasz@icloud.com")
    for include_claims in (False, True):
        latest = scanner.latest_by_resource(ids, "2026-10-01T12:00:00Z", include_claims=include_claims)
        assert list(latest) == sorted(latest, key=lambda k: (k[0], k[1], k[2] or ""))
        for k, r in latest.items():
            assert k == (r.system_id, r.resource_id, r.replica_or_table)
            assert include_claims or not r.claim_only
    # case_11's findings come only from the evidence_03 handover (claim-only):
    wanted = {"search_052", "analytics_2034", "support_864", "data_flow_9522"}
    assert wanted.isdisjoint({k[1] for k in scanner.latest_by_resource(ids, "2026-10-01T12:00:00Z")})
    assert wanted <= {k[1] for k in scanner.latest_by_resource(ids, "2026-10-01T12:00:00Z", include_claims=True)}
    assert wanted <= {h.resource_id for h in scanner.find_records(ids, "2026-10-01T12:00:00Z") if h.claim_only}


def test_retained_records_are_not_dropped(scanner, dataset_dir):
    ids = identifiers_for(dataset_dir, "user_21")
    hits = scanner.find_for_subject(ids, "2026-09-15T12:00:00Z")
    cats = {h.data_category for h in hits}
    assert {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"} <= cats


def test_results_are_deterministic(scanner, dataset_dir):
    ids = identifiers_for_email(dataset_dir, "e.varga90@yahoo.com")
    a = [(h.evidence_id, h.locator, h.resource_id) for h in scanner.find_for_subject(ids, "2026-09-15T12:00:00Z")]
    b = [(h.evidence_id, h.locator, h.resource_id) for h in scanner.find_for_subject(ids, "2026-09-15T12:00:00Z")]
    assert a == b and a


def test_returned_records_are_copies(scanner):
    ids = SubjectIdentifiers(emails=frozenset({"leila.haddad@yahoo.com"}))
    h = scanner.find_for_subject(ids, "2026-09-08T13:40:00Z")[0]
    h.identifiers_matched.append("mutated")
    assert all("mutated" not in r.identifiers_matched for r in scanner.records)


def test_sample_cases_surface_cited_findings(scanner, dataset_dir):
    """Each FINDING in sample_output.csv must be discoverable from the subject's
    identifiers (or from a cited resource id) in the cited evidence file."""
    import json
    reqs = {r["case_id"]: r for r in csv.DictReader((dataset_dir / "sample_deletion_requests.csv").open(encoding="utf-8"))}
    missing = []
    for row in csv.DictReader((dataset_dir / "sample_output.csv").open(encoding="utf-8")):
        req = reqs[row["case_id"]]
        steps = [s for s in json.loads(row["steps_json"]) if s["phase"] == "FINDING"]
        if not steps:
            continue
        ids = identifiers_for_email(dataset_dir, req["email"])
        hits = {(h.evidence_id, h.resource_id) for h in scanner.find_for_subject(ids, req["audit_at"])}
        for s in steps:
            if (s["evidence_id"], s["resource_id"]) not in hits:
                missing.append((row["case_id"], s["resource_id"], s["evidence_id"]))
    assert missing == []
