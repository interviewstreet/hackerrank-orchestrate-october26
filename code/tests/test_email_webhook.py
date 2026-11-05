"""Resend webhook verification and delivery reconciliation (Svix signatures)."""
import json

import pytest

from emailkit import SECRET, approved_email, make_service
from integrations.email import WebhookConfigError, WebhookVerificationError
from integrations.email.webhook_handler import sign, verify_webhook

NOW = 1_800_000_000.0


def signed(body: dict, secret: str = SECRET, svix_id: str = "msg_1", ts: float = NOW):
    raw = json.dumps(body).encode()
    t = str(int(ts))
    return {"svix-id": svix_id, "svix-timestamp": t, "svix-signature": "v1," + sign(secret, svix_id, t, raw)}, raw


def test_matches_the_official_svix_test_vector():
    body = b'{"event_type":"ping","data":{"success":true}}'
    hdr = {"svix-id": "msg_loFOjxBNrRLzqYUf", "svix-timestamp": "1731705121",
           "svix-signature": "v1,rAvfW3dJ/X/qxhsaXPOyyCGmRKsaKWcsNccKXlIktD0="}
    assert verify_webhook("whsec_plJ3nmyCDGBKInavdOK15jsl", hdr, body, now=1731705121) == "msg_loFOjxBNrRLzqYUf"
    with pytest.raises(WebhookVerificationError):
        verify_webhook("whsec_plJ3nmyCDGBKInavdOK15jsl", hdr, body + b" ", now=1731705121)


def test_valid_signature_accepted_and_header_names_are_case_insensitive():
    hdr, raw = signed({"type": "email.sent"})
    hdr = {k.title(): v for k, v in hdr.items()}                       # Svix-Id, Svix-Timestamp, Svix-Signature
    assert verify_webhook(SECRET, hdr, raw, now=NOW) == "msg_1"


def test_several_signatures_in_header_one_valid():
    hdr, raw = signed({"type": "email.sent"})
    hdr["svix-signature"] = "v1,AAAA v2,BBBB " + hdr["svix-signature"]
    assert verify_webhook(SECRET, hdr, raw, now=NOW) == "msg_1"


@pytest.mark.parametrize("mutate", ["body", "secret", "id", "missing_sig", "missing_id", "bad_ts", "old", "future", "v2_only", "empty_sig"])
def test_bad_requests_are_rejected(mutate):
    hdr, raw = signed({"type": "email.sent"})
    other = "whsec_" + "b3RoZXItc2VjcmV0LW90aGVyLXNlY3JldA=="
    secret = SECRET
    if mutate == "body": raw += b" "
    if mutate == "secret": secret = other
    if mutate == "id": hdr["svix-id"] = "msg_other"
    if mutate == "missing_sig": del hdr["svix-signature"]
    if mutate == "missing_id": del hdr["svix-id"]
    if mutate == "bad_ts": hdr["svix-timestamp"] = "yesterday"
    if mutate == "old": hdr["svix-timestamp"] = str(int(NOW) - 301)
    if mutate == "future": hdr["svix-timestamp"] = str(int(NOW) + 301)
    if mutate == "v2_only": hdr["svix-signature"] = hdr["svix-signature"].replace("v1,", "v2,")
    if mutate == "empty_sig": hdr["svix-signature"] = "v1,"
    with pytest.raises(WebhookVerificationError):
        verify_webhook(secret, hdr, raw, now=NOW)


@pytest.mark.parametrize("secret", ["", "whsec_not base64 !!"])
def test_missing_or_broken_secret_refuses_everything(secret):
    hdr, raw = signed({"type": "email.sent"})
    with pytest.raises(WebhookConfigError):
        verify_webhook(secret, hdr, raw, now=NOW)


def _sent_email(svc):
    rec = approved_email(svc)
    return svc.send(rec.id, "r")                                      # resend_id = resend_1


def test_delivered_event_updates_delivery_status_only():
    svc, _ = make_service()
    rec = _sent_email(svc)
    hdr, raw = signed({"type": "email.delivered", "data": {"email_id": rec.resend_id}})
    assert svc.handle_webhook(hdr, raw, now=NOW)["handled"] is True
    got = svc.store.get(rec.id)
    assert got.delivery_status == "delivered" and got.state == "SENT"


def test_bounce_is_recorded_without_changing_a_sent_state_and_status_never_regresses():
    svc, _ = make_service()
    rec = _sent_email(svc)
    for i, typ in enumerate(["email.bounced", "email.delivered"]):
        hdr, raw = signed({"type": typ, "data": {"email_id": rec.resend_id}}, svix_id=f"msg_{i}")
        svc.handle_webhook(hdr, raw, now=NOW)
    got = svc.store.get(rec.id)
    assert got.delivery_status == "bounced" and got.state == "SENT"


def test_redelivered_webhook_is_applied_once():
    svc, _ = make_service()
    rec = _sent_email(svc)
    hdr, raw = signed({"type": "email.delivered", "data": {"email_id": rec.resend_id}})
    assert svc.handle_webhook(hdr, raw, now=NOW)["handled"] is True
    assert svc.handle_webhook(hdr, raw, now=NOW) == {"handled": False, "reason": "duplicate"}
    assert len([e for e in svc.store.events(rec.id) if "webhook" in e["note"]]) == 1


def test_webhook_settles_an_email_stuck_in_sending():
    from integrations.email import EmailState
    svc, _ = make_service()
    rec = approved_email(svc)
    svc.store.transition(rec.id, [EmailState.APPROVED], EmailState.SENDING, "r")
    svc.store.update_fields(rec.id, [EmailState.SENDING], "r", resend_id="rid_9")        # the send call died after Resend accepted it
    hdr, raw = signed({"type": "email.delivered", "data": {"email_id": "rid_9"}})
    svc.handle_webhook(hdr, raw, now=NOW)
    assert svc.store.get(rec.id).state == "SENT"


def test_failed_event_settles_sending_as_failed():
    from integrations.email import EmailState
    svc, _ = make_service()
    rec = approved_email(svc)
    svc.store.transition(rec.id, [EmailState.APPROVED], EmailState.SENDING, "r")
    svc.store.update_fields(rec.id, [EmailState.SENDING], "r", resend_id="rid_9")
    hdr, raw = signed({"type": "email.failed", "data": {"email_id": "rid_9"}})
    svc.handle_webhook(hdr, raw, now=NOW)
    assert svc.store.get(rec.id).state == "FAILED"


def test_unknown_email_and_uninteresting_events_are_acknowledged_not_applied():
    svc, _ = make_service()
    rec = _sent_email(svc)
    h1, r1 = signed({"type": "email.delivered", "data": {"email_id": "someone_else"}}, svix_id="m1")
    assert svc.handle_webhook(h1, r1, now=NOW) == {"handled": False, "reason": "unknown_email"}
    h2, r2 = signed({"type": "email.opened", "data": {"email_id": rec.resend_id}}, svix_id="m2")
    assert svc.handle_webhook(h2, r2, now=NOW) == {"handled": False, "reason": "ignored_event"}
    assert svc.store.get(rec.id).delivery_status == ""


def test_unsigned_webhook_changes_nothing():
    svc, _ = make_service()
    rec = _sent_email(svc)
    raw = json.dumps({"type": "email.bounced", "data": {"email_id": rec.resend_id}}).encode()
    with pytest.raises(WebhookVerificationError):
        svc.handle_webhook({}, raw, now=NOW)
    assert svc.store.get(rec.id).delivery_status == ""
