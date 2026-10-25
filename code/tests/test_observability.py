import ast
import csv
import json
import tempfile
import unittest
from pathlib import Path

from code.evaluation.observability import (
    ABSENT,
    POST_AUDIT,
    _context_linked,
    _expected_resources,
    render_report,
)


class ObservabilityAuditTests(unittest.TestCase):
    def test_expected_resources_are_deduplicated_per_case(self):
        steps = [
            {"resource_id": "account_1"},
            {"resource_id": "account_1"},
            {"resource_id": "audit_record_2"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample_output.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["case_id", "deletion_status", "steps_json"]
                )
                writer.writeheader()
                writer.writerow({
                    "case_id": "case_x", "deletion_status": "COMPLETE",
                    "steps_json": json.dumps(steps),
                })
            self.assertEqual(
                _expected_resources(path)["case_x"],
                ["account_1", "audit_record_2"],
            )

    def test_linkage_requires_identifier_near_resource(self):
        occurrences = [{
            "text": "resource_id=account_1 subject=user_1 " + "x" * 1400
                    + " subject=user_2 resource_id=account_2"
        }]
        self.assertTrue(_context_linked(occurrences, "account_1", ["user_1"]))
        self.assertFalse(_context_linked(occurrences, "account_1", ["user_2"]))

    def test_report_marks_failed_gate_and_never_exports_runtime_mapping(self):
        result = {
            "pre_audit_candidates": 1,
            "total_case_resources": 3,
            "candidate_recall": 1 / 3,
            "gate_passed": False,
            "counts": {ABSENT: 1, POST_AUDIT: 1, "PRE_AUDIT_UNLINKED": 1},
            "blocked": [
                {"case_id": "case_x", "resource_id": "audit_record_x",
                 "audit_at": "2026-01-01T00:00:00Z", "category": ABSENT,
                 "post_audit_sources": []},
            ],
        }
        report = render_report(result)
        self.assertIn("100% observability gate: **FAIL**", report)
        self.assertIn("`audit_record_x`", report)
        self.assertNotIn("lineage_resource_ids", report)

    def test_prediction_modules_do_not_import_evaluation_diagnostic(self):
        code_root = Path("code")
        for path in code_root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            self.assertNotIn("code.evaluation.observability", imported, path.name)
