# Public benchmark and evaluation report

## Public sample results

The current solver was evaluated by running `solve_case` on all 32 rows in `dataset/sample_deletion_requests.csv` and comparing against `dataset/sample_output.csv`. The sample labels are used only by `code/evaluation/evaluate_public.py`; they are never read by the prediction path.

| Measure | Before this improvement pass | Current | Definition |
|---|---:|---:|---|
| Case-level deletion-status accuracy | 27/32 (84.4%) | 29/32 (90.6%) | Exact status equality |
| Exact step-array / sequence accuracy | 3/32 (9.4%) | 7/32 (21.9%) | Entire ordered step array matches |
| Exact step objects | 122/193 (63.2%) | 148/193 (76.7%) | Multiset match over all seven fields |
| Exact step fields | 651/1,351 (48.2%) | 834/1,351 (61.7%) | Position-wise field equality; absent predicted fields count wrong |

This is public-sample performance only. It does not establish hidden-test accuracy. These before/after values come from the same direct evaluator and prior predictor snapshot. The user-supplied baseline elsewhere in the conversation reports 20/32 statuses, 22/193 objects, 429/1,351 fields, and 19/32 arrays; its array count conflicts with a direct full-array comparison of that prior snapshot (3/32), so it is recorded as a separate, non-comparable measurement. The current exact-object count remains 27 below the official reference of 175/193. The direct baseline in the first implementation pass was also measured as 27/32 statuses, 3/32 arrays, 122/193 step objects, and 651/1,351 fields; this shows the measured improvement within this work session independently of the historical report values.

## Mismatch analysis

### Incorrect status

3 cases: case_01, case_02, case_04.

### Missing or extra steps

Across 25 mismatching arrays: 45 expected step objects are missing and 1 extra step objects are predicted. Case IDs: case_01, case_02, case_03, case_04, case_07, case_08, case_09, case_10, case_16, case_17, case_18, case_19, case_20, case_21, case_22, case_23, case_24, case_25, case_26, case_27, case_28, case_29, case_30, case_31, case_32. Repeated patterns are absent account-absence verifications and retained security-log verifications. Some cases also miss a distinct evidence-linked resource; those are not safely inferred from neighboring records.

### Incorrect phase, operation, state, or system/resource identifier

Matched steps paired by phase/system/resource contain 0 core-field discrepancies. Counts: none. Most unmatched system/resource pairs are represented as missing/extra steps above, rather than treated as a confident correction to an existing resource ID.

### Incorrect evidence_id

0 cases have otherwise identical step semantics but a different evidence ID: None.

### Incorrect step ordering

0 cases have the same shared step signatures in a different relative order: None.

## General improvements made

- Correlate identity-bearing evidence log events to resource readbacks using trace IDs while taking state only from the readback, not a workflow success claim.
- Parse multi-segment resource identifiers in pipe-delimited handover records and normalize support replica events to their owning support system.
- Treat positive support and analytics readback row counts and eligible backup restore candidates as state evidence; continue to honor the supplied policy when choosing remediation.
- Recognize SHA-256 email correlation keys derived from current or historical participant-facing identities.
- Treat a matching support PDF attachment as a present record to delete, and avoid emitting a conflicting duplicate account-absence verification for an account already found present.
- Preserve evidence capture cutoffs, exact identifier matching, deterministic phase/operation ordering, and evidence IDs on findings; remediation and future checks remain uncited.

## Additional evaluation cases created

1. **Non-deletion request:** an export/access request must return `NOT_APPLICABLE` with `[]` even when the workflow status says complete.
2. **Historical email:** an old email in `user_audit_log.csv` must resolve the same user and locate a pre-cutoff evidence record.
3. **Tombstone redaction:** keep the stable `user_id`, report direct identifiers, and plan `REDACT_RECORD` plus redaction verification.
4. **Recreation risk:** an enabled connector and restorable backup require flow disable/restore block before record deletion and future checks.

These contract cases are documented scenarios, not claimed automated executions.

## Full-dataset run

`py code/main.py` generated root `output.csv` with 518 sorted rows. The program validated the header, unique row count, allowed statuses, JSON arrays, and consecutive step numbers. Independent output validation is recorded in the submission checklist and repeated before packaging.

## Remaining limitations

Some anonymized analytics records and account reads lack a direct identity-to-resource link in participant-facing evidence, so this implementation intentionally avoids linking them by array position or sample case pattern. Some expected retained-record checks are not identified when evidence carries only indirect references. Screenshots are not OCR-processed. These gaps explain much of the remaining sequence mismatch; no hidden-test score is claimed. Three public requests and 22 full-dataset requests lack a matched state observation and are therefore marked INCOMPLETE rather than COMPLETE; some such rows have no safe evidence-backed step to emit, so their remediation sequence remains unresolved.

## Per-case step differences

This table lists the exact normalized step objects not shared with the reference. A `missing` row is an expected step not emitted; `extra` is a predicted step with no exact reference match.

| Case | Missing expected steps | Extra predicted steps |
|---|---|---|
| case_01 | `VERIFICATION/account_service/account_001/VERIFY_RECORD_ABSENT/ABSENT/evidence_54` | — |
| case_02 | `VERIFICATION/account_service/account_002/VERIFY_RECORD_ABSENT/ABSENT/evidence_54` | — |
| case_03 | `VERIFICATION/analytics_platform/analytics_9406/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_94` | — |
| case_04 | `VERIFICATION/account_service/account_004/VERIFY_RECORD_ABSENT/ABSENT/evidence_54`, `VERIFICATION/analytics_platform/analytics_901/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_56` | — |
| case_07 | `VERIFICATION/account_service/account_007/VERIFY_RECORD_ABSENT/ABSENT/` | — |
| case_08 | `VERIFICATION/account_service/account_008/VERIFY_RECORD_ABSENT/ABSENT/` | — |
| case_09 | `VERIFICATION/account_service/account_3960/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_4902/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_10 | `VERIFICATION/account_service/account_010/VERIFY_RECORD_ABSENT/ABSENT/` | — |
| case_16 | `FINDING/search_service/search_1007/REPORT_REMAINING_RECORD/PRESENT/evidence_05`, `REMEDIATION/search_service/search_1007/DELETE_RECORD/ABSENT/`, `VERIFICATION/search_service/search_1007/VERIFY_RECORD_ABSENT/ABSENT/` | — |
| case_17 | — | `VERIFICATION/account_service/account_6523/VERIFY_RECORD_ABSENT/ABSENT/` |
| case_18 | `VERIFICATION/account_service/account_5521/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_6645/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_19 | `FINDING/support_platform/support_9553/REPORT_EXPOSED_PII/PRESENT/evidence_01`, `REMEDIATION/support_platform/support_9553/REDACT_RECORD/REDACTED/` | — |
| case_20 | `VERIFICATION/account_service/account_5037/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_5569/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_21 | `VERIFICATION/account_service/account_6440/VERIFY_RECORD_ABSENT/ABSENT/evidence_92`, `VERIFICATION/analytics_platform/analytics_5335/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_92` | — |
| case_22 | `FINDING/search_service/search_8911/REPORT_REMAINING_RECORD/PRESENT/evidence_05`, `REMEDIATION/search_service/search_8911/DELETE_RECORD/ABSENT/`, `VERIFICATION/account_service/account_4990/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/search_service/search_8911/VERIFY_RECORD_ABSENT/ABSENT/` | — |
| case_23 | `VERIFICATION/account_service/account_410/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_4128/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_24 | `FINDING/account_service/account_5334/REPORT_REMAINING_RECORD/PRESENT/evidence_92`, `REMEDIATION/account_service/account_5334/DELETE_RECORD/ABSENT/`, `VERIFICATION/account_service/account_5334/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_7095/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_25 | `VERIFICATION/account_service/account_3136/VERIFY_RECORD_ABSENT/ABSENT/evidence_92`, `VERIFICATION/analytics_platform/analytics_1895/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_92` | — |
| case_26 | `VERIFICATION/account_service/account_5684/VERIFY_RECORD_ABSENT/ABSENT/evidence_92`, `VERIFICATION/analytics_platform/analytics_4566/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_92` | — |
| case_27 | `VERIFICATION/account_service/account_3866/VERIFY_RECORD_ABSENT/ABSENT/evidence_92`, `VERIFICATION/analytics_platform/analytics_4574/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_92` | — |
| case_28 | `VERIFICATION/account_service/account_5482/VERIFY_RECORD_ABSENT/ABSENT/evidence_92`, `VERIFICATION/analytics_platform/analytics_6077/VERIFY_RECORD_ANONYMIZED/ANONYMIZED/evidence_92` | — |
| case_29 | `VERIFICATION/account_service/account_7012/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_3954/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_30 | `VERIFICATION/account_service/account_4163/VERIFY_RECORD_ABSENT/ABSENT/`, `VERIFICATION/security_service/audit_record_1707/VERIFY_RECORD_PRESENT/PRESENT/` | — |
| case_31 | `VERIFICATION/account_service/account_4857/VERIFY_RECORD_ABSENT/ABSENT/evidence_51` | — |
| case_32 | `VERIFICATION/account_service/account_8858/VERIFY_RECORD_ABSENT/ABSENT/` | — |

## Core field discrepancies

No mismatched core fields were found among steps sharing the same phase, system, and resource. Resource/system mismatches appear as missing/extra steps above.
