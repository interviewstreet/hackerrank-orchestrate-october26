# ERASIGHT: Member 2 PRD, Part 2: What Is Left To Do

Each section below is self-contained. Do them in any order, one per new chat. Open each chat from the repo root on branch `member-2-backend-resend`, and read `AGENTS.md`, `CLAUDE.md`, and `PRD_done.md` first.
Rules for every chat: do not push without Rach's approval; append a `log.txt` entry; never commit secrets; never send real email from tests; no `dataset/`, venvs or nested archives inside `code.zip`.

## Sections A and B: DONE
Evaluation/usage reports and the pytest suite are finished (see PRD_done.md, Sections 8 and 9). After any engine change, rerun `python3 code/main.py`, `pytest code/tests`, and `python3 code/evaluation/generate_reports.py`.

## Section C: Resend email integration (P1/P2)
**Goal:** `code/integrations/email/` with resend_client, email_service, draft_generator, templates, approval_service, webhook_handler.
- Workflow states: DRAFT, PENDING_APPROVAL, APPROVED or REJECTED, SENDING, SENT or FAILED. Nothing is sent without explicit human approval; duplicate sends are prevented.
- Webhook signature verification using `RESEND_WEBHOOK_SECRET`.
- A FastAPI email router that Member 1 mounts; do not edit Member 1's files (`api.py`, frontend, Slack).
- Env vars: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`. Rach must supply the key and a verified sender; keep them in `.env` only.
- **Done when:** router imports cleanly, pytest tests with a mocked Resend client pass (add them under `code/tests/`), no real email is sent.
- **Start prompt:** "Do Section C of PRD_todo.md."

## Section D: Packaging, docs and handoff (P0, deliverable)
**Goal:** the files needed for submission.
- Add `pytest` to `requirements.txt`. `.env.example` (`SLACK_WEBHOOK_URL`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`, all empty), `requirements.txt`, README setup and run instructions (include `pdftotext` and `tesseract`).
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
