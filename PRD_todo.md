# ERASIGHT: Member 2 PRD, Part 2: What Is Left To Do

Each section below is self-contained. Do them in any order, one per new chat. Open each chat from the repo root on branch `member-2-backend-resend`, and read `AGENTS.md`, `CLAUDE.md`, and `PRD_done.md` first.
Rules for every chat: do not push without Rach's approval; append a `log.txt` entry; never commit secrets; never send real email from tests; no `dataset/`, venvs or nested archives inside `code.zip`.

## Section A: Evaluation and usage reports (P0, deliverable)
**Goal:** `code/evaluation/evaluation_report.md` and `code/evaluation/usage_report.md`.
- Evaluation report: case, step, field and sequence accuracy from `code/evaluation/main.py`; at least 3 custom evaluation cases (lookalike identity, active data flow, backup/restore or tombstone risk) with expected results and actual results; failures and the improvements made; the assumptions listed in PRD_done.md.
- Usage report: state truthfully that the shipped agent is deterministic and makes zero model calls, so run-time tokens and cost are 0. Give the real figures for the AI coding assistant used during development only if known, otherwise say they are not measured.
- **Done when:** both files exist, numbers match a fresh evaluator run, custom cases are runnable.
- **Start prompt for new chat:** "Do Section A of PRD_todo.md."

## Section B: Tests (P1)
**Goal:** pytest suite under `code/tests/` (or the layout the repo asks for).
- Evidence parsing, identity resolution including lookalike emails, detection and policy decisions, request classification, output validation (`validate_output_csv`), and the pipeline on a few sample cases.
- Email tests must mock Resend (see Section C).
- **Done when:** `pytest` passes locally and uses no network.
- **Start prompt:** "Do Section B of PRD_todo.md."

## Section C: Resend email integration (P1/P2)
**Goal:** `code/integrations/email/` with resend_client, email_service, draft_generator, templates, approval_service, webhook_handler.
- Workflow states: DRAFT, PENDING_APPROVAL, APPROVED or REJECTED, SENDING, SENT or FAILED. Nothing is sent without explicit human approval; duplicate sends are prevented.
- Webhook signature verification using `RESEND_WEBHOOK_SECRET`.
- A FastAPI email router that Member 1 mounts; do not edit Member 1's files (`api.py`, frontend, Slack).
- Env vars: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`. Rach must supply the key and a verified sender; keep them in `.env` only.
- **Done when:** router imports cleanly, tests with a mocked Resend client pass, no real email is sent.
- **Start prompt:** "Do Section C of PRD_todo.md."

## Section D: Packaging, docs and handoff (P0, deliverable)
**Goal:** the files needed for submission.
- `.env.example` (`SLACK_WEBHOOK_URL`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`, all empty), `requirements.txt`, README setup and run instructions (include `pdftotext` and `tesseract`).
- Document the shared result contract for Member 1.
- Read `agent_trace_instructions.md` and build `agent-trace.zip` as it directs; build `code.zip` from `code/` (no dataset, venvs, caches or nested archives).
- Confirm `log.txt` is complete and root `output.csv` is current.
- **Start prompt:** "Do Section D of PRD_todo.md."

## Section E: Optional accuracy polish
**Goal:** close the last sample gaps listed in PRD_done.md (cases 04, 17, 18, 20, 23, 24) without hardcoding answers or case numbers or guessing from numeric id patterns.
- Re-run `PYTHONPATH=code python code/evaluation/main.py --diff all` after each change; keep deletion_status at 32/32.
- Regenerate `output.csv` with `python code/main.py` and re-validate.
- **Start prompt:** "Do Section E of PRD_todo.md."

## Open items for Rach
- Provide the Resend API key and a verified sender when starting Section C.
- Decide when to push; no push has happened yet.
