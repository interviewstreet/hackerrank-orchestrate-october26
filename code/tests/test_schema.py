import json
import unittest

from pydantic import ValidationError

import helpers
import intent
import main as pipeline
import schema
import validate
from schema import OPERATIONS, OutputRow, Step


def _gold_rows():
    import csv
    path = helpers.CODE_DIR.parent / "dataset" / "sample_output.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        return [(r["case_id"], r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(handle)]


class SchemaTest(unittest.TestCase):
    def test_single_source_of_truth(self):
        self.assertIs(validate.OP_RANK, schema.OP_RANK)
        self.assertIs(validate.step_sort_key, schema.step_sort_key)
        self.assertIs(validate.HEADER, schema.HEADER)
        self.assertIs(pipeline.HEADER, schema.HEADER)
        self.assertEqual(set(intent.CLASSES), {label.value for label in schema.IntentLabel})

    def test_operation_table(self):
        self.assertEqual(len(OPERATIONS), 15)
        self.assertEqual(len({op for _, op, _ in OPERATIONS}), 15)
        phases = [phase for phase, _, _ in OPERATIONS]
        self.assertEqual(phases, sorted(phases, key=schema.PHASE_ORDER.index))

    def test_gold_rows_pass_the_models(self):
        for case_id, status, steps in _gold_rows():
            row = OutputRow(case_id=case_id, deletion_status=status, steps=steps)
            self.assertEqual(row.steps_as_dicts(), steps)

    def test_step_rejects_bad_pairs_and_types(self):
        good = {"step_no": 1, "phase": "VERIFICATION", "system_id": "s", "resource_id": "r",
                "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": "e"}
        Step(**good)
        for change in ({"state": "PRESENT"}, {"phase": "FINDING"}, {"step_no": "1"}, {"step_no": 0},
                       {"operation": "VERIFY_GONE"}, {"extra": 1}, {"system_id": ""}):
            with self.assertRaises(ValidationError, msg=str(change)):
                Step(**{**good, **change})

    def test_output_row_rules(self):
        verify = {"step_no": 1, "phase": "VERIFICATION", "system_id": "s", "resource_id": "r",
                  "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": "e"}
        OutputRow(case_id="case_1", deletion_status="INCOMPLETE")  # phase 1 placeholder is allowed here
        bad = [
            dict(deletion_status="NOT_APPLICABLE", steps=[verify]),
            dict(deletion_status="COMPLETE", steps=[{**verify, "evidence_id": ""}]),
            dict(deletion_status="INCOMPLETE", steps=[verify]),           # verification must be ""
            dict(deletion_status="COMPLETE", steps=[{**verify, "step_no": 2}]),
            dict(deletion_status="DONE", steps=[]),
        ]
        for kwargs in bad:
            with self.assertRaises(ValidationError, msg=str(kwargs)):
                OutputRow(case_id="case_1", **kwargs)


if __name__ == "__main__":
    unittest.main()
