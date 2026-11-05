# ERASIGHT: Ghost Data Still Exists

HackerRank Orchestrate (October 2026) submission. ERASIGHT is a deletion-audit agent: for every request in
`dataset/deletion_requests.csv` it decides whether the person really asked for deletion, reconstructs what still
exists at the case's `audit_at` time, applies `dataset/deletion_rules.csv`, and writes `output.csv` with the
findings, an ordered remediation plan and the verification checks.

Challenge page: https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
Full contract: [`problem_statement.md`](./problem_statement.md) and [`AGENTS.md`](./AGENTS.md) (section 6).

## How it works (short)
The decisions come from a **deterministic, rule-based engine. It makes no network calls and no model calls.**

1. **Classify** the request text (multilingual, negations first). Anything that is not a deletion request is `NOT_APPLICABLE` with `steps_json=[]`.
2. **Resolve identity** from the request email using current identities and the audit history. Matching is exact; lookalike emails are never merged.
3. **Load evidence** (SQL snapshots of every replica type, JSON, four log layouts, text, PDFs via `pdftotext`, screenshots via `tesseract`) into time-stamped observations that keep their evidence id.
4. **Reconstruct state at `audit_at`.** Later evidence is ignored; workflow statuses and activity results are treated as claims, not proof.
5. **Apply policy** (delete / redact / anonymize / retain / tombstone, restore blocks, data-flow disable) and emit findings, remediation and verification in the required phase and operation order.

Two optional layers sit beside the engine and never change `output.csv`:
- an **advisory language-model layer** (plain-language explanations and a "needs human review" flag), and
- a **Resend email integration** (human-approved, duplicate-safe emails). Both are described below.

## Requirements
- Python 3.10 or newer (CI uses 3.12). The agent itself uses only the standard library.
- System tools for PDF and screenshot evidence:
  - `pdftotext` (package `poppler-utils`)
  - `tesseract` (package `tesseract-ocr`)
  - Debian/Ubuntu: `sudo apt-get install poppler-utils tesseract-ocr`; macOS: `brew install poppler tesseract`.
- Only for tests: `pytest` (and `pytest-cov`). Only for the email HTTP router: `fastapi` and `httpx`.

## Setup
```bash
git clone <this repository> && cd <repository>
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt                     # pytest, pytest-cov, fastapi, httpx (requirements.txt has no required packages)
cp .env.example .env                                    # only needed for the email and advisory layers; never commit .env
```
The `dataset/` folder must sit at the repository root. It is not part of `code.zip`.

## Run
From the repository root:

| Goal | Command |
|---|---|
| Generate and validate the answer file | `python3 code/main.py` (writes the root `output.csv`; options `--dataset`, `--output`) |
| Score against the 32 sample cases | `PYTHONPATH=code python3 code/evaluation/main.py` (add `--diff all` or `--diff case_07` for missing/extra steps) |
| Run the six team-written evaluation cases | `PYTHONPATH=code python3 code/evaluation/custom_cases.py` |
| Run all tests | `python3 -m pytest code/tests` |
| Regenerate the two reports | `python3 code/evaluation/generate_reports.py` |

`code/main.py` finishes with `output validation: OK` when the file has the exact header `case_id,deletion_status,steps_json`,
518 rows sorted by `case_id`, valid JSON arrays, consecutive step numbers and only allowed phases, operations and states.
It exits with a non-zero code and lists the problems otherwise.

Tests that need the real `dataset/` and the root `output.csv` (9 of them) skip themselves when either is absent, so run `python3 code/main.py` first for the full count. The router test skips if `fastapi` is not installed.
With the dev requirements installed the suite is 188 tests, all using fakes (no network, no model calls, no real email).

### Reports
`code/evaluation/evaluation_report.md` (accuracy, six custom cases, failures and improvements) and
`code/evaluation/usage_report.md` (model calls and tokens; the engine itself uses none) are written by
`generate_reports.py` from a fresh run. After any engine change run, in this order:
`python3 code/main.py`, `python3 -m pytest code/tests`, `python3 code/evaluation/generate_reports.py`.

## Environment variables
Read from the real environment or from an uncommitted `.env` at the repository root (real environment variables win).
`.env.example` lists every name with empty values. **Never commit `.env`.**

| Variable | Used by | Purpose |
|---|---|---|
| `RESEND_API_KEY` | email | Resend API key (required for a live send) |
| `RESEND_FROM_EMAIL` | email | Verified sender address |
| `RESEND_WEBHOOK_SECRET` | email | Svix signing secret (`whsec_...`) for delivery webhooks; webhooks are refused without it |
| `EMAIL_DB_PATH` | email | Optional path of the SQLite outbox (default `email_outbox.db`, gitignored) |
| `EMAIL_OPERATORS` | email API | `name:sha256-of-token` pairs for the people who may draft, approve and send; create with `python3 code/email_operator_token.py --name <Name> --env-file .env`. Empty disables every email route |
| `EMAIL_ALLOWED_RECIPIENTS` | email | Comma-separated addresses or `@domain`s that live email may go to; empty disables every email route |
| `EMAIL_ALLOW_SELF_APPROVAL` | email | `1` lets the drafter also approve (one-person demos only); default: a different person must approve |
| `LLM_PROVIDER` | advisory | `openai` (any OpenAI-compatible gateway, default) or `anthropic` |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_PROVIDER_NAME` | advisory | Gateway key, base URL ending in `/v1`, exact model id, display name for the report |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | advisory | Only when `LLM_PROVIDER=anthropic` |
| `LLM_PRICE_INPUT_PER_MTOK`, `LLM_PRICE_OUTPUT_PER_MTOK` | advisory | Optional USD per million tokens, used only to estimate cost in `usage_report.md` |
| `SLACK_WEBHOOK_URL` | Slack (Member 1) | Not used by the engine, advisory layer or email package |

`python3 code/main.py` needs none of these.

## Advisory language-model layer (optional)
Decisions stay rule-based. Deterministic triggers (unresolved identity, possible lookalike email, mixed wording, nothing attributable) choose
which cases get a model call; the rest get a template explanation. The model's JSON is rejected if it is malformed, cites any resource or
evidence id the engine did not produce, or contradicts the engine's status; any failure falls back to the template.

```bash
python3 code/advise.py                    # templates only, no key needed
python3 code/advise.py --model [--limit N]   # needs LLM_* in .env; writes explanations.json and code/evaluation/advisor_usage.json
python3 code/advise.py --demo [--model]      # runs on the built-in mini dataset, which includes a lookalike case
python3 code/advise.py --list-models         # print model ids your key can use
```
Run `generate_reports.py` afterwards so `usage_report.md` shows the real calls and tokens.

## Email integration (optional)
`code/integrations/email/` sends deletion-audit emails only after a named person approves the exact content.
States: `DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED -> SENDING -> SENT | FAILED`. Duplicate sends are prevented per case + recipient + kind,
by an atomic `APPROVED -> SENDING` claim, and by a Resend `Idempotency-Key`. Webhooks are verified with the Svix signature on the raw body.
The endpoint table and the (optional, FastAPI-only) router are in [`code/integrations/email/README.md`](./code/integrations/email/README.md);
the cross-team contract is in [`code/CONTRACT.md`](./code/CONTRACT.md).

Try the whole flow from a terminal without sending anything:
```bash
python3 code/email_demo.py --to you@example.com --dry-run
```
For the web app, email goes through the existing `code/server.py` (no second server) using `integrations/email/http_adapter.py`: every request needs a personal login token, the approver must be a different person from the drafter, and only allowed recipients are accepted. The adapter is built and tested; `server.py` and the frontend still have to call it (steps in [`INTEGRATION_PLAN.md`](./code/integrations/email/INTEGRATION_PLAN.md)).

A real send needs `RESEND_API_KEY` and `RESEND_FROM_EMAIL` (and `RESEND_WEBHOOK_SECRET` only if webhooks are used). Resend's free sender
`onboarding@resend.dev` is for testing: it delivers only to the address your Resend account uses, so emailing real customers needs a domain you
own and have verified in Resend. For the demo, allow your own Resend address plus Resend's test inboxes `delivered@resend.dev` and
`bounced@resend.dev` (see `INTEGRATION_PLAN.md`); the dataset customers are fictional. No test ever contacts Resend.

## Repository layout
```text
code/main.py                entry point: dataset/ -> output.csv
code/engine/                loader, parsers, identity, classifier, state reconstruction, policy, planners, pipeline, output validator
code/advisor/               optional language-model explanations and review flags
code/advise.py              CLI for the advisory layer
code/integrations/email/    Resend integration (state machine, store, client, router, webhooks)
code/email_demo.py          terminal demo of the approval workflow
code/email_operator_token.py  create a login token for one person who may approve or send email
code/evaluation/            scorer, custom cases, invariants, report generator, evaluation_report.md, usage_report.md
code/tests/                 pytest suite (includes an invented mini dataset with hand-derived answers)
code/CONTRACT.md            shared result and email interface for the frontend/API owner
output.csv                  final answers (518 rows)
log.txt                     agent session log (chat transcript submission)
```

## Known limits
- On the 32 public samples `deletion_status` is 32/32, but 5 cases still miss steps (6 steps in total, no wrong steps). Cases 04, 18 and 20 refer to ids that appear nowhere in the data; case 23 has three equally plausible worker activities; case 24 depends on whether an empty snapshot outranks a live lookup (the alternative rule fixed 24 but broke 31). Details are in `evaluation_report.md`.
- The other 486 requests have no answer key. Their behaviour is checked by policy/time invariants over all 518 rows and by the invented mini dataset, not by a score.
- Regenerating `output.csv` on a different machine changed one row (`case_34`) with no engine change: the status stays INCOMPLETE, but one of its two remaining records (`support_9538`) was not found on the other machine, so it has 4 steps instead of 7. The likely cause is an OCR or PDF tool-version difference, not yet confirmed. The committed `output.csv` and the reports come from one consistent run; regenerate both together if you rerun on another machine.
- No live email send has been tried yet; it needs the Resend credentials above, and Resend only sends from an address on a domain verified in your Resend account.
