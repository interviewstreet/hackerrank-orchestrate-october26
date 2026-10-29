import unittest
import tempfile
from pathlib import Path
from code.remediation import plan_remediation
from code.decision import classify_requests

class TestRemediation(unittest.TestCase):
    def setUp(self):
        # Minimal identities and rules
        self.identities = [{"user_id": "u123", "email": "user@example.com", "name": "U", "phone": "1", "email_hash": "h", "snapshot_update_time": "2026-01-01T00:00:00Z"}]
        self.audit_log = []
        self.system_activity = []
        self.deletion_rules = [{"required_action": "DELETE", "data_category": "records"}]
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        # Helper to create evidence
    def _create_evidence(self, system_id, category, content, captured_at):
        ev_dir = Path(self.tmp_dir.name) / "evidence" / system_id
        ev_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{category}.txt"
        file_path = ev_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return {
            "file_id": f"evidence_{system_id}_{category}",
            "file_path": str(file_path),
            "origin": "test",
            "captured_at": captured_at,
        }

    def test_missing_marker_generates_steps(self):
        ev = self._create_evidence("systemA", "records", "some info", "2026-09-01T00:00:00Z")
        request = {"case_id": "c1", "email": "user@example.com", "audit_at": "2026-10-01T00:00:00Z"}
        steps = plan_remediation(request, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        self.assertEqual(len(steps), 3)  # FINDING, REMEDIATION, VERIFICATION
        self.assertEqual(steps[0]["phase"], "FINDING")
        self.assertEqual(steps[0]["system_id"], "systemA")
        self.assertEqual(steps[0]["resource_id"], "records_resource")
        self.assertEqual(steps[0]["evidence_id"], ev["file_id"])
        # step numbers consecutive
        self.assertEqual([s["step_no"] for s in steps], [1,2,3])
        # remediation operation matches mapping
        self.assertEqual(steps[1]["operation"], "DELETE_RECORD")
        self.assertEqual(steps[2]["operation"], "VERIFY_RECORD_ABSENT")

    def test_marker_proves_completion_no_steps(self):
        ev = self._create_evidence("systemB", "records", "DELETE_CONFIRMED", "2026-09-01T00:00:00Z")
        request = {"case_id": "c2", "email": "user@example.com", "audit_at": "2026-10-01T00:00:00Z"}
        steps = plan_remediation(request, self.identities, self.audit_log, self.system_activity, self.deletion_rules, [ev])
        # Since evidence proves deletion, status should be COMPLETE -> no steps
        self.assertEqual(steps, [])

if __name__ == "__main__":
    unittest.main()
