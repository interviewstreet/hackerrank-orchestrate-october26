# 04 — Evaluation spec and required report templates

Required files inside `code/` (the code judge reads **Markdown and source**, and ignores raw `.csv/.json/.jsonl/.sql/.log`, so put every number and every custom case description in `.md`/`.py`):

```
code/evaluation/evaluation_report.md
code/evaluation/usage_report.md
```

## 1. Evaluator spec (`code/evaluation/evaluate.py`)

Inputs: predictions (pipeline run on `sample_deletion_requests.csv`) and `dataset/sample_output.csv`.

**Metrics**

| Metric | Definition |
|---|---|
| Case status accuracy | exact `deletion_status` match / cases |
| Step key | `(phase, system_id, resource_id, operation, state)` — evidence ignored |
| Step precision / recall / F1 | micro-averaged over all cases using multiset match of step keys |
| Field accuracy | for each of `phase, system_id, resource_id, operation, state, evidence_id`: over steps matched on the other keys + over position-aligned steps |
| Evidence accuracy | among matched findings/COMPLETE-verifications, fraction with identical `evidence_id`; among remediation/future-verification, fraction that are `""` |
| Step-count accuracy | cases where `len(pred)==len(gold)` |
| Sequence accuracy | (a) **exact**: whole ordered array equals gold (ignoring key order); (b) **LCS ratio**: `LCS(pred_keys, gold_keys) / max(len)` averaged over cases; (c) **order violations**: count of adjacent pairs violating the sort key |
| Per-case exact match | status + steps all equal |
| NA handling | precision/recall of `NOT_APPLICABLE` (samples have none → rely on custom cases and the disagreement report; say so honestly in the report) |

**Outputs:** console table + `results_latest.json` + a ranked "worst cases" diff with `MISSING`, `EXTRA`, `WRONG_EVIDENCE`, `WRONG_ORDER` tags.

**Hidden-test hygiene:** the 32 samples are for *validation*, not training the rules by copying. Run the evaluator also on a **leave-pattern-out** basis if time permits (e.g., temporarily disable one rule and confirm failures appear), to show the metrics are not trivially memorized.

**Real-data self-checks (no gold available) — add to `evaluate.py --self-check` and report them:**
- Validator passes on all 518 rows.
- Status distribution is plausible (e.g., NA ≈ 2%, COMPLETE vs INCOMPLETE roughly similar to sample proportions 10:22).
- 0 steps cite evidence captured after `audit_at` (hard assertion).
- Every INCOMPLETE case has ≥1 finding; every COMPLETE case has ≥1 verification with non-empty evidence.
- Agreement of `reported_status` vs our status as a *diagnostic* (how often workflow claims were wrong) — a nice talking point.
- Determinism: run twice → identical `output.csv` hash; shuffled input → identical rows.

## 2. Template: `code/evaluation/evaluation_report.md`

```markdown
# Evaluation Report — Ghost Data Audit Agent

## 1. Summary
- Approach: deterministic evidence→facts→policy engine; LLM only for request-intent classification (+ optional vision fallback).
- Final full-dataset run: 518 rows, validator OK, deterministic hash: <sha256 of output.csv>.
- Sample validation set: 32 cases (dataset/sample_output.csv).

## 2. Case-level status accuracy
| Metric | Value |
|---|---|
| Status accuracy (samples) | X/32 (xx.x%) |
| COMPLETE precision / recall | ... |
| INCOMPLETE precision / recall | ... |
| NOT_APPLICABLE | not present in samples; validated with custom cases C1, C4 + CLASSIFY_REQUEST cross-check (N agree / M disagree) |

## 3. Step-level and field-level accuracy
| Metric | Value |
|---|---|
| Step precision / recall / F1 | ... |
| Field accuracy: phase / system_id / resource_id / operation / state | ... |
| Evidence-id accuracy | ... |
| Step-count accuracy | ... |

## 4. Sequence accuracy
| Metric | Value |
|---|---|
| Exact ordered-array match | X/32 |
| Mean LCS ratio | ... |
| Order-key violations | 0 |

## 5. Real-dataset self-checks (no gold labels)
(list each check from evaluate.py --self-check with result)

## 6. Additional evaluation cases created by the team
For each of ≥3 (target 6): ID, scenario, why it is hard, input overlay, expected status/steps, actual result (PASS/FAIL), file that runs it.

| ID | Scenario | Expected | Result |
|---|---|---|---|
| C1 | Non-English request that says "do not delete my account" | NOT_APPLICABLE, [] | PASS |
| C2 | Request uses an OLD email; leftover search doc has only old email | INCOMPLETE, finding on search doc | PASS |
| C3 | Newer evidence file (after audit_at) shows leftover; before audit_at it is clean | COMPLETE, evidence cites only pre-audit file | PASS |
| C4 | Tombstone still holds email hash | INCOMPLETE, EXPOSED_PII + REDACT; user_id kept | PASS |
| C5 | Backup restorable vs already blocked | RESTORE_RISK+BLOCK vs clean | PASS |
| C6 | UPPERCASE email in evidence | linked and reported | PASS |

## 7. Failures found and improvements made
Chronological table from iteration_log.md:
| # | Failure (category) | Root cause | Fix (general) | Metric before → after |
|---|---|---|---|---|

## 8. Known limitations and risks
(honest list: e.g., hypotheses H1..H5 validated only on 32 samples; OCR errors; rules for unseen categories; ambiguous retention dates.)

## 9. How to reproduce
Commands: `python3 code/main.py`, `python3 code/evaluation/evaluate.py`, `python3 code/evaluation/custom_cases/run_custom_cases.py`.
```

## 3. Template: `code/evaluation/usage_report.md`

Must describe **the final full-dataset run that produced `output.csv`**. Generate it from `usage_stats.json`, with a cold cache (delete `code/cache/` before the final run) so token counts are real; then you may keep the cache for reruns. State this explicitly.

```markdown
# Token Usage and Cost Report (final full-dataset run)

Run: `python3 code/main.py` on 518 requests, <date>, cold cache.

## Models
| Provider | Model | Purpose | Calls | Input tokens | Output tokens | Total tokens | Est. cost (USD) |
|---|---|---|---|---|---|---|---|
| <provider> | <exact model id> | request-intent classification (batched) | N | N | N | N | $x.xxxx |
| <provider or "local"> | tesseract OCR | screenshot text extraction | 0 LLM calls | 0 | 0 | 0 | $0 |
| (optional) <provider> | <vision model> | OCR fallback | N | N | N | N | $x.xxxx |

## Overall
| Metric | Value |
|---|---|
| Total model calls | N |
| Total input tokens | N |
| Total output tokens | N |
| Total tokens | N |
| Requests processed | 518 |
| Average tokens per request | total/518 |
| Estimated total cost | $x.xxxx |
| Estimated cost per request | $x.xxxxxx |
| Cache hits (not billed) | N |

## Pricing used
Input $X / 1M tokens, output $Y / 1M tokens (source: provider pricing page, date). 

## Token-efficiency design
- 375 unique request texts, batched ~25 per call; temperature 0; disk cache by SHA-256.
- All evidence parsing is deterministic code (SQL/JSON/log/txt/PDF) and local OCR (images): zero tokens.
- `--no-llm` fallback exists (rule-based), so the pipeline runs with 0 tokens.
- No API keys or credentials appear in this report.
```
If you ran with `--no-llm` for the final run, say so honestly: models = none, tokens = 0, and describe where the LLM would be used.

## 4. Template: `README.md`

```markdown
# Ghost Data Still Exists — Deletion Audit Agent

## What it does
(3 sentences) + pipeline diagram (text).

## Setup
Python 3.10+; `python3 -m venv .venv && source .venv/bin/activate`; `pip install -r code/requirements.txt`;
install Tesseract (OS-specific commands).
Optional LLM: `export ANTHROPIC_API_KEY=...` (never commit). Variables: LLM_PROVIDER, LLM_MODEL.

## Run
- Full: `python3 code/main.py` → writes ./output.csv (518 rows)
- No LLM: `python3 code/main.py --no-llm`
- Debug cases: `python3 code/main.py --cases case_05,case_06 --debug`
- Evaluate: `python3 code/evaluation/evaluate.py`; custom: `python3 code/evaluation/custom_cases/run_custom_cases.py`

## Design (short)
Evidence parsers → fact store → identity resolution → state at audit_at → policy engine → planner → validator.
Key rules: time cutoff, claims-vs-evidence, case-insensitive identity matching, ordering keys.

## Repository layout
(tree)

## Determinism & no hardcoding
Statement + how verified (shuffle test, hash).

## Limitations
```
Also include `code/requirements.txt` (pandas, pillow, pytesseract, pdfplumber, plus your LLM SDK if used).
