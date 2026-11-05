import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import EmailPanel, { EmailReviewButtons } from './EmailPanel';
import { canReview, createEmailClient, EmailApiError, recipientAllowed, type EmailDetail, type EmailStatus } from './email';

const id = 'a'.repeat(32);
const token = 'fake-operator-token-not-real';
const status: EmailStatus = { operator: 'Bob', can_send: true, separate_approver_required: true, allowed_recipients: ['person@example.test', '@allowed.test'] };
const detail: EmailDetail = {
  email: { id, case_id: 'case_1', recipient: 'person@example.test', subject: 'Subject', body_text: 'Body',
    state: 'PENDING_APPROVAL', approved_by: '', delivery_status: '' },
  events: [{ at: '2026-01-01T00:00:00Z', from_state: null, to_state: 'DRAFT', actor: 'Alice', note: 'created' }],
};
const json = (value: unknown, code = 200) => new Response(JSON.stringify(value), { status: code });

test('all email routes include credentials, current CSRF, and bearer headers without token in URL/body', async () => {
  const original = globalThis.fetch;
  const calls: { path: string; method: string; body: any }[] = [];
  let sessions = 0;
  globalThis.fetch = async (url, options) => {
    const path = String(url);
    assert.equal(options?.credentials, 'include');
    if (path === '/api/session') return json({ csrf_token: `csrf-${++sessions}` });
    const headers = options?.headers as Record<string, string>;
    assert.equal(headers.Authorization, `Bearer ${token}`);
    assert.equal(headers['X-CSRF-Token'], `csrf-${sessions}`);
    assert.equal(headers['Content-Type'], 'application/json');
    assert.ok(!path.includes(token) && !String(options?.body).includes(token));
    calls.push({ path, method: options?.method || 'GET', body: options?.body ? JSON.parse(String(options.body)) : undefined });
    if (path === '/api/email/status') return json(status);
    if (path.startsWith('/api/email/emails?')) return json({ emails: [detail.email] });
    return json({ ...detail, created: true });
  };
  try {
    const client = createEmailClient('', token);
    await client.status(); await client.list('case_1'); await client.detail(id);
    await client.create('case_1', 'person@example.test');
    await client.edit(id, 'New subject', 'New body', false);
    await client.edit(id, 'Re-draft', 'New body', true);
    for (const action of ['submit', 'approve', 'reject', 'send'] as const) await client.action(id, action, 'Reason');
    assert.equal(sessions, 10);
    assert.deepEqual(calls[3].body, { case_id: 'case_1', recipient: 'person@example.test', audience: 'requester' });
    assert.equal(calls[4].method, 'PUT');
    assert.deepEqual(calls[4].body, { subject: 'New subject', body: 'New body' });
    assert.ok(calls[5].path.endsWith('/redraft') && calls[5].method === 'POST');
    assert.deepEqual(calls[8].body, { reason: 'Reason' });
    assert.deepEqual(calls[9].body, {});
    assert.ok(calls.every(call => !call.body?.actor && !call.body?.approver));
  } finally { globalThis.fetch = original; }
});

test('operator tokens never touch persistent browser storage and a fresh panel starts logged out', async () => {
  const original = globalThis.fetch;
  const saved = ['localStorage', 'sessionStorage'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const);
  for (const [key] of saved) Object.defineProperty(globalThis, key, { configurable: true, get() { throw new Error('Persistent storage must not be accessed'); } });
  globalThis.fetch = async url => String(url) === '/api/session' ? json({ csrf_token: 'csrf' }) : json(status);
  try {
    const client = createEmailClient('', token);
    await client.status();
    assert.ok(!JSON.stringify(client).includes(token));
    await assert.rejects(createEmailClient('', '').status(), error => error instanceof EmailApiError && error.status === 401);
    for (let refresh = 0; refresh < 2; refresh++) {
      const html = renderToStaticMarkup(<EmailPanel base="" caseId="case_1" demo={false}/>);
      assert.match(html, /type="password"/);
      assert.match(html, /autoComplete="off"/i);
      assert.match(html, /value=""/);
      assert.ok(!html.includes(token) && !html.includes('Signed in as'));
    }
  } finally {
    globalThis.fetch = original;
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
  }
});

test('drafter, editor and submitter cannot approve, including case variations and demo self-approval mode', () => {
  for (const note of ['created', 'draft edited', 're-drafted after rejection', 'submitted for approval']) {
    const authored = { ...detail, events: [{ ...detail.events[0], note, actor: ' Alice ' }] };
    const alice = { ...status, operator: 'alice', separate_approver_required: false };
    assert.equal(canReview(alice, authored.email, authored.events), false);
    const html = renderToStaticMarkup(<EmailReviewButtons status={alice} detail={authored} disabled={false} approve={() => {}} reject={() => {}}/>);
    assert.match(html, /<button disabled="">Approve<\/button>/);
    assert.match(html, /<button disabled="">Reject<\/button>/);
  }
  assert.equal(canReview(status, detail.email, []), false);
});

test('independent reviewer is enabled only while pending approval; loading disables the buttons', () => {
  assert.equal(canReview(status, detail.email, detail.events), true);
  let html = renderToStaticMarkup(<EmailReviewButtons status={status} detail={detail} disabled={false} approve={() => {}} reject={() => {}}/>);
  assert.match(html, /<button>Approve<\/button>/);
  for (const state of ['DRAFT', 'APPROVED', 'REJECTED', 'SENDING', 'SENT', 'FAILED'] as const) {
    assert.equal(canReview(status, { ...detail.email, state }, detail.events), false);
  }
  html = renderToStaticMarkup(<EmailReviewButtons status={status} detail={detail} disabled approve={() => {}} reject={() => {}}/>);
  assert.match(html, /<button disabled="">Approve<\/button>/);
});

for (const code of [401, 403, 409, 429, 503]) test(`email HTTP ${code} is clear and does not expose upstream secrets`, async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async url => String(url) === '/api/session' ? json({ csrf_token: 'csrf' }) : json({ error: token }, code);
  try { await assert.rejects(createEmailClient('', token).status(), error => error instanceof EmailApiError && error.status === code && !error.message.includes(token)); }
  finally { globalThis.fetch = original; }
});

test('network uncertainty is not retried and cannot claim a confirmed send', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async url => {
    if (String(url) === '/api/session') return json({ csrf_token: 'csrf' });
    calls++; throw new Error(token);
  };
  try {
    await assert.rejects(createEmailClient('', token).action(id, 'send'), /could not be confirmed/);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});

test('recipient selection accepts exact addresses or allowed domains, not subdomains/lookalikes', () => {
  assert.equal(recipientAllowed(status.allowed_recipients, 'PERSON@example.test'), true);
  assert.equal(recipientAllowed(status.allowed_recipients, 'other@allowed.test'), true);
  for (const address of ['other@example.test', 'a@sub.allowed.test', 'a@allowed.test.evil', 'not-email']) {
    assert.equal(recipientAllowed(status.allowed_recipients, address), false);
  }
});

test('case list validation rejects emails belonging to a different case', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async url => String(url) === '/api/session' ? json({ csrf_token: 'csrf' }) : json({ emails: [detail.email] });
  try { await assert.rejects(createEmailClient('', token).list('case_2'), EmailApiError); }
  finally { globalThis.fetch = original; }
});


test('an HTTP 200 FAILED send stays FAILED and is never presented as SENT', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async url => String(url) === '/api/session' ? json({ csrf_token: 'csrf' })
    : json({ email: { ...detail.email, state: 'FAILED' } });
  try { assert.equal((await createEmailClient('', token).action(id, 'send')).state, 'FAILED'); }
  finally { globalThis.fetch = original; }
});


test('401 explains token/configuration mismatch while 403 remains a session/permission error', async () => {
  const original = globalThis.fetch;
  try {
    for (const code of [401, 403]) {
      globalThis.fetch = async url => String(url) === '/api/session' ? json({ csrf_token: 'csrf' }) : json({}, code);
      await assert.rejects(createEmailClient('', token).status(), error => {
        assert.ok(error instanceof EmailApiError);
        assert.equal(error.status, code);
        if (code === 401) {
          assert.match(error.message, /restart the API/);
          assert.ok(!error.message.includes('expired'));
        } else {
          assert.match(error.message, /Permission denied/);
          assert.ok(!error.message.includes('token was not accepted'));
        }
        return true;
      });
    }
  } finally { globalThis.fetch = original; }
});
