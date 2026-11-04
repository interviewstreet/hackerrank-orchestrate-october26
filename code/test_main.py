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

    # --- P2 -> P3 contract (CONTRACTS.md, section 1) -----------------------

    def test_find_records_has_exactly_contract_keys(self):
        """P2's real find_records() returns a dict with exactly the 5 keys.
        The values are real evidence now, so only the shape is checked."""
        from evidence_search import find_records
        from models import EVIDENCE_KEYS
        from utils import parse_ts
        audit_at = parse_ts(DELETION_CASE["audit_at"])
        # Same hand-over as main.process_case(): a copy with a parsed audit_at
        evidence_case = dict(DELETION_CASE, audit_at=audit_at)
        identity = self.resolver.resolve(DELETION_CASE["email"], audit_at=audit_at)
        ev = find_records(identity, evidence_case)
        self.assertIsInstance(ev, dict)
        self.assertEqual(set(ev), set(EVIDENCE_KEYS))
        self.assertEqual(set(EVIDENCE_KEYS), {"records", "latest_by_resource",
                                              "referenced_resources", "absence_proofs",
                                              "identifier_provenance"})

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
        # P3 note: originally also asserted status "INCOMPLETE", which was the
        # placeholder decide() output. The real engine decides from evidence
        # (COMPLETE for this case), so only the test's intent is checked: an
        # extra key warns but the case still runs.
        self.assertFalse(failed)
        self.assertIn("extra key(s) debug", err)

    def test_placeholder_decide_has_proposed_p4_keys(self):
        from policy_engine import decide
        from models import empty_evidence
        d = decide(None, empty_evidence(), DELETION_CASE)
        self.assertEqual(d["deletion_status"], "INCOMPLETE")
        for k in ("resources", "flows", "restore_risks", "timeline"):
            self.assertEqual(d[k], [])

    def test_naive_audit_at_does_not_crash(self):
        # P3 note: originally expected the placeholder status INCOMPLETE. A naive
        # audit_at is read as UTC, so it must give the same decision as "...Z".
        case = dict(DELETION_CASE, audit_at="2026-10-01 00:00:00")
        (status, steps, _, failed), _ = self._run(case)
        (status_z, steps_z, _, _), _ = self._run(dict(DELETION_CASE, audit_at="2026-10-01T00:00:00Z"))
        self.assertFalse(failed)
        self.assertEqual((status, steps), (status_z, steps_z))

    def test_empty_audit_at_gives_incomplete_without_search(self):
        """No cut-off -> INCOMPLETE [] and find_records() is never called."""
        for value in ("", "   "):
            with self.subTest(audit_at=value):
                case = dict(DELETION_CASE, audit_at=value)
                with mock.patch.object(main, "find_records") as fr:
                    (status, steps_json, label, failed), err = self._run(case)
                fr.assert_not_called()
                self.assertEqual((status, steps_json, failed), ("INCOMPLETE", "[]", False))
                self.assertEqual(label, "IS_DELETION")
                self.assertIn("empty timestamp (case_test audit_at)", err)
                self.assertIn("case_test: no audit_at", err)

    def test_missing_audit_at_column_gives_incomplete_without_search(self):
        case = {k: v for k, v in DELETION_CASE.items() if k != "audit_at"}
        with mock.patch.object(main, "find_records") as fr:
            (status, steps_json, _, failed), _ = self._run(case)
        fr.assert_not_called()
        self.assertEqual((status, steps_json, failed), ("INCOMPLETE", "[]", False))

    def test_find_records_receives_aware_utc_datetime(self):
        """Including when the CSV value has no timezone (assumed UTC)."""
        from datetime import datetime, timezone
        from models import empty_evidence
        values = {
            "2026-10-01T00:00:00Z": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "2026-10-01 00:00:00": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "2026-10-01T02:00:00+02:00": datetime(2026, 10, 1, tzinfo=timezone.utc),
        }
        for raw, expected in values.items():
            with self.subTest(audit_at=raw):
                case = dict(DELETION_CASE, audit_at=raw)
                with mock.patch.object(main, "find_records",
                                       return_value=empty_evidence()) as fr:
                    (_, _, _, failed), _ = self._run(case)
                self.assertFalse(failed)
                passed = fr.call_args.args[1]["audit_at"]
                self.assertIsInstance(passed, datetime)
                self.assertIsNotNone(passed.tzinfo)
                self.assertEqual(passed.utcoffset().total_seconds(), 0)
                self.assertEqual(passed, expected)

    def test_original_case_dict_not_changed(self):
        from models import empty_evidence
        case = dict(DELETION_CASE, audit_at="2026-10-01 00:00:00")
        before = dict(case)
        with mock.patch.object(main, "find_records",
                               return_value=empty_evidence()) as fr:
            self._run(case)
        self.assertEqual(case, before)
        self.assertIsNot(fr.call_args.args[1], case)
        # The other fields reach P2 unchanged
        passed = dict(fr.call_args.args[1])
        del passed["audit_at"]
        self.assertEqual(passed, {k: v for k, v in before.items() if k != "audit_at"})

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
