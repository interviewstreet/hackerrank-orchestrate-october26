import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
import main as pipeline
from loaders import case_number, load_requests
from validate import validate_file


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = pipeline.build_context()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_case_number(self):
        self.assertEqual(case_number("case_100"), 100)
        self.assertLess(case_number("case_33"), case_number("case_100"))
        with self.assertRaises(ValueError):
            case_number("100")

    def test_rows_are_in_numeric_order(self):
        ids = ["case_100", "case_9", "case_33"]
        requests = helpers.write_requests(self.dir / "req.csv", ids)
        out = self.dir / "out.csv"
        pipeline.write_output(pipeline.run_cases(load_requests(requests), self.ctx), out)
        with open(out, encoding="utf-8", newline="") as handle:
            got = [row["case_id"] for row in csv.DictReader(handle)]
        self.assertEqual(got, ["case_9", "case_33", "case_100"])

    def test_one_bad_case_does_not_stop_the_run(self):
        ids = ["case_1", "case_2", "case_3"]
        requests = load_requests(helpers.write_requests(self.dir / "req.csv", ids))
        real = pipeline.run_case

        def flaky(req, ctx):
            if req.case_id == "case_2":
                raise RuntimeError("boom")
            return real(req, ctx)

        with mock.patch.object(pipeline, "run_case", flaky), mock.patch("sys.stderr"):
            results = pipeline.run_cases(requests, self.ctx)
        self.assertEqual([r.case_id for r in results], ids)
        self.assertEqual(results[1].flags, ["case_error"])

    def test_serialization_is_compact_and_sorted(self):
        text = pipeline.serialize_steps([{"step_no": 1, "phase": "VERIFICATION", "evidence_id": "e"}])
        self.assertEqual(text, '[{"evidence_id":"e","phase":"VERIFICATION","step_no":1}]')
        self.assertEqual(json.loads(text)[0]["step_no"], 1)

    def test_full_run_is_valid_in_phase1_mode(self):
        out = self.dir / "output.csv"
        pipeline.main(["--out", str(out)])
        requests = helpers.CODE_DIR.parent / "dataset" / "deletion_requests.csv"
        self.assertEqual(validate_file(out, requests, phase1=True), [])


if __name__ == "__main__":
    unittest.main()
