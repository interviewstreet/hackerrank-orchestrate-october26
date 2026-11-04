import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sendSlackReport } from './slack';

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
test('Slack sends only the case ID with session credentials and CSRF protection', async () => {
  const original = globalThis.fetch;
  const calls: { url: string; options?: RequestInit }[] = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return calls.length === 1 ? json({ csrf_token: 'csrf', slack_configured: true, slack_report_format: 'html-v1' }) : json({ status: 'sent', case_id: 'case_1' });
  };
  try {
    await sendSlackReport('', 'case_1');
    assert.equal(calls[1].url, '/api/cases/case_1/slack');
    assert.equal(calls[1].options?.body, '{}');
    assert.equal(calls[1].options?.credentials, 'include');
    assert.equal((calls[1].options?.headers as Record<string,string>)['X-CSRF-Token'], 'csrf');
  } finally { globalThis.fetch = original; }
});
test('Demo cases never reach the server', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('Must not call fetch'); };
  try { await assert.rejects(sendSlackReport('', 'DEMO-001'), /Demo cases cannot be sent/); }
  finally { globalThis.fetch = original; }
});
test('Missing configuration never attempts delivery', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return json({ csrf_token: 'csrf', slack_configured: false, slack_report_format: 'html-v1' }); };
  try { await assert.rejects(sendSlackReport('', 'case_1'), /not configured/); assert.equal(calls, 1); }
  finally { globalThis.fetch = original; }
});
for (const status of [403, 404, 409, 429, 502, 503]) test(`Slack failure ${status} is visible without exposing upstream text`, async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => ++calls === 1 ? json({ csrf_token: 'csrf', slack_configured: true, slack_report_format: 'html-v1' }) : json({ error: 'sensitive upstream body' }, status);
  try {
    await assert.rejects(sendSlackReport('', 'case_1'), error => error instanceof Error && !error.message.includes('sensitive') && !error.message.includes('sent for'));
  } finally { globalThis.fetch = original; }
});
test('Network failures and unconfirmed successes do not report delivery', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => { throw new Error('private webhook URL'); };
    await assert.rejects(sendSlackReport('', 'case_1'), /could not be confirmed/);
    let calls = 0;
    globalThis.fetch = async () => ++calls === 1 ? json({ csrf_token: 'csrf', slack_configured: true, slack_report_format: 'html-v1' }) : json({ status: 'sent', case_id: 'case_2' });
    await assert.rejects(sendSlackReport('', 'case_1'), /could not be confirmed/);
  } finally { globalThis.fetch = original; }
});


test('Older text-only servers are rejected before any Slack post', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return json({ csrf_token: 'csrf', slack_configured: true }); };
  try {
    await assert.rejects(sendSlackReport('', 'case_1'), /Restart the EraSight backend/);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});
