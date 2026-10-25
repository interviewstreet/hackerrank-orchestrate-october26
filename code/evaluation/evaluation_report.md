# Evaluation Report — Ghost Data Audit Agent

## 1. Summary
- Approach: deterministic evidence→facts→policy engine; an LLM is used only for
  request-intent classification when an API key is configured, with a
  rule-based classifier as the always-available fallback (`--no-llm`).
- Final full-dataset run: `python3 code/main.py` → 518 rows, validator OK,
  deterministic sha256 of `output.csv`:
  `8a1a07ab0c3e01bb3d814f714e36e373941735a440a221faebfe907f967812b3`
  (identical across repeated runs, with warm and cold caches).
- Sample validation set: 32 cases (`dataset/sample_output.csv`), evaluated by
  `python3 code/evaluation/evaluate.py`.

## 2. Case-level status accuracy (samples)
| Metric | Value |
|---|---|
| Status accuracy | 32/32 (100.0%) |
| COMPLETE precision / recall | 10/10 predicted COMPLETE correct; 10/10 gold COMPLETE found |
| INCOMPLETE precision / recall | 22/22 predicted INCOMPLETE correct; 22/22 gold INCOMPLETE found |
| NOT_APPLICABLE | Not present in the 32 samples; validated with custom cases C1 (+ real-data cross-check below) |

## 3. Step-level and field-level accuracy (samples)
| Metric | Value |
|---|---|
| Step precision / recall / F1 | 0.988 / 0.855 / 0.917 |
| Field accuracy: phase | 1.000 |
| Field accuracy: system_id | 0.727 |
| Field accuracy: resource_id | 0.727 |
| Field accuracy: operation | 0.794 |
| Field accuracy: state | 0.794 |
| Field accuracy: evidence_id | 1.000 |
| Evidence-id accuracy (matched steps) | 1.000 |
| Step-count accuracy | 9/32 (0.281) |

Field accuracies are position-aligned, so every missing step shifts the rest
of a case; the step-key metrics above are the meaningful ones. Almost all
losses are *missing* steps (recall), not wrong steps (precision 0.988):
resources that carry no identifier in any evidence file cannot be linked to
a subject without guessing, and we never guess.

## 4. Sequence accuracy (samples)
| Metric | Value |
|---|---|
| Exact ordered-array match | 9/32 |
| Mean LCS ratio | 0.745 |
| Order-key violations | 0 (enforced by construction and re-checked by the validator) |

## 5. Real-dataset self-checks (no gold labels)
- Validator passes on all 518 rows: header, natural case order, step keys,
  operation/state mapping, phase ordering, evidence-id validity.
- Status distribution: COMPLETE 153, INCOMPLETE 355, NOT_APPLICABLE 10
  (NA ≈ 1.9%, in line with the 10 `CLASSIFY_REQUEST` events in
  `system_activity.csv`; the two signals agree in count).
- Determinism: two consecutive full runs (and one cold-cache run) produce
  byte-identical `output.csv`.
- Every INCOMPLETE case has ≥1 finding; every COMPLETE case with any linked
  record has verification steps citing evidence. Two cases (early-2026
  audits that predate every evidence snapshot of their subjects) have no
  linkable record at all and are COMPLETE with an empty step list — see
  Limitations.
- Citations: 1,062 steps cite evidence. In 20 of them the cited *file* was
  captured after the case's `audit_at`, but the cited snapshot/log lines
  inside it are timestamped at or before `audit_at`; whenever a file
  captured by `audit_at` proves the same verdict, that file is cited
  instead. No cited fact is itself dated after `audit_at`.
- Workflow-claim diagnostic: of 254 requests the workflow reported
  COMPLETE, only 90 survive the evidence audit; 164 are INCOMPLETE. This
  confirms `reported_status` must never be trusted as proof.

## 6. Additional evaluation cases created by the team
Run with `python3 code/evaluation/custom_cases/run_custom_cases.py`
(synthetic in-memory overlays driving the real pipeline; 6/6 PASS):

| ID | Scenario | Expected | Result |
|---|---|---|---|
| C1 | "do not delete… send me a copy" vs Spanish/Korean deletion requests | NON_DELETE, DELETE, DELETE | PASS |
| C2 | Leftover search document reachable only via the subject's old (historical) email | INCOMPLETE + search finding | PASS |
| C3 | Leftover visible only in evidence timestamped after `audit_at` | COMPLETE, cites only pre-audit file | PASS |
| C4 | Tombstone still holding an email hash vs tombstone with only `user_id` | INCOMPLETE + REDACT vs COMPLETE | PASS |
| C5 | Backup restorable vs restore-blocked | RESTORE_RISK + BLOCK_RESTORE vs VERIFY_RESTORE_BLOCKED | PASS |
| C6 | UPPERCASE email in evidence | Record still linked and reported | PASS |

Supporting test scripts: `code/evaluation/test_identity.py`
(518/518 requests resolve; 418 current-email, 100 historical-email) and
`code/evaluation/test_parsers.py` (2,916 facts parsed from 94 evidence
files; the five zero-fact files were manually verified to contain no
parsable resource records).

## 7. Failures found and improvements made
| # | Failure | Root cause | Fix | Metric effect |
|---|---|---|---|---|
| 1 | Resources vanished when the only containing file was captured after `audit_at` (e.g. a Sept-16 audit whose records sit in a Sept-18 observability export) | File-level (manifest) eligibility was stricter than the evidence model | Facts are eligible by their own (inner) timestamp; citation prefers a by-`audit_at`-captured file proving the same verdict | Recall ↑; matched-step evidence accuracy stayed 1.000 |
| 2 | Identifier-free compliant records assigned to the wrong subject (same account repeatedly paired to different people) | Assignment by observation-time proximity inside the primary file | Assignment by elimination only: exactly one identifier-free candidate for an uncovered system in the case's primary file, otherwise none | Step F1 0.846 → 0.890 → 0.904 |
| 3 | Support tickets whose message body still contained the customer's email were judged redacted | Exposure was only read from identifier fields, not free-text bodies | Email patterns inside message/body fields count as exposed PII | Step F1 0.904 → 0.917 |
| 4 | Console screenshots cross-linked other customers' records | Every email on a screenshot was treated as its subject | A screenshot links only its first (opened) subject's identifiers | Removed false data-flow findings |
| 5 | Syslog-dialect logs lost their trace context, so lookups could not be linked (one full-run case lost all its records) | Bare `tr-…` trace tokens and bare service names were not parsed | Fallback bare-trace/service extraction in the log parser | Two full-run cases recovered their findings |
| 6 | Tombstones keeping only `user_id` were flagged exposed | Any `user_id` field counted as exposure | For `ACCOUNT_TOMBSTONE`, exposure requires a direct identifier beyond `user_id` | Custom case C4 passes; no sample regression |
| 7 | Cases with no linkable record crashed validation as "COMPLETE with no verification steps" | Empty step list treated as malformed | Empty COMPLETE is the documented no-violation-found outcome | Full run validates cleanly |

## 8. Known limitations and risks
- Records that carry no identifier in *any* evidence file (a deleted
  account known only as a bare resource id, an anonymized analytics
  profile, an audit record) cannot be attributed to a subject without
  guessing. This is the dominant recall loss on the samples (~14.5% of
  gold steps, almost all of them single verification steps); we accept it
  rather than hardcode or guess pairings.
- Two of the 518 cases were audited (Feb/Apr 2026) before every evidence
  snapshot of their subjects; with nothing linkable at or before
  `audit_at` they are reported COMPLETE with no steps.
- OCR depends on the locally installed Tesseract; if it is unavailable the
  image parser degrades gracefully (other parsers still cover most
  screenshot subjects via logs/SQL/JSON). Screenshot subject pairing uses
  the opened record, so list-only screenshots contribute less.
- The 32 samples contain no NOT_APPLICABLE case; NA behaviour rests on
  the custom cases, the request-text classifier, and the count agreement
  with `CLASSIFY_REQUEST` activity.
- Category is inferred from record/event types and collection names; a
  wholly unseen category with no rule would be skipped rather than
  misclassified.

## 9. How to reproduce
```bash
python3 code/main.py                                  # 518-row output.csv
python3 code/evaluation/evaluate.py                   # sample metrics above
python3 code/evaluation/custom_cases/run_custom_cases.py
python3 code/evaluation/test_identity.py
python3 code/evaluation/test_parsers.py
```
