# Evaluation report

## Full evaluation input

The final run processed all 518 requests from `dataset/deletion_requests.csv` and wrote 518 ordered rows to the repository-root `output.csv`.

| Status | Cases |
| --- | ---: |
| `COMPLETE` | 43 |
| `INCOMPLETE` | 466 |
| `NOT_APPLICABLE` | 9 |

The hidden answer key is not participant-facing, so accuracy against the 518 evaluation answers cannot be measured locally. The accuracy figures below use only the 32 participant-facing cases and `dataset/sample_output.csv`.

## Public-sample metrics

Generated predictions with:

```bash
npm --prefix code run dev -- --requests sample_deletion_requests.csv --output sample_predictions.csv
python3 code/evaluation/evaluate_samples.py --predictions sample_predictions.csv
```

| Metric | Result |
| --- | ---: |
| Case-level status accuracy | 25 / 32 (78.13%) |
| Exact ordered-sequence accuracy | 10 / 32 (31.25%) |
| Step-field accuracy | 805 / 1,351 (59.59%) |
| Expected / predicted steps | 193 / 135 |
| Matched steps | 128 |
| Step precision | 128 / 135 (94.81%) |
| Step recall | 128 / 193 (66.32%) |
| Step F1 | 78.05% |
| `NOT_APPLICABLE` contract | Not represented in the 32 public cases |

Field accuracy is measured position-by-position after aligning each case's expected and predicted arrays to their maximum length. Step precision, recall, and F1 match complete step signatures without using `step_no`.

## Participant-created evaluation cases

Run with `npm --prefix code run evaluate:custom`. All three passed.

1. **Negated deletion plus export:** “I do not want you to delete my account; please export my data.” Expected and actual intent: `OTHER_REQUEST`. This case found a negation bug involving a pronoun between “want” and “to”; the classifier was fixed and the case now passes.
2. **Spanish deletion request:** “Por favor, elimina mi cuenta y todos mis datos personales.” Expected and actual intent: `DELETE_REQUEST`.
3. **Historical identity and audit cutoff:** an old email resolves to its user when the earlier email change is available by `audit_at`; a later email change after the cutoff is excluded. Both assertions pass.

## Failures found and changes made

- A same-time `profile_lookup_started` observation could mask a more informative completed 404 readback. The selector now prefers a known state over `UNKNOWN` when timestamps tie, while retaining conservative severity ordering between known states. This recovered evidence-backed absence for a public case.
- A unique account deletion activity event close to a request's `reported_at` can locate the profile resource, but the event result is ignored. The agent queries participant-visible SQL profile snapshots captured after that event and uses those snapshots to establish presence or absence. Requests with competing nearby events remain unresolved. This improved public-sample status accuracy and stopped an unsupported `COMPLETE` classification when another nearby deletion resource lacked a state observation.
- The PDF text extractor did not carry an explicit resource reference to the adjacent contact-detail lines. It now extracts resource-like references and email/phone values from document lines, allowing an attachment record to be linked to the subject.
- A document resource-ID pattern initially treated `user_...` stable references as resource IDs. The pattern now excludes those identity references.
- Explicitly null direct identifiers are retained as null markers in JSON observations (and ignored as identity values). Support messages with the full name/email/phone set explicitly cleared can be verified as redacted.
- The negation evaluator missed “do not want you to delete.” Its optional-pronoun pattern is fixed and covered by a participant-created case.
- Public-sample status accuracy remains limited by resource-link gaps. Some records in redacted or anonymized state no longer carry a direct identifier, and some SQL snapshots contain no row for an account. The current engine does not promote those records to a subject match without a grounded link, so it conservatively leaves some cases `INCOMPLETE`.

## Structural validation

`npm --prefix code run validate:output` passed on the final full-dataset output: 518 request rows, 2,232 total steps, allowed statuses and operation/state pairs, valid JSON arrays, consecutive step numbers, phase ordering, and evidence-ID rules. The public-sample evaluator ran successfully, and all three custom evaluation cases passed.

## Next improvements

- Improve the evidence graph for resource references that have had direct identifiers removed, using explicit activity-to-resource and snapshot relationships rather than timestamp proximity alone.
- Expand policy-condition handling for legal holds, support records, tombstones, and retention expiry.
- Add more multilingual negation and request-intent cases, and measure additional public-sample sequence coverage.
