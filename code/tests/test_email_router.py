"""The FastAPI router Member 1 mounts, exercised end to end with a mocked Resend."""
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import Depends, FastAPI, Header, HTTPException            # noqa: E402
from fastapi.testclient import TestClient                              # noqa: E402

from emailkit import SECRET, FakeResend, make_service                  # noqa: E402
from integrations.email.router import create_email_router             # noqa: E402
from integrations.email.webhook_handler import sign                    # noqa: E402

CASE = {"case_id": "case_77", "deletion_status": "INCOMPLETE",
        "summary": {"systems_checked": 3, "findings_count": 2, "remediation_count": 4, "verification_count": 4}}


def client_for(svc, **kw):
    app = FastAPI()
    app.include_router(create_email_router(svc, **kw))
    return TestClient(app)


def draft(c, **over):
    body = {"case_id": "case_01", "recipient": "p@example.test", "subject": "S", "body": "B"}
    body.update(over)
    return c.post("/email/drafts", json=body)


def test_full_flow_over_http():
    svc, fake = make_service()
    c = client_for(svc)
    r = draft(c)
    assert r.status_code == 201 and r.json()["created"] and r.json()["email"]["state"] == "DRAFT"
    eid = r.json()["email"]["id"]
    assert c.post(f"/email/emails/{eid}/send", json={"actor": "x"}).status_code == 409           # not approved
    assert c.post(f"/email/emails/{eid}/submit", json={"actor": "analyst"}).json()["state"] == "PENDING_APPROVAL"
    assert c.post(f"/email/emails/{eid}/send", json={"actor": "x"}).status_code == 409
    assert c.post(f"/email/emails/{eid}/approve", json={"approver": "reviewer"}).json()["state"] == "APPROVED"
    assert fake.calls == []
    assert c.post(f"/email/emails/{eid}/send", json={"actor": "reviewer"}).json()["state"] == "SENT"
    assert c.post(f"/email/emails/{eid}/send", json={"actor": "reviewer"}).json()["state"] == "SENT"
    assert len(fake.calls) == 1
    got = c.get(f"/email/emails/{eid}").json()
    assert [e["to_state"] for e in got["events"]][-1] == "SENT"
    assert [e["id"] for e in c.get("/email/emails", params={"case_id": "case_01"}).json()] == [eid]
    assert c.get("/email/emails", params={"state": "DRAFT"}).json() == []


def test_reject_and_redraft_over_http():
    svc, _ = make_service()
    c = client_for(svc)
    eid = draft(c).json()["email"]["id"]
    c.post(f"/email/emails/{eid}/submit", json={"actor": "a"})
    r = c.post(f"/email/emails/{eid}/reject", json={"approver": "reviewer", "reason": "wrong tone"})
    assert r.json()["state"] == "REJECTED" and r.json()["rejection_reason"] == "wrong tone"
    r = c.post(f"/email/emails/{eid}/redraft", json={"subject": "S2", "body": "B2", "actor": "a"})
    assert r.json()["state"] == "DRAFT" and r.json()["revision"] == 2
    assert c.put(f"/email/emails/{eid}/draft", json={"subject": "S3", "body": "B3", "actor": "a"}).json()["subject"] == "S3"


def test_error_mapping():
    svc, _ = make_service()
    c = client_for(svc)
    assert c.get("/email/emails/nope").status_code == 404
    assert c.post("/email/emails/nope/approve", json={"approver": "r"}).status_code == 404
    assert draft(c, recipient="not-an-email").status_code == 422
    assert draft(c, subject=None, body=None).status_code == 422                                   # nothing to build a draft from
    assert c.post("/email/emails/x/approve", json={"approver": ""}).status_code == 422
    eid = draft(c).json()["email"]["id"]
    assert c.post(f"/email/emails/{eid}/approve", json={"approver": "r"}).status_code == 409      # still a DRAFT


def test_send_without_credentials_is_503_and_stays_approved():
    svc, fake = make_service(configured=False)
    c = client_for(svc)
    eid = draft(c).json()["email"]["id"]
    c.post(f"/email/emails/{eid}/submit", json={"actor": "a"}); c.post(f"/email/emails/{eid}/approve", json={"approver": "r"})
    assert c.post(f"/email/emails/{eid}/send", json={"actor": "r"}).status_code == 503
    assert c.get(f"/email/emails/{eid}").json()["email"]["state"] == "APPROVED" and fake.calls == []


def test_duplicate_draft_returns_200_style_created_false():
    svc, _ = make_service()
    c = client_for(svc)
    first, second = draft(c).json(), draft(c, subject="Other").json()
    assert first["created"] and not second["created"] and first["email"]["id"] == second["email"]["id"]


def test_draft_generated_from_case_provider():
    svc, _ = make_service()
    c = client_for(svc, case_provider=lambda cid: CASE if cid == "case_77" else None)
    r = c.post("/email/drafts", json={"case_id": "case_77", "recipient": "p@example.test"})
    assert r.status_code == 201 and "case_77" in r.json()["email"]["subject"] and "2 place(s)" in r.json()["email"]["body_text"]
    assert c.post("/email/drafts", json={"case_id": "case_99", "recipient": "q@example.test"}).status_code == 422


def test_dependencies_protect_everything_except_the_webhook():
    svc, _ = make_service()

    def auth(x_user: str = Header(default="")):
        if x_user != "alice":
            raise HTTPException(401, "login required")

    c = client_for(svc, dependencies=[Depends(auth)])
    assert draft(c).status_code == 401
    assert c.get("/email/emails").status_code == 401
    assert c.post("/email/emails/x/approve", json={"approver": "r"}).status_code == 401
    ok = c.post("/email/drafts", headers={"x-user": "alice"},
                json={"case_id": "c", "recipient": "p@example.test", "subject": "S", "body": "B"})
    assert ok.status_code == 201
    # the webhook is not behind Member 1's login; it is protected by its signature instead
    assert c.post("/email/webhooks/resend", content=b"{}").status_code == 400


def _signed(body: dict, ts: int = None, svix_id: str = "msg_1"):
    import time
    raw = json.dumps(body).encode()
    t = str(int(ts if ts is not None else time.time()))
    return {"svix-id": svix_id, "svix-timestamp": t, "svix-signature": "v1," + sign(SECRET, svix_id, t, raw)}, raw


def test_webhook_endpoint_end_to_end():
    svc, _ = make_service()
    c = client_for(svc)
    eid = draft(c).json()["email"]["id"]
    c.post(f"/email/emails/{eid}/submit", json={"actor": "a"}); c.post(f"/email/emails/{eid}/approve", json={"approver": "r"})
    rid = c.post(f"/email/emails/{eid}/send", json={"actor": "r"}).json()["resend_id"]
    hdr, raw = _signed({"type": "email.delivered", "data": {"email_id": rid}})
    ok = c.post("/email/webhooks/resend", content=raw, headers=hdr)
    assert ok.status_code == 200 and ok.json()["handled"] is True
    assert c.get(f"/email/emails/{eid}").json()["email"]["delivery_status"] == "delivered"
    bad = c.post("/email/webhooks/resend", content=raw, headers={**hdr, "svix-signature": "v1,AAAA"})
    assert bad.status_code == 400
    old_hdr, old_raw = _signed({"type": "email.bounced", "data": {"email_id": rid}}, ts=1_000_000, svix_id="msg_old")
    assert c.post("/email/webhooks/resend", content=old_raw, headers=old_hdr).status_code == 400   # replayed, too old


def test_webhook_without_secret_is_503():
    from integrations.email import EmailConfig
    svc, _ = make_service()
    svc.config = EmailConfig(api_key="k", from_email="a@b.test", webhook_secret="")
    hdr, raw = _signed({"type": "email.sent", "data": {}})
    assert client_for(svc).post("/email/webhooks/resend", content=raw, headers=hdr).status_code == 503
