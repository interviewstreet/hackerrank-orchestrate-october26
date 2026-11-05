"""The authenticated HTTP adapter for code/server.py. Resend is always a fake: no test can send a real email."""
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from emailkit import API_KEY, OPEN_STORES, FakeResend
from integrations.email import EmailConfig, EmailService, EmailStore, ResendClient
from integrations.email.config import parse_allowed
from integrations.email.http_adapter import MAX_BODY, EmailHttpAdapter
from integrations.email.operators import (Operators, OperatorConfigError, hash_token, parse_operators,
                                          upsert_operator_line)

ALICE, BOB = "alice-secret-token-123", "bob-secret-token-456"
JSON = {"Content-Type": "application/json"}
P = "/api/email"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def build(*, allowed=("person@example.test", "@ok.test"), self_ok=False, operators=True, fake=None, gap=0.0,
          max_failures=10, clock=None, store=None, case_provider=None):
    fake = fake or FakeResend()
    cfg = EmailConfig(api_key=API_KEY, from_email="Privacy <privacy@example.test>", db_path=":memory:",
                      allowed_recipients=tuple(allowed), allow_self_approval=self_ok)
    store = store or EmailStore(":memory:")
    OPEN_STORES.append(store)
    svc = EmailService(store, ResendClient(cfg.api_key, cfg.from_email, transport=fake), cfg)
    ops = Operators({"Alice": hash_token(ALICE), "Bob": hash_token(BOB)} if operators else {})
    ad = EmailHttpAdapter(svc, ops, case_provider=case_provider, clock=clock or Clock(), min_send_gap=gap,
                          max_failures=max_failures)
    return ad, svc, fake


def call(ad, method, path, token=ALICE, body=None, headers=None, raw=None):
    h = dict(JSON if (body is not None or raw is not None) else {})
    if token is not None:
        h["Authorization"] = f"Bearer {token}"
    h.update(headers or {})
    data = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
    return ad.handle(method, P + path, h, data)


def draft(ad, token=ALICE, to="person@example.test", case="case_01"):
    status, data = call(ad, "POST", "/drafts", token, {"case_id": case, "recipient": to, "subject": "S", "body": "B"})
    assert status == 201, data
    return data["email"]["id"]


# ---- fail closed ----------------------------------------------------------------------------------------------
def test_no_operators_configured_disables_every_route():
    ad, _, fake = build(operators=False)
    for method, path in [("GET", "/status"), ("GET", "/emails"), ("POST", "/drafts"), ("POST", f"/emails/{'a' * 32}/send")]:
        status, data = call(ad, method, path, ALICE, {} if method == "POST" else None)
        assert status == 503 and "no operators" in data["error"]
    assert fake.calls == []


def test_no_allowed_recipients_disables_every_route():
    ad, _, fake = build(allowed=())
    status, data = call(ad, "GET", "/status")
    assert status == 503 and "allowed recipients" in data["error"] and fake.calls == []


# ---- authentication ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("token,headers", [(None, None), ("wrong-token", None), ("", None), ("x" * 500, None),
                                           (None, {"Authorization": "Basic YWxpY2U6cHc="}),
                                           (None, {"Authorization": ALICE})])
def test_missing_or_bad_credentials_get_401(token, headers):
    ad, _, _ = build()
    status, data = call(ad, "GET", "/emails", token, headers=headers)
    assert status == 401 and ALICE not in json.dumps(data) and "wrong-token" not in json.dumps(data)


def test_every_route_needs_a_login():
    ad, _, _ = build()
    eid = draft(ad)
    for method, path in [("GET", "/status"), ("GET", "/emails"), ("GET", f"/emails/{eid}"), ("POST", "/drafts"),
                         ("PUT", f"/emails/{eid}/draft"), ("POST", f"/emails/{eid}/submit"),
                         ("POST", f"/emails/{eid}/approve"), ("POST", f"/emails/{eid}/reject"),
                         ("POST", f"/emails/{eid}/send"), ("POST", f"/emails/{eid}/redraft")]:
        assert call(ad, method, path, None, {} if method != "GET" else None)[0] == 401, (method, path)


def test_failed_logins_are_rate_limited_then_recover():
    clock = Clock()
    ad, _, _ = build(max_failures=3, clock=clock)
    for _ in range(3):
        assert call(ad, "GET", "/status", "nope")[0] == 401
    assert call(ad, "GET", "/status", ALICE)[0] == 429            # even the right token waits during the lockout
    clock.t += 61
    assert call(ad, "GET", "/status", ALICE)[0] == 200


def test_status_reports_who_you_are():
    ad, _, _ = build()
    status, data = call(ad, "GET", "/status", BOB)
    assert status == 200 and data["operator"] == "Bob" and data["separate_approver_required"] is True
    assert data["can_send"] is True and "person@example.test" in data["allowed_recipients"]


# ---- identity is the server's, never the request's --------------------------------------------------------------
def test_names_in_the_body_are_ignored_and_the_login_name_is_recorded():
    ad, svc, _ = build()
    status, data = call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "person@example.test",
                                                      "subject": "S", "body": "B", "actor": "Mallory"})
    eid = data["email"]["id"]
    call(ad, "POST", f"/emails/{eid}/submit", ALICE, {"actor": "Mallory"})
    call(ad, "POST", f"/emails/{eid}/approve", BOB, {"approver": "Alice", "actor": "Alice"})
    actors = {(e["note"], e["actor"]) for e in svc.store.events(eid)}
    assert ("created", "Alice") in actors and ("submitted for approval", "Alice") in actors and ("approved", "Bob") in actors
    assert all(a != "Mallory" for _, a in actors) and svc.store.get(eid).approved_by == "Bob"


# ---- separation of duties --------------------------------------------------------------------------------------
def test_the_drafter_cannot_approve_their_own_email():
    ad, svc, _ = build()
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    status, data = call(ad, "POST", f"/emails/{eid}/approve", ALICE)
    assert status == 403 and "different person" in data["error"] and svc.store.get(eid).state == "PENDING_APPROVAL"
    assert call(ad, "POST", f"/emails/{eid}/approve", BOB)[0] == 200


def test_the_submitter_cannot_approve_even_if_someone_else_drafted():
    ad, _, _ = build()
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", BOB)
    assert call(ad, "POST", f"/emails/{eid}/approve", BOB)[0] == 403
    assert call(ad, "POST", f"/emails/{eid}/approve", ALICE)[0] == 403          # Alice drafted it


def test_self_approval_works_only_with_the_explicit_demo_switch():
    ad, _, _ = build(self_ok=True)
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    assert call(ad, "POST", f"/emails/{eid}/approve", ALICE)[0] == 200
    assert call(ad, "GET", "/status", ALICE)[1]["separate_approver_required"] is False


# ---- full workflow and duplicate safety ----------------------------------------------------------------------
def test_full_flow_sends_exactly_once():
    ad, svc, fake = build()
    eid = draft(ad, ALICE)
    assert call(ad, "POST", f"/emails/{eid}/send", BOB)[0] == 409               # not approved yet
    assert fake.calls == []
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    call(ad, "POST", f"/emails/{eid}/approve", BOB)
    status, data = call(ad, "POST", f"/emails/{eid}/send", BOB)
    assert status == 200 and data["email"]["state"] == "SENT" and len(fake.calls) == 1
    assert call(ad, "POST", f"/emails/{eid}/send", BOB)[1]["email"]["state"] == "SENT" and len(fake.calls) == 1
    assert API_KEY not in json.dumps(data)
    status, data = call(ad, "GET", f"/emails/{eid}", ALICE)
    assert [e["to_state"] for e in data["events"]][-2:] == ["SENDING", "SENT"]
    assert call(ad, "GET", "/emails?state=SENT", ALICE)[1]["emails"][0]["id"] == eid


def test_a_second_draft_for_the_same_case_and_recipient_is_not_created():
    ad, _, _ = build()
    first = draft(ad)
    status, data = call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "PERSON@example.test",
                                                       "subject": "S2", "body": "B2"})
    assert status == 200 and data["created"] is False and data["email"]["id"] == first


def test_content_edited_after_approval_cannot_be_sent():
    ad, svc, fake = build()
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    assert call(ad, "POST", f"/emails/{eid}/approve", BOB)[0] == 200
    assert call(ad, "PUT", f"/emails/{eid}/draft", ALICE, {"subject": "New", "body": "Changed"})[0] == 409
    assert fake.calls == []


def test_resend_failure_is_reported_without_secrets_and_needs_new_approval():
    fake = FakeResend([(500, {"name": "application_error", "message": "boom"})])
    ad, _, _ = build(fake=fake)
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    call(ad, "POST", f"/emails/{eid}/approve", BOB)
    status, data = call(ad, "POST", f"/emails/{eid}/send", BOB)
    assert status == 200 and data["email"]["state"] == "FAILED" and API_KEY not in json.dumps(data)
    assert call(ad, "POST", f"/emails/{eid}/send", BOB)[0] == 409


def test_reject_and_redraft_cycle():
    ad, _, _ = build()
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    status, data = call(ad, "POST", f"/emails/{eid}/reject", BOB, {"reason": "tone"})
    assert status == 200 and data["email"]["state"] == "REJECTED" and data["email"]["rejected_by"] == "Bob"
    status, data = call(ad, "POST", f"/emails/{eid}/redraft", ALICE, {"subject": "S2", "body": "B2"})
    assert status == 200 and data["email"]["state"] == "DRAFT" and data["email"]["revision"] == 2


# ---- recipients ---------------------------------------------------------------------------------------------
def test_recipients_outside_the_allowlist_are_refused_at_draft_time():
    ad, _, _ = build()
    status, data = call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "stranger@gmail.com",
                                                      "subject": "S", "body": "B"})
    assert status == 403 and "allowed list" in data["error"]
    assert call(ad, "GET", "/emails", ALICE)[1]["emails"] == []
    assert draft(ad, to="anyone@ok.test")                                          # whole domain allowed


def test_the_allowlist_is_checked_again_at_send_time():
    ad, svc, fake = build()
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    call(ad, "POST", f"/emails/{eid}/approve", BOB)
    # same database, but the allowlist has since been tightened
    tight_cfg = EmailConfig(api_key=API_KEY, from_email="x@example.test", db_path=":memory:", allowed_recipients=("other@ok.test",))
    tight = EmailService(svc.store, ResendClient(API_KEY, "x@example.test", transport=fake), tight_cfg)
    ad2 = EmailHttpAdapter(tight, Operators({"Bob": hash_token(BOB)}), clock=Clock(), min_send_gap=0)
    status, data = call(ad2, "POST", f"/emails/{eid}/send", BOB)
    assert status == 403 and fake.calls == [] and svc.store.get(eid).state == "APPROVED"


def test_allowlist_parsing_and_matching():
    assert parse_allowed(" A@x.com; @y.org ,a@x.com,, ") == ("a@x.com", "@y.org")
    cfg = EmailConfig(allowed_recipients=parse_allowed("a@x.com,@y.org"))
    assert cfg.recipient_allowed("A@X.com") and cfg.recipient_allowed("z@y.org")
    assert not cfg.recipient_allowed("b@x.com") and not cfg.recipient_allowed("z@sub.y.org")
    assert not cfg.recipient_allowed("a@x.com.evil.test") and not cfg.recipient_allowed("")
    assert EmailConfig().recipient_allowed("anyone@anywhere.test")               # the core alone has no restriction
    env = EmailConfig.from_env({"EMAIL_ALLOWED_RECIPIENTS": "a@x.com", "EMAIL_ALLOW_SELF_APPROVAL": "1"})
    assert env.allowed_recipients == ("a@x.com",) and env.allow_self_approval is True
    assert EmailConfig.from_env({}).allow_self_approval is False


# ---- request hygiene ----------------------------------------------------------------------------------------
def test_malformed_requests_get_clean_errors():
    ad, _, _ = build()
    assert call(ad, "POST", "/drafts", ALICE, raw=b"{not json")[0] == 400
    assert call(ad, "POST", "/drafts", ALICE, raw=b"[1,2]")[0] == 400
    assert call(ad, "POST", "/drafts", ALICE, raw=b"")[0] == 400
    assert call(ad, "POST", "/drafts", ALICE, raw=b"{}", headers={"Content-Type": "text/plain"})[0] == 415
    assert call(ad, "POST", "/drafts", ALICE, raw=b" " * (MAX_BODY + 1) + b"{}")[0] == 413
    assert call(ad, "POST", "/drafts", ALICE, {"case_id": "../etc", "recipient": "person@example.test", "subject": "S", "body": "B"})[0] == 422
    assert call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "not-an-email", "subject": "S", "body": "B"})[0] == 422
    assert call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "person@example.test", "subject": 5, "body": "B"})[0] == 422
    assert call(ad, "POST", "/drafts", ALICE, {"case_id": "case_01", "recipient": "person@example.test"})[0] == 422   # no generator
    assert call(ad, "GET", "/emails?limit=abc", ALICE)[0] == 422


def test_routing_errors():
    ad, _, _ = build()
    eid = draft(ad)
    assert call(ad, "DELETE", f"/emails/{eid}", ALICE)[0] == 405
    assert call(ad, "GET", f"/emails/{eid}/send", ALICE)[0] == 405
    assert call(ad, "GET", "/nothing", ALICE)[0] == 404
    assert call(ad, "GET", "/emails/not-a-real-id", ALICE)[0] == 404
    assert call(ad, "GET", f"/emails/{'0' * 32}", ALICE)[0] == 404
    assert ad.handle("GET", "/api/emailx", {}, b"")[0] == 404 and ad.handle("GET", "/api/cases", {}, b"")[0] == 404


def test_send_is_one_at_a_time_with_a_minimum_gap():
    clock = Clock()
    ad, _, fake = build(gap=2.0, clock=clock)
    ids = []
    for case in ("case_01", "case_02"):
        eid = draft(ad, ALICE, case=case)
        call(ad, "POST", f"/emails/{eid}/submit", ALICE)
        call(ad, "POST", f"/emails/{eid}/approve", BOB)
        ids.append(eid)
    assert call(ad, "POST", f"/emails/{ids[0]}/send", BOB)[0] == 200
    assert call(ad, "POST", f"/emails/{ids[1]}/send", BOB)[0] == 429 and len(fake.calls) == 1
    clock.t += 3
    assert call(ad, "POST", f"/emails/{ids[1]}/send", BOB)[0] == 200 and len(fake.calls) == 2
    ad._send_lock.acquire()
    try:
        clock.t += 10
        assert call(ad, "POST", f"/emails/{ids[0]}/send", BOB)[0] == 409
    finally:
        ad._send_lock.release()


def test_concurrent_sends_of_one_email_send_once():
    fake = FakeResend(delay=0.05)
    ad, _, _ = build(fake=fake)
    eid = draft(ad, ALICE)
    call(ad, "POST", f"/emails/{eid}/submit", ALICE)
    call(ad, "POST", f"/emails/{eid}/approve", BOB)
    out = []
    ts = [threading.Thread(target=lambda: out.append(call(ad, "POST", f"/emails/{eid}/send", BOB)[0])) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(fake.calls) == 1 and 200 in out


def test_unexpected_errors_do_not_leak_details():
    ad, svc, _ = build()
    eid = draft(ad)
    svc.store.get = lambda _id: (_ for _ in ()).throw(RuntimeError("secret internals " + API_KEY))
    status, data = call(ad, "GET", f"/emails/{eid}", ALICE)
    assert status == 500 and "secret" not in json.dumps(data) and API_KEY not in json.dumps(data)


def test_drafts_can_be_generated_from_a_case_the_server_knows():
    from engine.contracts import CaseAuditResult
    case = CaseAuditResult(case_id="case_09", deletion_status="COMPLETE").to_dict()
    ad, _, _ = build(case_provider=lambda cid: case if cid == "case_09" else None)
    status, data = call(ad, "POST", "/drafts", ALICE, {"case_id": "case_09", "recipient": "person@example.test"})
    assert status == 201 and "case_09" in data["email"]["subject"]
    assert call(ad, "POST", "/drafts", ALICE, {"case_id": "case_10", "recipient": "person@example.test"})[0] == 422
    status, _ = call(ad, "POST", "/drafts", ALICE, {"case_id": "case_09", "recipient": "x@ok.test", "audience": "everyone"})
    assert status == 422


# ---- operator configuration and the token tool ------------------------------------------------------------------
def test_operator_parsing_rejects_bad_configuration_without_echoing_hashes():
    good = hash_token("t")
    assert parse_operators(f"Alice:{good}, Bob:{good}") == {"Alice": good, "Bob": good}
    for bad in (f"Alice{good}", "Alice:short", f":{good}", f"Al/ice:{good}", f"Alice:{good.upper()[:-1]}z"):
        with pytest.raises(OperatorConfigError) as e:
            Operators(parse_operators(bad))
        assert good not in str(e.value)
    with pytest.raises(OperatorConfigError):
        Operators({"Alice": good, "alice": good})
    assert not Operators.from_env({}).enabled and Operators.from_env({"EMAIL_OPERATORS": f"A:{good}"}).enabled
    assert Operators({"A": good}).authenticate("t") == "A" and Operators({"A": good}).authenticate("T") is None


def test_env_line_upsert_keeps_other_lines_and_replaces_by_name():
    a, b, c = hash_token("a"), hash_token("b"), hash_token("c")
    text = "RESEND_API_KEY=re_x\nEMAIL_OPERATORS=Alice:" + a + "\nOTHER=1\n"
    out = upsert_operator_line(text, "Bob", b)
    assert out.splitlines()[0] == "RESEND_API_KEY=re_x" and out.splitlines()[2] == "OTHER=1"
    assert out.splitlines()[1] == f"EMAIL_OPERATORS=Alice:{a},Bob:{b}"
    again = upsert_operator_line(out, "alice", c)                      # same person, new token: old entry replaced, no duplicate
    assert again.splitlines()[1] == f"EMAIL_OPERATORS=Bob:{b},alice:{c}"
    assert upsert_operator_line("", "Bob", b) == f"EMAIL_OPERATORS=Bob:{b}\n"
    assert "\r\n" in upsert_operator_line("A=1\r\nB=2\r\n", "Bob", b)


def test_token_tool_stores_only_the_hash(tmp_path):
    root = Path(__file__).resolve().parents[2]
    env = tmp_path / ".env"
    env.write_text("KEEP=me\n", encoding="utf-8")
    out = subprocess.run([sys.executable, "-I", str(root / "code" / "email_operator_token.py"), "--name", "Rach",
                          "--env-file", str(env)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    token = out.stdout.strip().splitlines()[-1]
    saved = env.read_text(encoding="utf-8")
    assert "KEEP=me" in saved and token not in saved and f"Rach:{hash_token(token)}" in saved
    assert Operators.from_env({"EMAIL_OPERATORS": saved.split("EMAIL_OPERATORS=")[1].splitlines()[0]}).authenticate(token) == "Rach"
    bad = subprocess.run([sys.executable, "-I", str(root / "code" / "email_operator_token.py"), "--name", "bad/name"],
                         capture_output=True, text=True, timeout=60)
    assert bad.returncode == 1
