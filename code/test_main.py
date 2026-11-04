"""
test_main.py — tests that one bad case never stops the run.

Run from the repo root with:
    python3 code/test_main.py
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import main
from identity_resolver import IdentityResolver

DATASET_DIR = Path(__file__).parent.parent / "dataset"

DELETION_CASE = {
    "case_id": "case_test",
    "email": "oliver-bennett@gmail.com",
    "requested_at": "2026-09-01T00:00:00Z",
    "reported_status": "COMPLETE",
    "reported_at": "2026-09-02T00:00:00Z",
    "audit_at": "2026-10-01T00:00:00Z",
    "request_text": "Please delete my account.",
}


@unittest.skipUnless((DATASET_DIR / "user_identities.csv").exists(), "dataset not present")
class TestRunCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.resolver = IdentityResolver(DATASET_DIR / "user_identities.csv",
                                        DATASET_DIR / "user_audit_log.csv")

    def _run(self, case):
        err = io.StringIO()
        with redirect_stderr(err):
            result = main.run_case(case, self.resolver)
        return result, err.getvalue()

    def test_normal_case(self):
        # P3 note: originally asserted the placeholder result ("INCOMPLETE", "[]").
        # With the real policy engine the case is decided from evidence, so this
        # checks the test's intent: it runs, is not an error, and yields a
        # contract status with a JSON step array.
        (status, steps_json, label, failed), _ = self._run(DELETION_CASE)
        self.assertFalse(failed)
        self.assertIn(status, ("COMPLETE", "INCOMPLETE"))
        self.assertIsInstance(json.loads(steps_json), list)
        self.assertEqual(label, "IS_DELETION")

    def test_not_applicable(self):
        case = dict(DELETION_CASE, request_text="Please don't delete my account.")
        (status, steps_json, _, failed), _ = self._run(case)
        self.assertEqual((status, steps_json, failed), ("NOT_APPLICABLE", "[]", False))

    def test_exception_in_teammate_code_gives_incomplete(self):
        with mock.patch.object(main, "find_records", side_effect=RuntimeError("boom")):
            (status, steps_json, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, steps_json, failed), ("INCOMPLETE", "[]", True))
        self.assertIn("case_test", err)
        self.assertIn("boom", err)

    def test_decide_returning_none_gives_incomplete(self):
        with mock.patch.object(main, "decide", return_value=None):
            (status, steps_json, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, failed), ("INCOMPLETE", True))
        self.assertIn("decide() must return a dict", err)

    def test_build_steps_returning_non_list_gives_incomplete(self):
        with mock.patch.object(main, "build_steps", return_value="oops"):
            (status, _, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, failed), ("INCOMPLETE", True))
        self.assertIn("build_steps() must return a list", err)

    def test_naive_audit_at_does_not_crash(self):
        # P3 note: originally expected the placeholder status INCOMPLETE. A naive
        # audit_at is read as UTC, so it must give the same decision as "...Z".
        case = dict(DELETION_CASE, audit_at="2026-10-01 00:00:00")
        (status, steps, _, failed), _ = self._run(case)
        (status_z, steps_z, _, _), _ = self._run(dict(DELETION_CASE, audit_at="2026-10-01T00:00:00Z"))
        self.assertFalse(failed)
        self.assertEqual((status, steps), (status_z, steps_z))

    def test_empty_audit_at_warns_but_runs(self):
        case = dict(DELETION_CASE, audit_at="")
        (status, _, _, failed), err = self._run(case)
        self.assertEqual((status, failed), ("INCOMPLETE", False))
        self.assertIn("empty timestamp (case_test audit_at)", err)

    def test_bad_audit_at_gives_incomplete(self):
        case = dict(DELETION_CASE, audit_at="not a date")
        (status, _, _, failed), err = self._run(case)
        self.assertEqual((status, failed), ("INCOMPLETE", True))
        self.assertIn("cannot parse timestamp", err)

    def test_missing_request_text_gives_incomplete(self):
        case = {k: v for k, v in DELETION_CASE.items() if k != "request_text"}
        (status, _, _, failed), _ = self._run(case)
        self.assertEqual((status, failed), ("INCOMPLETE", True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
