import unittest
from pathlib import Path

from code.evidence import (
    build_evidence_index,
    parse_json_evidence,
    parse_log_evidence,
    parse_sql_evidence,
    parse_text_evidence,
)
from code.identity import resolve_identity
from code.ingest import load_all


class EvidenceParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_all(".")
        cls.root = Path("dataset/evidence")

    def identity(self, email):
        return resolve_identity(email, "", self.data)

    def test_sql_snapshot_proves_absence(self):
        hits = parse_sql_evidence(
            self.root / "databases/customer_accounts_failover_replica_20260902.sql",
            self.identity("amina.elmasri@gmail.com"),
        )
        self.assertEqual((hits[0]["resource_id"], hits[0]["state"]), ("account_001", "ABSENT"))
        self.assertEqual(hits[0]["system_id"], "account_service")

    def test_sql_snapshot_finds_active_record(self):
        hits = parse_sql_evidence(
            self.root / "databases/customer_accounts_failover_replica_20260902.sql",
            self.identity("leila.haddad@yahoo.com"),
        )
        self.assertTrue(any(hit["resource_id"] == "account_005" and hit["state"] == "ACTIVE" for hit in hits))

    def test_json_distinguishes_clean_and_exposed_tombstones(self):
        path = self.root / "records/customer_data_snapshot_bundle_20260915.json"
        clean = parse_json_evidence(path, self.identity("a.eze08@gmail.com"))
        exposed = parse_json_evidence(path, self.identity("addo.kofi@gmail.com"))
        self.assertTrue(any(hit["resource_id"] == "tombstone_440" and hit["state"] == "REDACTED" for hit in clean))
        self.assertTrue(any(hit["resource_id"] == "tombstone_9178" and hit["state"] == "PRESENT" for hit in exposed))

    def test_log_trace_correlates_start_and_completion(self):
        hits = parse_log_evidence(
            self.root / "logs/resource_lookup_trace_20260926_103856.log",
            self.identity("mori.ren@gmail.com"),
        )
        resources = {hit["resource_id"] for hit in hits}
        self.assertTrue({"search_4013", "support_5569", "analytics_037", "data_flow_4890"} <= resources)

    def test_handover_support_attachment_keeps_resource_id_and_category(self):
        hits = parse_text_evidence(
            self.root / "records/customer_account_handover_20261001.txt",
            self.identity("noor-khalil@proton.me"),
        )
        attachment = next(hit for hit in hits if hit["resource_id"] == "support_4218")
        self.assertEqual(attachment["data_category"], "SUPPORT_ATTACHMENT")
        self.assertEqual(attachment["system_id"], "support_platform")

    def test_newest_account_readback_supersedes_migrated_resource_id(self):
        identity = self.identity("leonie.g9352@outlook.com")
        index = build_evidence_index(".", self.data["evidence_manifest"], identity, "2026-09-18T12:00:00Z")
        self.assertIn("account_4092", index)
        self.assertNotIn("account_6523", index)
