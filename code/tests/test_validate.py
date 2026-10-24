import copy
import json
import tempfile
import unittest
from pathlib import Path

import helpers
from loaders import parse_ts
from validate import validate_file, validate_steps

AUDIT_AT = parse_ts("2026-09-01T00:00:00Z")
EV_TIMES = {"evidence_01": parse_ts("2026-08-01T00:00:00Z"), "evidence_99": parse_ts("2026-09-02T00:00:00Z")}


def step(no, phase, system, resource, op, state, ev=""):
    return {"step_no": no, "phase": phase, "system_id": system, "resource_id": resource,
            "operation": op, "state": state, "evidence_id": ev}


INCOMPLETE = [
    step(1, "FINDING", "search_service", "search_1", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_01"),
    step(2, "FINDING", "integration_service", "flow_1", "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", "evidence_01"),
    step(3, "REMEDIATION", "integration_service", "flow_1", "DISABLE_DATA_FLOW", "DISABLED"),
    step(4, "REMEDIATION", "search_service", "search_1", "DELETE_RECORD", "ABSENT"),
    step(5, "VERIFICATION", "account_service", "account_1", "VERIFY_RECORD_ABSENT", "ABSENT"),
    step(6, "VERIFICATION", "search_service", "search_1", "VERIFY_RECORD_ABSENT", "ABSENT"),
    step(7, "VERIFICATION", "integration_service", "flow_1", "VERIFY_DATA_FLOW_DISABLED", "DISABLED"),
]
COMPLETE = [
    step(1, "VERIFICATION", "account_service", "account_1", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_01"),
    step(2, "VERIFICATION", "security_service", "audit_1", "VERIFY_RECORD_PRESENT", "PRESENT", "evidence_01"),
]


def errors_for(status, steps, phase1=False):
    text = steps if isinstance(steps, str) else json.dumps(steps)
    return validate_steps("case_1", status, text, phase1=phase1, audit_at=AUDIT_AT, ev_times=EV_TIMES)


class StepRulesTest(unittest.TestCase):
    def assertError(self, status, steps, fragment, phase1=False):
        errs = errors_for(status, steps, phase1)
        self.assertTrue(any(fragment in e for e in errs), f"expected {fragment!r} in {errs}")

    def mutate(self, base, index, **changes):
        steps = copy.deepcopy(base)
        steps[index].update(changes)
        return steps

    def test_valid_rows_pass(self):
        self.assertEqual(errors_for("INCOMPLETE", INCOMPLETE), [])
        self.assertEqual(errors_for("COMPLETE", COMPLETE), [])
        self.assertEqual(errors_for("NOT_APPLICABLE", []), [])

    def test_status_enum(self):
        self.assertError("DONE", COMPLETE, "bad deletion_status")

    def test_steps_json_parses(self):
        self.assertError("COMPLETE", "[{bad json", "not valid JSON")

    def test_steps_json_is_array(self):
        self.assertError("COMPLETE", '{"step_no": 1}', "not a JSON array")

    def test_not_applicable_needs_empty_array(self):
        self.assertError("NOT_APPLICABLE", COMPLETE, "NOT_APPLICABLE must have steps_json=[]")

    def test_placeholder_only_in_phase1(self):
        self.assertError("INCOMPLETE", [], "must have at least one step")
        self.assertEqual(errors_for("INCOMPLETE", [], phase1=True), [])
        self.assertError("COMPLETE", [], "must have at least one step", phase1=True)

    def test_step_no_starts_at_one_and_is_consecutive(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, step_no=0), "step_no must be 1")
        self.assertError("COMPLETE", self.mutate(COMPLETE, 1, step_no=3), "step_no must be 2")
        self.assertError("COMPLETE", self.mutate(COMPLETE, 1, step_no="2"), "step_no must be 2")

    def test_exact_keys(self):
        steps = copy.deepcopy(COMPLETE)
        steps[0]["extra"] = 1
        del steps[1]["evidence_id"]
        self.assertError("COMPLETE", steps, "keys mismatch")

    def test_bad_phase(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, phase="CHECK"), "bad phase")

    def test_bad_operation(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, operation="VERIFY_GONE"), "bad operation")

    def test_operation_phase_pair(self):
        self.assertError("INCOMPLETE", self.mutate(INCOMPLETE, 0, phase="VERIFICATION"),
                         "not allowed in phase")

    def test_operation_state_pair(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, state="PRESENT"), "needs state ABSENT")

    def test_canonical_order(self):
        steps = copy.deepcopy(INCOMPLETE)
        steps[2], steps[3] = steps[3], steps[2]  # DELETE before DISABLE
        for i, s in enumerate(steps, start=1):
            s["step_no"] = i
        self.assertError("INCOMPLETE", steps, "canonical order")

    def test_canonical_order_by_system_then_resource(self):
        steps = [step(1, "VERIFICATION", "search_service", "s_1", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_01"),
                 step(2, "VERIFICATION", "account_service", "a_1", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_01")]
        self.assertError("COMPLETE", steps, "canonical order")

    def test_complete_only_verification(self):
        steps = [step(1, "FINDING", "search_service", "s_1", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_01")]
        self.assertError("COMPLETE", steps, "COMPLETE allows only VERIFICATION")

    def test_complete_cites_evidence(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, evidence_id=""), "must cite evidence")

    def test_incomplete_finding_cites_evidence(self):
        self.assertError("INCOMPLETE", self.mutate(INCOMPLETE, 0, evidence_id=""), "FINDING must cite evidence")

    def test_incomplete_remediation_has_empty_evidence(self):
        self.assertError("INCOMPLETE", self.mutate(INCOMPLETE, 2, evidence_id="evidence_01"),
                         'REMEDIATION must have evidence_id ""')

    def test_incomplete_verification_has_empty_evidence(self):
        self.assertError("INCOMPLETE", self.mutate(INCOMPLETE, 5, evidence_id="evidence_01"),
                         'VERIFICATION must have evidence_id ""')

    def test_evidence_after_audit_at(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, evidence_id="evidence_99"), "after audit_at")

    def test_unknown_evidence(self):
        self.assertError("COMPLETE", self.mutate(COMPLETE, 0, evidence_id="evidence_404"), "unknown evidence_id")

    def test_duplicate_step(self):
        steps = [copy.deepcopy(COMPLETE[0]), copy.deepcopy(COMPLETE[0])]
        steps[1]["step_no"] = 2
        self.assertError("COMPLETE", steps, "duplicate step")


class FileRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.ids = ["case_9", "case_33", "case_100"]  # numeric order != lexicographic order
        self.requests = helpers.write_requests(self.dir / "requests.csv", self.ids)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, rows, header=None):
        out = helpers.write_rows(self.dir / "out.csv", rows, header)
        return validate_file(out, self.requests, phase1=True, check_evidence=False)

    def good_rows(self):
        return [[cid, "NOT_APPLICABLE", "[]"] for cid in self.ids]

    def assertFileError(self, rows, fragment, header=None):
        errs = self.check(rows, header)
        self.assertTrue(any(fragment in e for e in errs), f"expected {fragment!r} in {errs}")

    def test_valid_file(self):
        self.assertEqual(self.check(self.good_rows()), [])

    def test_exact_header(self):
        self.assertFileError(self.good_rows(), "header must be", header=["case_id", "status", "steps_json"])

    def test_one_row_per_case_missing(self):
        self.assertFileError(self.good_rows()[:2], "missing case_id")

    def test_one_row_per_case_extra(self):
        self.assertFileError([*self.good_rows(), ["case_500", "NOT_APPLICABLE", "[]"]], "unknown case_id")

    def test_duplicate_case(self):
        rows = self.good_rows()
        self.assertFileError([*rows, rows[0]], "duplicate case_id")

    def test_numeric_sort(self):
        rows = sorted(self.good_rows())  # lexicographic: case_100, case_33, case_9
        self.assertFileError(rows, "not sorted by numeric case_id")

    def test_column_count(self):
        rows = self.good_rows()
        rows[0] = rows[0] + ["x"]
        self.assertFileError(rows, "expected 3 columns")

    def test_phase1_placeholder_file(self):
        rows = [[cid, "INCOMPLETE", "[]"] for cid in self.ids]
        self.assertEqual(self.check(rows), [])
        out = helpers.write_rows(self.dir / "out.csv", rows)
        self.assertTrue(validate_file(out, self.requests, phase1=False, check_evidence=False))


if __name__ == "__main__":
    unittest.main()
