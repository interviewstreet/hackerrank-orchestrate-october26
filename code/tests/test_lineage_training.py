import csv
import json
import tempfile
import unittest
from pathlib import Path

from code.lineage_training import (
    _resources,
    build_training_examples,
    render_training_report,
)


class LineageTrainingSetTests(unittest.TestCase):
    def _write_csv(self, path, fieldnames, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_resource_extraction_rejects_service_and_event_names(self):
        text = (
            "account_service audit_record_read_completed "
            "resource_id=account_123 resource_id=audit_record_456"
        )
        self.assertEqual(_resources(text), ["account_123", "audit_record_456"])

    def test_examples_need_no_canonical_output_and_use_disjoint_users(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            evidence = dataset / "evidence"
            evidence.mkdir(parents=True)
            self._write_csv(
                dataset / "user_identities.csv",
                ["user_id", "name", "email", "phone", "email_hash", "updated_at"],
                [
                    {"user_id": "user_1", "name": "A", "email": "a@example.test",
                     "phone": "", "email_hash": "", "updated_at": "2026-01-01T00:00:00Z"},
                    {"user_id": "user_2", "name": "B", "email": "b@example.test",
                     "phone": "", "email_hash": "", "updated_at": "2026-01-01T00:00:00Z"},
                ],
            )
            self._write_csv(
                dataset / "user_audit_log.csv",
                ["audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"],
                [],
            )
            self._write_csv(
                dataset / "system_activity.csv",
                ["activity_id", "event_time", "event_type", "source_system",
                 "target_system", "resource_id", "reported_result", "details"],
                [],
            )
            payload = {"records": [
                {"resource_id": "account_1", "user_id": "user_1",
                 "email": "a@example.test"},
                {"resource_id": "account_2", "user_id": "user_2",
                 "email": "b@example.test"},
            ]}
            (evidence / "records.json").write_text(json.dumps(payload), encoding="utf-8")
            self._write_csv(
                dataset / "evidence_files.csv",
                ["file_id", "file_path", "origin", "captured_at"],
                [{"file_id": "evidence_1", "file_path": "evidence/records.json",
                  "origin": "test", "captured_at": "2026-01-01T00:00:00Z"}],
            )

            examples, summary = build_training_examples(root)
            positives = [row for row in examples if row["label"] == 1]
            negatives = [row for row in examples if row["label"] == 0]
            self.assertEqual(len(positives), 2)
            self.assertEqual(len(negatives), 2)
            self.assertEqual(summary["positives"], 2)
            train = {row["user_id"] for row in examples if row["split"] == "train"}
            validation = {row["user_id"] for row in examples if row["split"] == "validation"}
            self.assertFalse(train & validation)
            # The fixture intentionally has no sample_output.csv; generation succeeds
            # only if canonical output is never loaded.
            self.assertFalse((dataset / "sample_output.csv").exists())

    def test_report_contains_aggregates_not_edge_identifiers(self):
        report = render_training_report({
            "examples": 2, "positives": 1, "hard_negatives": 1, "users": 1,
            "train_examples": 2, "validation_examples": 0,
            "train_users": 1, "validation_users": 0,
            "ambiguous_contexts_excluded": 0, "workflow_edges_added": 0,
            "positive_sources": {"evidence_json": 1},
        })
        self.assertIn("Positive grounded edges: **1**", report)
        self.assertNotIn("resource_id", report)
        self.assertNotIn("user_id", report)
