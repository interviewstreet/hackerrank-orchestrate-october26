"""Server-side Slack notifications. No identities or free-form evidence leave the server."""
from __future__ import annotations

import json
import os
import re
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from engine.contracts import CaseAuditResult, OPERATION_STATE
from engine.util import RESOURCE_PREFIX_CATEGORY

SYSTEMS = {system: system.replace('_', ' ') for _, system, _ in RESOURCE_PREFIX_CATEGORY}
FINDINGS = {
    'REPORT_REMAINING_RECORD': ('HIGH', 'Required record deletion remains incomplete'),
    'REPORT_EXPOSED_PII': ('HIGH', 'Required identifier treatment remains incomplete'),
    'REPORT_ACTIVE_DATA_FLOW': ('HIGH', 'An active data flow can recreate deleted data'),
    'REPORT_RESTORE_RISK': ('MEDIUM', 'A restore path can recreate deleted data'),
}
ACTIONS = {
    'DISABLE_DATA_FLOW': 'Disable data flow', 'BLOCK_RESTORE': 'Block unsafe restore',
    'DELETE_RECORD': 'Delete record', 'REDACT_RECORD': 'Redact identifiers',
    'ANONYMIZE_RECORD': 'Anonymize record',
}
EVIDENCE_ID = re.compile(r'(?:evidence|activity|audit)_\d{1,12}\Z')
CASE_ID = re.compile(r'(?:case|sample(?:_case)?|mini)_\d{1,12}\Z')


class SlackError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def webhook_url() -> str:
    value = os.environ.get('SLACK_WEBHOOK_URL', '').strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SlackError('Slack webhook configuration is invalid.', 503) from None
    if (parsed.scheme != 'https' or parsed.netloc not in {'hooks.slack.com', 'hooks.slack-gov.com'}
            or not re.fullmatch(r'/services/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', parsed.path)
            or parsed.query or parsed.fragment):
        raise SlackError('Slack is not configured. Set a valid SLACK_WEBHOOK_URL on the server.', 503)
    return value


def severity(result: CaseAuditResult) -> str:
    levels = [FINDINGS[f.get('operation')][0] for f in result.findings if f.get('operation') in FINDINGS]
    if 'HIGH' in levels:
        return 'HIGH'
    if 'MEDIUM' in levels:
        return 'MEDIUM'
    return 'UNKNOWN' if result.deletion_status == 'INCOMPLETE' else 'NONE'


def report_sections(result: CaseAuditResult) -> list[tuple[str, str]]:
    if not CASE_ID.fullmatch(result.case_id) or result.deletion_status not in {'COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE'}:
        raise SlackError('This case cannot be safely shared.', 422)
    def citation(step):
        value = step.get('evidence_id', '')
        return value if isinstance(value, str) and EVIDENCE_ID.fullmatch(value) else ''

    def system(step):
        return SYSTEMS.get(step.get('system_id'), 'Unlisted system')

    finding_lines = []
    for f in result.findings:
        label = FINDINGS.get(f.get('operation'), ('UNKNOWN', 'Unclassified finding'))[1]
        ref = citation(f)
        known = f.get('operation') in FINDINGS and bool(ref)
        finding_lines.append(f"- {'UNRESOLVED' if known else 'UNKNOWN'} - {system(f)}: {label}. "
                             + (f'Evidence: {ref}.' if ref else 'No safe evidence reference supplied.'))
    remediation = [s for s in result.steps if s.get('phase') == 'REMEDIATION']
    # Keep every action in backend order; grouping could hide dependencies.
    actions = [f"{i}. {ACTIONS.get(s.get('operation'), 'Review unclassified remediation')} / {system(s)}"
               for i, s in enumerate(remediation, 1)]
    verification = []
    verified = 0
    for step in result.steps:
        if step.get('phase') != 'VERIFICATION':
            continue
        op = step.get('operation')
        expected = OPERATION_STATE.get(op)
        valid = expected == ('VERIFICATION', step.get('state'))
        ref = citation(step)
        proven = valid and bool(ref) and result.deletion_status == 'COMPLETE'
        verified += proven
        status = 'VERIFIED' if proven else ('UNRESOLVED' if valid and not ref else 'UNKNOWN')
        label = op.replace('_', ' ').capitalize() if valid else 'Unclassified verification'
        verification.append(f"- {status} - {system(step)}: {label}. "
                            + (f'Evidence: {ref}.' if proven else 'Not confirmed; requires evidence-backed verification.'))
    systems = sorted({system(s) for s in [*result.findings, *result.steps]})
    no_actions = ('Manual investigation required; no remediation supplied.' if result.deletion_status == 'INCOMPLETE'
                  else 'No remediation supplied by the backend result.')
    return [
        ('Case overview', f'Case ID: {result.case_id}\nOverall deletion status: {result.deletion_status}\n'
         f'Risk severity: {severity(result)}\nSeverity is derived from finding operations, not an independent risk assessment.'),
        ('Affected systems', ', '.join(systems) or 'Unknown - no systems supplied.'),
        ('Evidence-backed findings', '\n'.join(finding_lines) or 'No findings supplied. This alone does not prove deletion.'),
        ('Evidence references', '\n'.join(sorted({citation(item) for item in [*result.evidence, *result.findings, *result.steps]
                                                     if citation(item)})) or 'Unknown - no safe evidence references supplied.'),
        ('Remediation recommendations - not executed', '\n'.join(actions) or no_actions),
        ('Verification status', f'{verified} evidence-backed checks verified; {len(verification) - verified} checks not confirmed.\n'
         + ('\n'.join(verification) or ('Not applicable - backend classified the request as NOT_APPLICABLE.'
            if result.deletion_status == 'NOT_APPLICABLE' else 'UNKNOWN - no verification checks supplied.'))),
        ('Report scope', 'VERIFIED means an evidence-cited completed check. UNRESOLVED means a cited issue or a pending check. '
         'UNKNOWN means missing or unrecognized evidence or check details. Personal identifiers, resource IDs and raw evidence are excluded.'),
    ]


def html_report(result: CaseAuditResult) -> bytes:
    sections = report_sections(result)
    content = ''.join(f'<section><h2>{escape(title)}</h2><pre>{escape(body)}</pre></section>'
                      for title, body in sections)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; '
            'base-uri \'none\'; form-action \'none\'">'
            '<title>EraSight Investigation Report</title><style>'
            'body{font:16px/1.6 system-ui,sans-serif;color:#182534;background:#f4f6f8;margin:0;padding:40px}'
            'main{max-width:960px;margin:auto;background:white;padding:40px;border-top:6px solid #15766c}'
            'h1{font-size:28px}h2{font-size:18px;color:#15766c}section{border-top:1px solid #dce3e8;padding:16px 0}'
            'pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}'
            '@media print{body,main{padding:0;background:white}section{break-inside:avoid}}'
            '</style></head><body><main><h1>EraSight &mdash; Investigation Report</h1>'
            + content + '</main></body></html>').encode('utf-8')


def report_link(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if (parsed.scheme == 'https' and re.fullmatch(r'[a-z0-9-]+\.slack(?:-gov)?\.com', parsed.netloc)
                and re.fullmatch(r'/files/[A-Z0-9]+/F[A-Z0-9]+(?:/[a-zA-Z0-9_.-]+)?', parsed.path)
                and not parsed.query and not parsed.fragment):
            return value
    except (ValueError, TypeError):
        pass
    raise SlackError('Slack did not return a safe report link. No report delivery was confirmed.')


def payload(result: CaseAuditResult, report_url: str) -> dict:
    overview = report_sections(result)[0][1].replace('Overall deletion status:', 'Deletion Status:').replace('Risk severity:', 'Risk Severity:')
    overview = '\n\n'.join(overview.splitlines())
    link = report_link(report_url)
    summary = 'EraSight \u2014 Investigation Report\n\nCase Overview\n\n' + overview + '\n\nFull HTML Investigation Report: ' + link
    return {'text': summary, 'blocks': [
        {'type': 'header', 'text': {'type': 'plain_text', 'text': 'EraSight \u2014 Investigation Report', 'emoji': False}},
        {'type': 'section', 'text': {'type': 'plain_text', 'text': 'Case Overview\n\n' + overview, 'emoji': False}},
        {'type': 'section', 'text': {'type': 'mrkdwn',
         'text': f'<{link}|Download Full HTML Investigation Report> (Slack sign-in required)'}},
    ], 'unfurl_links': False, 'unfurl_media': False}


def upload_config() -> tuple[str, str]:
    token = os.environ.get('SLACK_BOT_TOKEN', '').strip()
    channel = os.environ.get('SLACK_REPORT_CHANNEL_ID', '').strip()
    if not re.fullmatch(r'xoxb-[A-Za-z0-9-]+', token) or not re.fullmatch(r'[CG][A-Z0-9]{8,}', channel):
        raise SlackError('HTML reports require server-side SLACK_BOT_TOKEN and SLACK_REPORT_CHANNEL_ID configuration.', 503)
    return token, channel


def configuration() -> None:
    webhook_url()
    upload_config()


def upload_report(result: CaseAuditResult, opener) -> str:
    token, channel = upload_config()
    content = html_report(result)

    def api(method, data):
        encoded = urlencode({key: json.dumps(value) if isinstance(value, (list, dict)) else value
                             for key, value in data.items()}).encode('utf-8')
        request = Request('https://slack.com/api/' + method, data=encoded,
                          headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/x-www-form-urlencoded'},
                          method='POST')
        with opener.open(request, timeout=10) as response:
            try:
                value = json.loads(response.read(262144))
            except (ValueError, UnicodeError):
                raise SlackError('Slack returned an invalid report-upload response.') from None
            if response.status != 200 or not isinstance(value, dict) or value.get('ok') is not True:
                errors = {
                    'not_in_channel': 'The report bot is not in the configured Slack channel. Invite the app that issued SLACK_BOT_TOKEN and verify SLACK_REPORT_CHANNEL_ID.',
                    'missing_scope': 'The report bot needs files:write and files:read permissions. Reinstall the Slack app after adding these scopes.',
                }
                code = value.get('error') if isinstance(value, dict) else None
                raise SlackError(errors.get(code, 'Slack could not complete the report upload. Check bot permissions and channel access.'))
            return value

    ticket = api('files.getUploadURLExternal', {'filename': result.case_id + '-investigation.html', 'length': len(content)})
    upload_url, file_id = ticket.get('upload_url', ''), ticket.get('file_id', '')
    try:
        parsed = urlsplit(upload_url)
        safe_upload = (parsed.scheme == 'https' and parsed.netloc == 'files.slack.com'
                       and parsed.path.startswith('/upload/v1/') and not parsed.fragment)
    except (ValueError, TypeError):
        safe_upload = False
    if not safe_upload or not isinstance(file_id, str) or not re.fullmatch(r'F[A-Z0-9]+', file_id):
        raise SlackError('Slack returned an invalid report-upload destination.')
    # Upload tickets receive only sanitized HTML; never forward the bot token.
    request = Request(upload_url, data=content, headers={'Content-Type': 'text/html; charset=utf-8'}, method='POST')
    with opener.open(request, timeout=10) as response:
        if response.status != 200:
            raise SlackError('Slack did not accept the HTML report upload.')
    completed = api('files.completeUploadExternal', {
        'files': [{'id': file_id, 'title': result.case_id + ' - Full HTML Investigation Report'}], 'channel_id': channel})
    if not any(isinstance(f, dict) and f.get('id') == file_id for f in completed.get('files', [])):
        raise SlackError('Slack did not confirm the uploaded report.')
    info = api('files.info', {'file': file_id})
    file = info.get('file', {})
    if not isinstance(file, dict) or file.get('id') != file_id or file.get('public_url_shared') is not False:
        raise SlackError('Slack did not confirm a private report link.')
    return report_link(file.get('permalink', ''))



class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def deliver(result: CaseAuditResult) -> None:
    url = webhook_url()
    upload_config()
    try:
        opener = build_opener(NoRedirect())
        link = upload_report(result, opener)
        request = Request(url, data=json.dumps(payload(result, link)).encode('utf-8'),
                          headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
        with opener.open(request, timeout=10) as response:
            if response.status != 200 or response.read(64).strip() != b'ok':
                raise SlackError('Slack did not accept the notification. No delivery was confirmed.')
    except HTTPError as error:
        if error.code == 429:
            raise SlackError('Slack rate limit reached. Wait before trying again.', 429) from None
        raise SlackError('Slack rejected the notification. Check the server webhook configuration.') from None
    except (URLError, TimeoutError, OSError):
        raise SlackError('Slack delivery could not be confirmed. Check the channel before retrying.') from None
