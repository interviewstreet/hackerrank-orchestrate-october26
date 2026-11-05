"""Draft generation from real engine results (mini dataset): customer-safe by default, internal notes opt-in."""
import re

import pytest

from engine.case_analyzer import analyze_case, build_context
from minidata import build_mini_dataset
from emailkit import make_service
from integrations.email.draft_generator import build_draft

INTERNAL_ID = re.compile(r"\b(?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|legal_hold|"
                         r"marketing|object|cache)_\d+\b|\bevidence_\d+\b")


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    d = build_mini_dataset(tmp_path_factory.mktemp("mini"))
    ec = build_context(d)
    return [analyze_case(r, ec) for r in ec.ctx.requests]


def test_every_status_gets_a_requester_safe_draft(results):
    assert {r.deletion_status for r in results} >= {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}
    for r in results:
        d = build_draft(r)
        assert r.case_id in d.subject and "\n" not in d.subject
        assert not INTERNAL_ID.search(d.subject + d.body_text), "requester email leaked an internal id"
        assert d.meta["deletion_status"] == r.deletion_status and d.meta["audience"] == "requester"


def test_status_wording_matches_engine_status(results):
    for r in results:
        body = build_draft(r).body_text
        if r.deletion_status == "COMPLETE":
            assert "removed or is held" in body and "still stored" not in body
        elif r.deletion_status == "INCOMPLETE":
            assert "still stored" in body and "removed or is held" not in body
        else:
            assert "not a request to delete" in body


def test_explanation_is_only_used_for_the_internal_audience(results):
    r = next(x for x in results if x.deletion_status == "INCOMPLETE")
    note = "Data remains in account_001 (evidence_01)."
    assert note not in build_draft(r, explanation=note).body_text                           # default: never leaked
    internal = build_draft(r, explanation=note, review_needed=True, review_reason="lookalike email", audience="internal")
    assert note in internal.body_text and "lookalike email" in internal.body_text and internal.meta["explanation_used"]


def test_bad_inputs(results):
    with pytest.raises(ValueError):
        build_draft(results[0], audience="public")
    with pytest.raises(ValueError):
        build_draft({"case_id": "c", "deletion_status": "UNKNOWN"})


def test_create_draft_from_case_enters_the_workflow_as_a_draft(results):
    svc, fake = make_service()
    rec, created = svc.create_draft_from_case(results[0], "person@example.test")
    assert created and rec.state == "DRAFT" and rec.case_id == results[0].case_id and fake.calls == []
    again, created2 = svc.create_draft_from_case(results[0].to_dict(), "person@example.test")   # dict form works too
    assert not created2 and again.id == rec.id


def _case(steps, status="INCOMPLETE"):
    return {"case_id": "case_x", "deletion_status": status,
            "summary": {"systems_checked": 3, "findings_count": 2, "remediation_count": 4, "verification_count": 3},
            "steps": [{"system_id": s} for s in steps]}


def test_incomplete_email_says_in_progress_and_names_only_systems_the_case_touches():
    body = build_draft(_case(["account_service", "search_service", "integration_service", "backup_service"])).body_text
    assert "case_x" in body and "still in progress" in body
    for phrase in ("account and identity databases", "search indexes and caches",
                   "connected services that copy data between systems", "backup and retention systems"):
        assert phrase in body
    assert "analytics" not in body and "application logs" not in body          # not touched by this case
    assert "only once those checks have passed" in body                           # confirmation follows verification
    assert "not able to promise a completion date" in body and "retention policy requires it" in body   # no date guarantee; retention respected
    assert "has been deleted" not in body and "is complete" not in body           # never claims completion early


def test_incomplete_email_without_known_systems_omits_the_clause_but_stays_valid():
    body = build_draft(_case([])).body_text
    assert "following kinds of system" not in body and "still in progress" in body and "{" not in body


def test_incomplete_email_never_shows_internal_system_ids(results):
    for r in (x for x in results if x.deletion_status == "INCOMPLETE"):
        body = build_draft(r).body_text
        assert not INTERNAL_ID.search(body) and "_service" not in body and "_platform" not in body


def test_complete_and_not_applicable_wording_is_unchanged():
    assert "removed or is held" in build_draft(_case(["account_service"], "COMPLETE")).body_text
    assert "following kinds of system" not in build_draft(_case(["account_service"], "COMPLETE")).body_text
