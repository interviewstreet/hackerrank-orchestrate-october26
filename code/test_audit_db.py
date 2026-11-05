"""
test_audit_db.py — tests for audit_db.py and the save_case() call in main.py.

Run from the repo root with:
    python3 code/test_audit_db.py
"""
from __future__ import annotations

import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import audit_db
from models import ClassificationResult, IdentityBundle, IdentityChange

UTC = timezone.utc
DATASET_DIR = Path(__file__).parent.parent / "dataset"

CASE = {
    "case_id": "case_t1",
    "email": "old.mail@example.com",
    "request_text": "Please delete my account.",
    "reported_status": "COMPLETE",
    "requested_at": "2026-09-01T00:00:00Z",
    "audit_at": "2026-10-01T00:00:00Z",
}


def make_identity() -> IdentityBundle:
    return IdentityBundle(
        user_id="user_9",
        current_email="new.mail@example.com",
        current_name="Ana Lima",
        current_phone="+55 11 91234 5678",
        current_email_hash="h_new",
        historical_emails=["old.mail@example.com"],
        historical_phones=[],
        historical_email_hashes=["h_old"],
        request_email="old.mail@example.com",
        history=[
            IdentityChange("audit_7", "email", "old.mail@example.com",
                           "new.mail@example.com", "2026-05-01T00:00:00Z"),
            IdentityChange("audit_8", "email_hash", "h_old", "h_new",
                           "2026-05-01T00:00:00Z"),
        ],
    )


def make_classifier() -> ClassificationResult:
    return ClassificationResult(
        ClassificationResult.IS_DELETION, "HIGH", ["DELETION:delete"], "deletion requested",
        language="en", signals=["deletion: delete"],
        reason="Deletion request: the person asks to delete their data (“delete”).")


def make_record(eid, rid, idents, captured):
    return SimpleNamespace(evidence_id=eid, system_id="account_service", resource_id=rid,
                           identifiers_matched=idents, captured_at=captured)


EVIDENCE = {
    "records": [
        make_record("evidence_1", "account_1",
                    ["email:new.mail@example.com", "name:ana lima"],
                    datetime(2026, 9, 20, 10, 0, tzinfo=UTC)),
        # same record seen twice -> one row per identifier, no duplicates
        make_record("evidence_1", "account_1", ["email:new.mail@example.com"],
                    datetime(2026, 9, 20, 10, 0, tzinfo=UTC)),
    ],
    "latest_by_resource": {}, "referenced_resources": [], "absence_proofs": {},
    "identifier_provenance": {},
}

DECISION = {
    "deletion_status": "INCOMPLETE",
    "resources": [{"system_id": "account_service", "resource_id": "account_1",
                   "category": "USER_PROFILE", "required_treatment": "DELETE",
                   "state_at_audit": "PRESENT", "satisfied": False,
                   "evidence_ids": ["evidence_1"]}],
    "flows": [{"system_id": "crm_sync", "resource_id": "job_1", "kind": "SYNC",
               "active_at_audit": True, "evidence_id": "activity_3"}],
    "restore_risks": [{"system_id": "backup_vault", "resource_id": "snapshot_4",
                       "active_at_audit": True, "evidence_id": "activity_5"}],
    "timeline": [
        {"time": "2026-09-01T00:00:00Z", "system_id": "account_service",
         "resource_id": "account_1", "event": "DELETE", "state_after": "PRESENT",
         "evidence_id": "activity_2"},
        {"time": "2026-09-02T00:00:00Z", "system_id": "crm_sync",
         "resource_id": "job_1", "event": "SYNC", "state_after": "PRESENT",
         "evidence_id": "activity_3"},
    ],
}

STEPS = [
    {"step_no": 1, "phase": "FINDING", "system_id": "account_service",
     "resource_id": "account_1", "operation": "REPORT_REMAINING_RECORD",
     "state": "PRESENT", "evidence_id": "evidence_1"},
    {"step_no": 2, "phase": "REMEDIATION", "system_id": "account_service",
     "resource_id": "account_1", "operation": "DELETE_RECORD", "state": "ABSENT",
     "evidence_id": ""},
]


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "audit.db"
        self.conn = audit_db.connect(self.path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def save_full(self, **over):
        kwargs = dict(our_status="INCOMPLETE", classification="IS_DELETION",
                      classifier=make_classifier(), identity=make_identity(), evidence=EVIDENCE, decision=DECISION,
                      steps=STEPS)
        kwargs.update(over)
        audit_db.save_case(self.conn, CASE, **kwargs)

    def q(self, sql, *args):
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]


class TestSchema(DbTestCase):

    def test_all_tables_exist_with_requested_columns(self):
        expected = {
            "cases": ["case_id", "email", "request_text", "reported_status", "our_status",
                      "classification", "requested_at", "audit_at", "language",
                      "confidence", "matched_signals", "reason"],
            "identities": ["case_id", "user_id", "kind", "value", "is_historical", "audit_id",
                           "changed_at", "matches_request"],
            "evidence_hits": ["case_id", "file_id", "system_id", "resource_id",
                              "matched_identifier", "captured_at", "replica_or_table",
                              "origin"],
            "lineage_edges": ["case_id", "activity_id", "event_time", "event_type", "kind",
                              "label", "source_system", "source_resource_id",
                              "target_system", "target_resource_id", "reported_result",
                              "details"],
            "resources": ["case_id", "system_id", "resource_id", "category",
                          "required_treatment", "state_at_audit", "satisfied",
                          "evidence_ids"],
            "flows": ["case_id", "system_id", "resource_id", "kind", "active_at_audit",
                      "evidence_id"],
            "restore_risks": ["case_id", "system_id", "resource_id", "active_at_audit",
                              "evidence_id"],
            "timeline": ["case_id", "seq", "time", "system_id", "resource_id", "event",
                         "state_after", "evidence_id"],
            "steps": ["case_id", "step_no", "phase", "system_id", "resource_id",
                      "operation", "state", "evidence_id"],
        }
        for table, cols in expected.items():
            with self.subTest(table=table):
                got = [r["name"] for r in self.q(f"PRAGMA table_info({table})")]
                self.assertEqual(got, cols)

    def test_connect_twice_is_safe(self):
        audit_db.connect(self.path).close()   # CREATE TABLE IF NOT EXISTS

    def test_connect_twice_keeps_rows(self):
        self.save_full()
        self.conn.close()
        self.conn = audit_db.connect(self.path)
        self.assertEqual(audit_db.table_counts(self.conn)["cases"], 1)

    def test_old_schema_is_rebuilt(self):
        """An audit.db from before the classifier columns is upgraded, not crashed on."""
        self.conn.close()
        self.path.unlink()
        old = sqlite3.connect(str(self.path))
        old.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY, email TEXT NOT NULL, "
                    "request_text TEXT NOT NULL, reported_status TEXT NOT NULL, "
                    "our_status TEXT NOT NULL, classification TEXT NOT NULL, "
                    "requested_at TEXT NOT NULL, audit_at TEXT NOT NULL)")
        old.execute("INSERT INTO cases VALUES ('c','e','t','COMPLETE','INCOMPLETE',"
                    "'IS_DELETION','r','a')")
        old.commit()
        old.close()
        self.conn = audit_db.connect(self.path)
        cols = [r["name"] for r in self.q("PRAGMA table_info(cases)")]
        self.assertEqual(cols, audit_db.EXPECTED_COLUMNS["cases"])
        self.save_full()   # works with the new columns
        self.assertEqual(audit_db.table_counts(self.conn)["cases"], 1)


class TestSaveCase(DbTestCase):

    def test_case_row(self):
        self.save_full()
        row = self.q("SELECT * FROM cases")[0]
        self.assertEqual(row, dict(
            CASE, our_status="INCOMPLETE", classification="IS_DELETION",
            language="en", confidence="HIGH", matched_signals='["deletion: delete"]',
            reason="Deletion request: the person asks to delete their data (“delete”)."))

    def test_without_classifier_fields_are_empty(self):
        self.save_full(classifier=None)
        row = self.q("SELECT language, confidence, matched_signals, reason FROM cases")[0]
        self.assertEqual(row, {"language": "", "confidence": "", "matched_signals": "[]",
                               "reason": ""})

    def test_identities_current_and_historical_with_audit_ids(self):
        self.save_full()
        rows = self.q("SELECT kind, value, is_historical, audit_id FROM identities "
                      "ORDER BY rowid")
        self.assertEqual(rows, [
            {"kind": "email", "value": "new.mail@example.com", "is_historical": 0,
             "audit_id": "audit_7"},          # set by audit_7
            {"kind": "phone", "value": "+55 11 91234 5678", "is_historical": 0,
             "audit_id": ""},                 # never changed
            {"kind": "email_hash", "value": "h_new", "is_historical": 0,
             "audit_id": "audit_8"},
            {"kind": "name", "value": "Ana Lima", "is_historical": 0, "audit_id": ""},
            {"kind": "email", "value": "old.mail@example.com", "is_historical": 1,
             "audit_id": "audit_7"},          # replaced by audit_7
            {"kind": "email_hash", "value": "h_old", "is_historical": 1,
             "audit_id": "audit_8"},
        ])
        self.assertEqual({r["user_id"] for r in self.q("SELECT user_id FROM identities")},
                         {"user_9"})

    def test_identity_change_time_and_request_email(self):
        self.save_full()
        rows = {(r["value"], r["is_historical"]): r for r in self.q(
            "SELECT value, is_historical, changed_at, matches_request FROM identities")}
        old = rows[("old.mail@example.com", 1)]
        self.assertEqual((old["changed_at"], old["matches_request"]),
                         ("2026-05-01T00:00:00Z", 1))   # request email = old email
        self.assertEqual(rows[("new.mail@example.com", 0)]["matches_request"], 0)
        self.assertEqual(rows[("+55 11 91234 5678", 0)]["changed_at"], "")   # never changed

    def test_empty_phone_not_saved(self):
        ident = make_identity()
        ident.current_phone = ""
        self.save_full(identity=ident)
        self.assertEqual(self.q("SELECT * FROM identities WHERE kind='phone'"), [])

    def test_evidence_hits_one_row_per_identifier_no_duplicates(self):
        self.save_full()
        rows = self.q("SELECT file_id, resource_id, matched_identifier, captured_at "
                      "FROM evidence_hits ORDER BY matched_identifier")
        self.assertEqual(rows, [
            {"file_id": "evidence_1", "resource_id": "account_1",
             "matched_identifier": "email:new.mail@example.com",
             "captured_at": "2026-09-20T10:00:00Z"},
            {"file_id": "evidence_1", "resource_id": "account_1",
             "matched_identifier": "name:ana lima",
             "captured_at": "2026-09-20T10:00:00Z"},
        ])

    def test_evidence_origin_and_replica(self):
        rec = make_record("evidence_2", "account_1", ["email:new.mail@example.com"],
                          datetime(2026, 9, 20, tzinfo=UTC))
        rec.replica_or_table = "reporting_replica"
        self.save_full(evidence=dict(EVIDENCE, records=[rec]),
                       file_origins={"evidence_2": "customer_data_reporting_replica_capture"})
        row = self.q("SELECT replica_or_table, origin FROM evidence_hits")[0]
        self.assertEqual(row, {"replica_or_table": "reporting_replica",
                               "origin": "customer_data_reporting_replica_capture"})

    def test_lineage_edges_saved_and_replaced(self):
        edge = {"activity_id": "activity_9", "event_time": "2026-09-01T00:00:00Z",
                "event_type": "SYNC_RECORD", "kind": "movement", "label": "sync",
                "source_system": "account_service", "source_resource_id": "account_1",
                "target_system": "account_replication_cluster",
                "target_resource_id": "account_1", "reported_result": "SUCCESS",
                "details": "Replication worker reported its final checkpoint."}
        self.save_full(lineage_edges=[edge])
        self.assertEqual(self.q("SELECT activity_id, kind, target_system FROM lineage_edges"),
                         [{"activity_id": "activity_9", "kind": "movement",
                           "target_system": "account_replication_cluster"}])
        self.save_full(lineage_edges=[])          # re-run clears old edges
        self.assertEqual(audit_db.table_counts(self.conn)["lineage_edges"], 0)

    def test_decision_tables(self):
        self.save_full()
        res = self.q("SELECT * FROM resources")[0]
        self.assertEqual(res["satisfied"], 0)
        self.assertEqual(json.loads(res["evidence_ids"]), ["evidence_1"])
        self.assertEqual(self.q("SELECT active_at_audit FROM flows")[0]["active_at_audit"], 1)
        self.assertEqual(self.q("SELECT system_id, resource_id, active_at_audit, evidence_id "
                                "FROM restore_risks"),
                         [{"system_id": "backup_vault", "resource_id": "snapshot_4",
                           "active_at_audit": 1, "evidence_id": "activity_5"}])
        self.assertEqual([r["event"] for r in self.q("SELECT event FROM timeline ORDER BY seq")],
                         ["DELETE", "SYNC"])

    def test_steps(self):
        self.save_full()
        rows = self.q("SELECT step_no, operation, evidence_id FROM steps ORDER BY step_no")
        self.assertEqual(rows, [
            {"step_no": 1, "operation": "REPORT_REMAINING_RECORD", "evidence_id": "evidence_1"},
            {"step_no": 2, "operation": "DELETE_RECORD", "evidence_id": ""},
        ])

    def test_placeholder_decision_leaves_tables_empty(self):
        self.save_full(decision={"deletion_status": "INCOMPLETE", "resources": [],
                                 "flows": [], "restore_risks": [], "timeline": []},
                       steps=[])
        counts = audit_db.table_counts(self.conn)
        self.assertEqual((counts["resources"], counts["flows"], counts["restore_risks"],
                          counts["timeline"], counts["steps"]), (0, 0, 0, 0, 0))

    def test_early_stop_saves_only_the_case_row(self):
        audit_db.save_case(self.conn, CASE, our_status="NOT_APPLICABLE",
                           classification="NOT_APPLICABLE")
        counts = audit_db.table_counts(self.conn)
        self.assertEqual(counts["cases"], 1)
        self.assertEqual(sum(counts.values()), 1)

    def test_rerun_replaces_old_rows(self):
        self.save_full()
        before = audit_db.table_counts(self.conn)
        self.save_full()
        self.assertEqual(audit_db.table_counts(self.conn), before)
        # a smaller re-run removes rows that are no longer produced
        self.save_full(steps=STEPS[:1], decision={"resources": []})
        after = audit_db.table_counts(self.conn)
        self.assertEqual((after["steps"], after["resources"], after["flows"],
                          after["restore_risks"]), (1, 0, 0, 0))

    def test_rerun_does_not_touch_other_cases(self):
        self.save_full()
        audit_db.save_case(self.conn, dict(CASE, case_id="case_t2"),
                           our_status="INCOMPLETE", classification="IS_DELETION")
        self.save_full()
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM cases")[0]["n"], 2)

    def test_failed_save_keeps_previous_rows(self):
        self.save_full()
        before = audit_db.table_counts(self.conn)
        bad = [dict(STEPS[0], step_no="not a number")]
        with self.assertRaises(ValueError):
            self.save_full(steps=bad)
        self.assertEqual(audit_db.table_counts(self.conn), before)


# ---------------------------------------------------------------------------
# main.py integration: save_case() is called, and a DB error never stops a run
# ---------------------------------------------------------------------------

@unittest.skipUnless((DATASET_DIR / "user_identities.csv").exists(), "dataset not present")
class TestMainSavesCases(DbTestCase):

    @classmethod
    def setUpClass(cls):
        import main
        from identity_resolver import IdentityResolver
        cls.main = main
        cls.resolver = IdentityResolver(DATASET_DIR / "user_identities.csv",
                                        DATASET_DIR / "user_audit_log.csv")

    MAIN_CASE = {"case_id": "case_test", "email": "oliver-bennett@gmail.com",
                 "requested_at": "2026-09-01T00:00:00Z", "reported_status": "COMPLETE",
                 "reported_at": "2026-09-02T00:00:00Z",
                 "audit_at": "2026-10-01T00:00:00Z",
                 "request_text": "Please delete my account."}

    def run_case(self, case, db):
        err = io.StringIO()
        with redirect_stderr(err):
            result = self.main.run_case(case, self.resolver, db)
        return result, err.getvalue()

    def test_normal_case_is_saved(self):
        from models import empty_evidence
        with mock.patch.object(self.main, "find_records", return_value=empty_evidence()):
            (status, steps_json, label, failed), _ = self.run_case(self.MAIN_CASE, self.conn)
        self.assertFalse(failed)
        row = self.q("SELECT * FROM cases")[0]
        self.assertEqual((row["our_status"], row["classification"]),
                         (status, "IS_DELETION"))
        self.assertEqual(row["audit_at"], "2026-10-01T00:00:00Z")   # CSV string kept
        self.assertGreater(len(self.q("SELECT * FROM identities")), 0)

    def test_not_applicable_is_saved(self):
        case = dict(self.MAIN_CASE, request_text="Please don't delete my account.")
        self.run_case(case, self.conn)
        row = self.q("SELECT our_status, classification, language, confidence, "
                     "matched_signals, reason FROM cases")[0]
        self.assertEqual(row["our_status"], "NOT_APPLICABLE")
        self.assertEqual(row["classification"], "NOT_APPLICABLE")
        self.assertEqual((row["language"], row["confidence"]), ("en", "HIGH"))
        self.assertEqual(json.loads(row["matched_signals"]), ["negation: don't delete"])
        self.assertTrue(row["reason"].startswith("Not a deletion request"))

    def test_failed_case_is_saved_as_incomplete(self):
        with mock.patch.object(self.main, "decide", side_effect=RuntimeError("boom")):
            (status, _, _, failed), _ = self.run_case(self.MAIN_CASE, self.conn)
        self.assertTrue(failed)
        row = self.q("SELECT our_status, classification, reason FROM cases")[0]
        self.assertEqual((row["our_status"], row["classification"]),
                         ("INCOMPLETE", "IS_DELETION"))
        self.assertTrue(row["reason"].startswith("Deletion request"))

    def test_database_error_does_not_change_the_answer(self):
        from models import empty_evidence
        with mock.patch.object(self.main, "find_records", return_value=empty_evidence()):
            expected, _ = self.run_case(self.MAIN_CASE, None)
            with mock.patch.object(self.main.audit_db, "save_case",
                                   side_effect=sqlite3.OperationalError("disk full")):
                got, err = self.run_case(self.MAIN_CASE, self.conn)
        self.assertEqual(got, expected)
        self.assertIn("could not save to audit.db", err)
        self.assertIn("disk full", err)

    def test_real_case_43_saves_lineage_edges(self):
        import csv
        import lineage
        with open(DATASET_DIR / "deletion_requests.csv", newline="", encoding="utf-8") as fh:
            case = next(r for r in csv.DictReader(fh) if r["case_id"] == "case_43")
        src = lineage.LineageSource(DATASET_DIR)
        err = io.StringIO()
        with redirect_stderr(err):
            result = self.main.run_case(case, self.resolver, self.conn, src)
        self.assertEqual(result, self.main.run_case(case, self.resolver))  # map never changes the answer
        edges = self.q("SELECT activity_id, target_system FROM lineage_edges")
        self.assertIn({"activity_id": "activity_3886",
                       "target_system": "account_replication_cluster"}, edges)
        origin = self.q("SELECT origin FROM evidence_hits WHERE file_id = 'evidence_94'")
        self.assertTrue(origin and origin[0]["origin"])

    def test_closed_connection_only_warns(self):
        self.conn.close()
        (status, _, _, failed), err = self.run_case(self.MAIN_CASE, self.conn)
        self.assertFalse(failed)
        self.assertIn("could not save to audit.db", err)
        self.conn = audit_db.connect(self.path)   # for tearDown

    def test_main_writes_output_csv_when_db_cannot_open(self):
        with mock.patch.object(self.main.audit_db, "connect",
                               side_effect=sqlite3.OperationalError("locked")), \
             mock.patch.object(self.main, "OUTPUT_PATH", Path(self.tmp.name) / "out.csv"), \
             mock.patch.object(self.main, "find_records",
                               side_effect=lambda i, c: __import__("models").empty_evidence()):
            err, out = io.StringIO(), io.StringIO()
            with redirect_stderr(err), mock.patch("sys.stdout", out):
                self.assertEqual(self.main.main(), 0)
        self.assertIn("continuing without the database", err.getvalue())
        lines = (Path(self.tmp.name) / "out.csv").read_text().splitlines()
        self.assertEqual(len(lines), 519)


if __name__ == "__main__":
    unittest.main(verbosity=2)
