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
