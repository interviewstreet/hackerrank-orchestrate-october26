# Resend email integration (Member 2)

Human-approved, duplicate-safe email for deletion-audit results. Standard library only, except `router.py` (needs `fastapi`).
Nothing is sent unless a named person approved that exact content.

> **Note:** the team's API is `code/server.py` (standard-library `ThreadingHTTPServer`), not FastAPI. Do not mount this router there and do not create a second server; see [INTEGRATION_PLAN.md](./INTEGRATION_PLAN.md) (identity from the server, separation of duties, recipient allowlist). The router below is only for a FastAPI deployment.

## Mount it (FastAPI deployments only)
```python
from fastapi import Depends
from integrations.email import build_service_from_env
from integrations.email.router import create_email_router

service = build_service_from_env()          # reads RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_WEBHOOK_SECRET, EMAIL_DB_PATH
app.include_router(create_email_router(
    service,
    dependencies=[Depends(your_login_check)],          # REQUIRED in production: protects every route except the webhook
    case_provider=lambda case_id: results_by_id.get(case_id),   # optional: CaseAuditResult.to_dict() so drafts can be generated
))
```
`code/` must be on `sys.path` (the engine and tests already do this). Member 1's files are not modified by this package.

## Safety settings (also apply to the HTTP adapter)
- `EMAIL_ALLOWED_RECIPIENTS` (addresses or `@domain`): when set, drafts and sends to anyone else are refused (checked at draft and again at send). The HTTP adapter refuses to run without it.
- The person who drafted, edited, re-drafted or submitted an email cannot approve it. `EMAIL_ALLOW_SELF_APPROVAL=1` switches that off for one-person demos.
- `EMAIL_OPERATORS` (hashed login tokens) is used by `http_adapter.py`; see [INTEGRATION_PLAN.md](./INTEGRATION_PLAN.md).

## Workflow
`DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED -> SENDING -> SENT | FAILED`
- Only `PENDING_APPROVAL` can become `APPROVED`; only `APPROVED` can become `SENDING`. Nothing else leads there.
- `REJECTED -> DRAFT` (re-draft, revision + 1) and `FAILED -> PENDING_APPROVAL` (a failed send needs approval again) are the only extra edges.
- Content can be edited only in `DRAFT`. Approval stores a hash of subject + body; `send` refuses if it no longer matches.
- Every change writes an audit event (who, when, from, to). Read it with `GET /email/emails/{id}`.

## Duplicate-send prevention
- One email per **case + recipient + kind** (`kind` defaults to `audit_result`). A second draft returns the existing one (`created: false`).
- The state change `APPROVED -> SENDING` is one atomic SQLite `UPDATE`, so concurrent or repeated send calls cannot both win; a `SENT` email is returned as is.
- The same idempotency key is sent to Resend (`Idempotency-Key`), so a retry after a timeout cannot double-send inside Resend's 24-hour window.

## Endpoints (prefix `/email`)
| Method | Path | Purpose |
|---|---|---|
| POST | `/drafts` | `{case_id, recipient, subject?, body?, audience?, explanation?, actor?}`; omit subject/body to generate from `case_provider` |
| GET | `/emails?case_id=&state=` | list |
| GET | `/emails/{id}` | email + audit events |
| PUT | `/emails/{id}/draft` | edit (DRAFT only) |
| POST | `/emails/{id}/redraft` | new content after rejection |
| POST | `/emails/{id}/submit` | `{actor}` -> PENDING_APPROVAL |
| POST | `/emails/{id}/approve` | `{approver}` |
| POST | `/emails/{id}/reject` | `{approver, reason?}` |
| POST | `/emails/{id}/send` | `{actor}`; 409 if not approved, 503 if Resend is not configured |
| POST | `/webhooks/resend` | Resend delivery events; verified with the Svix signature, not with Member 1's login |

## Drafts
`audience="requester"` (default) uses customer-safe wording built from the engine's counts; it never contains internal resource or evidence ids.
`audience="internal"` appends the advisory explanation and any review flag for the approver to read (it may contain internal ids, so remove it before approving a customer email).

## Resend setup
1. Verify a sender/domain in Resend and set `RESEND_FROM_EMAIL`; create an API key and set `RESEND_API_KEY`.
2. Add a webhook pointing at `<your host>/email/webhooks/resend`; copy its signing secret (`whsec_...`) into `RESEND_WEBHOOK_SECRET`.
3. Webhooks without the secret are refused (503); bad signatures or timestamps older than 5 minutes are refused (400).

## Limits to know
- Through the FastAPI router the approver name is whatever the caller sends; trust it only behind real authentication. The HTTP adapter (used with `code/server.py`) takes the name from the login token instead.
- If a send times out the outcome is unknown: the email is `FAILED`, and a re-approved retry reuses the same key (safe for 24 hours).
- The SQLite outbox contains email bodies (it is gitignored); do not commit `email_outbox.db`.

## Try it from the terminal (no API needed)
`python code/email_demo.py --to you@example.com --dry-run` shows the whole flow without sending. Drop `--dry-run` to send one real demo email (needs `RESEND_API_KEY` and `RESEND_FROM_EMAIL` in `.env`); it sends only after you type your name to approve.

## Tests
`pytest code/tests/test_email_*.py` uses a fake Resend transport (and a localhost-only server for the real HTTP path). Real email is never sent.
