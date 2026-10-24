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

## Failures Found and Improvements Made

Phase 1 used raw substring matching, classified heterogeneous SQL rows from table names alone, and parsed logs line by line. This produced false cross-user hits, missed trace-correlated resources, and misclassified data flows, blocked backups, redacted support records, and tombstones.

Phase 2 added boundary-safe identifier matching; normalized service/category/state inference; recursive JSON records; SQLite `record_json` expansion; trace-level log correlation; pipe-delimited handover parsing; PDF extraction with fallback; OCR support; deterministic deduplication; temporal evidence selection; and explicit process/restore compliance handling. The incomplete-case planner now includes verification for both remediated and already-compliant resources.

Phase 4 fixed support-attachment parsing, added newest-readback reconstruction for migrated account resource IDs, and cached immutable SQL, JSON, PDF, image, and text extraction work within each run. These changes improved sample status accuracy from the Phase 1 baseline of **68.8% to 100.0%**, exact positional step accuracy from **0.0% to 65.8%**, field accuracy to **73.6%**, and sequence accuracy from **0.0% to 46.9%**.
