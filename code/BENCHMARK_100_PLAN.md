# Grounded Plan Toward 100% Benchmark Accuracy

## Objective and non-negotiable boundary

Target 193/193 public steps, 1,158/1,158 fields, and 32/32 complete sequences only through a method that generalizes to the 518-case evaluation set. `sample_output.csv` remains evaluation-only: the predictor, training code, feature generation, and saved weights must never read it. Exact sample resource IDs may not be memorized, mapped by case ID, or inferred from organizer-only or post-`audit_at` data.

A 100% claim is conditional on candidate observability. A ranker cannot recover an exact resource ID that is absent from every legal candidate source. The first gate therefore tests whether every expected resource is present in participant-visible input at or before the case cutoff; failure is reported as a dataset/evaluator blocker rather than bypassed.

## Stage 1 — Candidate-observability audit (Complete)

1. Built `code/evaluation/observability.py`, an evaluation-only diagnostic that compares expected public resources with IDs available from participant inputs at or before each `audit_at`.
2. Classified resources as retrievable, linked-but-unretrieved, pre-audit unlinked, post-audit only, or globally absent.
3. Kept the diagnostic outside prediction code and added a test preventing production modules from importing it.
4. Enforced the gate: training cannot claim 100% unless pre-audit candidate recall is 100%.

Measured result: **104/111 unique case-resource pairs (93.7%)** are observable before their cutoffs, so the gate **fails**. Seven security verifications are blocked: five IDs first appear in post-audit captures and two do not occur in participant-facing prediction inputs. See `code/evaluation/observability_report.md`.

## Stage 2 — Build a self-supervised lineage training set (Complete)

Generated labels only from unambiguous participant-visible identity/resource edges, including stable references, current or historical identifiers, explicit catalog links, and trace-grouped evidence. Ambiguous multi-subject contexts are excluded rather than guessed.

`code/lineage_training.py` now produces in-memory numeric-feature examples and hard negatives from resources grounded to other subjects in the same artifact/system where possible. Exact edge rows are not persisted. A deterministic SHA-256 user split prevents a subject from appearing in both training and validation, and generation succeeds without `sample_output.csv`.

Measured corpus: **7,533 examples**, comprising **2,036 positive grounded edges** and **5,497 hard negatives** across **835 subjects**. This includes **290 newly added request-scoped workflow edges** connected to pre-audit grounded anchors. The split contains **658 training users / 5,985 examples** and **177 validation users / 1,548 examples**. See `code/evaluation/training_set_report.md`.

## Stage 3 — Train a deterministic resource-lineage ranker

Implement a small regularized logistic or pairwise ranking model using Python stdlib only. Features must be case-independent:

- explicit identifier/stable-reference match;
- catalog-link and trace-link strength;
- resource-ID continuity across actions and evidence;
- event-to-report and event-to-audit time distance;
- operation order and dependency cadence;
- source/target system and policy compatibility;
- reported-outcome compatibility, used only for identity correlation;
- same-artifact and same-workflow evidence;
- ambiguity count and competing-subject evidence;
- post-audit flag, which is a hard rejection rather than a learned feature.

Use leave-one-user-out validation, deterministic initialization, and fixed iteration order. Calibrate a confidence threshold that preserves 100% edge precision; abstain below the threshold.

## Stage 4 — Security-specific lineage reconstruction

For retained security records, search in this order:

1. stable subject reference in a pre-audit security record;
2. explicit catalog identity link;
3. request-scoped security readback trace;
4. resource continuity from a grounded retain/archive workflow;
5. uniquely ranked candidate with no competing subject and confidence above the calibrated threshold.

A `RETAIN_RECORD` claim may identify a resource but cannot prove `PRESENT`; final-state verification still requires eligible evidence. Never choose the nearest global security record solely by timestamp.

## Stage 5 — Safe two-pass integration

1. Run current identifier/catalog retrieval.
2. Score unresolved candidate edges with the trained ranker.
3. Add only unique, above-threshold, pre-audit resource IDs to lineage.
4. Re-run evidence retrieval.
5. Use evidence for state and workflow claims only for resource identity or future checks.
6. Preserve deterministic planner ordering and deduplication.

Add an automated guard proving that prediction modules do not import or open `sample_output.csv`.

## Stage 6 — Evaluation gates

Report both canonical-set and positional metrics:

- candidate recall and edge precision;
- status accuracy;
- set step precision/recall;
- positional step accuracy;
- field accuracy;
- complete sequence accuracy;
- abstention count and false cross-user edges.

Acceptance for a real 100% result:

- 100% pre-audit candidate recall;
- 100% lineage edge precision;
- 193/193 positional steps;
- 1,158/1,158 fields;
- 32/32 complete sequences;
- zero extra steps and zero contract errors;
- all existing and new leakage/boundary tests pass.

## Stage 7 — Blocker resolution when candidate recall is below 100%

If the observability gate remains below 100%, do not weaken safeguards or train on expected outputs. Produce a minimal dataset/evaluator change request instead:

- add a pre-audit `subject_reference` or `LINK_RESOURCE_IDENTITY` edge for each missing security resource;
- move an eligible security readback capture to or before `audit_at` only if that reflects intended truth; or
- remove/relax exact resource-ID expectations that cannot be derived from participant input.

After that correction, retrain from participant data, rerun the 32-case regression, then proceed to the 518-case Phase 3 release run.

## Explicitly rejected shortcuts

- training on or loading `sample_output.csv` in prediction code;
- case-ID/resource-ID lookup tables;
- post-audit resource discovery;
- nearest-record guesses in the global stream;
- organizer-only truth or generator internals;
- optimizing public sequence metrics by adding ungrounded steps.
