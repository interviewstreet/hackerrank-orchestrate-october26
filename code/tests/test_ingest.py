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

    def test_rejects_duplicate_primary_key(self):
        rows = [{"case_id": "case_1"}, {"case_id": "case_1"}]
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            _index_unique(rows, "case_id", "test.csv")
