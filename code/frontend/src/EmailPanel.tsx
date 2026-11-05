import { useEffect, useRef, useState } from 'react';
import { canReview, createEmailClient, EmailApiError, recipientAllowed, type EmailClient, type EmailDetail, type EmailStatus, type EmailRecord } from './email';

export function EmailReviewButtons({ status, detail, disabled, approve, reject }: {
  status: EmailStatus | null; detail: EmailDetail; disabled: boolean; approve: () => void; reject: () => void;
}) {
  const allowed = !!status && canReview(status, detail.email, detail.events);
  return <div className="title-actions"><button disabled={disabled || !allowed} onClick={approve}>Approve</button><button disabled={disabled || !allowed} onClick={reject}>Reject</button></div>;
}

export default function EmailPanel({ base, caseId, demo }: { base: string; caseId: string; demo: boolean }) {
  const [token, setToken] = useState('');
  const [client, setClient] = useState<EmailClient | null>(null);
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [scope, setScope] = useState('');
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [reason, setReason] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const epoch = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => { epoch.current++; pending.current?.abort(); }, []);

  function disconnect() {
    epoch.current++; pending.current?.abort(); pending.current = null;
    setToken(''); setClient(null); setStatus(null); setEmails([]); setDetail(null);
    setSubject(''); setBody(''); setReason(''); setRecipient(''); setScope('');
    setConfirmed(false); setBusy(false); setStale(false); setNotice('');
  }
  function showDetail(value: EmailDetail | null) {
    setDetail(value); setSubject(value?.email.subject || ''); setBody(value?.email.body_text || ''); setReason(''); setConfirmed(false);
  }
  async function run<T,>(work: (signal: AbortSignal) => Promise<T>, accept: (value: T) => void) {
    if (pending.current || demo) return;
    const version = ++epoch.current;
    const controller = new AbortController(); pending.current = controller;
    setBusy(true); setError(''); setNotice(''); setConfirmed(false);
    try {
      const value = await work(controller.signal);
      if (version === epoch.current) { accept(value); setStale(false); }
    } catch (failure) {
      if (version !== epoch.current) return;
      if (failure instanceof EmailApiError && failure.status === 401) { disconnect(); setToken(''); }
      else setStale(!!client);
      setError(failure instanceof EmailApiError ? failure.message : 'Email request could not be confirmed. Refresh status before retrying.');
    } finally { if (version === epoch.current) { pending.current = null; setBusy(false); } }
  }
  async function snapshot(active: EmailClient, signal: AbortSignal, id?: string) {
    const currentStatus = await active.status(signal);
    const records = await active.list(caseId, signal);
    const selected = records.find(e => e.id === id) || records[0];
    const currentDetail = selected ? await active.detail(selected.id, signal) : null;
    if (currentDetail && currentDetail.email.case_id !== caseId) throw new EmailApiError(0);
    return { currentStatus, records, currentDetail };
  }
  function apply(value: Awaited<ReturnType<typeof snapshot>>) {
    setStatus(value.currentStatus); setEmails(value.records); showDetail(value.currentDetail);
  }
  function connect() {
    const active = createEmailClient(base, token);
    void run(signal => snapshot(active, signal), value => {
      setClient(active); setToken(''); apply(value);
      const first = value.currentStatus.allowed_recipients[0] || '';
      setScope(first); setRecipient(first.startsWith('@') ? '' : first);
    });
  }
  function refresh(id = detail?.email.id) {
    if (client) void run(signal => snapshot(client, signal, id), apply);
  }
  function change(action: 'save' | 'submit' | 'approve' | 'reject' | 'send') {
    if (!client || !detail || stale || (action === 'send' && !confirmed)) return;
    if ((action === 'approve' || action === 'reject') && (!status || !canReview(status, detail.email, detail.events))) return;
    void run(async signal => {
      const email = action === 'save'
        ? await client.edit(detail.email.id, subject, body, detail.email.state === 'REJECTED', signal)
        : await client.action(detail.email.id, action, reason, signal);
      if (email.id !== detail.email.id || email.case_id !== caseId) throw new EmailApiError(0);
      return snapshot(client, signal, email.id);
    }, value => { apply(value); setNotice(action === 'send' ? `Send result: ${value.currentDetail?.email.state || 'unknown'}.` : 'Email state refreshed from the server.'); });
  }
  const email = detail?.email;
  const editable = email?.state === 'DRAFT' || email?.state === 'REJECTED';
  const dirty = !!email && (subject !== email.subject || body !== email.body_text);
  const locked = busy || stale;
  const reviewAllowed = !!status && !!detail && canReview(status, detail.email, detail.events);
  return <section className="email-panel" aria-label={`Customer email for ${caseId}`} aria-busy={busy}>
    <h3>Customer email</h3>
    {demo ? <p className="muted">Email actions are unavailable for demo cases.</p> : <>
      {!client ? <form onSubmit={e => { e.preventDefault(); connect(); }}>
        <label>Operator token<input className="input" type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} value={token} onChange={e => setToken(e.target.value)} disabled={busy}/></label>
        <small>Kept only in memory. Refreshing or leaving this case clears the login.</small>
        <button type="submit" disabled={busy || !token.trim()}>Check operator access</button>
      </form> : <>
        <div className="identity-row"><span>Signed in as</span><strong>{status?.operator}</strong></div>
        <p>{status?.can_send ? 'Resend is configured for sending.' : 'Sending is unavailable: configure Resend on the server.'} Independent approval is required in this panel.</p>
        <div className="title-actions"><button disabled={busy} onClick={() => refresh()}>Refresh email status</button><button onClick={() => { disconnect(); setError(''); }}>Clear operator login</button></div>
        <form onSubmit={e => { e.preventDefault(); if (client && status && !locked && recipientAllowed(status.allowed_recipients, recipient) && recipientAllowed([scope], recipient)) void run(async signal => {
          const created = await client.create(caseId, recipient, signal);
          return snapshot(client, signal, created.id);
        }, value => { apply(value); setNotice('Draft loaded. Review its content before submission.'); }); }}>
          <label>Allowed recipient<select aria-label="Allowed recipient" value={scope} disabled={locked} onChange={e => { setScope(e.target.value); setRecipient(e.target.value.startsWith('@') ? '' : e.target.value); }}>
            {status?.allowed_recipients.map(address => <option key={address} value={address}>{address.startsWith('@') ? `Address at ${address}` : address}</option>)}
          </select></label>
          {scope.startsWith('@') && <label>Recipient address<input className="input" type="email" value={recipient} placeholder={`name${scope}`} disabled={locked} onChange={e => setRecipient(e.target.value)}/></label>}
          <button disabled={locked || !status || !recipientAllowed(status.allowed_recipients, recipient) || !recipientAllowed([scope], recipient)}>Create or open draft</button>
        </form>
        {emails.length > 0 ? <label>Case email<select aria-label="Case email" value={email?.id || ''} disabled={busy} onChange={e => refresh(e.target.value)}>
          {emails.map(item => <option key={item.id} value={item.id}>{item.recipient} / {item.state}</option>)}
        </select></label> : <p className="empty">No email drafts for this case.</p>}
        {email && detail && <>
          <div className="identity-row"><span>{email.recipient}</span><strong>{email.state}</strong></div>
          <label>Subject<input className="input" value={subject} maxLength={200} disabled={locked || !editable} onChange={e => setSubject(e.target.value)}/></label>
          <label>Message<textarea rows={8} value={body} maxLength={20000} disabled={locked || !editable} onChange={e => setBody(e.target.value)}/></label>
          <div className="title-actions">
            <button disabled={locked || !editable || !subject.trim() || !body.trim() || (!dirty && email.state !== 'REJECTED')} onClick={() => change('save')}>{email.state === 'REJECTED' ? 'Re-draft' : 'Save draft'}</button>
            <button disabled={locked || dirty || !['DRAFT', 'FAILED'].includes(email.state)} onClick={() => change('submit')}>Submit for approval</button>
          </div>
          {dirty && <small>Save the current content before submitting for approval.</small>}
          <label>Rejection reason<input className="input" value={reason} maxLength={500} disabled={locked || !reviewAllowed} onChange={e => setReason(e.target.value)}/></label>
          <EmailReviewButtons status={status} detail={detail} disabled={locked} approve={() => change('approve')} reject={() => change('reject')}/>
          {email.state === 'PENDING_APPROVAL' && !reviewAllowed && <small>The drafter, editor, and submitter cannot approve this email. Sign in as an independent operator.</small>}
          <label className="email-confirm"><input type="checkbox" checked={confirmed} disabled={locked || email.state !== 'APPROVED' || !status?.can_send} onChange={e => setConfirmed(e.target.checked)}/>I confirm sending this approved email to {email.recipient}.</label>
          <button className="primary" disabled={locked || email.state !== 'APPROVED' || !status?.can_send || !confirmed} onClick={() => change('send')}>Send approved email</button>
          <p role="status">Workflow: {email.state}. {email.delivery_status ? `Provider event: ${email.delivery_status}.` : 'Inbox delivery is not verified; SENT means the provider accepted the send.'}</p>
          {email.state === 'FAILED' && <p role="alert">Sending failed. Refresh the record and submit it for independent approval before another attempt.</p>}
          <details><summary>Audit trail ({detail.events.length})</summary>{detail.events.length ? detail.events.map((event, index) => <div className="history-row" key={index}><div><strong>{event.actor} / {event.to_state}</strong><p>{event.note}</p><small>{event.at}</small></div></div>) : <p>No audit events supplied.</p>}</details>
        </>}
      </>}
    </>}
    {busy && <p role="status">Loading email workflow...</p>}
    {stale && <p className="muted">Refresh email status before another action.</p>}
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
