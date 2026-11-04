# Shared contract: engine output and email router (Member 2 -> Member 1)

Everything here is produced by Member 2's code. Member 1's files (`api.py`, frontend, Slack) are not modified by it.
All code lives under `code/`; put `code/` on `sys.path` (the engine, tests and CLIs already do).

## 1. `output.csv` (the graded file)
Written by `python3 code/main.py` to the repository root.

- Header exactly `case_id,deletion_status,steps_json`; one row per request in `dataset/deletion_requests.csv` (518); sorted by `case_id`.
- `deletion_status`: `COMPLETE`, `INCOMPLETE` or `NOT_APPLICABLE`. `NOT_APPLICABLE` always has `steps_json` equal to `[]`.
- `steps_json` is a compact JSON array (UTF-8, no extra whitespace). Each step has exactly these keys:

| Key | Type | Meaning |
|---|---|---|
| `step_no` | int | 1, 2, 3, ... consecutive |
| `phase` | string | `FINDING`, then `REMEDIATION`, then `VERIFICATION` |
| `system_id` | string | e.g. `account_service`, `export_service` |
| `resource_id` | string | e.g. `account_005` |
| `operation` | string | one of the operations below |
| `state` | string | fixed by the operation (below) |
| `evidence_id` | string | a manifest `file_id`, `activity_id` or `audit_id`; empty string for remediation and future checks |

| Phase | Operation -> state |
|---|---|
| FINDING | `REPORT_REMAINING_RECORD` -> PRESENT, `REPORT_EXPOSED_PII` -> PRESENT, `REPORT_ACTIVE_DATA_FLOW` -> ACTIVE, `REPORT_RESTORE_RISK` -> ACTIVE |
| REMEDIATION | `DISABLE_DATA_FLOW` -> DISABLED, `BLOCK_RESTORE` -> BLOCKED, `DELETE_RECORD` -> ABSENT, `REDACT_RECORD` -> REDACTED, `ANONYMIZE_RECORD` -> ANONYMIZED |
| VERIFICATION | `VERIFY_RECORD_ABSENT` -> ABSENT, `VERIFY_RECORD_PRESENT` -> PRESENT, `VERIFY_RECORD_REDACTED` -> REDACTED, `VERIFY_RECORD_ANONYMIZED` -> ANONYMIZED, `VERIFY_DATA_FLOW_DISABLED` -> DISABLED, `VERIFY_RESTORE_BLOCKED` -> BLOCKED |

Order inside a phase: operation order as listed above, then `system_id`, then `resource_id`.
`COMPLETE` cases contain only verification steps that cite evidence; `INCOMPLETE` cases contain findings (cited), remediation (empty `evidence_id`) and verification (empty `evidence_id`).
`python3 code/main.py` validates all of this (`engine/validate_output.py`) and exits non-zero on any problem.

## 2. In-process results for the API and graph
```python
from engine.pipeline import run_all_cases          # reads dataset/, no network, no model calls
results = run_all_cases("dataset")                  # list of CaseAuditResult, one per request
case = results[0].to_dict()                          # plain dict, JSON-serializable
```
`CaseAuditResult.to_dict()` keys (definition: `engine/contracts.py`):

| Key | Type | Content |
|---|---|---|
| `case_id` | string | request id |
| `deletion_status` | string | `COMPLETE` / `INCOMPLETE` / `NOT_APPLICABLE` |
| `summary` | object | `systems_checked`, `findings_count`, `remediation_count`, `verification_count` (ints) |
| `identities` | array | per resolved subject: `identity_id`, `resolved_identifiers` (list of `{type, value, ...}` for user_id / email / email_hash / phone), `matched_evidence` (ids), `resolution_status` (`RESOLVED`, `PARTIALLY_RESOLVED`, `AMBIGUOUS`, `UNRESOLVED`), `confidence` (0-1) |
| `findings` | array | `{system_id, resource_id, operation, evidence_id, reason}` for each reported problem |
| `steps` | array | the same step objects that are serialized into `steps_json` |
| `evidence` | array | `{evidence_id, file_path, captured_at}` for every evidence file cited by a step |
| `graph_data` | object | `nodes` and `edges` (below) |

`graph_data.nodes`: the first node is the subject `{id: "user:<user_id>", type: "subject", label: <name>}`; every other node is a resource
`{id: <resource_id>, type: <data category>, system: <system_id>, status: "COMPLIANT" | "VIOLATION", label}`.
`graph_data.edges`: `{source: "user:<user_id>", target: <resource_id>, relation: "identifier_match" | "inferred_from_activity"}`.
`NOT_APPLICABLE` results have empty `identities`, `findings`, `steps`, `evidence` and an empty graph.

Notes for consumers: `steps` and `findings` are facts at the case's `audit_at`; never recompute them in the frontend. `run_all_cases` takes a few seconds,
so compute it once at start-up (or cache it), not per request.

## 3. Optional advisory explanations
`python3 code/advise.py [--model]` writes `explanations.json` (gitignored) next to `output.csv`. It adds a plain-language explanation and a
"needs human review" flag per case. It never changes `deletion_status` or `steps`. Without `--model` it uses templates and needs no key.

## 4. Email router (FastAPI)
Full endpoint table, workflow rules and Resend setup: [`integrations/email/README.md`](./integrations/email/README.md). Interface summary:

```python
from fastapi import Depends
from integrations.email import build_service_from_env
from integrations.email.router import create_email_router

service = build_service_from_env()      # reads RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_WEBHOOK_SECRET, EMAIL_DB_PATH
app.include_router(create_email_router(
    service,
    dependencies=[Depends(your_login_check)],                       # REQUIRED in production; protects every route except the webhook
    case_provider=lambda case_id: results_by_id.get(case_id),       # optional: dict from section 2, lets drafts be generated from a case
))                                                                  # default prefix "/email"
```
- Requires `fastapi` (and `httpx` only for tests). The email core itself is standard library only.
- State machine: `DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED -> SENDING -> SENT | FAILED`. Only `approve` leads to `APPROVED`; nothing is sent without it.
  `REJECTED -> DRAFT` (re-draft) and `FAILED -> PENDING_APPROVAL` (a failed send needs approval again) are the only extra edges.
- Typical UI flow: `POST /email/drafts` -> `POST /email/emails/{id}/submit` -> `POST /email/emails/{id}/approve` -> `POST /email/emails/{id}/send`.
  Poll `GET /email/emails/{id}` for the state, `delivery_status` and the audit events.
- A second draft for the same case + recipient + kind returns the existing email (`created: false`), so double-clicks cannot create duplicates.
- HTTP errors: 404 unknown email, 409 wrong state or content changed after approval, 422 invalid input, 503 Resend (or the webhook secret) not configured.
- Webhook: `POST /email/webhooks/resend` is verified with the Svix signature, not with your login. Bad signature or a timestamp older than 5 minutes -> 400; missing secret -> 503.
- Customer-facing drafts (`audience="requester"`, the default) never contain internal resource or evidence ids; `audience="internal"` appends the advisory explanation for the approver only.
- The approver name is whatever the caller sends. Put real authentication in front of the router and pass the authenticated user as `actor` / `approver`.
- The SQLite outbox (`email_outbox.db`, or `EMAIL_DB_PATH`) holds email bodies: keep it out of git (it is gitignored) and out of `code.zip`.

## 5. Not covered here
Wiring explanations into the UI and mounting the router in `api.py` are Member 1's tasks.
