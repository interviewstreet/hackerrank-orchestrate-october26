# Three-Phase Resource-Lineage Improvement Plan

## Phase 1 — Grounded Catalog Lineage (Complete)

- Extract subject-to-resource links only from audit-time-filtered `LINK_RESOURCE_IDENTITY` events.
- Add linked resource IDs to evidence matching without trusting workflow result claims.
- Make activity identity matching boundary-safe (`user_1` does not match `user_10`).
- Fall back to Gemini 2.5 Pro vision transcription when Tesseract is unavailable or ambiguous.
- Preserve current public metrics and add focused lineage, temporal, and vision-fallback tests.

Acceptance: all existing tests plus lineage tests pass; no extra sample steps; status accuracy remains 100%.

## Phase 2 — Workflow and Negative-Evidence Correlation

- Build request-scoped resource-lineage graphs from catalog links, pre-deletion resource IDs, workflow action dependencies, and trace IDs.
- Correlate account lookup misses with the account resource acted on by the subject's workflow.
- Carry analytics resource identity across anonymization so a null-PII record remains attributable to the audit lineage, not to the person.
- Link retained security records through stable subject references and catalog/workflow edges.
- Require participant-visible evidence at or before `audit_at` for every recovered verification.

Target: recover the 28 missing sample verification steps with zero extra steps and without case-specific golden mappings.

## Phase 3 — Full Regression and Release

- Re-run all 32 public cases and compare both set-aligned and canonical positional metrics.
- Re-run all 518 evaluation cases and strict output validation.
- Review every new lineage edge for temporal and evidence grounding.
- Update evaluation and usage reports, regenerate `output.csv`, rebuild `code.zip`, and run required preflight.

Target: 95%+ exact step and field accuracy, 31/32 or better sequence accuracy, and zero output-contract errors.
