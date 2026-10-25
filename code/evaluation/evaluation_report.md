# Evaluation report — Ghost Data Still Exists

All numbers come from `python3 code/evaluation/main.py`, which runs the full pipeline on the
32 labeled samples (`dataset/sample_deletion_requests.csv`) and compares with
`dataset/sample_output.csv`. Samples 01-10 are hand-made scenarios; 11-32 follow the same
generator patterns as the 518 evaluation requests, so 11-32 is the better proxy for the hidden set.

## Metric definitions

| Metric | Definition |
|---|---|
| Case accuracy | `deletion_status` equal to the labeled status |
| Sequence accuracy | the whole `steps_json` array equal, order and step numbers included |
| Step (row) precision / recall / F1 | multiset match of full steps: phase, system_id, resource_id, operation, state, evidence_id |
| Resource recall | share of labeled steps whose (phase, system_id, resource_id) the prediction also emits |
| Field accuracy | labeled steps aligned to predictions on (phase, system_id, resource_id); per field, share with the same value |

## Results on the labeled samples (final run)

| Metric | All 32 | Samples 01-10 | Samples 11-32 |
|---|---|---|---|
| Case accuracy | 100.0% | 100.0% | 100.0% |
| Sequence accuracy | 65.6% | 80.0% | 59.1% |
| Step precision | 98.9% | 100.0% | 98.7% |
| Step recall | 94.3% | 90.3% | 95.1% |
| Step F1 | 96.6% | 94.9% | 96.9% |
| Resource recall | 94.3% | 90.3% | 95.1% |
| Field accuracy: operation | 94.3% | 90.3% | 95.1% |
| Field accuracy: state | 94.3% | 90.3% | 95.1% |
| Field accuracy: evidence_id | 94.3% | 90.3% | 95.1% |

Field accuracy equals resource recall: every step whose resource was found has the right
operation, state and evidence. All remaining error is in which resources are found.

Intent classification on all 550 request texts (518 evaluation + 32 samples): rules decide 549;
the 10 non-deletion requests (case_533 to case_542) are all classified `NOT_APPLICABLE`; one
sample text (case_26, "confirm that the profile is gone") is routed to the model fallback.

Full evaluation run: 518 rows, 0 contract violations (consecutive step numbers, empty arrays for
`NOT_APPLICABLE`, verification-only `COMPLETE`), statuses 151 `COMPLETE` / 357 `INCOMPLETE` /
10 `NOT_APPLICABLE`, 3,202 steps. A cached run and a from-scratch run produce byte-identical files.

## Participant-made evaluation cases

Run with `python3 code/evaluation/main.py --custom`. Inputs live in
`code/evaluation/custom_cases/requests.csv`, expected answers in `expected.csv`; both are
reproduced here because raw CSV files are not visible to the code judge. Expected answers for
custom_01 and custom_02 were derived by hand from the evidence before the pipeline existed.

| Case | What it tests | Input | Expected | Result |
|---|---|---|---|---|
| custom_01 | historical, upper-case email; person-to-record links under the old address; retained audit record linked by user_id only | email `CHOI.JIHOON94@GMAIL.COM`, requested 2026-09-03, reported COMPLETE 2026-09-06, audit 2026-10-01 (same row as case_40) | `INCOMPLETE`: search_3200 remaining and support_4887 exposed (both cite evidence_03, the handover captured at the audit minute); remediation delete + redact; verifications for account_1810 absent, audit_record_8349 present and the two fixes | pass |
| custom_02 | report says COMPLETE, evidence shows remnants after the reported time | email `aadebayo3975@fastmail.com`, requested 2026-09-07, reported COMPLETE 2026-09-09, audit 2026-10-01 (case_36 row) | `INCOMPLETE`: export_7689 and search_5575 remaining (evidence_03); delete both; verify account_5823 absent, audit_record_2966 present | pass |
| custom_03 | Spanish request that names deletion only to forbid it | "No borren mi cuenta, por favor. Solo quiero actualizar el número de teléfono asociado a este correo." | `NOT_APPLICABLE`, `[]` | pass |
| custom_04 | Japanese negated deletion | 「アカウントは削除しないでください。登録されている住所だけを変更したいです。」 | `NOT_APPLICABLE`, `[]` | pass |

Custom case score: 4/4 statuses, 100% sequence, step and field accuracy.

## Failures found and improvements made

Each row is a change made after reading a scorer diff, with the sample score after it.

| Step | Failure observed | Change | Step F1 | Sequence |
|---|---|---|---|---|
| Baseline | empty pipeline, always INCOMPLETE | — | 0% | 0% |
| M3 | first full pipeline, identifier links only | parsers for all text evidence, rules, policy table | 82.0% | 12.5% |
| M3 | audit records reported absent although an export lists them (case_21) | a snapshot's omission never overrides an explicit observation | 89.8% | 25.0% |
| M3 | support replica copy treated as a message to redact (case_10) | legacy contact index classified as SECONDARY_IDENTIFIER (delete) | (same run) | |
| M4 | deleted accounts carry no identifier (337 of 518 cases) | global window assignment of worker deletions, elimination, proximity tie-break | 94.9% | 59.4% |
| M4 | a March 404 lookup tied a resource to an August request (case_17) | not-found lookups link only after the request | 95.2% | 62.5% |
| M5 | case_07 attachment only in a PDF | pypdf + OCR media parser; emails accepted only if they match a known identity | 95.8% | 62.5% |
| M5 | screenshots mixed rows from several people | data-catalog LINK_RESOURCE_IDENTITY rows pair each media file with its resource and owner | 95.5% | 59.4% |
| M5 | catalog links from other months attached to sample cases 07 and 17 | catalog links count only inside the case's [request, audit] window | 96.6% | 65.6% |
| M6 | 18 evaluation cases COMPLETE with an uncited verification | deletable records seen only in later files take the covering snapshot before the audit; retained records are never inferred absent | 96.6% (no sample change) | 65.6% |
| M6 | negation rules were English only | Spanish, Portuguese, French, Japanese and Korean negations | (custom cases 03-04) | |

Changes that were measured and rejected:

- Dropping lookup-key links on every not-found result: F1 fell from 94.9% to 93.3%.
- Assigning downstream records (analytics, support) to the nearest preceding account job: jobs
  interleave, 13 found vs 11 wrong. Downstream records are linked only when exactly one request
  can claim them.
- Unique-only account assignment: 6 of 28 accounts found. The proximity tie-break finds 14 of 18
  window-linked accounts with 1 wrong.

## Remaining errors and known limitations

- **Anonymized analytics in shared windows (7 sample steps).** Several requests reported the same
  day share one evidence file, and the all-null analytics profile names nobody; the pipeline
  leaves these unlinked rather than guess.
- **Two audit records (samples 18, 20)** appear in no evidence file the pipeline can read.
- **One account swap (sample 23)** in a window with two failed deletions a minute apart.
- **Screenshots ran through OCR**, not the vision model: no API key was configured for the
  final run. The vision path is implemented and cached; OCR misreads only lose links because an
  extracted email must exactly match a known identity.
- `cache/review.jsonl` lists every proximity-chosen account (78), every unlinked ambiguous
  record, and every verification that has no citable evidence, for human review.
