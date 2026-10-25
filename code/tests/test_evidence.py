import unittest
from pathlib import Path
from unittest.mock import patch

from code.evidence import (
    _contains,
    build_evidence_index,
    parse_image_evidence,
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
        identity = self.identity("amina.elmasri@gmail.com")
        identity["lineage_resource_ids"] = ["account_001"]
        hits = parse_sql_evidence(
            self.root / "databases/customer_accounts_failover_replica_20260902.sql",
            identity,
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
        clean_identity = self.identity("a.eze08@gmail.com")
        clean_identity["lineage_resource_ids"] = ["account_4857"]
        clean = parse_json_evidence(path, clean_identity)
        exposed = parse_json_evidence(path, self.identity("addo.kofi@gmail.com"))
        self.assertTrue(any(hit["resource_id"] == "tombstone_440" and hit["state"] == "REDACTED" for hit in clean))
        self.assertTrue(any(hit["resource_id"] == "account_4857" and hit["state"] == "ABSENT" for hit in clean))
        self.assertTrue(any(hit["resource_id"] == "tombstone_9178" and hit["state"] == "PRESENT" for hit in exposed))

    def test_log_trace_correlates_start_and_completion(self):
        hits = parse_log_evidence(
            self.root / "logs/resource_lookup_trace_20260926_103856.log",
            self.identity("mori.ren@gmail.com"),
        )
        resources = {hit["resource_id"] for hit in hits}
        self.assertTrue({"search_4013", "support_5569", "analytics_037", "data_flow_4890"} <= resources)

    def test_identifier_boundaries_and_casefolding(self):
        self.assertTrue(_contains('subject=user_1;', 'user_1'))
        self.assertFalse(_contains('subject=user_10;', 'user_1'))
        self.assertTrue(_contains('EMAIL=AMINA.ELMASRI@GMAIL.COM', 'amina.elmasri@gmail.com'))

    def test_human_readable_resource_is_linked_only_near_subject(self):
        text = (
            "account_999 decoy@example.test\n" + "unrelated filler " * 30
            + "support_123 Subject a@example.test attachment"
        )
        identity = {"user_id": "user_1", "all_emails": ["a@example.test"],
                    "all_phones": [], "all_email_hashes": []}
        with patch("code.evidence._read_text", return_value=text):
            hits = parse_text_evidence(Path("attachment.txt"), identity)
        self.assertEqual([hit["resource_id"] for hit in hits], ["support_123"])

    def test_catalog_resource_collision_with_foreign_email_is_rejected(self):
        text = "marketing_123 - other@example.test - ACTIVE"
        identity = {"user_id": "user_1", "all_emails": ["subject@example.test"],
                    "all_phones": [], "all_email_hashes": [],
                    "lineage_resource_ids": ["marketing_123"]}
        with patch("code.evidence._read_text", return_value=text):
            self.assertEqual(parse_text_evidence(Path("screen.txt"), identity), [])

    def test_text_parser_rejects_service_and_event_names_as_resources(self):
        text = (
            'service=account_service event=analytics_profile_scan_started '
            'resource_id=account_123 email=amina.elmasri@gmail.com'
        )
        with patch("code.evidence._read_text", return_value=text):
            hits = parse_log_evidence(Path("trace.log"), self.identity("amina.elmasri@gmail.com"))
        self.assertEqual([hit["resource_id"] for hit in hits], ["account_123"])

    def test_image_uses_vision_fallback_when_tesseract_is_unavailable(self):
        identity = {
            "user_id": "user_1", "all_emails": ["a@example.test"],
            "all_phones": [], "all_email_hashes": [],
        }
        transcription = (
            "service=search_service resource_id=search_1 state=PRESENT "
            "email=a@example.test"
        )
        with patch("code.evidence._extract_image_text", return_value=""), patch(
            "code.evidence._gemini_vision_text", return_value=transcription
        ):
            hits = parse_image_evidence(Path("screen.png"), identity)
        self.assertEqual(hits[0]["resource_id"], "search_1")
        self.assertEqual(hits[0]["system_id"], "search_service")

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
