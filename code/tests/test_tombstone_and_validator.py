"""Rule 15 (account tombstone) and the stricter output validator."""
import csv
import json

import pytest

from engine.contracts import Observation
from engine.policy_engine import evaluate
from engine.state_reconstructor import ResourceState
from engine.validate_output import validate_output_csv

RULES = {"ACCOUNT_TOMBSTONE": {"rule_id": "rule_15", "required_action": "REDACT"}}


class _Ctx:
    rules = RULES


def _rs(state, refs=("user_9",), exposed=False, fields=()):
    o = Observation("evidence_1", "2026-09-01T00:00:00Z", "identity_service", "tombstone_9", "ACCOUNT_TOMBSTONE",
                    state, user_refs=list(refs))
    return ResourceState("tombstone_9", "identity_service", "ACCOUNT_TOMBSTONE", state, exposed=exposed,
                         exposed_fields=list(fields), evidence_id="evidence_1", observations=[o])


def test_tombstone_with_only_stable_ref_is_compliant():
    d = evaluate(_Ctx, _rs("PRESENT"), "2026-09-02T00:00:00Z", "user_9")
    assert d.compliant and d.verification_op == "VERIFY_RECORD_REDACTED"


@pytest.mark.parametrize("state", ["ABSENT", "UNKNOWN"])
def test_missing_or_unknown_tombstone_is_not_compliant(state):
    d = evaluate(_Ctx, _rs(state), "2026-09-02T00:00:00Z", "user_9")
    assert not d.compliant and d.remediation_op != "DELETE_RECORD"


def test_tombstone_must_keep_the_stable_user_id():
    assert not evaluate(_Ctx, _rs("PRESENT", refs=("user_1",)), "2026-09-02T00:00:00Z", "user_9").compliant
    assert not evaluate(_Ctx, _rs("PRESENT", refs=()), "2026-09-02T00:00:00Z", "user_9").compliant


def test_exposed_tombstone_is_redacted_never_deleted():
    d = evaluate(_Ctx, _rs("PRESENT", exposed=True, fields=("email", "name")), "2026-09-02T00:00:00Z", "user_9")
    assert (d.finding_op, d.remediation_op, d.verification_op) == (
        "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")


def _write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


def _rows(root):
    return [list(r) for r in csv.reader(open(root / "output.csv", encoding="utf-8", newline=""))]


def _find(rows, status):
    return next(i for i, r in enumerate(rows) if i and r[1] == status)


def _problems(root, tmp_path, rows):
    p = tmp_path / "bad.csv"
    _write(p, rows)
    return validate_output_csv(p, root / "dataset")


def _edit(rows, i, fn):
    steps = json.loads(rows[i][2])
    fn(steps)
    rows[i][2] = json.dumps(steps, separators=(",", ":"))


def test_rejects_not_applicable_object(root, tmp_path):
    rows = _rows(root)
    rows[_find(rows, "NOT_APPLICABLE")][2] = "{}"
    assert any("array" in p for p in _problems(root, tmp_path, rows))


def test_rejects_finding_without_citation(root, tmp_path):
    rows = _rows(root)
    i = _find(rows, "INCOMPLETE")
    _edit(rows, i, lambda s: s[0].__setitem__("evidence_id", ""))
    assert any("no evidence_id" in p for p in _problems(root, tmp_path, rows))


def test_rejects_wrong_phase_order(root, tmp_path):
    rows = _rows(root)
    i = _find(rows, "INCOMPLETE")

    def swap(s):
        s[0], s[-1] = s[-1], s[0]
        for n, st in enumerate(s, 1):
            st["step_no"] = n
    _edit(rows, i, swap)
    assert any("later phase" in p for p in _problems(root, tmp_path, rows))


def test_rejects_complete_without_verification_citation(root, tmp_path):
    rows = _rows(root)
    i = _find(rows, "COMPLETE")
    _edit(rows, i, lambda s: s[0].__setitem__("evidence_id", ""))
    assert any("must cite evidence" in p for p in _problems(root, tmp_path, rows))


def test_rejects_cited_remediation(root, tmp_path):
    rows = _rows(root)
    i = next(i for i, r in enumerate(rows) if i and r[1] == "INCOMPLETE" and '"REMEDIATION"' in r[2])
    def cite(s):
        next(x for x in s if x["phase"] == "REMEDIATION")["evidence_id"] = "evidence_1"
    _edit(rows, i, cite)
    assert any("empty evidence_id" in p for p in _problems(root, tmp_path, rows))
