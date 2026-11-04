# ERASIGHT: Member 2 PRD, Part 1: What Is Done

Owner: Rachana Shende (Member 2). Branch: `member-2-backend-resend`. Latest local commit: see `git log` (work on Sections A and B of the TODO is included). **Nothing has been pushed.**
Sections are independent; each one lists its files and how to check it.

## How to run and check
- Generate the answer file: `python code/main.py` (from the repo root). It reads `dataset/` and writes the root `output.csv`, then validates it.
- Score against the 32 sample cases: `PYTHONPATH=code python code/evaluation/main.py` (add `--diff all` or `--diff case_07` to see missing/extra steps).
- The engine is deterministic: no network, no model calls. It needs Python 3 stdlib only, plus the local tools `pdftotext` and `tesseract` for PDFs and screenshots.

## Section 1: Repo, logging, git: DONE
- Repo at `Desktop/EraSight`, branch `member-2-backend-resend`.
- `.gitignore` covers `.env`, caches, venvs.
- `log.txt` has entries up to "Core engine, accuracy tuning and output.csv generation". Each new session must append its own entry (tool=Claude Code, model=claude-sonnet-5-5).
- Commits carry the `Co-Authored-By` and `Claude-Session` trailers.

## Section 2: Dataset loader and evidence parsers: DONE
Files: `code/engine/{contracts,util,dataset_loader,evidence_loader}.py`, `code/engine/parsers/*`.
- Parses SQL snapshots (every replica type), JSON bundles and exports, four log layouts, text files, PDFs and PNG screenshots (OCR).
- Every fact keeps its provenance: evidence id, capture time, event time, links.

## Section 3: Identity resolution and request classification: DONE
Files: `identity_resolver.py`, `request_classifier.py`.
- Exact current/historical email, hash and phone matching; RESOLVED / AMBIGUOUS / UNRESOLVED; lookalike emails are not merged.
- Multilingual classifier, negations first. All 32 samples classify as deletion; 10 cases (case_533-542) in the full set are NOT_APPLICABLE.

## Section 4: Evidence matching and state reconstruction: DONE
Files: `evidence_matcher.py`, `state_reconstructor.py`.
- Ownership by identifier, user reference or email hash. A resource tied to a different user is dropped.
- Activity-based inference for records with no identifier (404 accounts, anonymized analytics), with peer ordering when several cases share a report time.
- Replica-aware absence inference. Retained categories (audit logs, legal hold, backups) never infer absence.
- Time rule: a fact must have happened at or before `audit_at`; evidence can be cited only if its file was captured at or before `audit_at`.

## Section 5: Policy, findings, remediation and verification planners: DONE
Files: `policy_engine.py`, `ghost_detector.py`, `remediation_planner.py`, `verification_planner.py`, `case_analyzer.py`.
- Rules from `deletion_rules.csv` (DELETE / REDACT / ANONYMIZE / RETAIN, backup restore block, data-flow disable).
- Step order: phase, then operation order, then system, then resource. COMPLETE cases cite evidence in verification; INCOMPLETE cases leave evidence empty for remediation and future checks.
- Per-case result follows the shared contract (summary, identities, findings, steps, evidence, graph_data).

## Section 6: Output generation: DONE
Files: `code/main.py`, `engine/pipeline.py`, `engine/validate_output.py`, root `output.csv`.
- `run_all_cases(dataset_dir)` returns the structured results for Member 1's API.
- `output.csv`: 518 rows (156 COMPLETE, 352 INCOMPLETE, 10 NOT_APPLICABLE); the validator passes.

## Section 7: Evaluator: DONE
File: `code/evaluation/main.py`.

Latest sample results (32 cases):
| Metric | Value |
|---|---|
| deletion_status accuracy | 32/32 |
| Exact-case match | 26/32 |
| Step precision / recall / F1 | about 0.99 / 0.97 / 0.98 |
| Evidence-id accuracy | about 0.97 |
| Sequence similarity | about 0.97 |

Sample results above are from the latest run (exact-case 27/32, step precision 100%, recall 96.9%).
Known remaining sample gaps (6 missing steps, no wrong steps): case_04 `account_004` (appears in no evidence), cases 18 and 20 missing an audit record, case_23 `account_410`, case_24 `account_5334` (remediation for it).

## Assumptions to mention in the evaluation report
- Peer ordering: cases sharing a report time take worker activities in case order.
- Inferred analytics records are attributed only to cases that are otherwise complete.
- These were tuned on the 32 samples and are not confirmed on the other 486 cases.

## Section 8: Evaluation and usage reports: DONE (was TODO Section A)
- `code/evaluation/evaluation_report.md` and `usage_report.md`, regenerated from a fresh run by `python3 code/evaluation/generate_reports.py` (all numbers measured).
- Six team-written cases in `code/evaluation/custom_cases.py` (lookalike identity, email normalisation, multilingual request, negated request, audit before evidence, other customer's active flow): 6/6 pass.
- `code/evaluation/invariants.py`: policy/time rules checked over all 518 rows and the answer key: 0 violations.
- Usage report states zero model calls, 0 tokens, $0.00.

## Section 9: Tests: DONE (was TODO Section B)
- `pytest code/tests` runs 30 tests (classifier, identity incl. lookalikes, pipeline accuracy floors and determinism, policy/time invariants, output validation, custom cases). Install with `pip install pytest`. No network used.
- Email tests are not written yet (they belong to Section C).

## Fixes made while building Sections 8 and 9 (found by the new cases)
- Spanish/other-language deletion verbs were missed; vocabulary broadened.
- Worker activity after `audit_at` was used; now ignored.
- A case with nothing attributable could return COMPLETE with no steps; COMPLETE now needs at least one proven-compliant resource.
- Resources known only from evidence older than the request are not claimed (case_07/case_61 behaviour); `output.csv` regenerated (only case_61 changed).

## Section 10: Advisory language-model layer: BUILT, not yet run against a live model
Files: `code/advisor/{llm_client,review,explain,advisor}.py`, `code/advise.py`, `code/tests/test_advisor.py`, `.env.example`.
- Decisions stay rule-based. The layer only adds a plain-language explanation and a "needs human review" flag; it never edits `output.csv`.
- Deterministic triggers choose which cases get a model call (unresolved identity, possible lookalike email, mixed wording, no attributable records). On the 518 requests 6 are flagged; all others get a template explanation with no call.
- Safety: the model's JSON is rejected if malformed or if it cites any resource/evidence id the engine did not produce; any failure falls back to the template. The client is provider-neutral: an OpenAI-compatible gateway (AgentRouter) via `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` in `.env`, or Anthropic if `LLM_PROVIDER=anthropic`. The key is never logged.
- Run: `python code/advise.py` (templates, no key) or `python code/advise.py --model [--limit N]` (writes `explanations.json` and `code/evaluation/advisor_usage.json`). `python code/evaluation/generate_reports.py` then reports the real calls and tokens in `usage_report.md`.
- 13 unit tests use a fake model (44 tests pass in total). **Not yet tested with the real API: this needs the key.**

## Section 11: Gap-closing round (tests, mini dataset, advisor checks): DONE
- `code/tests/minidata.py` + `test_mini_dataset.py`: a tiny invented dataset (4 customers, 3 evidence files, 6 requests) with fully hand-derived expected steps (lookalike, restore risk, active flow, negated request, absence proven by a later snapshot, audit before evidence). 6/6 exact. No dependency on `dataset/`.
- `test_parsers.py` (SQL, JSON lookup, log layouts, txt) and `test_engine_units.py` (state reconstruction, replica logic, time gates, policy decisions) use inline fixtures. 74 tests pass; coverage of `code/engine` + `code/advisor` is about 91% (measure with `pytest --cov=code/engine --cov=code/advisor`).
- Tests that need the real `dataset/` skip themselves when it is absent. `.github/workflows/tests.yml` runs the suite and `main.py` on every push (installs poppler and tesseract). `requirements.txt` / `requirements-dev.txt` added.
- Advisor: model wording that contradicts the engine's status is rejected (`contradicts_status`); `python code/advise.py --demo` runs the advisor on the mini dataset (includes the lookalike case) and writes `code/evaluation/advisor_demo.json`; flagged real cases are saved to `code/evaluation/advisor_examples.json`.

## Section 12: Resend email integration (TODO Section C): DONE (needs Rach's keys for a live send)
Files: `code/integrations/email/*` (config, models/state machine, SQLite store, resend_client, draft_generator, templates, approval_service, email_service, webhook_handler, router, README), tests `code/tests/test_email_*.py` + `emailkit.py`.
- Workflow DRAFT -> PENDING_APPROVAL -> APPROVED/REJECTED -> SENDING -> SENT/FAILED; approval is the only way to APPROVED; content hash checked at send; audit event per change.
- Duplicate sends prevented by one email per case+recipient+kind, an atomic APPROVED->SENDING claim, and a Resend `Idempotency-Key`.
- Webhooks: Svix signature verified on the raw body (checked against the official Svix test vector), 5-minute replay window, duplicate message ids ignored, secret required.
- `create_email_router(service, dependencies=..., case_provider=...)` for Member 1 to mount; documented in `code/integrations/email/README.md`.
- Advisory explanations can be the draft body (`audience="internal"`); the default customer-facing draft never contains internal ids.
- 76 new tests, all with a fake Resend (no real email); email package coverage about 97%. A live send has NOT been tried: it needs `RESEND_API_KEY`, a verified `RESEND_FROM_EMAIL` and `RESEND_WEBHOOK_SECRET` in `.env`.
- Note: regenerating `output.csv` on the Linux sandbox changed one row (case_34) with no engine change, probably an OCR/tool-version difference; the committed `output.csv` was left as is.

## Still open after this round (be honest in the interview)
- Sample cases 04, 18, 20, 23, 24: 6 steps missing. Cases 04, 18, 20 reference ids (`account_004`, `audit_record_6645`, `audit_record_5569`) that appear in no evidence or activity, so they cannot be derived without guessing. Case 23 (`account_410`) has 3 equally plausible worker activities. Case 24 (`account_5334`) depends on whether an empty JSON snapshot outranks a live lookup: switching rules fixed case 24 but broke case 31, so the original rule stays.
- The other 486 requests have no answer key; behaviour there is checked only by invariants and by the mini dataset.
- Live-model runs: only the 6 mixed-wording cases ran live. The lookalike demo (`python code/advise.py --demo --model`) has not been run live yet. Cost is not computed until Groq prices are set in `.env`.
- Explanations can now be used as an internal email draft body (Section 12); the UI wiring is Member 1's.
