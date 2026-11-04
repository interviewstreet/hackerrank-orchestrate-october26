import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.invariants import check_rows    # noqa: E402


def _context(root):
    audit, captured = {}, {}
    for name in ("deletion_requests.csv", "sample_deletion_requests.csv"):
        with open(root / "dataset" / name, encoding="utf-8", newline="") as fh:
            audit.update({r["case_id"]: r["audit_at"] for r in csv.DictReader(fh)})
    with open(root / "dataset" / "evidence_files.csv", encoding="utf-8", newline="") as fh:
        captured = {r[0]: r[-1] for r in csv.reader(fh) if r and r[0].startswith("evidence_")}
    return audit, captured


def test_generated_output_obeys_policy_and_time_rules(root):
    audit, captured = _context(root)
    with open(root / "output.csv", encoding="utf-8", newline="") as fh:
        assert check_rows(csv.DictReader(fh), audit, captured) == []


def test_invariants_accept_the_public_answer_key(root):
    audit, captured = _context(root)
    with open(root / "dataset" / "sample_output.csv", encoding="utf-8", newline="") as fh:
        assert check_rows(csv.DictReader(fh), audit, captured) == []


def test_invariants_catch_a_deleted_audit_record(root):
    audit, captured = _context(root)
    bad = [{"case_id": "case_01", "deletion_status": "INCOMPLETE", "steps_json":
            '[{"step_no":1,"phase":"REMEDIATION","system_id":"security_service","resource_id":"audit_record_1",'
            '"operation":"DELETE_RECORD","state":"ABSENT","evidence_id":""}]'}]
    assert any("not allowed" in p for p in check_rows(bad, audit, captured))


def test_invariants_catch_evidence_captured_after_audit(root):
    audit, captured = _context(root)
    late = max(captured, key=captured.get)
    bad = [{"case_id": "case_01", "deletion_status": "COMPLETE", "steps_json":
            f'[{{"step_no":1,"phase":"VERIFICATION","system_id":"account_service","resource_id":"account_1",'
            f'"operation":"VERIFY_RECORD_ABSENT","state":"ABSENT","evidence_id":"{late}"}}]'}]
    assert any("after audit_at" in p for p in check_rows(bad, audit, captured))


def test_activity_after_audit_is_not_used(ec):
    from engine.case_analyzer import analyze_case
    r = dict(next(x for x in ec.ctx.sample_requests if x["case_id"] == "case_26"))
    r["audit_at"] = "2026-09-02T09:00:00Z"          # before the deletion worker acted
    res = analyze_case(r, ec)
    assert res.deletion_status != "COMPLETE" and not res.steps
