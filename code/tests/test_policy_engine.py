"""P3 tests: deletion policy and evidence validation (policy_engine, rules,
activity, step_builder).

Most tests build an isolated world in tmp_path: P2's MiniDataset writes real
evidence files that the production scanner parses, plus test identity,
audit-log and activity CSVs and a copy of the real deletion_rules.csv.
Synthetic ObservedRecords are used where a category has no evidence format
in the corpus (cache entries, email delivery logs, telemetry, ...).
"""
from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from evidence import ABSENT, PRESENT, ObservedRecord
from identity_resolver import IdentityResolver
from policy_engine import PolicyContext, decide
from rules import RuleBook, RecordFacts
from step_builder import build_steps
from test_independent_validation import BLOB_TABLE, SQL_HEADER, MiniDataset, blob_insert, snap

REAL_DATASET = Path(__file__).resolve().parents[2] / "dataset"
UTC = timezone.utc
EMAIL = "ana.subject@example.org"
OLD_EMAIL = "ana.old@example.org"
UID = "user_900"
REQ, REP, AUDIT = "2026-09-01T10:00:00Z", "2026-09-02T12:00:00Z", "2026-09-10T12:00:00Z"


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def sha(e: str) -> str:
    return hashlib.sha256(e.encode()).hexdigest()


# --------------------------------------------------------------------------
# isolated world
# --------------------------------------------------------------------------
class World:
    def __init__(self, tmp_path: Path):
        self.ds = MiniDataset(tmp_path)
        self.root = self.ds.root
        shutil.copy(REAL_DATASET / "deletion_rules.csv", self.root / "deletion_rules.csv")
        self.users = [
            {"user_id": UID, "name": "Ana Subject", "email": EMAIL, "phone": "+44 7700 900111",
             "email_hash": sha(EMAIL), "updated_at": "2026-08-01T00:00:00Z"},
            {"user_id": "user_901", "name": "Ana Subject", "email": "other.ana@example.org",
             "phone": "+44 7700 900222", "email_hash": sha("other.ana@example.org"),
             "updated_at": "2026-08-01T00:00:00Z"},
        ]
        self.audit = []
        self.activity = []
        self._ctx = None

    def change_email(self, old: str, new: str, at: str, uid: str = UID):
        n = len(self.audit) + 1
        self.audit.append({"audit_id": f"audit_{n:02d}", "user_id": uid, "event_time": at,
                           "field_name": "email", "old_value": old, "new_value": new})

    def act(self, at, etype, src, tgt, rid, result, details):
        n = len(self.activity) + 1
        aid = f"activity_{n:02d}"
        self.activity.append({"activity_id": aid, "event_time": at, "event_type": etype, "source_system": src,
                              "target_system": tgt, "resource_id": rid, "reported_result": result,
                              "details": details})
        return aid

    def _write(self, name, rows, fields):
        with (self.root / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def context(self) -> PolicyContext:
        if self._ctx is None:
            self._write("user_identities.csv", self.users,
                        ["user_id", "name", "email", "phone", "email_hash", "updated_at"])
            self._write("user_audit_log.csv", self.audit,
                        ["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"])
            self._write("system_activity.csv", self.activity,
                        ["activity_id", "event_time", "event_type", "source_system", "target_system",
                         "resource_id", "reported_result", "details"])
            self._ctx = PolicyContext(self.root, scanner=self.ds.scanner(), request_files=())
        return self._ctx

    def decide(self, records=(), *, email=EMAIL, requested=REQ, reported=REP, audit=AUDIT,
               text="Please delete my account.", case_id="case_t"):
        ctx = self.context()
        case = {"case_id": case_id, "email": email, "requested_at": requested, "reported_status": "COMPLETE",
                "reported_at": reported, "audit_at": audit, "request_text": text}
        identity = ctx.resolver.resolve(email, audit_at=ts(audit), requested_at=ts(requested), case_id=case_id)
        assert identity is not None
        return decide(identity, list(records), case, context=ctx)


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def obs(rid, system, category, *, presence=PRESENT, at="2026-09-05T10:00:00Z", ev="evidence_01",
        pii=None, raw=None, claim=False, replica=None, matched=None, captured=None, collection=None):
    raw = dict(raw or {})
    raw.setdefault("resource_id", rid)
    return ObservedRecord(
        evidence_id=ev, system_id=system, resource_id=rid, data_category=category, collection=collection,
        replica_or_table=replica, observed_at=ts(at), captured_at=ts(captured or at), presence=presence,
        pii_fields=dict(pii or {}), identifiers_matched=list(matched or [f"email:{EMAIL}"]), raw_state=raw,
        claim_only=claim, source_format="json", locator=f"{rid}@{at}",
        linked_terms=frozenset({("resource_id", rid.lower())}))


def ops(decision):
    return [(s["system_id"], s["resource_id"], s["operation"], s["evidence_id"])
            for k in ("findings", "remediation", "verification") for s in decision[k]]


def by_res(decision, rid):
    return [(k, s["operation"], s["evidence_id"]) for k in ("findings", "remediation", "verification")
            for s in decision[k] if s["resource_id"] == rid]


# ==========================================================================
# Rule book: loaded from the real CSV, never hard-coded
# ==========================================================================
def test_rulebook_loads_all_15_rules_from_csv():
    book = RuleBook.load(REAL_DATASET / "deletion_rules.csv")
    with open(REAL_DATASET / "deletion_rules.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(book.rules) == len(rows) == 15
    for r, rule in zip(rows, book.rules):
        assert (rule.rule_id, rule.data_category, rule.required_action, rule.condition) == \
               (r["rule_id"], r["data_category"], r["required_action"], r["condition"])


def test_rulebook_follows_csv_action_changes(tmp_path):
    rows = list(csv.DictReader(open(REAL_DATASET / "deletion_rules.csv", newline="", encoding="utf-8")))
    for r in rows:
        if r["data_category"] == "CACHE_ENTRY":
            r["required_action"] = "RETAIN"
    p = tmp_path / "rules.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert RuleBook.load(p).apply(RecordFacts(category="CACHE_ENTRY")).action == "RETAIN"


def test_rulebook_rejects_unknown_condition(tmp_path):
    p = tmp_path / "rules.csv"
    p.write_text("rule_id,data_category,condition,required_action\nrule_x,USER_PROFILE,When the moon is full,DELETE\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="unrecognised"):
        RuleBook.load(p)


# expected (finding, remediation, verification) for a non-compliant record of each category
NONCOMPLIANT = [
    ("rule_01", "account_1", "account_service", "USER_PROFILE", {"email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_02", "secondary_1", "identity_service", "SECONDARY_IDENTIFIER", {"email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_03", "search_1", "search_service", "SEARCH_INDEX_ENTRY", {"email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_04", "cache_1", "cache_service", "CACHE_ENTRY", {"email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_05", "support_1", "support_platform", "SUPPORT_MESSAGE", {"requester_email": EMAIL},
     {"message_excerpt": "Customer asked about order ORD-1 with agent Maya."},
     "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
    ("rule_06", "support_2", "support_platform", "SUPPORT_ATTACHMENT", {"uploaded_by": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_07", "analytics_1", "analytics_platform", "ANALYTICS_PROFILE", {"email": EMAIL}, {},
     "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
    ("rule_08", "telemetry_1", "telemetry_service", "PRODUCT_TELEMETRY", {}, {"user_id": UID},
     "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
    ("rule_09", "export_1", "export_service", "USER_EXPORT", {"owner_email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_10", "marketing_1", "marketing_platform", "MARKETING_PROFILE", {"email": EMAIL}, {},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    ("rule_11", "email_delivery_1", "email_delivery_service", "EMAIL_DELIVERY_LOG", {"recipient_email": EMAIL}, {},
     "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
    ("rule_12", "audit_record_1", "security_service", "SECURITY_AUDIT_LOG", {},
     {"retention_until": "2020-01-01T00:00:00Z", "subject_reference": UID},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),   # retention expired
    ("rule_13", "legal_hold_1", "legal_service", "LEGAL_HOLD_RECORD", {},
     {"retained_until": "01 Jan 2020", "subject_reference": UID},
     "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),   # hold expired
    ("rule_14", "backup_1", "backup_service", "BACKUP_ARCHIVE", {}, {"restore_allowed": True},
     "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"),
    ("rule_15", "tombstone_1", "identity_service", "ACCOUNT_TOMBSTONE", {"name": "Ana Subject", "email": EMAIL},
     {"account_status": "DELETED", "subject_reference": UID},
     "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
]


@pytest.mark.parametrize("rule_id,rid,system,cat,pii,raw,finding,remediation,verification", NONCOMPLIANT,
                         ids=[r[0] for r in NONCOMPLIANT])
def test_each_rule_noncompliant_record(world, rule_id, rid, system, cat, pii, raw, finding, remediation, verification):
    d = world.decide([obs(rid, system, cat, pii=pii, raw=raw)])
    assert d["deletion_status"] == "INCOMPLETE"
    assert by_res(d, rid) == [("findings", finding, "evidence_01"), ("remediation", remediation, ""),
                              ("verification", verification, "")]
    assert next(r for r in d["resources"] if r["resource_id"] == rid)["rule_id"] == rule_id


# compliant counterparts: the case is COMPLETE and the step cites the proving evidence
COMPLIANT = [
    ("rule_05", "support_1", "support_platform", "SUPPORT_MESSAGE", {},
     {"message_excerpt": "Customer asked about an order.", "customer_reference": UID}, "VERIFY_RECORD_REDACTED"),
    ("rule_07", "analytics_1", "analytics_platform", "ANALYTICS_PROFILE", {},
     {"email": None, "customer_reference": None}, "VERIFY_RECORD_ANONYMIZED"),
    ("rule_08", "telemetry_1", "telemetry_service", "PRODUCT_TELEMETRY", {}, {}, "VERIFY_RECORD_ANONYMIZED"),
    ("rule_11", "email_delivery_1", "email_delivery_service", "EMAIL_DELIVERY_LOG", {}, {}, "VERIFY_RECORD_REDACTED"),
    ("rule_12", "audit_record_1", "security_service", "SECURITY_AUDIT_LOG", {},
     {"retention_until": "2034-09-30T23:59:59Z", "subject_reference": UID}, "VERIFY_RECORD_PRESENT"),
    ("rule_13", "legal_hold_1", "legal_service", "LEGAL_HOLD_RECORD", {},
     {"retained_until": "04 May 2033", "subject_reference": UID}, "VERIFY_RECORD_PRESENT"),
    ("rule_14", "backup_1", "backup_service", "BACKUP_ARCHIVE", {}, {"restore_allowed": False}, "VERIFY_RESTORE_BLOCKED"),
    ("rule_15", "tombstone_1", "identity_service", "ACCOUNT_TOMBSTONE", {},
     {"account_status": "DELETED", "subject_reference": UID, "name": None, "email": None}, "VERIFY_RECORD_REDACTED"),
]


@pytest.mark.parametrize("rule_id,rid,system,cat,pii,raw,verification", COMPLIANT, ids=[r[0] for r in COMPLIANT])
def test_each_rule_compliant_record(world, rule_id, rid, system, cat, pii, raw, verification):
    d = world.decide([obs(rid, system, cat, pii=pii, raw=raw, matched=[f"user_id:{UID}"])])
    assert d["deletion_status"] == "COMPLETE"
    assert by_res(d, rid) == [("verification", verification, "evidence_01")]


# ==========================================================================
# condition-specific behaviour
# ==========================================================================
def test_support_message_without_shared_context_is_deleted(world):
    d = world.decide([obs("support_7", "support_platform", "SUPPORT_MESSAGE", raw={"rows": "1"})])
    assert [o for _, _, o, _ in ops(d)] == ["REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"]


def test_support_message_shared_context_from_request_text(world):
    r = obs("support_7", "support_platform", "SUPPORT_MESSAGE", pii={"matched_value": EMAIL}, raw={"rows": "1"})
    d = world.decide([r], text="Some of those messages also relate to another customer, so keep the conversation.")
    assert [o for _, _, o, _ in ops(d)] == ["REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"]


def test_shared_support_attachment_is_redacted_not_deleted():
    book = RuleBook.load(REAL_DATASET / "deletion_rules.csv")
    assert book.apply(RecordFacts(category="SUPPORT_ATTACHMENT", subject_only=True)).action == "DELETE"
    assert book.apply(RecordFacts(category="SUPPORT_ATTACHMENT", subject_only=False)).action == "REDACT"


def test_analytics_attributable_by_user_reference_only(world):
    d = world.decide([obs("analytics_2", "analytics_platform", "ANALYTICS_PROFILE", raw={"user_id": UID},
                          matched=[f"user_id:{UID}"])])
    assert by_res(d, "analytics_2")[0] == ("findings", "REPORT_EXPOSED_PII", "evidence_01")


def test_email_log_redaction_requires_email(world):
    book = RuleBook.load(REAL_DATASET / "deletion_rules.csv")
    assert book.apply(RecordFacts(category="EMAIL_DELIVERY_LOG", has_email=True)).action == "REDACT"
    assert book.apply(RecordFacts(category="EMAIL_DELIVERY_LOG", has_email=False)).action == "NONE"


def test_tombstone_with_empty_pii_is_still_present_not_deleted(world):
    d = world.decide([obs("tombstone_5", "identity_service", "ACCOUNT_TOMBSTONE",
                          raw={"account_status": "DELETED", "subject_reference": UID}, matched=[f"user_id:{UID}"])])
    assert d["deletion_status"] == "COMPLETE"
    # kept and verified redacted -- never treated as absent / deleted
    assert by_res(d, "tombstone_5") == [("verification", "VERIFY_RECORD_REDACTED", "evidence_01")]


def test_correctly_retained_records_are_not_failures(world):
    d = world.decide([
        obs("audit_record_9", "security_service", "SECURITY_AUDIT_LOG",
            raw={"retention_until": "2033-12-31T23:59:59Z"}, matched=[f"user_id:{UID}"]),
        obs("legal_hold_9", "legal_service", "LEGAL_HOLD_RECORD", raw={"retained_until": "2033-05-04"},
            matched=[f"user_id:{UID}"], ev="evidence_02"),
    ])
    assert d["deletion_status"] == "COMPLETE" and not d["findings"]
    assert [s["operation"] for s in d["verification"]] == ["VERIFY_RECORD_PRESENT", "VERIFY_RECORD_PRESENT"]


# ==========================================================================
# identity validation
# ==========================================================================
def test_historical_email_matches_evidence(world):
    world.change_email(OLD_EMAIL, EMAIL, "2026-05-01T00:00:00Z")
    world.ds.bundle("b1", "2026-09-05T00:00:00Z", [snap("search_service", "customer_search_documents",
                    "2026-09-05T00:00:00Z", [{"resource_id": "search_77", "email": OLD_EMAIL}])])
    d = world.decide()
    assert by_res(d, "search_77")[0] == ("findings", "REPORT_REMAINING_RECORD", "evidence_01")
    assert d["identity"]["history_audit_ids"] == ["audit_01"]


def test_identity_change_after_audit_at_is_not_used(world):
    later = "ana.later@example.org"
    world.change_email(EMAIL, later, "2026-12-01T00:00:00Z")   # after AUDIT
    world.users[0]["email"] = later
    world.ds.bundle("b1", "2026-09-05T00:00:00Z", [snap("search_service", "customer_search_documents",
                    "2026-09-05T00:00:00Z", [{"resource_id": "search_78", "email": later}])])
    d = world.decide()
    assert not by_res(d, "search_78")
    assert d["identity"]["history_audit_ids"] == []


def test_name_only_match_is_weak(world):
    named = obs("search_5", "search_service", "SEARCH_INDEX_ENTRY", pii={"display_name": "Ana Subject"},
                matched=["name:ana subject"])
    d = world.decide([named])
    assert not by_res(d, "search_5")
    assert any("name-only" in n for n in d["notes"])


def test_name_match_confirmed_by_user_reference_is_kept(world):
    named = obs("search_5", "search_service", "SEARCH_INDEX_ENTRY", pii={"display_name": "Ana Subject"},
                raw={"customer_reference": UID}, matched=["name:ana subject"])
    assert by_res(world.decide([named]), "search_5")


def test_record_of_another_user_is_ignored(world):
    other = dataclasses.replace(obs("search_6", "search_service", "SEARCH_INDEX_ENTRY",
                                    matched=[f"email:{EMAIL}"]), subject_reference="user_901")
    d = world.decide([other])
    assert not by_res(d, "search_6")


# ==========================================================================
# evidence validation
# ==========================================================================
def test_claim_only_found_is_a_finding_citing_the_claim(world):
    d = world.decide([obs("search_8", "search_service", "SEARCH_INDEX_ENTRY", claim=True, ev="evidence_03",
                          raw={"result": "FOUND"})])
    assert by_res(d, "search_8")[0] == ("findings", "REPORT_REMAINING_RECORD", "evidence_03")


def test_claim_only_not_found_does_not_prove_absence(world):
    d = world.decide([obs("account_8", "account_service", "USER_PROFILE", presence=ABSENT, claim=True,
                          ev="evidence_03", raw={"result": "NOT_FOUND"})])
    assert d["deletion_status"] == "COMPLETE"
    assert not d["verification"]          # nothing may cite the claim as proof
    assert d["unverified"] and d["unverified"][0]["resource_id"] == "account_8"


def test_claim_never_overrides_authoritative_store_state(world):
    d = world.decide([
        obs("search_9", "search_service", "SEARCH_INDEX_ENTRY", presence=ABSENT, at="2026-09-05T10:00:00Z",
            ev="evidence_01"),
        obs("search_9", "search_service", "SEARCH_INDEX_ENTRY", claim=True, at="2026-09-06T10:00:00Z",
            ev="evidence_03", raw={"result": "FOUND"}),
    ])
    assert d["deletion_status"] == "COMPLETE"
    assert by_res(d, "search_9") == [("verification", "VERIFY_RECORD_ABSENT", "evidence_01")]


def test_same_instant_authoritative_conflict_is_reported_and_conservative(world):
    d = world.decide([
        obs("account_3", "account_service", "USER_PROFILE", ev="evidence_01", pii={"email": EMAIL}),
        obs("account_3", "account_service", "USER_PROFILE", presence=ABSENT, ev="evidence_02"),
    ])
    assert d["conflicts"] and d["conflicts"][0]["evidence_ids"] == ["evidence_01", "evidence_02"]
    assert by_res(d, "account_3")[0] == ("findings", "REPORT_REMAINING_RECORD", "evidence_01")


def test_evidence_after_audit_at_is_never_used(world):
    late = obs("search_10", "search_service", "SEARCH_INDEX_ENTRY", at="2026-09-11T00:00:00Z")
    late_capture = obs("search_11", "search_service", "SEARCH_INDEX_ENTRY", at="2026-09-05T00:00:00Z",
                       captured="2026-09-12T00:00:00Z")
    d = world.decide([late, late_capture])
    assert not by_res(d, "search_10") and not by_res(d, "search_11")


def test_equivalent_instants_with_different_offsets(world):
    # 14:00+02:00 is exactly 12:00Z: a record observed at that instant is in window
    edge = obs("search_12", "search_service", "SEARCH_INDEX_ENTRY", at="2026-09-10T12:00:00Z")
    d = world.decide([edge], audit="2026-09-10T14:00:00+02:00")
    assert by_res(d, "search_12")
    d2 = world.decide([edge], audit="2026-09-10T13:59:59+02:00")
    assert not by_res(d2, "search_12")


def test_older_evidence_before_request_is_not_relevant(world):
    d = world.decide([obs("legal_hold_3", "legal_service", "LEGAL_HOLD_RECORD", at="2026-05-29T08:00:00Z",
                          matched=[f"user_id:{UID}"])])
    assert not d["resources"] and any("before requested_at" in n for n in d["notes"])


def test_primary_absent_replica_present_is_remaining(world):
    sql = SQL_HEADER.format(captured="2026-09-05T00:00:00Z") + BLOB_TABLE.format(t="customer_data_primary") \
        + BLOB_TABLE.format(t="customer_data_read_replica")
    sql += blob_insert("customer_data_primary", "account_50", "account_service", "customer_profiles",
                       {"resource_id": "account_50", "email": "someone@else.io"}, "2026-09-05T00:00:00Z")
    sql += blob_insert("customer_data_read_replica", "account_51", "account_service", "customer_profiles",
                       {"resource_id": "account_51", "email": EMAIL, "customer_reference": UID}, "2026-09-05T00:00:00Z")
    sql += "COMMIT;\n"
    world.ds.add("evidence/databases/customer_data_read_replica_t.sql", sql, "2026-09-05T00:00:00Z")
    d = world.decide()
    res = next(r for r in d["resources"] if r["resource_id"] == "account_51")
    assert {c["replica_or_table"] for c in res["copies"]} == {"customer_data_read_replica"}
    assert by_res(d, "account_51")[0] == ("findings", "REPORT_REMAINING_RECORD", "evidence_01")


def test_primary_copy_proof_does_not_prove_replica_absence(world):
    # account seen in the replica, later a primary-only listing omits it
    sql = SQL_HEADER.format(captured="2026-09-04T00:00:00Z") + BLOB_TABLE.format(t="customer_data_read_replica")
    sql += blob_insert("customer_data_read_replica", "account_60", "account_service", "customer_profiles",
                       {"resource_id": "account_60", "email": EMAIL}, "2026-09-04T00:00:00Z") + "COMMIT;\n"
    world.ds.add("evidence/databases/replica_t.sql", sql, "2026-09-04T00:00:00Z")
    world.ds.bundle("b2", "2026-09-06T00:00:00Z", [snap("account_service", "customer_profiles",
                    "2026-09-06T00:00:00Z", [{"resource_id": "account_99", "email": "x@y.io"}])])
    ctx = world.context()
    proofs = ctx.valid_absence_proofs("account_service", "account_60", "USER_PROFILE", ts(AUDIT), "any")
    assert proofs and all(p.replica_or_table is None for p in proofs)
    assert not ctx.valid_absence_proofs("account_service", "account_60", "USER_PROFILE", ts(AUDIT),
                                        "customer_data_read_replica")
    d = world.decide()
    assert by_res(d, "account_60")[0][1] == "REPORT_REMAINING_RECORD"


def test_invalid_absence_proofs_are_rejected(world):
    # file with a parse issue -> INCOMPLETE scope -> never proof
    world.ds.add("evidence/records/broken.json", '{"exported_at": "2026-09-06T00:00:00Z", "snapshots": [',
                 "2026-09-06T00:00:00Z")
    world.ds.bundle("b3", "2026-09-07T00:00:00Z", [snap("search_service", "customer_search_documents",
                    "2026-09-07T00:00:00Z", [{"resource_id": "search_1", "email": "x@y.io"}])])
    ctx = world.context()
    at = ts(AUDIT)
    valid = ctx.valid_absence_proofs("search_service", "search_2", "SEARCH_INDEX_ENTRY", at)
    assert [p.evidence_id for p in valid] == ["evidence_02"]
    # captured after audit_at -> rejected
    assert not ctx.valid_absence_proofs("search_service", "search_2", "SEARCH_INDEX_ENTRY", ts("2026-09-06T12:00:00Z"))
    # wrong collection -> rejected
    assert not ctx.valid_absence_proofs("search_service", "search_2", "SEARCH_INDEX_ENTRY", at,
                                        collection="index_queries")
    # wrong category -> rejected
    assert not ctx.valid_absence_proofs("search_service", "search_2", "USER_PROFILE", at)


def test_contradiction_after_audit_does_not_affect_historical_audit(world):
    world.ds.bundle("b1", "2026-09-05T00:00:00Z", [snap("search_service", "customer_search_documents",
                    "2026-09-05T00:00:00Z", [{"resource_id": "search_3", "email": "x@y.io"}])])
    world.ds.bundle("b2", "2026-09-20T00:00:00Z", [snap("search_service", "customer_search_documents",
                    "2026-09-20T00:00:00Z", [{"resource_id": "search_70", "email": EMAIL}])])
    ctx = world.context()
    proofs = ctx.valid_absence_proofs("search_service", "search_70", "SEARCH_INDEX_ENTRY", ts(AUDIT))
    assert [p.evidence_id for p in proofs] == ["evidence_01"]


# ==========================================================================
# activity: workflow linkage and recreation risks
# ==========================================================================
def test_workflow_account_is_verified_absent_with_snapshot_proof(world):
    world.act("2026-09-02T11:00:00Z", "DELETE_RECORD", "deletion_worker", "account_service", "account_77",
              "SUCCESS", "Deletion worker submitted primary profile account_77 to account_service.")
    world.ds.bundle("b1", "2026-09-05T00:00:00Z", [snap("account_service", "customer_profiles",
                    "2026-09-05T00:00:00Z", [{"resource_id": "account_12", "email": "x@y.io"}])])
    d = world.decide()
    assert d["deletion_status"] == "COMPLETE"
    assert by_res(d, "account_77") == [("verification", "VERIFY_RECORD_ABSENT", "evidence_01")]


def test_workflow_resource_of_another_subject_is_not_linked(world):
    world.act("2026-09-02T11:00:00Z", "DELETE_RECORD", "deletion_worker", "account_service", "account_78",
              "SUCCESS", "Deletion worker submitted primary profile account_78 to account_service.")
    world.ds.bundle("b1", "2026-09-01T12:00:00Z", [snap("account_service", "customer_profiles",
                    "2026-09-01T12:00:00Z", [{"resource_id": "account_78", "email": "other.ana@example.org"}])])
    assert not by_res(world.decide(), "account_78")


def test_success_claim_does_not_prove_deletion(world):
    world.act("2026-09-02T11:00:00Z", "DELETE_RECORD", "deletion_worker", "search_service", "search_40",
              "SUCCESS", "Deletion worker reported the requested operation as completed. Target resource: search_40.")
    d = world.decide([obs("search_40", "search_service", "SEARCH_INDEX_ENTRY", at="2026-09-05T00:00:00Z")])
    assert by_res(d, "search_40")[0][1] == "REPORT_REMAINING_RECORD"


def test_active_sync_and_restore_risks_and_safe_order(world):
    a_flow = world.act("2026-09-03T08:00:00Z", "CHECK_DATA_FLOW", "deletion_worker", "integration_service",
                       "data_flow_5", "SUCCESS", "Connector status check confirmed that data flow data_flow_5 remains enabled.")
    a_repop = world.act("2026-09-04T08:00:00Z", "SYNC_RECORD", "integration_service", "search_service",
                        "data_flow_6", "SUCCESS", "Active connector repopulated downstream resource search_20.")
    a_rest = world.act("2026-09-04T09:00:00Z", "CHECK_RESTORE_ACCESS", "deletion_worker", "backup_service",
                       "backup_5", "SUCCESS", "Restore-access check confirmed that archive backup_5 can still be restored.")
    d = world.decide([
        obs("data_flow_5", "integration_service", "DATA_FLOW", at="2026-09-02T00:00:00Z", raw={"enabled": False}),
        obs("backup_5", "backup_service", "BACKUP_ARCHIVE", at="2026-09-02T00:00:00Z", raw={"restore_allowed": False}),
        obs("search_20", "search_service", "SEARCH_INDEX_ENTRY", at="2026-09-05T00:00:00Z", pii={"email": EMAIL}),
    ])
    assert d["deletion_status"] == "INCOMPLETE"
    f = {(s["resource_id"], s["operation"]): s["evidence_id"] for s in d["findings"]}
    assert f[("data_flow_5", "REPORT_ACTIVE_DATA_FLOW")] == a_flow      # newer check beats older "disabled"
    assert f[("data_flow_6", "REPORT_ACTIVE_DATA_FLOW")] == a_repop     # it recreated the subject's search entry
    assert f[("backup_5", "REPORT_RESTORE_RISK")] == a_rest
    rem = [s["operation"] for s in d["remediation"]]
    assert rem == ["DISABLE_DATA_FLOW", "DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD"]
    ver = {(s["resource_id"], s["operation"]) for s in d["verification"]}
    for s in d["remediation"]:
        target = {"DISABLE_DATA_FLOW": "VERIFY_DATA_FLOW_DISABLED", "BLOCK_RESTORE": "VERIFY_RESTORE_BLOCKED",
                  "DELETE_RECORD": "VERIFY_RECORD_ABSENT"}[s["operation"]]
        assert (s["resource_id"], target) in ver


def test_catalog_alias_links_document_to_resource(world):
    world.act("2026-09-01T11:00:00Z", "LINK_RESOURCE_IDENTITY", "data_catalog", "export_service", "export_9",
              "SUCCESS", f"Data catalog linked export_9 (NST-2026-0901-9) to {EMAIL} and {UID}.")
    world.ds.bundle("b1", "2026-09-05T00:00:00Z", [snap("account_history_service", "statements",
                    "2026-09-05T00:00:00Z", [{"resource_id": "NST-2026-0901-9", "subject_reference": UID}])])
    d = world.decide()
    assert by_res(d, "export_9")[0] == ("findings", "REPORT_REMAINING_RECORD", "evidence_01")


# ==========================================================================
# step builder / output contract
# ==========================================================================
def test_step_builder_numbers_phases_and_blanks_future_evidence(world):
    d = world.decide([obs("search_1", "search_service", "SEARCH_INDEX_ENTRY"),
                      obs("data_flow_1", "integration_service", "DATA_FLOW", raw={"enabled": True})])
    steps = build_steps(d)
    assert [s["step_no"] for s in steps] == list(range(1, len(steps) + 1))
    phases = [s["phase"] for s in steps]
    assert phases == sorted(phases, key=["FINDING", "REMEDIATION", "VERIFICATION"].index)
    assert all(set(s) == {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
               for s in steps)
    assert all(s["evidence_id"] for s in steps if s["phase"] == "FINDING")
    assert all(s["evidence_id"] == "" for s in steps if s["phase"] != "FINDING")
    assert steps[len(d["findings"])]["operation"] == "DISABLE_DATA_FLOW"


def test_resource_ids_use_numeric_natural_sorting(world):
    records = [
        obs("account_10", "account_service", "USER_PROFILE",
            pii={"email": EMAIL}),
        obs("account_9", "account_service", "USER_PROFILE",
            pii={"email": EMAIL}),
    ]

    d = world.decide(records)

    assert [s["resource_id"] for s in d["findings"]] == [
        "account_9",
        "account_10",
    ]


def test_step_builder_rejects_values_outside_contract():
    with pytest.raises(ValueError):
        build_steps({"deletion_status": "INCOMPLETE", "findings": [
            {"system_id": "s", "resource_id": "r", "operation": "REPORT_SOMETHING", "state": "PRESENT", "evidence_id": "e"}]})
    with pytest.raises(ValueError):
        build_steps({"deletion_status": "COMPLETE", "verification": [
            {"system_id": "s", "resource_id": "r", "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": ""}]})
    assert build_steps({"deletion_status": "NOT_APPLICABLE"}) == []


def test_decide_is_deterministic(world):
    recs = [obs("search_1", "search_service", "SEARCH_INDEX_ENTRY"), obs("support_1", "support_platform",
            "SUPPORT_MESSAGE", pii={"requester_email": EMAIL}, raw={"message_excerpt": "order"})]
    a = json.dumps(build_steps(world.decide(recs)))
    b = json.dumps(build_steps(world.decide(list(reversed(recs)))))
    assert a == b


# ==========================================================================
# real participant data (sample answers are public)
# ==========================================================================
@pytest.fixture(scope="module")
def real_ctx():
    from evidence_search import get_scanner
    resolver = IdentityResolver(REAL_DATASET / "user_identities.csv", REAL_DATASET / "user_audit_log.csv")
    return PolicyContext(REAL_DATASET, scanner=get_scanner(REAL_DATASET), resolver=resolver)


def _sample(case_id):
    for f in ("sample_deletion_requests.csv",):
        for r in csv.DictReader(open(REAL_DATASET / f, newline="", encoding="utf-8")):
            if r["case_id"] == case_id:
                return r
    raise KeyError(case_id)


def _expected(case_id):
    for r in csv.DictReader(open(REAL_DATASET / "sample_output.csv", newline="", encoding="utf-8")):
        if r["case_id"] == case_id:
            return r["deletion_status"], json.loads(r["steps_json"])
    raise KeyError(case_id)


# Regression set: public samples the engine reproduces exactly. The other
# samples differ only where participant data cannot decide (see
# evaluation/evaluation_report.md); their statuses are checked below.
EXACT_SAMPLES = ["case_01", "case_02", "case_05", "case_06", "case_07", "case_08", "case_10", "case_11",
                 "case_12", "case_13", "case_14", "case_15", "case_16", "case_17", "case_19", "case_21"]


@pytest.mark.parametrize("case_id", [f"case_{i:02d}" for i in range(1, 33)])
def test_public_sample_status_matches(real_ctx, case_id):
    case = _sample(case_id)
    identity = real_ctx.resolver.resolve(case["email"], audit_at=ts(case["audit_at"]),
                                         requested_at=ts(case["requested_at"]), case_id=case_id)
    assert decide(identity, [], case, context=real_ctx)["deletion_status"] == _expected(case_id)[0]


@pytest.mark.parametrize("case_id", EXACT_SAMPLES)
def test_public_sample_cases_match_published_answers(real_ctx, case_id):
    case = _sample(case_id)
    identity = real_ctx.resolver.resolve(case["email"], audit_at=ts(case["audit_at"]),
                                         requested_at=ts(case["requested_at"]), case_id=case_id)
    steps = build_steps(decide(identity, [], case, context=real_ctx))
    status, expected = _expected(case_id)
    key = lambda s: tuple(s[k] for k in ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"))  # noqa: E731
    assert decide(identity, [], case, context=real_ctx)["deletion_status"] == status
    assert [key(s) for s in steps] == [key(s) for s in expected]


def test_not_applicable_request_has_no_steps():
    import main
    resolver = IdentityResolver(REAL_DATASET / "user_identities.csv", REAL_DATASET / "user_audit_log.csv")
    case = {"case_id": "case_na", "email": "amina.elmasri@gmail.com", "requested_at": "2026-08-18T09:14:00Z",
            "reported_status": "NOT_STARTED", "reported_at": "2026-08-20T16:42:00Z", "audit_at": "2026-09-03T11:30:00Z",
            "request_text": "Please send me a copy of all the personal data you hold about me."}
    status, steps_json, _, failed = main.run_case(case, resolver)
    assert (status, steps_json, failed) == ("NOT_APPLICABLE", "[]", False)
