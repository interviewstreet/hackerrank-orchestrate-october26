"""Hand-built and custom evaluation test cases exercising ordering, status rules,
and edge-case system recovery scenarios.
"""
import json
from audit.steps import make_step as m, finalize
from audit.validate import validate_row


def test_incomplete_ordering_and_evidence():
    steps = [
        m("VERIFY_RECORD_ABSENT", "search_index", "idx_9"),
        m("DELETE_RECORD", "search_index", "idx_9"),
        m("DISABLE_DATA_FLOW", "sync_job", "job_2"),
        m("REPORT_ACTIVE_DATA_FLOW", "sync_job", "job_2", "act_44"),
        m("REPORT_REMAINING_RECORD", "account_service", "account_005", "evidence_01"),
        m("REDACT_RECORD", "account_service", "tomb_1"),
    ]
    out = finalize("INCOMPLETE", steps)
    assert [s["operation"] for s in out] == [
        "REPORT_REMAINING_RECORD", "REPORT_ACTIVE_DATA_FLOW",
        "DISABLE_DATA_FLOW", "DELETE_RECORD", "REDACT_RECORD", "VERIFY_RECORD_ABSENT"
    ]
    assert [s["step_no"] for s in out] == list(range(1, 7))
    assert all(s["evidence_id"] == "" for s in out if s["phase"] != "FINDING")
    assert validate_row("c", "INCOMPLETE", json.dumps(out)) == []


def test_complete_only_verification_with_evidence():
    steps = [
        m("VERIFY_RECORD_ABSENT", "a", "r1", "evidence_02"),
        m("VERIFY_RECORD_PRESENT", "billing", "inv_1", "evidence_03"),
        m("DELETE_RECORD", "a", "r1")
    ]
    out = finalize("COMPLETE", steps)
    assert all(s["phase"] == "VERIFICATION" for s in out)
    assert validate_row("c", "COMPLETE", json.dumps(out)) == []


def test_not_applicable_empty():
    assert finalize("NOT_APPLICABLE", [m("DELETE_RECORD", "a", "r")]) == []
    assert validate_row("c", "NOT_APPLICABLE", "[]") == []
    assert validate_row("c", "NOT_APPLICABLE", '[{"x":1}]') != []


# Custom Evaluation Case 1: Cross-Region Replica Lag Recreation
def test_custom_case_cross_region_replica_lag():
    """Scenario: Primary account DB deleted profile, but secondary read replica has lag.

    Expected findings, remediation, and post-remediation verification.
    """
    steps = [
        m("REPORT_REMAINING_RECORD", "account_service", "account_replica_01", "evidence_54"),
        m("DELETE_RECORD", "account_service", "account_replica_01"),
        m("VERIFY_RECORD_ABSENT", "account_service", "account_replica_01"),
    ]
    out = finalize("INCOMPLETE", steps)
    assert len(out) == 3
    assert out[0]["operation"] == "REPORT_REMAINING_RECORD"
    assert out[0]["evidence_id"] == "evidence_54"
    assert out[1]["operation"] == "DELETE_RECORD"
    assert out[1]["evidence_id"] == ""
    assert out[2]["operation"] == "VERIFY_RECORD_ABSENT"
    assert out[2]["evidence_id"] == ""
    assert validate_row("eval_case_01", "INCOMPLETE", json.dumps(out)) == []


# Custom Evaluation Case 2: Active Integration Bridge Sync Risk
def test_custom_case_active_sync_bridge_risk():
    """Scenario: Integration data flow connector remains active, threatening data recreation.

    Expected: FINDING(REPORT_ACTIVE_DATA_FLOW) -> REMEDIATION(DISABLE_DATA_FLOW) -> VERIFICATION(VERIFY_DATA_FLOW_DISABLED).
    """
    steps = [
        m("REPORT_ACTIVE_DATA_FLOW", "integration_service", "data_flow_088", "evidence_45"),
        m("DISABLE_DATA_FLOW", "integration_service", "data_flow_088"),
        m("VERIFY_DATA_FLOW_DISABLED", "integration_service", "data_flow_088"),
    ]
    out = finalize("INCOMPLETE", steps)
    assert len(out) == 3
    assert out[0]["phase"] == "FINDING"
    assert out[1]["phase"] == "REMEDIATION"
    assert out[2]["phase"] == "VERIFICATION"
    assert validate_row("eval_case_02", "INCOMPLETE", json.dumps(out)) == []


# Custom Evaluation Case 3: Restore Risk with Concurrent Legal Hold Record
def test_custom_case_restore_risk_and_legal_retention():
    """Scenario: Active backup restore path threatens user data recreation while a legal hold
    record in security_service must be retained without deletion.
    """
    steps = [
        m("REPORT_RESTORE_RISK", "backup_service", "backup_snap_99", "evidence_32"),
        m("BLOCK_RESTORE", "backup_service", "backup_snap_99"),
        m("VERIFY_RESTORE_BLOCKED", "backup_service", "backup_snap_99"),
        m("VERIFY_RECORD_PRESENT", "security_service", "audit_record_777"),
    ]
    out = finalize("INCOMPLETE", steps)
    assert len(out) == 4
    # Finding must be first
    assert out[0]["operation"] == "REPORT_RESTORE_RISK"
    assert out[1]["operation"] == "BLOCK_RESTORE"
    # Verification phase: VERIFY_RECORD_PRESENT then VERIFY_RESTORE_BLOCKED according to OP_RANK
    assert out[2]["operation"] == "VERIFY_RECORD_PRESENT"
    assert out[3]["operation"] == "VERIFY_RESTORE_BLOCKED"
    assert validate_row("eval_case_03", "INCOMPLETE", json.dumps(out)) == []
