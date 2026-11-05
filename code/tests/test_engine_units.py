"""State reconstruction and policy decisions on synthetic observations (no dataset needed)."""
import pytest

from engine.contracts import Coverage, Observation
from engine.evidence_loader import EvidenceStore
from engine.policy_engine import evaluate
from engine.state_reconstructor import ResourceState, reconstruct

RULES = {"SEARCH_INDEX_ENTRY": {"rule_id": "r3", "required_action": "DELETE"},
         "SECURITY_AUDIT_LOG": {"rule_id": "r12", "required_action": "RETAIN"},
         "BACKUP_ARCHIVE": {"rule_id": "r14", "required_action": "RETAIN"},
         "ACCOUNT_TOMBSTONE": {"rule_id": "r15", "required_action": "REDACT"},
         "ANALYTICS_PROFILE": {"rule_id": "r7", "required_action": "ANONYMIZE"}}


class Ctx:
    rules = RULES


def obs(ev, rid, state, t, cat="SEARCH_INDEX_ENTRY", sys="search_service", fmt="sql", file_t=None, **kw):
    return Observation(evidence_id=ev, captured_at=file_t or t, system_id=sys, resource_id=rid, data_category=cat,
                       state=state, observed_at=t, source_format=fmt, file_captured_at=file_t or t, **kw)


def store(observations, coverage=()):
    s = EvidenceStore()
    s.observations = list(observations)
    s.coverage = list(coverage)
    s.index()
    return s


def test_latest_observation_before_audit_wins():
    s = store([obs("e1", "search_1", "PRESENT", "2026-01-01T00:00:00Z"), obs("e2", "search_1", "ABSENT", "2026-02-01T00:00:00Z")])
    assert reconstruct(s, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-03-01T00:00:00Z").state == "ABSENT"
    assert reconstruct(s, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-01-15T00:00:00Z").state == "PRESENT"


def test_evidence_from_a_file_captured_after_audit_is_not_used():
    s = store([obs("e1", "search_1", "PRESENT", "2026-01-01T00:00:00Z"),
               obs("e2", "search_1", "ABSENT", "2026-01-10T00:00:00Z", file_t="2026-06-01T00:00:00Z")])
    st = reconstruct(s, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-02-01T00:00:00Z")
    assert st.state == "PRESENT" and st.evidence_id == "e1"


def test_retained_record_missing_from_later_snapshot_is_not_treated_as_deleted():
    cov = [Coverage("e2", "2026-02-01T00:00:00Z", "security_service", "", "sql", "t", replica="primary", file_captured_at="2026-02-01T00:00:00Z")]
    s = store([obs("e1", "audit_record_1", "PRESENT", "2026-01-01T00:00:00Z", cat="SECURITY_AUDIT_LOG", sys="security_service")], cov)
    st = reconstruct(s, "audit_record_1", "security_service", "SECURITY_AUDIT_LOG", "2026-03-01T00:00:00Z")
    assert st.state == "PRESENT"


def test_absence_needs_a_later_full_snapshot_covering_the_system():
    cov = [Coverage("e2", "2026-02-01T00:00:00Z", "search_service", "", "sql", "t", replica="primary", file_captured_at="2026-02-01T00:00:00Z")]
    s = store([obs("e1", "search_1", "PRESENT", "2026-01-01T00:00:00Z")], cov)
    st = reconstruct(s, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-03-01T00:00:00Z")
    assert st.state == "ABSENT" and st.evidence_id == "e2"
    lookup = [Coverage("e3", "2026-02-01T00:00:00Z", "search_service", "", "json_lookup", "t", replica="primary", file_captured_at="2026-02-01T00:00:00Z")]
    s2 = store([obs("e1", "search_1", "PRESENT", "2026-01-01T00:00:00Z")], lookup)
    assert reconstruct(s2, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-03-01T00:00:00Z").state == "PRESENT"


def test_a_copy_on_another_replica_keeps_the_record_alive():
    cov = [Coverage("e2", "2026-02-01T00:00:00Z", "search_service", "", "sql", "t", replica="primary", file_captured_at="2026-02-01T00:00:00Z")]
    o = obs("e1", "search_1", "PRESENT", "2026-01-01T00:00:00Z")
    o.attrs["replica"] = "failover_replica"
    st = reconstruct(store([o], cov), "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-03-01T00:00:00Z")
    assert st.state == "PRESENT"                      # the primary-only snapshot cannot prove the failover copy is gone


def _rs(cat, state, **kw):
    return ResourceState("x_1", "sys", cat, state, evidence_id="e1", **kw)


@pytest.mark.parametrize("cat,state,compliant,op", [
    ("SEARCH_INDEX_ENTRY", "PRESENT", False, "DELETE_RECORD"),
    ("SEARCH_INDEX_ENTRY", "ABSENT", True, ""),
    ("BACKUP_ARCHIVE", "ACTIVE", False, "BLOCK_RESTORE"),
    ("BACKUP_ARCHIVE", "BLOCKED", True, ""),
    ("DATA_FLOW", "ACTIVE", False, "DISABLE_DATA_FLOW"),
    ("DATA_FLOW", "DISABLED", True, ""),
    ("SECURITY_AUDIT_LOG", "PRESENT", True, ""),
])
def test_policy_decisions(cat, state, compliant, op):
    d = evaluate(Ctx, _rs(cat, state), "2026-03-01T00:00:00Z")
    assert d.compliant is compliant and d.remediation_op == op


def test_audit_log_is_never_scheduled_for_deletion():
    d = evaluate(Ctx, _rs("SECURITY_AUDIT_LOG", "PRESENT"), "2026-03-01T00:00:00Z")
    assert d.verification_op == "VERIFY_RECORD_PRESENT" and not d.remediation_op


def test_tombstone_with_identifiers_must_be_redacted():
    d = evaluate(Ctx, _rs("ACCOUNT_TOMBSTONE", "PRESENT", exposed=True, exposed_fields=["email"]), "2026-03-01T00:00:00Z")
    assert not d.compliant and d.remediation_op == "REDACT_RECORD"
