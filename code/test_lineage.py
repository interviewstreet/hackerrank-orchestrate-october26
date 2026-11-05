"""
test_lineage.py — tests for lineage.py (the website's data lineage map).

Run from the repo root with:
    python3 code/test_lineage.py
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import export_web_data as ex
import lineage
from lineage import BACKUP, COPY, PRIMARY, edge_from_row, extract_edges, node_group
from utils import parse_ts

UTC = timezone.utc
REPO_ROOT = Path(__file__).parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
DB_PATH = REPO_ROOT / "audit.db"


def row(aid, etype, src, dst, rid, details="", t="2026-09-01T00:00:00Z", result="SUCCESS"):
    return {"activity_id": aid, "event_time": t, "event_type": etype, "source_system": src,
            "target_system": dst, "resource_id": rid, "reported_result": result,
            "details": details}


class TestNodeGroup(unittest.TestCase):

    def test_groups(self):
        cases = [
            (("account_service", (), None), PRIMARY),
            (("identity_service", ("customer_account_service",), None), PRIMARY),
            (("account_service", (), "reporting_replica"), COPY),          # a replica copy
            (("account_service", ("customer_data_read_replica_capture",), None), COPY),
            (("account_replication_cluster", (), None), COPY),
            (("search_service", (), None), COPY),
            (("analytics_platform", (), None), COPY),
            (("support_platform", ("support_platform",), None), COPY),
            (("export_service", (), None), COPY),
            (("security_service", ("central_observability_export",), None), COPY),   # logs
            (("backup_service", (), None), BACKUP),
            (("archive_service", (), None), BACKUP),
            (("legal_service", ("legal_retention_service",), None), BACKUP),
            (("object_storage", ("backup_service",), None), BACKUP),   # by file origin
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(node_group(*args), expected)


class TestEdgeFromRow(unittest.TestCase):
    RES = {"account_1", "search_7", "data_flow_3", "backup_4"}

    def test_sync_on_own_resource(self):
        e = edge_from_row(row("a1", "SYNC_RECORD", "account_service",
                              "account_replication_cluster", "account_1"), self.RES)
        self.assertEqual((e.kind, e.label, e.source_resource_id, e.target_resource_id),
                         ("movement", "sync", "account_1", "account_1"))

    def test_downstream_resource_named_in_details(self):
        e = edge_from_row(row("a2", "SYNC_RECORD", "integration_service", "search_service",
                              "data_flow_3",
                              "Active connector repopulated downstream resource search_7."),
                          self.RES)
        self.assertEqual((e.source_system, e.source_resource_id, e.target_system,
                          e.target_resource_id),
                         ("integration_service", "data_flow_3", "search_service", "search_7"))

    def test_row_found_only_through_details(self):
        """resource_id is someone else's flow, but details name our search record."""
        e = edge_from_row(row("a3", "SYNC_RECORD", "integration_service", "search_service",
                              "data_flow_999", "Connector repopulated search_7."), self.RES)
        self.assertEqual(e.target_resource_id, "search_7")

    def test_restore_and_index_and_export_are_movements(self):
        for etype, label in (("RESTORE_BACKUP", "restore"), ("INDEX_RECORD", "index"),
                             ("CREATE_EXPORT", "export"), ("REFRESH_CACHE", "cache")):
            with self.subTest(etype=etype):
                e = edge_from_row(row("a", etype, "x", "y", "backup_4"), self.RES)
                self.assertEqual((e.kind, e.label), ("movement", label))

    def test_flow_and_restore_claims_are_control(self):
        for etype in ("CHECK_DATA_FLOW", "DISABLE_DATA_FLOW", "BLOCK_RESTORE",
                      "CHECK_RESTORE_ACCESS"):
            with self.subTest(etype=etype):
                e = edge_from_row(row("a", etype, "deletion_worker", "integration_service",
                                      "data_flow_3"), self.RES)
                self.assertEqual(e.kind, "control")

    def test_other_claims_are_status_rows(self):
        """Kept for the time-travel timeline; never drawn on the map."""
        for etype, label in (("DELETE_RECORD", "delete"), ("REDACT_RECORD", "redact"),
                             ("ANONYMIZE_RECORD", "anonymize"), ("RETAIN_RECORD", "retain"),
                             ("LINK_RESOURCE_IDENTITY", "link resource identity")):
            with self.subTest(etype=etype):
                e = edge_from_row(row("a", etype, "deletion_worker", "account_service",
                                      "account_1"), self.RES)
                self.assertEqual((e.kind, e.label), ("status", label))

    def test_status_rows_not_on_map(self):
        lin = ex.build_lineage(
            hits=[], flows=[], restore_risks=[],
            edges=[{"activity_id": "a1", "event_time": "2026-09-02T00:00:00Z",
                    "event_type": "DELETE_RECORD", "kind": "status", "label": "delete",
                    "source_system": "deletion_worker", "source_resource_id": "account_1",
                    "target_system": "account_service", "target_resource_id": "account_1",
                    "reported_result": "SUCCESS", "details": "Deleted account_1."}])
        self.assertEqual((lin["nodes"], lin["edges"]), ([], []))

    def test_row_without_event_type_ignored(self):
        self.assertIsNone(edge_from_row(row("a", "", "x", "y", "account_1"), self.RES))

    def test_other_peoples_resources_ignored(self):
        self.assertIsNone(edge_from_row(row("a", "SYNC_RECORD", "account_service",
                                            "account_replication_cluster", "account_2",
                                            "Replication of account_2."), self.RES))


class TestExtractEdges(unittest.TestCase):
    AUDIT = datetime(2026, 9, 26, 11, tzinfo=UTC)

    def test_cutoff_inclusive_and_sorted(self):
        rows = [
            row("a3", "SYNC_RECORD", "s", "t", "account_1", t="2026-09-26T11:00:00Z"),  # = audit_at
            row("a1", "SYNC_RECORD", "s", "t", "account_1", t="2026-09-01T00:00:00Z"),
            row("a9", "SYNC_RECORD", "s", "t", "account_1", t="2026-09-26T11:00:01Z"),  # after
        ]
        got = [e.activity_id for e in extract_edges(rows, ["account_1"], self.AUDIT)]
        self.assertEqual(got, ["a1", "a3"])

    def test_naive_event_time_is_utc(self):
        rows = [row("a1", "SYNC_RECORD", "s", "t", "account_1", t="2026-09-26 12:00:00")]
        self.assertEqual(extract_edges(rows, ["account_1"], self.AUDIT), [])

    def test_resource_ids_case_insensitive(self):
        rows = [row("a1", "SYNC_RECORD", "s", "t", "ACCOUNT_1")]
        self.assertEqual(len(extract_edges(rows, ["account_1"], self.AUDIT)), 1)

    def test_no_audit_at_or_no_resources(self):
        rows = [row("a1", "SYNC_RECORD", "s", "t", "account_1")]
        self.assertEqual(extract_edges(rows, ["account_1"], None), [])
        self.assertEqual(extract_edges(rows, [], self.AUDIT), [])

    def test_case_resources_from_evidence(self):
        from types import SimpleNamespace as NS
        ev = {"records": [NS(resource_id="a_1"), NS(resource_id="b_2"), NS(resource_id="a_1")]}
        self.assertEqual(lineage.case_resources(ev), ["a_1", "b_2"])
        self.assertEqual(lineage.case_resources(None), [])


@unittest.skipUnless((DATASET_DIR / "system_activity.csv").exists(), "dataset not present")
class TestRealData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = lineage.LineageSource(DATASET_DIR)

    def test_case_43_replication_sync(self):
        edges = self.src.edges_for(["account_8681"], parse_ts("2026-09-26T11:00:00Z"))
        self.assertIn(("activity_3886", "account_service", "account_replication_cluster"),
                      [(e.activity_id, e.source_system, e.target_system) for e in edges])

    def test_every_origin_loaded(self):
        self.assertTrue(all(fid.startswith("evidence_") for fid in self.src.file_origins))
        self.assertGreater(len(self.src.file_origins), 50)

    @unittest.skipUnless(DB_PATH.exists(), "audit.db not built (run main.py)")
    def test_saved_edges_never_after_audit_at(self):
        db = sqlite3.connect(str(DB_PATH))
        late = db.execute("SELECT e.case_id, e.activity_id, e.event_time, c.audit_at "
                          "FROM lineage_edges e JOIN cases c USING (case_id)").fetchall()
        db.close()
        bad = [r for r in late if parse_ts(r[2]) > parse_ts(r[3])]
        self.assertEqual(bad, [])
        self.assertGreater(len(late), 0)


class TestLineageIsDisplayOnly(unittest.TestCase):
    """The map must never change a deletion decision."""

    def test_policy_engine_does_not_use_lineage(self):
        src = (Path(__file__).parent / "policy_engine.py").read_text(encoding="utf-8")
        self.assertNotIn("lineage", src)
        self.assertNotIn("system_activity", src)

    def test_restore_edge_into_backup_column(self):
        lin = ex.build_lineage(
            hits=[{"file_id": "evidence_5", "system_id": "backup_service",
                   "resource_id": "backup_4", "matched_identifier": "email:a@b.co",
                   "captured_at": "2026-09-01T00:00:00Z", "replica_or_table": "",
                   "origin": "backup_service"}],
            edges=[{"activity_id": "a1", "event_time": "2026-09-02T00:00:00Z",
                    "event_type": "RESTORE_BACKUP", "kind": "movement", "label": "restore",
                    "source_system": "backup_service", "source_resource_id": "backup_4",
                    "target_system": "search_service", "target_resource_id": "search_7",
                    "reported_result": "SUCCESS", "details": "Restore repopulated search_7."},
                   {"activity_id": "a2", "event_time": "2026-09-03T00:00:00Z",
                    "event_type": "CHECK_RESTORE_ACCESS", "kind": "control",
                    "label": "restore-access check", "source_system": "deletion_worker",
                    "source_resource_id": "backup_4", "target_system": "backup_service",
                    "target_resource_id": "backup_4", "reported_result": "SUCCESS",
                    "details": "backup_4 can still be restored."}],
            flows=[], restore_risks=[{"system_id": "backup_service", "resource_id": "backup_4",
                                      "active_at_audit": True, "evidence_id": "activity_2"}])
        by_id = {n["id"]: n for n in lin["nodes"]}
        backup = by_id["backup_service|backup_4|"]
        search = by_id["search_service|search_7|"]
        self.assertEqual((backup["group"], backup["source"]), ("backup", "evidence"))
        self.assertEqual((search["group"], search["source"]), ("copy", "activity"))
        self.assertEqual(lin["edges"][0]["from"], backup["id"])
        self.assertEqual(lin["edges"][0]["to"], search["id"])
        self.assertEqual([c["label"] for c in backup["claims"]], ["restore-access check"])
        self.assertTrue(backup["restore_risk"]["active_at_audit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
