# Email over the existing API (`code/server.py`)

Status: **adapter built and tested (Member 2). Not yet wired into `code/server.py` or the frontend (Member 1).**
There is one API server, `code/server.py` (standard-library `ThreadingHTTPServer` on 127.0.0.1). Do not create a second server and do not mount the FastAPI router there.

## Why the existing session was not enough
`GET /api/session` gives an anonymous session and CSRF token to any caller that passes the origin checks. That stops cross-site browser attacks but does not say *who* is approving, and the email package used to trust any name sent in the request. Email can reach a real customer, so the approval gate has to know the person.

## What the adapter does (`integrations/email/http_adapter.py`)
`EmailHttpAdapter.handle(method, target, headers, body) -> (status, dict)`. Pure Python, no framework, thread-safe.
- **Identity from the server.** Every route needs `Authorization: Bearer <token>`. The server hashes the token and looks it up in `EMAIL_OPERATORS` (`name:sha256` pairs; only hashes are stored). The matched name is the actor/approver in the audit trail. An `actor`/`approver` in the request body is ignored.
- **Fail closed.** No operators configured, or no `EMAIL_ALLOWED_RECIPIENTS`, gives 503 on every route.
- **Separation of duties.** Whoever drafted, edited, re-drafted or submitted an email cannot approve it (403). `EMAIL_ALLOW_SELF_APPROVAL=1` switches this off for a one-person demo; `/status` shows which mode is on.
- **Recipient allowlist.** Addresses (`a@x.com`) or whole domains (`@x.com`), checked at draft time and again at send time (403).
- **Abuse limits.** 10 failed logins per minute locks logins for the rest of the minute (429); sending is one at a time with a 2-second gap.
- **Unchanged guarantees** from the core: nothing is sent unless a person approved that exact content (hash checked at send), one email per case + recipient + kind, atomic `APPROVED -> SENDING`, and a Resend idempotency key.
- Errors are plain `{"error": "..."}`; unexpected failures return a generic 500 with no internals or keys.

## Endpoints (all under `/api/email`, all need the bearer token)
| Method | Path | Notes |
|---|---|---|
| GET | `/status` | `{operator, can_send, separate_approver_required, allowed_recipients}` |
| GET | `/emails?case_id=&state=&limit=` | `{emails: [...]}` |
| POST | `/drafts` | `{case_id, recipient, subject?, body?, audience?, explanation?}`; omit subject and body to generate from a case the server knows |
| GET | `/emails/{id}` | `{email, events}` (audit trail) |
| PUT | `/emails/{id}/draft` | `{subject, body}` while DRAFT |
| POST | `/emails/{id}/redraft` | `{subject, body}` after rejection |
| POST | `/emails/{id}/submit`, `/approve`, `/send` | body empty or `{}` |
| POST | `/emails/{id}/reject` | `{reason?}` |
Status codes: 401 bad or missing token, 403 recipient not allowed or approver also drafted, 404 unknown, 409 wrong state / content changed / another send running, 413/415/400/422 bad request, 429 rate limited, 503 not configured.

## What Member 1 adds to `code/server.py` (about 25 lines; not done by Member 2)
```python
# imports
import os
from integrations.email.email_service import build_service_from_env
from integrations.email.http_adapter import EmailHttpAdapter, MAX_BODY, PREFIX
from integrations.email.operators import Operators

# in main(), after load_env(...) and load_results(...):
server.email = EmailHttpAdapter(build_service_from_env(), Operators.from_env(os.environ),
                                case_provider=lambda cid: results_by_id[cid].to_dict() if cid in results_by_id else None)
# (create ApiServer first, then set server.email; results_by_id = {r.case_id: r for r in results})

# in Handler:
def email_request(self):
    """Answer /api/email/* requests. Returns True if the path was an email path."""
    if not (self.path == PREFIX or self.path.startswith(PREFIX + '/')):
        return False
    session = self.session()
    if not self.trusted_browser() or self.headers.get('Origin', '') not in ORIGINS | {''} or not session:
        self.reply(403, {'error': 'Email session expired. Refresh and try again.'})
    elif self.command != 'GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token', '').encode(), session['csrf'].encode('ascii')):
        self.reply(403, {'error': 'Email session expired. Refresh and try again.'})
    else:
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            size = -1
        if not 0 <= size <= MAX_BODY or self.headers.get('Transfer-Encoding'):
            self.reply(413, {'error': 'Request body is too large.'})
        else:
            self.reply(*self.server.email.handle(self.command, self.path, self.headers, self.rfile.read(size)))
    return True
# call it first in do_GET and do_POST:  if self.email_request(): return
# add:  do_PUT = lambda self: self.email_request() or self.reply(404, {'error': 'Endpoint not found.'})
# in do_OPTIONS: allow methods 'GET, POST, PUT' and headers 'Content-Type, X-CSRF-Token, Authorization'
```
Tested: this exact wiring was applied to a scratch copy of `member-1-frontend-slack` (commit `ee39f7e`) and exercised over real HTTP, 20 of 20 checks (origin, CSRF and token checks, allowlist, drafter cannot approve even by naming someone else, audit trail names, CORS preflight, existing routes unchanged). Her `server.py` itself was not modified.

Frontend: a login-token box whose value lives only in memory (a variable, never `localStorage`, the URL or Vite config), sent as the `Authorization` header; show `/status` (who you are, whether sending is possible); disable Approve for the person who drafted. Keep Slack as it is.

## Setting it up (each person who may approve or send)
1. `python code/email_operator_token.py --name Rachana --env-file .env` prints a login token once and stores only its hash in `.env`. Run it again with another name for a second person (a different approver is required).
2. Add to `.env`: `EMAIL_ALLOWED_RECIPIENTS=<comma-separated addresses or @domains>`; `RESEND_FROM_EMAIL=<a sender verified in Resend>`; `RESEND_API_KEY`.
3. **Sender and recipients.** The free sender `onboarding@resend.dev` is for testing only: it can deliver only to the address your Resend account uses, and any other recipient gets a 403. Emailing real customers needs a domain you own, verified in Resend (`bmsit.in` is not ours to verify). The dataset customers are fictional, so the demo uses test inboxes:
   - `RESEND_FROM_EMAIL=onboarding@resend.dev`
   - `EMAIL_ALLOWED_RECIPIENTS=<your Resend account email>,delivered@resend.dev,bounced@resend.dev`
   - Send one real email to your own address, plus `delivered@resend.dev` (Resend shows Delivered) and `bounced@resend.dev` (shows Bounced in the Resend dashboard only, because our app does not receive webhooks; it still shows SENT).
   - Use a different recipient for each email: the system sends one email per case, recipient and kind.
   - Staff (operators) draft and approve; the customer is only the recipient.

## Resend webhooks
`server.py` listens on 127.0.0.1 only, so Resend cannot reach it, and the approval routes must never be exposed through a tunnel. Without webhooks an email's state comes from the send call (`SENT` or `FAILED`); delivery events (delivered/bounced) are not recorded. If those are needed, run a separate minimal listener for `/webhooks/resend` only (`EmailService.handle_webhook` already verifies the Svix signature).

## Known limits
- The token is a shared secret per person; anyone who has it can act as that person. Tokens last until replaced.
- Operators and the allowlist are read at start-up; restart the server after changing `.env`.
- The sender and recipient addresses are not checked against Resend until a real send is tried.
- Not covered: `code/server.py` and the frontend are Member 1's and are untouched; the wiring above is untested until she adds it.
