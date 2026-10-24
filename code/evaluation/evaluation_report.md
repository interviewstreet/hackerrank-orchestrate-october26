# Evaluation Report

## Case-Level Deletion-Status Accuracy

The Phase 4 regression run against all 32 participant-visible sample cases classified **32 of 32 cases correctly (100.0%)**. This metric compares only `deletion_status` and does not imply that every generated step is canonical.

## Step-Level and Field-Level Accuracy

- Exact step count: **15 of 32 cases (46.9%)**
- Exact positional step match across phase, operation, state, system, resource, and evidence: **127 of 193 expected steps (65.8%)**
- Individual compared fields: **852 of 1,158 (73.6%)**

The principal remaining gap is evidence that proves an anonymized or absent resource without retaining a direct identifier. Such resources can be correctly classified as compliant but cannot always be linked to a subject using content-only identifier matching.

## Sequence Accuracy

**15 of 32 cases (46.9%)** have the complete canonical sequence in the correct position. Ordering of generated steps that are present follows the required operation table, then `system_id`, then `resource_id`.

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
