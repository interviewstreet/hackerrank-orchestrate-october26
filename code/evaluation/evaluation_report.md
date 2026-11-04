# Evaluation Report — Ghost Data Still Exists (TRACE)

Reproduce every number in this report with:

```bash
python code/evaluation/main.py                 # pipeline on the 32 public samples + scoring
cd code && python -m pytest -q tests test_identity_resolver.py test_main.py test_request_classifier.py test_utils.py # 508 passed, 1 skipped, 592 subtests passed
python code/main.py && python code/validate_output.py   # full 518-case run + contract check
```

The solution is fully deterministic (no model calls, no randomness). Two consecutive full runs
produce byte-identical `output.csv` files (verified by SHA-256).

## 1. What was measured

The only labelled data available to participants is `dataset/sample_output.csv` (32 cases). It was
used during development, so these are **in-sample** numbers and are optimistic. The 518 evaluation
requests have no public labels; for them we report contract validity and the distribution of
decisions (section 4).

Metric definitions (`code/evaluate.py`; JSON key order and whitespace ignored, array order kept):

| Metric | Definition |
|---|---|
| Case-level status accuracy | `deletion_status` equal |
| Exact case accuracy | status **and** the complete step list equal |
| Step-level (row) accuracy | position-wise: step *i* equal in all 7 fields, over `max(len(pred), len(expected))` positions |
| Step precision / recall / F1 | order-insensitive multiset match of steps (all fields except `step_no`) |
| Field-level accuracy | position-wise per field, over `max(len(pred), len(expected))` positions |
| Sequence accuracy | ordered list of `(phase, system_id, resource_id, operation)` identical |

## 2. Results on the 32 public sample cases (final version)

| Metric | Value |
|---|---|
| Case-level deletion-status accuracy | **1.000** (32/32) |
| Exact case accuracy | 0.500 (16/32) |
| Sequence accuracy | 0.500 (16/32) |
| Step-level (row) accuracy | 0.829 |
| Step precision | 0.941 |
| Step recall | 0.902 |
| Step F1 | 0.921 |

Field-level accuracy:

| step_no | phase | system_id | resource_id | operation | state | evidence_id |
|---|---|---|---|---|---|---|
| 0.959 | 0.959 | 0.886 | 0.829 | 0.891 | 0.891 | 0.953 |

Status by class: 10/10 COMPLETE, 22/22 INCOMPLETE (the sample set contains no NOT_APPLICABLE case;
that path is covered by tests and by the 10 non-deletion requests in the evaluation set).

### Remaining differences, by root cause

All 16 non-exact cases have the correct status; each differs only in one or two verification steps.

| Root cause | Cases | Why it cannot be fixed with participant data |
|---|---|---|
| Expected step's only evidence was **captured after `audit_at`** | 09, 23, 24, 29, 30 | e.g. `audit_record_4128` appears only in `evidence_02` (captured 2026-09-17) for an audit at 2026-09-15; `audit_record_4902` only in `evidence_06` (captured 09-18) for an audit at 09-16. Using them would break the cutoff rule (AGENTS.md §6.2/§6.6). |
| Expected resource appears **nowhere** in participant data | 04 (`account_004`), 18 (`audit_record_6645`), 20 (`audit_record_5569`) | Not in any evidence file, activity row or audit row. |
| **Interchangeable de-identified records in one workflow batch** | 03, 18/20, 22/23, 25/26, 27/28, 31/32 | Two or three requests share the same workflow window and `reported_at`; the deleted accounts (bare 404 lookups) and anonymised analytics rows carry no identifier. Activity order is not consistent across batches (08-30: reverse order, 09-02: same order), so no grounded rule separates them. |

## 3. Additional evaluation cases created by the participant

Each case is an isolated, synthetic world (real-format evidence files parsed by the production P2
scanner, plus test identity / audit / activity tables) in `code/tests/test_policy_engine.py`.
All pass.

| # | Case (test name) | Input | Expected | Result |
|---|---|---|---|---|
| C1 | Historical email (`test_historical_email_matches_evidence`) | Subject changed email in May; a search document still holds the old email | Old email resolved through `user_audit_log`; `REPORT_REMAINING_RECORD` → `DELETE_RECORD` → `VERIFY_RECORD_ABSENT`; `audit_01` in identity history | PASS |
| C2 | Identity change after the audit (`test_identity_change_after_audit_at_is_not_used`) | Email changed after `audit_at`; evidence uses the later email | Later email not used, record not attributed | PASS |
| C3 | Replica drift (`test_primary_absent_replica_present_is_remaining`, `test_primary_copy_proof_does_not_prove_replica_absence`) | Account absent from the primary table but present in the read replica; a later primary-only listing omits it | Remaining record reported from the replica copy; a primary-copy absence proof is not accepted for the replica | PASS |
| C4 | Claim-only lookup (`test_claim_only_not_found_does_not_prove_absence`, `test_claim_never_overrides_authoritative_store_state`) | Only a ledger `NOT_FOUND` claim for the account; separately, a store 404 followed by a newer `FOUND` claim | Claim cannot prove absence (no evidence-backed verification, listed in `unverified`); a claim never overrides store state | PASS |
| C5 | Recreation risks and safe order (`test_active_sync_and_restore_risks_and_safe_order`) | Connector observed disabled, then a status check confirms it still enabled; a second connector repopulated the subject's search entry; an archive check confirms restore access | Both flows `REPORT_ACTIVE_DATA_FLOW` (citing the activity ids), `REPORT_RESTORE_RISK`; remediation `DISABLE, DISABLE, BLOCK, DELETE`; every remediated item verified | PASS |
| C6 | Same-instant conflict (`test_same_instant_authoritative_conflict_is_reported_and_conservative`) | Two authoritative observations at the same instant: PRESENT and ABSENT | Conflict reported in `decision["conflicts"]`; resolved conservatively as PRESENT | PASS |
| C7 | Catalog alias (`test_catalog_alias_links_document_to_resource`) | Catalog links `export_9` (alias `NST-2026-0901-9`) to the subject; a statement document carries only the alias | Document treated as evidence of `export_9`; remaining export reported | PASS |
| C8 | Timezone edge (`test_equivalent_instants_with_different_offsets`) | Record observed at 12:00Z, audit at 14:00+02:00 and at 13:59:59+02:00 | Included at the equal instant, excluded one second earlier | PASS |
| C9 | Tombstone (`test_tombstone_with_empty_pii_is_still_present_not_deleted`) | Tombstone with all direct identifiers null | Kept and `VERIFY_RECORD_REDACTED` with evidence; never treated as deleted | PASS |
| C10 | All 15 rules (`test_each_rule_noncompliant_record`, `test_each_rule_compliant_record`) | One non-compliant and (where meaningful) one compliant record per CSV rule | Correct finding / remediation / verification per rule, rule id recorded | PASS |

Full test inventory: 508 tests passed, 1 skipped, and 592 subtests passed (includes the 32 P3-P4 contract invariant checks).

## 4. Full evaluation set (518 requests, final run)

* Contract check (`code/validate_output.py`): **VALID**. 518 rows, no missing or duplicate case ids,
  sorted, valid JSON arrays, exact step fields, consecutive numbering, phase order, allowed
  operation/state pairs, empty evidence for future steps, every cited id exists and was captured at
  or before that case's `audit_at`.
* Errors during the run: 0. Uncertain classifications: 0.
* Decisions: COMPLETE 153, INCOMPLETE 355, NOT_APPLICABLE 10. Steps: 3,117.

| Phase | Operation | Count |
|---|---|---|
| FINDING | REPORT_REMAINING_RECORD | 369 |
| FINDING | REPORT_EXPOSED_PII | 214 |
| FINDING | REPORT_ACTIVE_DATA_FLOW | 113 |
| FINDING | REPORT_RESTORE_RISK | 26 |
| REMEDIATION | DELETE_RECORD | 369 |
| REMEDIATION | REDACT_RECORD | 141 |
| REMEDIATION | DISABLE_DATA_FLOW | 113 |
| REMEDIATION | ANONYMIZE_RECORD | 73 |
| REMEDIATION | BLOCK_RESTORE | 26 |
| VERIFICATION | VERIFY_RECORD_ABSENT | 798 |
| VERIFICATION | VERIFY_RECORD_PRESENT | 311 |
| VERIFICATION | VERIFY_RECORD_ANONYMIZED | 186 |
| VERIFICATION | VERIFY_RECORD_REDACTED | 177 |
| VERIFICATION | VERIFY_DATA_FLOW_DISABLED | 144 |
| VERIFICATION | VERIFY_RESTORE_BLOCKED | 57 |

Reported workflow status compared with our decision: of 254 requests reported `COMPLETE`, 163 are
INCOMPLETE at `audit_at`; of 152 reported `PARTIALLY_COMPLETE`, 36 are in fact COMPLETE; of 112
reported `NOT_STARTED`, 26 are COMPLETE and 10 are not deletion requests.

## 5. Failures found and improvements made

Sample-set metrics after each change (status / exact / step-level / step F1):

| Version | Change | Status | Exact | Step-level | F1 |
|---|---|---|---|---|---|
| v0 | Integrated P1+P2 with the placeholder policy engine (every case `INCOMPLETE []`) | 0.688 | 0.000 | 0.000 | 0.000 |
| v1 | First policy engine | 1.000 | 0.312 | 0.430 | 0.654 |
| v2 | Fixed a verification-operation name bug that crashed 5 cases; absence proofs must match the observed **collection** (a listing of another store was overriding a PRESENT security record); cite a direct 404 read-back before a snapshot omission; prefer workflow resources **co-located** in the subject's own evidence files | 1.000 | 0.531 | 0.819 | 0.905 |
| v3 | Support tickets with a requester block are shared conversation context → REDACT, not DELETE | 1.000 | 0.531 | 0.834 | 0.921 |
| v4 | Two-pass workflow attribution: anonymised analytics rows only to requests that are otherwise compliant (removes speculative steps from incomplete requests) | 1.000 | 0.500 | 0.829 | 0.921 |
| v5 | Stricter rule: a claim never overrides store state (dropped to 0.438 / F1 0.910 because findings then cited an older check); fixed by citing the newest observation that *agrees* with the store-decided state | 1.000 | 0.500 | 0.829 | 0.921 |

Failures found on the **evaluation** set by inspecting decisions (no labels used) and fixed:

* `case_33`, `case_61` were COMPLETE with no steps. The catalog links resources by alias (a statement
  reference `NST-2026-0718-1842`, a file name `delivery_confirmation_19.pdf`). Alias resolution
  re-keys such evidence to the linked resource, so both are now evidence-backed INCOMPLETE findings.
* A tombstone alias equal to the user id (`user_17`) matched every record mentioning that user and
  invented a PII field. Alias matching now requires the record to *be* the artefact (same id,
  document reference or file name).
* `case_53`: a support-ticket screenshot (agent conversation with an order number) was deleted; the
  OCR text is now checked for conversation/order context, so it is redacted.

Changes made to teammates' code: none to P1/P2 logic. In P1's `test_main.py`, two assertions that
encoded placeholder output (`("INCOMPLETE", "[]")`) were replaced by the test's stated intent (the case
runs without error and yields a contract status; a naive `audit_at` equals the same UTC instant).
