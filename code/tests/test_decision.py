import unittest
import tempfile
from pathlib import Path
from code.decision import classify_requests

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        # Minimal dataset structures
        self.identities = [{
            "user_id": "u123",
            "email": "user@example.com",
            "name": "User",
            "phone": "123",
            "email_hash": "hash",
            "snapshot_update_time": "2026-01-01T00:00:00Z",
        }]
        self.audit_log = []
        self.system_activity = []
        self.deletion_rules = [{"required_action": "DELETE", "data_category": "records"}]
        # temporary directory for evidence files
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _create_evidence(self, filename: str, content: str, captured_at: str):
        file_path = Path(self.tmp_dir.name) / filename
        file_path.write_text(content, encoding="utf-8")
        return {
            "file_id": f"evidence_{filename}",
            "file_path": str(file_path),
            "origin": "test",
            "captured_at": captured_at,
        }

    def test_complete_case(self):
        ev = self._create_evidence(
            "evidence.txt",
            "some info\nDELETE_CONFIRMED\n",
            "2026-09-01T00:00:00Z",
        )
        requests = [{"case_id": "c1", "email": "user@example.com", "audit_at": "2026-10-01T00:00:00Z"}]
        result = classify_requests(requests, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        self.assertEqual(result["c1"], "COMPLETE")

    def test_incomplete_missing_marker(self):
        ev = self._create_evidence(
            "evidence.txt",
            "some info without marker",
            "2026-09-01T00:00:00Z",
        )
        requests = [{"case_id": "c2", "email": "user@example.com", "audit_at": "2026-10-01T00:00:00Z"}]
        result = classify_requests(requests, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        self.assertEqual(result["c2"], "INCOMPLETE")

    def test_not_applicable_no_user(self):
        ev = self._create_evidence(
            "evidence.txt",
            "DELETE_CONFIRMED",
            "2026-09-01T00:00:00Z",
        )
        requests = [{"case_id": "c3", "email": "unknown@example.com", "audit_at": "2026-10-01T00:00:00Z"}]
        result = classify_requests(requests, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        self.assertEqual(result["c3"], "NOT_APPLICABLE")

    def test_cutoff_ignores_late_evidence(self):
        ev = self._create_evidence(
            "evidence.txt",
            "DELETE_CONFIRMED",
            "2026-11-01T00:00:00Z",
        )
        requests = [{"case_id": "c4", "email": "user@example.com", "audit_at": "2026-10-01T00:00:00Z"}]
        result = classify_requests(requests, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        self.assertEqual(result["c4"], "INCOMPLETE")

if __name__ == "__main__":
    unittest.main()
