# ERASIGHT: Member 2 PRD: What Is Left To Do (final snapshot, updated 5 Nov 2026)

Replaces `PRD_todo.md`. What is finished is in `PRD_done.md` (Sections 12 and 13 cover C and D).
Do one section per new chat. Open each chat from the repo root on branch `member-2-backend-resend`. Read `AGENTS.md`, `CLAUDE.md` and `PRD_done.md` first.
Rules for every chat: do not push without Rach's approval; append a `log.txt` entry; never commit secrets; never send real email from tests; no dataset, venvs or nested archives in `code.zip`. Do not edit Member 1's files (`api.py`, frontend, Slack).

## Section C: Resend email integration: DONE (live send not tried)
Built and tested with a fake Resend (see `PRD_done.md` Section 12). A live send still needs `RESEND_API_KEY`, a verified `RESEND_FROM_EMAIL` and `RESEND_WEBHOOK_SECRET` from Rach.

## Section D: Packaging, docs and handoff: DONE except the agent trace
- Done: README, `code/CONTRACT.md`, `code.zip`, `output.csv` and reports confirmed current (not regenerated: engine unchanged), stale PRD text fixed (see `PRD_done.md` Section 13).
- Open (Rach's laptop): build `agent-trace.zip`. Run `python3 build_agent_trace.py` where the Claude Code sessions ran, add `/export` transcripts and the Claude web-app export, review the staged files, zip, open the zip once.
- Open: `log.txt` must be uploaded as the `chat_transcript`; check it once for personal data (it contains one personal email address in an earlier entry, and the log is append-only).

## Section E: Optional accuracy polish. LIKELY UNREACHABLE
Remaining sample gaps: cases 04, 18, 20, 23, 24 (6 missing steps). Each needs a guess or an organizer answer:
- 04, 18, 20: ids appear nowhere in the data.
- 23: ask organizers how a FAILED worker activity maps to one customer when several look the same; apply their rule everywhere if one exists.
- 24: empty snapshot vs live lookup precedence; needs a rule that fixes 24 without breaking 31.
After any engine change: `python3 code/main.py`, `pytest code/tests`, `python3 code/evaluation/generate_reports.py`, then rebuild `code.zip` (command in `PRD_done.md` Section 13).

## Small leftovers
- Optional: add sample-data tests to CI (needs a safe way to provide the dataset, or a trimmed fixture).
- Optional: coverage for CLI wrappers and evaluation scripts (currently unmeasured).
- Explanations are not yet wired into emails or the UI (Member 1's side; the email package can already use them as an internal draft body).
- Optional: find out why `case_34` differs between machines (likely OCR or PDF tool version) so `output.csv` is reproducible everywhere.

## Open items for Rach
- Provide the Resend key, verified sender and webhook secret to try a live send.
- Build and upload `agent-trace.zip` (above).
- Decide when to push. The last push (log entries, 4 Nov) was approved; the new docs, `code/CONTRACT.md`, README and `build_agent_trace.py` from this session are committed locally only.
- Optionally email the organizers about case 23's activity mapping.
