"""
test_main.py — tests that one bad case never stops the run.

Run from the repo root with:
    python3 code/test_main.py
"""
from __future__ import annotations

import io
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
        (status, steps_json, label, failed), _ = self._run(DELETION_CASE)
        self.assertEqual((status, steps_json, failed), ("INCOMPLETE", "[]", False))
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

    # --- P2 -> P3 contract (CONTRACTS.md, section 1) -----------------------

    def test_placeholder_find_records_has_exactly_contract_keys(self):
        from evidence_search import find_records
        from models import EVIDENCE_KEYS
        ev = find_records(self.resolver.resolve("oliver-bennett@gmail.com"), DELETION_CASE)
        self.assertEqual(set(ev), set(EVIDENCE_KEYS))
        self.assertEqual(set(EVIDENCE_KEYS), {"records", "latest_by_resource",
                                              "referenced_resources", "absence_proofs",
                                              "identifier_provenance"})
        self.assertTrue(all(len(v) == 0 for v in ev.values()))

    def test_decide_receives_evidence_dict(self):
        seen = {}

        def fake_decide(identity, evidence, case):
            seen["evidence"] = evidence
            return {"deletion_status": "INCOMPLETE"}

        with mock.patch.object(main, "decide", side_effect=fake_decide):
            (status, _, _, failed), _ = self._run(DELETION_CASE)
        self.assertFalse(failed)
        self.assertIn("absence_proofs", seen["evidence"])

    def test_find_records_returning_list_gives_incomplete(self):
        with mock.patch.object(main, "find_records", return_value=[]):
            (status, steps_json, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, steps_json, failed), ("INCOMPLETE", "[]", True))
        self.assertIn("find_records() must return a dict", err)

    def test_find_records_missing_key_gives_incomplete(self):
        from models import empty_evidence
        bad = empty_evidence()
        del bad["absence_proofs"]
        with mock.patch.object(main, "find_records", return_value=bad):
            (status, _, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, failed), ("INCOMPLETE", True))
        self.assertIn("missing key(s): absence_proofs", err)

    def test_find_records_extra_key_warns_but_runs(self):
        from models import empty_evidence
        with mock.patch.object(main, "find_records",
                               return_value=dict(empty_evidence(), debug=[1])):
            (status, _, _, failed), err = self._run(DELETION_CASE)
        self.assertEqual((status, failed), ("INCOMPLETE", False))
        self.assertIn("extra key(s) debug", err)

    def test_placeholder_decide_has_proposed_p4_keys(self):
        from policy_engine import decide
        from models import empty_evidence
        d = decide(None, empty_evidence(), DELETION_CASE)
        self.assertEqual(d["deletion_status"], "INCOMPLETE")
        for k in ("resources", "flows", "restore_risks", "timeline"):
            self.assertEqual(d[k], [])

    def test_naive_audit_at_does_not_crash(self):
        case = dict(DELETION_CASE, audit_at="2026-10-01 00:00:00")
        (status, _, _, failed), _ = self._run(case)
        self.assertEqual((status, failed), ("INCOMPLETE", False))

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
