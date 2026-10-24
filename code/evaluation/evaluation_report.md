# Evaluation Report

## Case-Level Deletion-Status Accuracy

The Phase 4 regression run against all 32 participant-visible sample cases classified **32 of 32 cases correctly (100.0%)**. This metric compares only `deletion_status` and does not imply that every generated step is canonical.

## Step-Level and Field-Level Accuracy

- Exact step count: **25 of 32 cases (78.1%)**
- Exact positional step match across phase, operation, state, system, resource, and evidence: **175 of 193 expected steps (90.7%)**
- Individual compared fields: **1,072 of 1,158 (92.6%)**

Workflow lineage now recovers identifier-free absent and anonymized resources. The remaining gap is seven retained-security resource IDs that appear only in artifacts captured after the relevant audit cutoffs.

## Sequence Accuracy

**25 of 32 cases (78.1%)** have the complete canonical sequence in the correct position. Ordering of generated steps that are present follows the required operation table, then `system_id`, then `resource_id`.

## Additional Evaluation Cases

### Custom Case 1 — Historical Email Resolution

Resolve an address found only in an email-change audit event. Expected behavior: recover the stable user ID, current identifier, old identifier, phones, and hashes; unknown addresses return `None`.

### Custom Case 2 — Trace-Correlated Evidence

A log places the subject identifier on a lookup-start line and the resource state on a completion line sharing the same trace ID. Expected behavior: join the trace and emit one normalized hit for the completed resource rather than treating either line in isolation.

### Custom Case 3 — Policy-Required Tombstone Retention

Compare a tombstone containing only a stable subject reference with one still exposing name, email, phone, and hash. Expected behavior: verify the first as `REDACTED`; report and remediate the second without deleting its stable reference.

### Custom Case 4 — Identifier Boundary Safety

Ensure `user_1` does not match evidence for `user_10` or `user_100`. Matching uses token boundaries for stable IDs, emails, phones, and hashes to prevent cross-subject evidence contamination.

### Custom Case 5 — Evidence Sandbox and Output Integrity

Reject a manifest path that escapes `dataset/`, deny SQLite `ATTACH` and extension loading, treat malformed non-object cache content as empty, reject duplicate output cases, and confirm atomic output writes leave no temporary file.

### Custom Case 6 — Exact Case Coverage and Release Preflight

Reject unknown or duplicate `--cases` values and detect equal-sized output files that substitute an unexpected case for a required one. The release preflight also verifies all evidence files, required report sections, source secret patterns, archive integrity, required ZIP members, and forbidden archive content.

## Failures Found and Improvements Made

Phase 1 used raw substring matching, classified heterogeneous SQL rows from table names alone, and parsed logs line by line. This produced false cross-user hits, missed trace-correlated resources, and misclassified data flows, blocked backups, redacted support records, and tombstones.

Phase 2 added boundary-safe identifier matching; normalized service/category/state inference; recursive JSON records; SQLite `record_json` expansion; trace-level log correlation; pipe-delimited handover parsing; PDF extraction with fallback; OCR support; deterministic deduplication; temporal evidence selection; and explicit process/restore compliance handling. The incomplete-case planner now includes verification for both remediated and already-compliant resources.

Phase 4 fixed support-attachment parsing, added newest-readback reconstruction for migrated account resource IDs, and cached immutable SQL, JSON, PDF, image, and text extraction work within each run. These changes improved sample status accuracy from the Phase 1 baseline of **68.8% to 100.0%**, exact positional step accuracy from **0.0% to 65.8%**, field accuracy to **73.6%**, and sequence accuracy from **0.0% to 46.9%**.

Phase 5 performed a security and submission-integrity review. It added strict CSV schemas and uniqueness checks, evidence path confinement, a SQLite authorizer, malformed-cache recovery, atomic output writes, duplicate-row detection, and stricter phase/evidence validation. These controls do not alter the measured prediction metrics; they fail closed on malformed or unsafe inputs and protect the final artifact from partial writes.

Phase 6 added exact input/output case-set comparison, strict partial-run case selection, and a single release preflight covering dataset counts, all 94 manifest paths, the 518-row output, required report sections, source secret scanning, ZIP integrity, required archive members, and forbidden content. Packaging now runs this preflight automatically and fails before submission when any release invariant is broken.

Phase 7 profiled the complete retrieval path and replaced repeated dynamic regular-expression compilation with boundary-safe casefolded token matching. It also caches normalized identity tokens, resolved manifest paths, and flattened JSON records. Prediction metrics remained identical while the measured full-run time fell from **235 seconds to 194 seconds** (approximately **17% faster**).

The first of a three-phase lineage improvement added audit-time-filtered data-catalog resource seeds, boundary-safe activity matching, and reliable Gemini vision fallback when local Tesseract OCR is unavailable. Its public metrics intentionally remained unchanged because the 28 canonical gaps were identifier-free account, analytics, and security verification resources.

Lineage Phase 2 added request-scoped workflow dependency correlation, a second evidence-retrieval pass using the grounded resource IDs, status-code and null-profile negative lookup handling, and complete-but-empty account snapshot interpretation. It recovered all 21 missing account and analytics verifications without case-specific resource mappings or extra sample steps. The dependency-complete regression now reports **32/32 status (100.0%)**, **175/193 positional steps (90.7%)**, **1,072/1,158 fields (92.6%)**, and **25/32 complete sequences (78.1%)**.

The Stage 1 candidate-observability audit measures **104/111 unique case-resource pairs (93.7%)** available at or before their case cutoffs. The remaining seven retained-security resources fail the gate: five first appear in post-audit captures and two are absent from participant-facing prediction inputs. The pipeline intentionally refuses to turn those public expected IDs into runtime mappings. Full classifications and source timing are in `evaluation/observability_report.md`.

Stage 2 constructs a self-supervised, user-disjoint lineage corpus without loading canonical output: **7,533 examples**, **2,036 grounded positives**, **5,497 hard negatives**, and **835 subjects**. The positives include **290 new request-scoped workflow edges** connected to pre-audit grounded anchors. Exact edge rows remain in memory and only aggregate counts are reported. The deterministic split has 658 training and 177 validation users with no overlap. Details are in `evaluation/training_set_report.md`; the staged design is in `BENCHMARK_100_PLAN.md`.
