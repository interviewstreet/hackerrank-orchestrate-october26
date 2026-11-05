"""Draft -> approval -> send workflow with a mocked Resend. No real email is ever sent."""
import socket
import threading

import pytest

from emailkit import API_KEY, FakeResend, approved_email, make_service
from integrations.email import (ContentChanged, EmailConfig, EmailNotConfigured, EmailNotFound, EmailState,
                                InvalidTransition, NotApproved, ResendError)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Belt and braces: even if a transport were wired wrongly, a real connection attempt fails the test."""
    def refuse(*a, **k):
        raise AssertionError("a test tried to open a real network connection")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr("integrations.email.resend_client.urllib_transport", refuse)


def test_happy_path_sends_exactly_once_with_audit_trail():
    svc, fake = make_service()
    rec, created = svc.create_draft("case_01", "Person@Example.test", "Hello", "Line one\n\nLine two")
    assert created and rec.state == "DRAFT" and rec.recipient == "person@example.test"
    assert svc.submit_for_approval(rec.id, "analyst").state == "PENDING_APPROVAL"
    assert fake.calls == []                                          # nothing sent before approval
    done = svc.approve(rec.id, "reviewer")
    assert done.state == "APPROVED" and done.approved_by == "reviewer" and fake.calls == []
    sent = svc.send(rec.id, "reviewer")
    assert sent.state == "SENT" and sent.resend_id == "resend_1" and sent.sent_at
    call = fake.calls[0]
    assert call["json"]["to"] == ["person@example.test"] and call["json"]["subject"] == "Hello"
    assert call["json"]["text"] == "Line one\n\nLine two" and call["json"]["html"] == "<p>Line one</p><p>Line two</p>"
    assert call["headers"]["Idempotency-Key"] == rec.idempotency_key
    assert call["headers"]["Authorization"] == f"Bearer {API_KEY}"
    trail = [(e["from_state"], e["to_state"]) for e in svc.store.events(rec.id)]
    assert trail == [("", "DRAFT"), ("DRAFT", "PENDING_APPROVAL"), ("PENDING_APPROVAL", "APPROVED"),
                     ("APPROVED", "SENDING"), ("SENDING", "SENT")]


@pytest.mark.parametrize("stop_at", ["DRAFT", "PENDING_APPROVAL", "REJECTED"])
def test_nothing_is_sent_without_approval(stop_at):
    svc, fake = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "B")
    if stop_at != "DRAFT":
        svc.submit_for_approval(rec.id, "a")
    if stop_at == "REJECTED":
        svc.reject(rec.id, "r", "no")
    with pytest.raises(NotApproved):
        svc.send(rec.id, "someone")
    assert fake.calls == [] and svc.store.get(rec.id).state == stop_at


def test_only_pending_can_be_approved_or_rejected():
    svc, _ = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "B")
    with pytest.raises(InvalidTransition):
        svc.approve(rec.id, "r")                                      # a DRAFT cannot skip the queue
    with pytest.raises(InvalidTransition):
        svc.reject(rec.id, "r")
    svc.submit_for_approval(rec.id, "a")
    svc.approve(rec.id, "r")
    with pytest.raises(InvalidTransition):
        svc.approve(rec.id, "r2")                                     # no double approval
    with pytest.raises(InvalidTransition):
        svc.reject(rec.id, "r2")                                      # an approved email cannot be rejected after the fact


def test_actor_must_be_a_named_person():
    svc, _ = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "B")
    svc.submit_for_approval(rec.id, "a")
    for bad in ("", "   ", "x" * 121):
        with pytest.raises(ValueError):
            svc.approve(rec.id, bad)
    assert svc.store.get(rec.id).state == "PENDING_APPROVAL"


def test_reject_then_redraft_then_approve_again():
    svc, fake = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "B")
    svc.submit_for_approval(rec.id, "a")
    r = svc.reject(rec.id, "reviewer", "tone is wrong")
    assert r.state == "REJECTED" and r.rejection_reason == "tone is wrong" and r.rejected_by == "reviewer"
    d = svc.redraft(rec.id, "S2", "B2", "a")
    assert d.state == "DRAFT" and d.revision == 2 and d.rejection_reason == "" and d.subject == "S2"
    svc.submit_for_approval(rec.id, "a"); svc.approve(rec.id, "reviewer")
    assert svc.send(rec.id, "reviewer").state == "SENT" and len(fake.calls) == 1
    with pytest.raises(InvalidTransition):
        svc.redraft(rec.id, "S3", "B3", "a")                          # only REJECTED can be re-drafted


def test_send_twice_never_sends_twice():
    svc, fake = make_service()
    rec = approved_email(svc)
    first = svc.send(rec.id, "r")
    again = svc.send(rec.id, "r")
    assert first.state == again.state == "SENT" and first.resend_id == again.resend_id
    assert len(fake.calls) == 1


def test_duplicate_draft_for_same_case_and_recipient_is_prevented():
    svc, _ = make_service()
    a, c1 = svc.create_draft("case_01", "P@Example.test", "S", "B")
    b, c2 = svc.create_draft("case_01", " p@example.test ", "Other", "Other body")
    assert c1 and not c2 and a.id == b.id and b.subject == "S"       # the first draft wins
    assert svc.create_draft("case_02", "p@example.test", "S", "B")[1]
    assert svc.create_draft("case_01", "q@example.test", "S", "B")[1]
    assert svc.create_draft("case_01", "p@example.test", "S", "B", kind="follow_up")[1]
    assert len(svc.store.list()) == 4


def test_duplicate_draft_after_send_returns_the_sent_email_not_a_new_one():
    svc, fake = make_service()
    rec = approved_email(svc)
    svc.send(rec.id, "r")
    again, created = svc.create_draft("case_01", "person@example.test", "S", "B")
    assert not created and again.state == "SENT" and again.id == rec.id
    assert svc.send(again.id, "r").state == "SENT"                    # still a no-op
    assert len(fake.calls) == 1


def test_concurrent_sends_produce_one_resend_call():
    svc, fake = make_service(FakeResend(delay=0.15))
    rec = approved_email(svc)
    results, errors = [], []

    def go():
        try:
            results.append(svc.send(rec.id, "r").state)
        except Exception as e:                                        # losers see "already sending"
            errors.append(type(e).__name__)

    threads = [threading.Thread(target=go) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(fake.calls) == 1
    assert svc.store.get(rec.id).state == "SENT"
    assert set(errors) <= {"InvalidTransition", "NotApproved"} and results.count("SENT") >= 1   # losers are refused, never re-send


def test_api_failure_marks_failed_and_retry_needs_new_approval_with_same_key():
    fake = FakeResend([(500, {"name": "application_error", "message": "boom"}), (200, {"id": "resend_ok"})])
    svc, _ = make_service(fake)
    rec = approved_email(svc)
    failed = svc.send(rec.id, "r")
    assert failed.state == "FAILED" and "500" in failed.last_error and API_KEY not in failed.last_error
    with pytest.raises(NotApproved):
        svc.send(rec.id, "r")                                         # FAILED never goes straight back to sending
    svc.submit_for_approval(rec.id, "a"); svc.approve(rec.id, "r")
    ok = svc.send(rec.id, "r")
    assert ok.state == "SENT" and ok.resend_id == "resend_ok" and ok.last_error == ""
    assert fake.calls[0]["headers"]["Idempotency-Key"] == fake.calls[1]["headers"]["Idempotency-Key"]


@pytest.mark.parametrize("reply,retryable", [((429, {"name": "rate_limit_exceeded", "message": "slow down"}), True),
                                             ((409, {"name": "concurrent_idempotent_requests", "message": "x"}), True),
                                             ((409, {"name": "invalid_idempotent_request", "message": "x"}), False),
                                             ((403, {"name": "validation_error", "message": "domain not verified"}), False),
                                             ((200, {}), False)])
def test_resend_errors_are_classified(reply, retryable):
    fake = FakeResend([reply])
    svc, _ = make_service(fake)
    client = svc.client
    with pytest.raises(ResendError) as ei:
        client.send(to="p@example.test", subject="S", text="B", idempotency_key="k")
    assert ei.value.retryable is retryable


@pytest.mark.parametrize("boom", [TimeoutError("slow"), ConnectionResetError("x"), RuntimeError("weird")])
def test_network_or_unexpected_errors_never_leave_email_stuck_in_sending(boom):
    svc, _ = make_service(FakeResend([boom]))
    rec = approved_email(svc)
    out = svc.send(rec.id, "r")
    assert out.state == "FAILED" and out.last_error


def test_missing_credentials_refuse_to_send_and_keep_approval():
    svc, fake = make_service(configured=False)
    rec = approved_email(svc)
    with pytest.raises(EmailNotConfigured):
        svc.send(rec.id, "r")
    assert svc.store.get(rec.id).state == "APPROVED" and fake.calls == []


def test_content_changed_after_approval_is_refused():
    svc, fake = make_service()
    rec = approved_email(svc)
    svc.store._db.execute("UPDATE emails SET body_text='Different body' WHERE id=?", (rec.id,))    # simulate tampering
    with pytest.raises(ContentChanged):
        svc.send(rec.id, "r")
    assert fake.calls == []


def test_content_can_only_be_edited_while_draft():
    svc, _ = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "B")
    assert svc.edit_draft(rec.id, "S2", "B2", "a").subject == "S2"
    svc.submit_for_approval(rec.id, "a")
    with pytest.raises(InvalidTransition):
        svc.edit_draft(rec.id, "S3", "B3", "a")
    with pytest.raises(EmailNotFound):
        svc.edit_draft("nope", "S", "B", "a")


@pytest.mark.parametrize("rcpt", ["", "not-an-email", "a@b.test, c@d.test", "a@b.test\nbcc: x@y.test", "<a@b.test>", "a b@c.test"])
def test_bad_recipients_are_rejected(rcpt):
    svc, _ = make_service()
    with pytest.raises(ValueError):
        svc.create_draft("case_01", rcpt, "S", "B")


def test_subject_must_be_one_line_and_fields_required():
    svc, _ = make_service()
    for args in (("case_01", "p@example.test", "Line1\nLine2", "B"), ("", "p@example.test", "S", "B"),
                 ("case_01", "p@example.test", "  ", "B"), ("case_01", "p@example.test", "S", " ")):
        with pytest.raises(ValueError):
            svc.create_draft(*args)


def test_html_part_escapes_markup():
    svc, fake = make_service()
    rec, _ = svc.create_draft("case_01", "p@example.test", "S", "Hi <script>alert(1)</script> & co")
    svc.submit_for_approval(rec.id, "a"); svc.approve(rec.id, "r"); svc.send(rec.id, "r")
    html = fake.calls[0]["json"]["html"]
    assert "<script>" not in html and "&lt;script&gt;" in html and "&amp;" in html


def test_secrets_do_not_appear_in_repr_or_errors():
    cfg = EmailConfig(api_key=API_KEY, from_email="a@b.test", webhook_secret="whsec_abc")
    assert API_KEY not in repr(cfg) and "whsec_abc" not in repr(cfg) and "whsec_abc" not in str(cfg)


def test_config_from_env_reads_only_the_three_variables():
    cfg = EmailConfig.from_env({"RESEND_API_KEY": " k ", "RESEND_FROM_EMAIL": "a@b.test", "RESEND_WEBHOOK_SECRET": "s"})
    assert cfg.can_send and cfg.can_verify_webhooks and cfg.api_key == "k" and cfg.db_path == "email_outbox.db"
    assert not EmailConfig.from_env({}).can_send


def test_unknown_email_id():
    svc, _ = make_service()
    with pytest.raises(EmailNotFound):
        svc.send("missing", "r")
    with pytest.raises(EmailNotFound):
        svc.approve("missing", "r")


def test_state_machine_has_no_edge_into_approved_except_from_pending():
    from integrations.email.models import TRANSITIONS
    into_approved = [s for s, outs in TRANSITIONS.items() if EmailState.APPROVED in outs]
    assert into_approved == [EmailState.PENDING_APPROVAL]
    into_sending = [s for s, outs in TRANSITIONS.items() if EmailState.SENDING in outs]
    assert into_sending == [EmailState.APPROVED]
