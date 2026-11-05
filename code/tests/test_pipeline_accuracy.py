import csv
import json

from engine.case_analyzer import analyze_case
from engine.pipeline import run_cases


def _expected(root):
    with open(root / "dataset" / "sample_output.csv", encoding="utf-8", newline="") as fh:
        return {r["case_id"]: r for r in csv.DictReader(fh)}


def test_sample_status_accuracy_is_perfect(ec, root):
    exp = _expected(root)
    wrong = [r.case_id for r in run_cases(ec.ctx.sample_requests, ec) if r.deletion_status != exp[r.case_id]["deletion_status"]]
    assert wrong == []


def test_sample_step_f1_floor(ec, root):
    exp = _expected(root)
    key = lambda s: (s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"])
    tp = pred = tot = 0
    for r in run_cases(ec.ctx.sample_requests, ec):
        p = {key(s) for s in r.steps}
        e = {key(s) for s in json.loads(exp[r.case_id]["steps_json"])}
        tp += len(p & e); pred += len(p); tot += len(e)
    precision, recall = tp / pred, tp / tot
    assert 2 * precision * recall / (precision + recall) >= 0.97


def test_results_are_deterministic(ec):
    first = [analyze_case(r, ec).steps for r in ec.ctx.sample_requests[:8]]
    second = [analyze_case(r, ec).steps for r in ec.ctx.sample_requests[:8]]
    assert first == second


def test_not_applicable_cases_have_no_steps(ec):
    na = [analyze_case(r, ec) for r in ec.ctx.requests if r["case_id"] in {f"case_{n}" for n in range(533, 543)}]
    assert len(na) == 10 and all(r.deletion_status == "NOT_APPLICABLE" and r.steps == [] for r in na)


def test_result_matches_shared_contract(ec):
    res = analyze_case(ec.ctx.sample_requests[0], ec)
    for k in ("case_id", "deletion_status", "summary", "identities", "findings", "steps", "evidence", "graph_data"):
        assert hasattr(res, k)
    assert set(res.summary) >= {"systems_checked", "findings_count", "remediation_count", "verification_count"}
    assert set(res.graph_data) == {"nodes", "edges"}
