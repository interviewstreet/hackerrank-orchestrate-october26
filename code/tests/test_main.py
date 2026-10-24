import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers
import main as pipeline
from loaders import DATASET_DIR, case_number, load_requests
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

    def _failing(self, case_id):
        real = pipeline.run_case

        def flaky(req, ctx):
            if req.case_id == case_id:
                raise RuntimeError("boom")
            return real(req, ctx)
        return mock.patch.object(pipeline, "run_case", flaky)

    def test_one_bad_case_gets_a_conservative_valid_row(self):
        samples = DATASET_DIR / "sample_deletion_requests.csv"
        requests = [r for r in load_requests(samples) if r.case_id in ("case_01", "case_02")]
        with self._failing("case_01"), mock.patch("sys.stderr"):
            results = pipeline.run_cases(requests, self.ctx)
        self.assertEqual([r.case_id for r in results], ["case_01", "case_02"])
        bad = results[0]
        self.assertEqual((bad.status, bad.flags), ("INCOMPLETE", ["case_error", "fallback_row"]))
        self.assertIn(("account_service", "account_001", "VERIFY_RECORD_ABSENT"),
                      {(s["system_id"], s["resource_id"], s["operation"]) for s in bad.steps})
        self.assertTrue(all(s["phase"] == "VERIFICATION" and s["evidence_id"] == "" for s in bad.steps))
        self.assertEqual([s["step_no"] for s in bad.steps], list(range(1, len(bad.steps) + 1)))
        with open(samples, encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        two = helpers.write_rows(self.dir / "two.csv", [r for r in rows[1:] if r[0] in ("case_01", "case_02")],
                                 header=rows[0])
        out = self.dir / "out.csv"
        pipeline.write_output(results, out)
        self.assertEqual(validate_file(out, two), [])

    def test_bad_case_with_no_known_target_fails_loudly(self):
        requests = load_requests(helpers.write_requests(self.dir / "req.csv", ["case_1", "case_2"]))
        with self._failing("case_2"), mock.patch("sys.stderr"), self.assertRaises(pipeline.CaseFailure):
            pipeline.run_cases(requests, self.ctx)

    def test_main_fails_when_the_written_file_is_invalid(self):
        requests = helpers.write_requests(self.dir / "req.csv", ["case_1"])
        invalid = [pipeline.CaseResult("case_1", "INCOMPLETE")]   # INCOMPLETE,[] breaks the contract
        with mock.patch.object(pipeline, "build_context", lambda **kw: self.ctx), \
                mock.patch.object(pipeline, "run_cases", lambda *a, **kw: invalid), mock.patch("sys.stderr"):
            code = pipeline.main(["--no-llm", "--requests", str(requests), "--out", str(self.dir / "o.csv")])
        self.assertEqual(code, 1)

    def test_serialization_is_compact_and_sorted(self):
        text = pipeline.serialize_steps([{"step_no": 1, "phase": "VERIFICATION", "evidence_id": "e"}])
        self.assertEqual(text, '[{"evidence_id":"e","phase":"VERIFICATION","step_no":1}]')
        self.assertEqual(json.loads(text)[0]["step_no"], 1)

    def test_full_run_is_valid(self):
        out = self.dir / "output.csv"
        self.assertEqual(pipeline.main(["--out", str(out)]), 0)   # main validates strictly before success
        requests = helpers.CODE_DIR.parent / "dataset" / "deletion_requests.csv"
        self.assertEqual(validate_file(out, requests), [])


if __name__ == "__main__":
    unittest.main()
