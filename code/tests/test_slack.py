"""All Slack delivery is mocked; no credentials or real network posts are required."""
import copy
import io
import json
import threading
import time
from http.client import HTTPConnection
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest

from engine.contracts import CaseAuditResult
from notifications import slack
import server
from presentation import present

WEBHOOK = 'https://hooks.slack.com/services/TEST/TEST/mock-secret'
REPORT_URL = 'https://example.slack.com/files/U12345678/F12345678/case_1-investigation.html'


@pytest.fixture
def result():
    return CaseAuditResult('case_1', 'INCOMPLETE',
        findings=[{'operation': 'REPORT_EXPOSED_PII', 'system_id': 'search_service',
                   'resource_id': 'search_1', 'evidence_id': 'evidence_1', 'reason': 'Private Person private@example.invalid'}],
        steps=[{'step_no': 1, 'phase': 'REMEDIATION', 'operation': 'DELETE_RECORD', 'system_id': 'search_service',
                'resource_id': 'search_1', 'state': 'ABSENT', 'evidence_id': ''}],
        identities=[{'name': 'Private Person', 'email': 'private@example.invalid', 'phone': '+1 555 9999'}],
        graph_data={'nodes': [{'id': 'subject', 'type': 'subject', 'label': 'Private Person'},
                             {'id': 'search_1', 'type': 'SEARCH_INDEX_ENTRY', 'status': 'VIOLATION', 'system': 'search_service'}],
                    'edges': [{'source': 'subject', 'target': 'search_1', 'relation': 'identifier_match'}]})


def test_payload_is_actual_and_excludes_pii_and_untrusted_text(result):
    before = copy.deepcopy(result)
    data = slack.payload(result, REPORT_URL)
    text = json.dumps(data)
    assert 'INCOMPLETE' in text and 'HIGH' in text
    report = slack.html_report(result).decode()
    assert 'search service' in report and 'Delete record' in report and '1. Delete record' in report
    for secret in ['Private Person', 'private@example.invalid', '+1 555 9999', 'search_1', WEBHOOK]:
        assert secret not in text and secret not in report
    assert result == before
    result.findings[0]['system_id'] = '<!channel> private@example.invalid'
    assert 'private@example.invalid' not in json.dumps(slack.payload(result, REPORT_URL))
    assert '<!channel>' not in json.dumps(slack.payload(result, REPORT_URL))
    assert all(len(b['text']['text']) <= 3000 for b in data['blocks'] if 'text' in b)


@pytest.mark.parametrize('status,level', [('COMPLETE', 'NONE'), ('NOT_APPLICABLE', 'NONE'), ('INCOMPLETE', 'UNKNOWN')])
def test_empty_results_are_not_falsely_safe(status, level):
    data = slack.payload(CaseAuditResult('case_2', status), REPORT_URL)
    assert status in data['text'] and level in data['text']
    if status == 'INCOMPLETE':
        assert 'Manual investigation required' in slack.html_report(CaseAuditResult('case_2', status)).decode()


@pytest.mark.parametrize('url', ['', 'http://hooks.slack.com/services/A/B/C', 'https://example.invalid/services/A/B/C',
                               'https://hooks.slack.com.evil.invalid/services/A/B/C',
                               'https://hooks.slack.com/services/A/B/C?secret=x', 'https://[invalid'])
def test_bad_configuration_is_safe(monkeypatch, url):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', url)
    with pytest.raises(slack.SlackError) as error:
        slack.webhook_url()
    assert error.value.status == 503
    if url:
        assert url not in str(error.value)


def test_deliver_posts_once_with_timeout_and_accepts_only_ok(monkeypatch, result):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener = MagicMock()
    response = opener.open.return_value.__enter__.return_value
    response.status = 200
    response.read.return_value = b'ok'
    monkeypatch.setattr(slack, 'build_opener', lambda *args: opener)
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'xoxb-test-token')
    monkeypatch.setenv('SLACK_REPORT_CHANNEL_ID', 'C12345678')
    monkeypatch.setattr(slack, 'upload_report', lambda *args: REPORT_URL)
    slack.deliver(result)
    request = opener.open.call_args.args[0]
    assert opener.open.call_count == 1 and opener.open.call_args.kwargs['timeout'] == 10
    assert request.full_url == WEBHOOK and request.get_method() == 'POST'
    assert 'private@example.invalid' not in request.data.decode()
    response.read.return_value = b'invalid_payload'
    with pytest.raises(slack.SlackError):
        slack.deliver(result)


@pytest.mark.parametrize('failure,status', [(HTTPError(WEBHOOK, 429, 'secret', {}, io.BytesIO()), 429),
    (HTTPError(WEBHOOK, 403, 'secret', {}, io.BytesIO()), 502),
    (URLError(WEBHOOK), 502), (TimeoutError(WEBHOOK), 502)])
def test_slack_failure_never_exposes_url(monkeypatch, result, failure, status):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'xoxb-test-token')
    monkeypatch.setenv('SLACK_REPORT_CHANNEL_ID', 'C12345678')
    monkeypatch.setattr(slack, 'upload_report', lambda *args: REPORT_URL)
    opener = MagicMock()
    opener.open.side_effect = failure
    monkeypatch.setattr(slack, 'build_opener', lambda *args: opener)
    with pytest.raises(slack.SlackError) as error:
        slack.deliver(result)
    assert error.value.status == status and 'mock-secret' not in str(error.value)
    assert opener.open.call_count == 1  # No automatic retries that could duplicate messages.
    assert slack.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid') is None


@pytest.fixture
def api(result, monkeypatch):
    monkeypatch.delenv('SLACK_WEBHOOK_URL', raising=False)
    app = server.ApiServer(('127.0.0.1', 0), [result])
    thread = threading.Thread(target=app.serve_forever, daemon=True)
    thread.start()
    def call(method, path, body=None, headers=None):
        conn = HTTPConnection('127.0.0.1', app.server_port, timeout=3)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        value = response.read()
        out = response.status, dict(response.getheaders()), json.loads(value) if value else None
        conn.close()
        return out
    yield app, call
    app.shutdown()
    app.server_close()
    thread.join()


def session_headers(call):
    code, headers, data = call('GET', '/api/session')
    assert data['slack_report_format'] == 'html-v1'
    assert code == 200 and 'HttpOnly' in headers['Set-Cookie'] and 'SameSite=Strict' in headers['Set-Cookie']
    assert WEBHOOK not in json.dumps(data)
    return {'Cookie': headers['Set-Cookie'].split(';')[0], 'X-CSRF-Token': data['csrf_token'],
            'Origin': 'http://127.0.0.1:5173', 'Content-Type': 'application/json'}


def test_endpoint_requires_session_csrf_origin_and_safe_host(api, monkeypatch):
    app, call = api
    mock = MagicMock()
    monkeypatch.setattr(server, 'deliver', mock)
    assert call('POST', '/api/cases/case_1/slack', '')[0] == 403
    headers = session_headers(call)
    # Denied requests need no body; unread bytes can cause a Windows TCP reset.
    for changed in [{'Origin': 'https://evil.invalid'}, {'X-CSRF-Token': 'wrong'}, {'Cookie': ''}, {'Host': 'evil.invalid'}]:
        assert call('POST', '/api/cases/case_1/slack', '', headers | changed)[0] == 403
    app.sessions[next(iter(app.sessions))]['expires'] = time.monotonic() - 1
    assert call('POST', '/api/cases/case_1/slack', '', headers)[0] == 403
    mock.assert_not_called()


def test_endpoint_uses_stored_result_and_blocks_duplicates(api, monkeypatch, result):
    app, call = api
    mock = MagicMock()
    monkeypatch.setattr(server, 'deliver', mock)
    headers = session_headers(call)
    code, _, body = call('POST', '/api/cases/case_1/slack', '{}', headers)
    assert code == 200 and body == {'status': 'sent', 'case_id': 'case_1'}
    mock.assert_called_once_with(result)
    assert call('POST', '/api/cases/case_1/slack', '{}', headers)[0] == 409
    assert mock.call_count == 1


@pytest.mark.parametrize('path,body,status', [('/api/cases/case_999/slack', '', 404),
    ('/api/cases/DEMO-001/slack', '', 400), ('/api/cases/case_1/slack', '{', 400),
    ('/api/cases/case_1/slack', '{"deletion_status":"COMPLETE"}', 400), ('/api/cases/case_1/nope', '', 404)])
def test_invalid_requests_do_not_send(api, monkeypatch, path, body, status):
    _, call = api
    mock = MagicMock()
    monkeypatch.setattr(server, 'deliver', mock)
    assert call('POST', path, body, session_headers(call))[0] == status
    mock.assert_not_called()


def test_missing_config_and_slack_failure_return_safe_errors(api, monkeypatch):
    _, call = api
    headers = session_headers(call)
    assert call('POST', '/api/cases/case_1/slack', '{}', headers)[0] == 503
    mock = MagicMock(side_effect=slack.SlackError('Slack rejected the notification.'))
    monkeypatch.setattr(server, 'deliver', mock)
    code, _, data = call('POST', '/api/cases/case_1/slack', '{}', headers)
    assert code == 502 and 'mock-secret' not in json.dumps(data)


def test_adapter_preserves_engine_decisions_and_does_not_expose_identity(result):
    before = copy.deepcopy(result)
    value = present(result)
    assert value['steps'] == result.steps and value['deletion_status'] == result.deletion_status
    assert value['findings'][0]['resource_id'] == 'search_1'
    assert value['graph_data']['edges'][0]['source'] == 'subject'
    assert 'Private Person' not in json.dumps(value)
    assert result == before


def test_api_refuses_results_when_evidence_processing_failed(monkeypatch):
    from types import SimpleNamespace
    context = SimpleNamespace(store=SimpleNamespace(status={'evidence_1': 'FAILED:private parser details'}))
    monkeypatch.setattr(server, 'build_context', lambda dataset: context)
    with pytest.raises(RuntimeError, match='Evidence processing is incomplete') as error:
        server.load_results('unused')
    assert 'private parser details' not in str(error.value)


def test_api_uses_real_engine_results_on_self_contained_dataset(tmp_path):
    from minidata import build_mini_dataset
    results = server.load_results(build_mini_dataset(tmp_path))
    assert len(results) == 6
    assert {r.deletion_status for r in results} == {'COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE'}
    assert all(present(r)['deletion_status'] == r.deletion_status for r in results)


def test_report_distinguishes_findings_and_future_checks(result):
    result.findings.append({'operation': 'REPORT_RESTORE_RISK', 'system_id': 'backup_service', 'evidence_id': ''})
    result.steps.append({'phase': 'VERIFICATION', 'operation': 'VERIFY_RECORD_ABSENT',
                         'system_id': 'search_service', 'state': 'ABSENT', 'evidence_id': ''})
    text = slack.html_report(result).decode()
    assert 'Investigation Report' in text
    assert 'UNRESOLVED - search service' in text and 'Evidence: evidence_1' in text
    assert 'UNKNOWN - backup service' in text
    assert '0 evidence-backed checks verified; 1 checks not confirmed' in text
    assert 'not executed' in text


def test_complete_verification_requires_citation_and_matching_state():
    result = CaseAuditResult('case_2', 'COMPLETE', steps=[
        {'phase': 'VERIFICATION', 'operation': 'VERIFY_RECORD_ABSENT', 'system_id': 'search_service',
         'state': 'ABSENT', 'evidence_id': 'evidence_2'},
        {'phase': 'VERIFICATION', 'operation': 'VERIFY_RECORD_ABSENT', 'system_id': 'search_service',
         'state': 'PRESENT', 'evidence_id': 'evidence_3'}])
    text = slack.html_report(result).decode()
    assert '1 evidence-backed checks verified; 1 checks not confirmed' in text
    assert 'VERIFIED - search service' in text and 'UNKNOWN - search service' in text
    result.deletion_status = 'INCOMPLETE'
    assert '0 evidence-backed checks verified' in slack.html_report(result).decode()


def test_report_bounds_large_payload_and_excludes_untrusted_fields(result):
    result.findings *= 1000
    result.findings[0]['evidence_id'] = 'private@example.invalid'
    result.steps *= 1000
    data = slack.payload(result, REPORT_URL)
    text = json.dumps(data)
    assert 'private@example.invalid' not in text
    report = slack.html_report(result).decode()
    assert report.count('Required identifier treatment remains incomplete') == 1000
    assert report.count('Delete record') == 1000
    assert 'Additional details omitted' not in report
    assert len(data['blocks']) <= 50
    assert all(len(b['text']['text']) <= 3000 for b in data['blocks'] if 'text' in b)


def test_remediation_keeps_backend_dependency_order(result):
    result.steps = [{'phase': 'REMEDIATION', 'operation': op, 'system_id': 'search_service'}
                    for op in ['DISABLE_DATA_FLOW', 'DELETE_RECORD', 'DISABLE_DATA_FLOW']]
    text = slack.html_report(result).decode()
    assert text.index('1. Disable data flow') < text.index('2. Delete record') < text.index('3. Disable data flow')



def test_message_exact_order_and_link(result):
    data = slack.payload(result, REPORT_URL)
    assert len(data['blocks']) == 3
    assert data['blocks'][0]['text']['text'] == 'EraSight \u2014 Investigation Report'
    overview = data['blocks'][1]['text']['text']
    assert overview == ('Case Overview\n\nCase ID: case_1\n\nDeletion Status: INCOMPLETE\n\n'
                        'Risk Severity: HIGH\n\nSeverity is derived from finding operations, not an independent risk assessment.')
    assert overview in data['text']
    assert data['blocks'][2]['text']['text'] == f'<{REPORT_URL}|Download Full HTML Investigation Report> (Slack sign-in required)'
    assert not data['unfurl_links'] and not data['unfurl_media']


@pytest.mark.parametrize('url', ['C:/Reports/case.html', 'file:///C:/case.html', 'http://localhost:8000/report',
    'https://example.invalid/report', 'https://example.slack.com.evil.invalid/files/U123/F123',
    'https://example.slack.com/files/U123/F123?token=secret', 'https://example.slack.com/files/U123/F123>evil'])
def test_report_link_rejects_local_or_unsafe_urls(result, url):
    with pytest.raises(slack.SlackError):
        slack.payload(result, url)


def test_html_omits_raw_evidence_and_free_text(result):
    result.evidence = [{'evidence_id': 'evidence_1', 'file_path': 'private@example.invalid', 'text': '<script>private</script>'}]
    result.findings.append({'system_id': '<script>alert(1)</script>', 'operation': 'private@example.invalid',
                            'evidence_id': '<script>private</script>'})
    report = slack.html_report(result).decode()
    assert report.startswith('<!doctype html>') and '<meta charset="utf-8">' in report
    assert 'Content-Security-Policy' in report
    for value in ['private@example.invalid', '<script>', 'Private Person', '+1 555 9999', 'search_1']:
        assert value not in report
    assert 'evidence_1' in report and 'UNKNOWN' in report


def test_missing_upload_configuration_sends_nothing(monkeypatch, result):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    monkeypatch.delenv('SLACK_BOT_TOKEN', raising=False)
    monkeypatch.delenv('SLACK_REPORT_CHANNEL_ID', raising=False)
    opener = MagicMock()
    monkeypatch.setattr(slack, 'build_opener', lambda *args: opener)
    with pytest.raises(slack.SlackError) as error:
        slack.deliver(result)
    assert error.value.status == 503
    opener.open.assert_not_called()


def upload_opener(monkeypatch, *, upload_url='https://files.slack.com/upload/v1/mock-ticket',
                  complete_ok=True, public=False, permalink=REPORT_URL):
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'xoxb-test-token')
    monkeypatch.setenv('SLACK_REPORT_CHANNEL_ID', 'C12345678')
    bodies = [
        {'ok': True, 'upload_url': upload_url, 'file_id': 'F12345678'},
        None,
        {'ok': complete_ok, 'files': [{'id': 'F12345678'}]},
        {'ok': True, 'file': {'id': 'F12345678', 'public_url_shared': public, 'permalink': permalink}},
        None,
    ]
    opener = MagicMock()
    responses = []
    for body in bodies:
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = json.dumps(body).encode() if body is not None else b'ok'
        responses.append(response)
    opener.open.side_effect = responses
    monkeypatch.setattr(slack, 'build_opener', lambda *args: opener)
    return opener


def test_deliver_uploads_full_private_html_then_posts_existing_webhook(monkeypatch, result):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener = upload_opener(monkeypatch)
    slack.deliver(result)
    calls = opener.open.call_args_list
    assert len(calls) == 5
    requests = [c.args[0] for c in calls]
    assert [r.full_url for r in requests] == [
        'https://slack.com/api/files.getUploadURLExternal', 'https://files.slack.com/upload/v1/mock-ticket',
        'https://slack.com/api/files.completeUploadExternal', 'https://slack.com/api/files.info', WEBHOOK]
    assert int(parse_qs(requests[0].data.decode())['length'][0]) == len(requests[1].data)
    assert parse_qs(requests[0].data.decode())['filename'] == ['case_1-investigation.html']
    assert all(requests[i].get_header('Content-type') == 'application/x-www-form-urlencoded' for i in [0, 2, 3])
    assert requests[1].data == slack.html_report(result)
    assert requests[1].get_header('Authorization') is None and requests[-1].get_header('Authorization') is None
    assert requests[0].get_header('Authorization') == 'Bearer xoxb-test-token'
    completion = parse_qs(requests[2].data.decode())
    assert completion['channel_id'] == ['C12345678']
    assert json.loads(completion['files'][0]) == [{'id': 'F12345678', 'title': 'case_1 - Full HTML Investigation Report'}]
    assert parse_qs(requests[3].data.decode())['file'] == ['F12345678']
    assert json.loads(requests[-1].data) == slack.payload(result, REPORT_URL)
    assert all(c.kwargs['timeout'] == 10 for c in calls)
    for r in requests:
        assert b'private@example.invalid' not in r.data


@pytest.mark.parametrize('options,count', [({'upload_url': 'https://evil.invalid/upload'}, 1),
    ({'upload_url': 'https://files.slack.com.evil.invalid/upload/v1/x'}, 1),
    ({'complete_ok': False}, 3), ({'public': True}, 4), ({'permalink': 'C:/report.html'}, 4)])
def test_failed_or_unsafe_upload_never_posts_webhook(monkeypatch, result, options, count):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener = upload_opener(monkeypatch, **options)
    with pytest.raises(slack.SlackError):
        slack.deliver(result)
    assert opener.open.call_count == count
    assert all(c.args[0].full_url != WEBHOOK for c in opener.open.call_args_list)


def test_endpoint_delivers_stored_case_with_uploaded_html(api, monkeypatch, result):
    _, call = api
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener = upload_opener(monkeypatch)
    headers = session_headers(call)
    status, _, body = call('POST', '/api/cases/case_1/slack', '{}', headers)
    assert status == 200 and body == {'status': 'sent', 'case_id': 'case_1'}
    assert opener.open.call_args_list[1].args[0].data == slack.html_report(result)
    assert call('POST', '/api/cases/case_1/slack', '{}', headers)[0] == 409
    assert opener.open.call_count == 5


@pytest.mark.parametrize('stage', range(4))
def test_upload_network_errors_are_safe_and_never_post_webhook(monkeypatch, result, stage):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener = upload_opener(monkeypatch)
    responses = list(opener.open.side_effect)
    responses[stage] = URLError('https://files.slack.com/upload/v1/private-ticket xoxb-test-token')
    opener.open.side_effect = responses
    with pytest.raises(slack.SlackError) as error:
        slack.deliver(result)
    assert 'private-ticket' not in str(error.value) and 'xoxb' not in str(error.value)
    assert opener.open.call_count == stage + 1
    assert all(c.args[0].full_url != WEBHOOK for c in opener.open.call_args_list)


def test_unconfigured_upload_is_visible_in_session(api, monkeypatch):
    _, call = api
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    monkeypatch.delenv('SLACK_BOT_TOKEN', raising=False)
    monkeypatch.delenv('SLACK_REPORT_CHANNEL_ID', raising=False)
    assert call('GET', '/api/session')[2]['slack_configured'] is False
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'xoxb-test-token')
    monkeypatch.setenv('SLACK_REPORT_CHANNEL_ID', 'C12345678')
    assert call('GET', '/api/session')[2]['slack_configured'] is True


@pytest.mark.parametrize('code,expected', [('not_in_channel', 'Invite the app'), ('missing_scope', 'Reinstall the Slack app'),
                                         ('invalid_arguments', 'Check bot permissions')])
def test_upload_errors_are_actionable_without_upstream_details(monkeypatch, result, code, expected):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', WEBHOOK)
    opener=upload_opener(monkeypatch)
    response=MagicMock()
    response.__enter__.return_value=response
    response.status=200
    response.read.return_value=json.dumps({'ok':False,'error':code,'details':'xoxb-private-secret'}).encode()
    opener.open.side_effect=[response]
    with pytest.raises(slack.SlackError) as error:
        slack.deliver(result)
    assert expected in str(error.value) and 'xoxb-private-secret' not in str(error.value)
    assert opener.open.call_count==1



def test_presentation_adds_only_actual_operational_request_metadata(result):
    request = {'case_id': result.case_id, 'email': 'private@example.invalid', 'request_text': 'Private Person',
               'requested_at': '2026-07-16T08:00:00Z', 'reported_at': '2026-07-18T08:00:00Z',
               'audit_at': '2026-07-19T13:00:00Z', 'reported_status': 'COMPLETE'}
    before = copy.deepcopy(result)
    value = present(result, request)
    assert value['request'] == {k: request[k] for k in ['requested_at', 'reported_status', 'reported_at', 'audit_at']}
    assert value['deletion_status'] == 'INCOMPLETE'  # Workflow claims never replace the engine result.
    assert value['steps'] == result.steps
    assert value['summary'] == result.summary
    assert 'Private Person' not in json.dumps(value) and 'private@example.invalid' not in json.dumps(value)
    assert result == before


def test_case_endpoint_serves_shared_live_data_and_metadata(api, result):
    app, call = api
    app.requests[result.case_id] = {'case_id': result.case_id, 'audit_at': '2026-07-19T13:00:00Z',
        'requested_at': '2026-07-16T08:00:00Z', 'reported_at': '2026-07-18T08:00:00Z',
        'reported_status': 'COMPLETE', 'email': 'private@example.invalid'}
    status, headers, data = call('GET', '/api/cases')
    assert status == 200 and headers['Cache-Control'] == 'no-store'
    assert data == [present(result, app.requests[result.case_id])]
    assert 'private@example.invalid' not in json.dumps(data)
    assert data[0]['graph_data']['edges'][0]['source'] == 'subject'



def test_api_refuses_a_second_server_on_the_same_port(api, result):
    app, _ = api
    with pytest.raises(OSError):
        server.ApiServer(('127.0.0.1', app.server_port), [result])
