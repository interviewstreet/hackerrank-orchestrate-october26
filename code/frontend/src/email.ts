export type EmailState = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'SENDING' | 'SENT' | 'FAILED';
export interface EmailStatus { operator: string; can_send: boolean; separate_approver_required: boolean; allowed_recipients: string[] }
export interface EmailRecord { id: string; case_id: string; recipient: string; subject: string; body_text: string; state: EmailState; approved_by: string; delivery_status: string }
export interface EmailEvent { at: string; from_state: string | null; to_state: string; actor: string; note: string }
export interface EmailDetail { email: EmailRecord; events: EmailEvent[] }

const messages: Record<number, string> = {
  400: 'Invalid email request. Check the fields and refresh.',
  401: 'Operator token was not accepted. Use the current login token and restart the API after changing operator settings.',
  403: 'Permission denied. Check the session, recipient allowlist, and independent approver.',
  404: 'Email API or record not found. Check the backend version and refresh.',
  409: 'The email state or approved content changed. Refresh before continuing.',
  413: 'The email request is too large.',
  415: 'The email API requires JSON requests.',
  422: 'Check the recipient, subject, and message fields.',
  429: 'Email rate limit reached. Wait before trying again.',
  503: 'Email is unavailable. Configure operators, allowed recipients, and Resend on the server.',
};
export class EmailApiError extends Error {
  constructor(public status: number) { super(messages[status] || 'Email request could not be confirmed. Refresh status before retrying.'); }
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object';
const textFields = (value: unknown, fields: string[]) => object(value) && fields.every(key => typeof value[key] === 'string');
const states = ['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SENDING', 'SENT', 'FAILED'];
function record(value: unknown): EmailRecord {
  if (!textFields(value, ['id', 'case_id', 'recipient', 'subject', 'body_text', 'state', 'approved_by', 'delivery_status']) ||
      !object(value) || !/^[0-9a-f]{32}$/.test(value.id as string) || !states.includes(value.state as string)) throw new EmailApiError(0);
  return value as unknown as EmailRecord;
}

/** Match the adapter's author audit notes. Missing audit history never enables approval. */
export function canReview(status: EmailStatus, email: EmailRecord, events: EmailEvent[]) {
  const authors = events.filter(e => ['created', 'draft edited', 're-drafted after rejection', 'submitted for approval'].includes(e.note));
  return email.state === 'PENDING_APPROVAL' && authors.length > 0 &&
    !authors.some(e => e.actor.trim().toLowerCase() === status.operator.trim().toLowerCase());
}
export function recipientAllowed(allowed: string[], address: string) {
  const value = address.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && allowed.some(item =>
    item.startsWith('@') ? value.slice(value.lastIndexOf('@')) === item.toLowerCase() : value === item.toLowerCase());
}

/** The token exists only in this closure. Every email request obtains the current session CSRF token. */
export function createEmailClient(base: string, operatorToken: string) {
  const token = operatorToken.trim();
  async function request(path: string, method = 'GET', body?: object, signal?: AbortSignal): Promise<any> {
    if (!token) throw new EmailApiError(401);
    const requestSignal = signal ? AbortSignal.any([signal, AbortSignal.timeout(30000)]) : AbortSignal.timeout(30000);
    try {
      const sessionResponse = await fetch(`${base}/api/session`, { credentials: 'include', signal: requestSignal });
      if (!sessionResponse.ok) throw new EmailApiError(sessionResponse.status);
      const session = await sessionResponse.json();
      if (!session || typeof session.csrf_token !== 'string') throw new EmailApiError(0);
      const response = await fetch(`${base}/api/email${path}`, {
        method, credentials: 'include', signal: requestSignal,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token, Authorization: `Bearer ${token}` },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      if (!response.ok) throw new EmailApiError(response.status);
      return await response.json();
    } catch (error) {
      if (signal?.aborted) throw error;
      throw error instanceof EmailApiError ? error : new EmailApiError(0);
    }
  }
  return {
    async status(signal?: AbortSignal): Promise<EmailStatus> {
      const data = await request('/status', 'GET', undefined, signal);
      if (!textFields(data, ['operator']) || typeof data.can_send !== 'boolean' || typeof data.separate_approver_required !== 'boolean' ||
          !Array.isArray(data.allowed_recipients) || !data.allowed_recipients.every((v: unknown) => typeof v === 'string')) throw new EmailApiError(0);
      return data;
    },
    async list(caseId: string, signal?: AbortSignal): Promise<EmailRecord[]> {
      const data = await request(`/emails?case_id=${encodeURIComponent(caseId)}&limit=1000`, 'GET', undefined, signal);
      if (!Array.isArray(data?.emails)) throw new EmailApiError(0);
      const emails = data.emails.map(record);
      if (emails.some((email: EmailRecord) => email.case_id !== caseId)) throw new EmailApiError(0);
      return emails;
    },
    async detail(id: string, signal?: AbortSignal): Promise<EmailDetail> {
      const data = await request(`/emails/${encodeURIComponent(id)}`, 'GET', undefined, signal);
      const email = record(data?.email);
      if (email.id !== id || !Array.isArray(data.events) || !data.events.every((e: unknown) => textFields(e, ['at', 'actor', 'note', 'to_state']))) throw new EmailApiError(0);
      return { email, events: data.events };
    },
    async create(caseId: string, recipient: string, signal?: AbortSignal) {
      const data = await request('/drafts', 'POST', { case_id: caseId, recipient: recipient.trim(), audience: 'requester' }, signal);
      const email = record(data?.email);
      if (email.case_id !== caseId) throw new EmailApiError(0);
      return email;
    },
    async edit(id: string, subject: string, body: string, redraft: boolean, signal?: AbortSignal) {
      return record((await request(`/emails/${encodeURIComponent(id)}/${redraft ? 'redraft' : 'draft'}`, redraft ? 'POST' : 'PUT', { subject, body }, signal))?.email);
    },
    async action(id: string, action: 'submit' | 'approve' | 'reject' | 'send', reason = '', signal?: AbortSignal) {
      return record((await request(`/emails/${encodeURIComponent(id)}/${action}`, 'POST', action === 'reject' ? { reason } : {}, signal))?.email);
    },
  };
}
export type EmailClient = ReturnType<typeof createEmailClient>;
