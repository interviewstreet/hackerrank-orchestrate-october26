"""Member One server wiring: real loopback HTTP, in-memory outbox, fake Resend only."""
import json
import threading
from http.client import HTTPConnection
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import server
from engine.contracts import CaseAuditResult
from emailkit import API_KEY, FakeResend
from integrations.email import EmailConfig, EmailService, EmailStore, ResendClient
from integrations.email.http_adapter import EmailHttpAdapter, MAX_BODY
from integrations.email.operators import Operators, hash_token

ALICE = 'fake-alice-operator-token'
BOB = 'fake-bob-operator-token'
ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture
def api():
    config = EmailConfig(api_key=API_KEY, from_email='privacy@example.test', db_path=':memory:',
                         allowed_recipients=('person@example.test',))
    fake = FakeResend()
    service = EmailService(EmailStore(':memory:'), ResendClient(API_KEY, config.from_email, transport=fake), config)
    result = CaseAuditResult('case_1', 'COMPLETE')
    app = server.ApiServer(('127.0.0.1', 0), [result])
    app.email = EmailHttpAdapter(service, Operators({'Alice': hash_token(ALICE), 'Bob': hash_token(BOB)}),
        case_provider=lambda cid: app.results[cid].to_dict() if cid in app.results else None, min_send_gap=0)
    thread = threading.Thread(target=app.serve_forever, daemon=True)
    thread.start()

    def call(method, path, body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', app.server_port, timeout=5)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers={'Origin': ORIGIN, 'Content-Type': 'application/json'} | (headers or {}))
        response = conn.getresponse()
        raw = response.read()
        value = response.status, dict(response.getheaders()), json.loads(raw) if raw else None
        conn.close()
        return value

    yield SimpleNamespace(app=app, call=call, result=result, service=service, fake=fake)
    app.shutdown()
    app.server_close()
    thread.join()
    service.store.close()


def login(api, token=ALICE):
    status, headers, data = api.call('GET', '/api/session')
    assert status == 200
    return {'Cookie': headers['Set-Cookie'].split(';', 1)[0], 'X-CSRF-Token': data['csrf_token'],
            'Authorization': 'Bearer ' + token}


def test_email_status_requires_both_session_and_operator_identity(api):
    assert api.call('GET', '/api/email/status', headers={'Authorization': 'Bearer ' + ALICE})[0] == 403
    headers = login(api)
    assert api.call('GET', '/api/email/status', headers=headers | {'Authorization': ''})[0] == 401
    status, response_headers, data = api.call('GET', '/api/email/status', headers=headers)
    assert status == 200 and data['operator'] == 'Alice' and data['can_send']
    assert data['separate_approver_required'] is True
    assert response_headers['Cache-Control'] == 'no-store'
    for secret in [API_KEY, ALICE, BOB]:
        assert secret not in json.dumps(data)


@pytest.mark.parametrize('changed', [{'Origin': 'https://evil.invalid'}, {'Host': 'evil.invalid'},
                                    {'Sec-Fetch-Site': 'cross-site'}, {'Cookie': ''}])
def test_email_http_preserves_host_origin_and_session_protections(api, changed):
    assert api.call('GET', '/api/email/status', headers=login(api) | changed)[0] == 403
    assert api.fake.calls == []


@pytest.mark.parametrize('method,path', [('POST', '/api/email/drafts'), ('PUT', '/api/email/emails/' + '0' * 32 + '/draft')])
def test_email_mutations_require_csrf(api, method, path):
    headers = login(api)
    assert api.call(method, path, headers=headers | {'X-CSRF-Token': 'wrong'})[0] == 403
    assert api.fake.calls == []


@pytest.mark.parametrize('framing', [{'Content-Length': str(MAX_BODY + 1)}, {'Content-Length': '-1'},
                                    {'Content-Length': 'invalid'}, {'Transfer-Encoding': 'chunked'}])
def test_email_rejects_oversized_or_unsupported_framing_before_read(api, framing):
    assert api.call('POST', '/api/email/drafts', headers=login(api) | framing)[0] == 413
    assert api.fake.calls == []


def test_expired_email_session_is_rejected(api):
    headers = login(api)
    api.app.sessions[next(iter(api.app.sessions))]['expires'] = 0
    assert api.call('GET', '/api/email/status', headers=headers)[0] == 403


def test_email_workflow_uses_real_server_case_and_separate_approver(api):
    alice = login(api)
    bob = login(api, BOB)
    status, _, data = api.call('POST', '/api/email/drafts', {'case_id': 'case_1', 'recipient': 'person@example.test',
                                                           'actor': 'forged-name'}, alice)
    assert status == 201 and data['email']['case_id'] == 'case_1'
    eid = data['email']['id']
    assert api.call('PUT', f'/api/email/emails/{eid}/draft', {'subject': 'Reviewed subject', 'body': 'Reviewed body'}, alice)[0] == 200
    assert api.call('POST', f'/api/email/emails/{eid}/submit', {}, alice)[0] == 200
    assert api.call('POST', f'/api/email/emails/{eid}/approve', {'approver': 'Bob'}, alice)[0] == 403
    assert api.call('POST', f'/api/email/emails/{eid}/send', {}, bob)[0] == 409
    assert api.fake.calls == []
    assert api.call('POST', f'/api/email/emails/{eid}/approve', {}, bob)[0] == 200
    status, _, data = api.call('POST', f'/api/email/emails/{eid}/send', {}, bob)
    assert status == 200 and data['email']['state'] == 'SENT' and len(api.fake.calls) == 1
    status, _, data = api.call('GET', f'/api/email/emails/{eid}', headers=bob)
    assert status == 200 and 'forged-name' not in json.dumps(data)
    assert 'Alice' in json.dumps(data['events']) and 'Bob' in json.dumps(data['events'])
    assert len(api.call('GET', '/api/email/emails?case_id=case_1', headers=alice)[2]['emails']) == 1


def test_email_allowlist_and_unknown_server_cases_are_rejected(api):
    headers = login(api)
    assert api.call('POST', '/api/email/drafts', {'case_id': 'case_1', 'recipient': 'outsider@example.test'}, headers)[0] == 403
    assert api.call('POST', '/api/email/drafts', {'case_id': 'case_999', 'recipient': 'person@example.test'}, headers)[0] == 422
    assert api.fake.calls == []


def test_email_fails_closed_when_uninitialized_or_unconfigured(api):
    headers = login(api)
    adapter = api.app.email
    api.app.email = None
    assert api.call('GET', '/api/email/status', headers=headers)[0] == 503
    api.app.email = adapter
    adapter.operators = Operators({})
    assert api.call('GET', '/api/email/status', headers=headers)[0] == 503
    assert api.fake.calls == []


def test_preflight_allows_authorization_and_put_only_for_trusted_origin(api):
    status, headers, _ = api.call('OPTIONS', '/api/email/drafts')
    assert status == 204 and 'PUT' in headers['Access-Control-Allow-Methods']
    assert 'Authorization' in headers['Access-Control-Allow-Headers']
    assert api.call('OPTIONS', '/api/email/drafts', headers={'Origin': 'https://evil.invalid'})[0] == 403


def test_existing_case_session_and_slack_routes_remain_unchanged(api, monkeypatch):
    assert api.call('GET', '/api/cases')[2][0]['case_id'] == 'case_1'
    assert api.call('PUT', '/api/cases')[0] == 404
    assert api.call('GET', '/api/emailx')[0] == 404
    sent = MagicMock()
    monkeypatch.setattr(server, 'deliver', sent)
    assert api.call('POST', '/api/cases/case_1/slack', {}, login(api))[0] == 200
    sent.assert_called_once_with(api.result)


def test_main_initializes_existing_adapter_with_raw_case_contract(api, monkeypatch):
    monkeypatch.setattr(server, 'load_env', lambda path: None)
    monkeypatch.setattr(server, 'load_results', lambda dataset: [api.result])
    monkeypatch.setattr(server, 'build_service_from_env', lambda: api.service)
    monkeypatch.setenv('EMAIL_OPERATORS', 'Alice:' + hash_token(ALICE))
    monkeypatch.setattr('sys.argv', ['server.py', '--port', '0'])

    class StartupServer:
        def __init__(self, address, results, requests):
            self.results = {r.case_id: r for r in results}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def serve_forever(self):
            assert isinstance(self.email, EmailHttpAdapter)
            assert self.email.case_provider('case_1') == api.result.to_dict()
            assert self.email.case_provider('missing') is None
            raise KeyboardInterrupt()

    monkeypatch.setattr(server, 'ApiServer', StartupServer)
    server.main()


@pytest.mark.parametrize('origin,host,status', [
    ('http://localhost:5173', 'localhost:5173', 200),
    ('http://127.0.0.1:5173', '127.0.0.1:5173', 200),
    ('http://localhost:4173', 'localhost:4173', 200),
    ('http://127.0.0.1:5174', '127.0.0.1:5174', 403),
])
def test_investigations_keep_local_proxy_checks_without_email_bearer_auth(api, origin, host, status):
    headers = login(api)
    headers.update({'Origin': origin, 'Host': host, 'Authorization': 'Bearer invalid-email-token'})
    # Even a bad email token must not turn a case read into an email-authentication check.
    code, _, data = api.call('GET', '/api/cases', headers=headers)
    assert code == status
    if status == 200:
        assert data[0]['case_id'] == 'case_1'
        assert api.call('GET', '/api/email/status', headers=headers)[0] == 401
    assert api.fake.calls == []



def test_operator_rotation_needs_a_fresh_configuration_snapshot(api, tmp_path, monkeypatch):
    import os
    from advisor.envfile import load_env
    from integrations.email.operators import upsert_operator_line
    # Isolate environment loading as well as the test-only token file.
    monkeypatch.setattr(os, 'environ', {})
    # These tokens and this file are test-only; never touch the repository .env.
    env_file = tmp_path / '.env'
    env_file.write_text(upsert_operator_line('', 'Member1', hash_token(ALICE)), encoding='utf-8')
    monkeypatch.delenv('EMAIL_OPERATORS', raising=False)
    load_env(env_file)
    api.app.email.operators = Operators.from_env(os.environ)
    headers = login(api, ALICE)
    assert api.call('GET', '/api/email/status', headers=headers)[2]['operator'] == 'Member1'

    env_file.write_text(upsert_operator_line(env_file.read_text(encoding='utf-8'), 'Member1', hash_token(BOB)), encoding='utf-8')
    load_env(env_file)  # Real environment values win; this does not hot-reload the adapter.
    changed = headers | {'Authorization': 'Bearer ' + BOB}
    assert api.call('GET', '/api/email/status', headers=changed)[0] == 401
    monkeypatch.delenv('EMAIL_OPERATORS', raising=False)
    load_env(env_file)  # Simulate a fresh process with no inherited override.
    api.app.email.operators = Operators.from_env(os.environ)
    assert api.call('GET', '/api/email/status', headers=changed)[2]['operator'] == 'Member1'
    assert api.call('GET', '/api/email/status', headers=headers)[0] == 401


def test_token_generator_writes_the_format_used_by_server_authentication(tmp_path, monkeypatch, capsys):
    import email_operator_token
    env_file = tmp_path / '.env'
    monkeypatch.setattr(email_operator_token, 'new_token', lambda: ALICE)
    monkeypatch.setattr('sys.argv', ['email_operator_token.py', '--name', 'Member1', '--env-file', str(env_file)])
    assert email_operator_token.main() == 0
    capsys.readouterr()  # Do not display even the test-only token/hash output.
    raw = env_file.read_text(encoding='utf-8').split('=', 1)[1].strip()
    operators = Operators.from_env({'EMAIL_OPERATORS': raw})
    assert operators.authenticate(ALICE) == 'Member1'
    assert operators.authenticate(BOB) is None
