import tempfile
import unittest
from pathlib import Path

from code.ingest import _index_unique, _rows, load_all


class IngestValidationTests(unittest.TestCase):
    def test_real_dataset_contract_and_counts(self):
        data = load_all(".")
        self.assertEqual(len(data["deletion_requests"]), 518)
        self.assertEqual(len(data["sample_requests"]), 32)
        self.assertEqual(len(data["evidence_manifest"]), 94)
        self.assertEqual(len(data["deletion_rules"]), 15)

    def test_rejects_wrong_csv_schema(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "deletion_requests.csv"
            path.write_text("case_id,email\ncase_1,a@example.test\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "columns do not match contract"):
                _rows(path)

    def test_rejects_timezone_naive_timestamp(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "deletion_requests.csv"
            path.write_text(
                "case_id,email,requested_at,reported_status,reported_at,audit_at,request_text\n"
                "case_1,a@example.test,2026-01-01T00:00:00,COMPLETE,"
                "2026-01-02T00:00:00Z,2026-01-03T00:00:00Z,delete\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "timezone-naive"):
                _rows(path)

    def test_rejects_duplicate_primary_key(self):
        rows = [{"case_id": "case_1"}, {"case_id": "case_1"}]
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            _index_unique(rows, "case_id", "test.csv")
