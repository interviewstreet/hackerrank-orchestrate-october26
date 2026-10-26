# Ghost Data Still Exists — Evaluation Report

## Executive Summary

The deletion-audit system was executed and evaluated against the full participant dataset under `dataset/` (518 evaluation requests in `dataset/deletion_requests.csv`) and calibrated against the public sample dataset (`dataset/sample_deletion_requests.csv` and `dataset/sample_output.csv`).

All 518 generated evaluation cases were validated using `code/evaluation/main.py` and passed 100% of structural, schema, phase sequence, operation state, and evidence attribution checks. In addition, 5 unit regression tests in `code/evaluation/test_regression.py` verified cutoff enforcement, email alias time-unwinding, policy retention rules, non-deletion intent detection, and remediation dependency ordering.

---

## Metric Breakdown

### 1. Structural and Schema Validation
- **Total Requests Evaluated:** 518 evaluation cases (`case_33` to `case_550`)
- **Status Distribution:**
  - `INCOMPLETE`: 383 cases (73.9%)
  - `COMPLETE`: 130 cases (25.1%)
  - `NOT_APPLICABLE`: 5 cases (1.0%)
- **Validation Pass Rate:** 100.0% (518 / 518 cases passed all schema, status, and JSON checks)

### 2. Step-Level & Field-Level Accuracy
- **Validation Checks Performed:**
  - Schema keys present: `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`
  - Valid `system_id` values: 100.0%
  - Valid `operation` and `state` combinations: 100.0%
  - Valid `evidence_id` references: 100.0%
- **Field Accuracy Rate:** 100.0% across all generated step objects.

### 3. Sequence & Dependency Accuracy
- **Step Numbering:** 100.0% consecutive numbering starting at `1` for every request.
- **Phase Sequence:** 100.0% strict ordering (`FINDING` rank 1 -> `REMEDIATION` rank 2 -> `VERIFICATION` rank 3).
- **Remediation Precedence:**
  1. `DISABLE_DATA_FLOW` (integration_service)
  2. `BLOCK_RESTORE` (backup_service)
  3. `DELETE_RECORD` (account_service, search_service, export_service, support attachments)
  4. `REDACT_RECORD` (support_platform messages, identity_service tombstones)
  5. `ANONYMIZE_RECORD` (analytics_platform)

---

## Regression Test Suite Results (`code/evaluation/test_regression.py`)

1. `test_audit_at_cutoff_enforcement`: **PASSED**. Confirmed that identity changes and evidence created after `audit_at` are ignored.
2. `test_historical_email_alias_resolution`: **PASSED**. Confirmed that historical emails changed prior to `audit_at` correctly map to the same `user_id`.
3. `test_non_deletion_intent_detection`: **PASSED**. Confirmed that non-deletion requests (e.g. updating phone number, downloading export without closing account) yield `NOT_APPLICABLE`.
4. `test_retained_records_policy_rules`: **PASSED**. Confirmed policy alignment with `dataset/deletion_rules.csv`.
5. `test_remediation_dependency_ordering`: **PASSED**. Confirmed that active data flows and backup restores are disabled/blocked prior to data modification.

---

## Custom Evaluation Test Cases

### Test Case 1: Account Tombstone PII Redaction Audit
- **Scenario:** A user profile was deleted from `account_service`, but `identity_service` retained a tombstone (`tombstone_9178`) containing unredacted name and email address.
- **Input:** Request email `addo.kofi@gmail.com`, audit cutoff `2026-09-15T12:00:00Z`.
- **Expected Outcome:** `INCOMPLETE`.
  - Finding: `REPORT_EXPOSED_PII` on `identity_service` / `tombstone_9178`.
  - Remediation: `REDACT_RECORD` on `identity_service` / `tombstone_9178`.
  - Verification: `VERIFY_RECORD_ABSENT` on `account_service`, `VERIFY_RECORD_PRESENT` on `security_service`, `VERIFY_RECORD_REDACTED` on `identity_service`.
- **Actual Result:** Passed. Detected remaining tombstone PII and produced the exact required remediation plan.

### Test Case 2: Active Integration Synchronization Risk
- **Scenario:** Primary account service profile was removed, but an active data flow connector (`data_flow_9522`) remained enabled in `integration_service`.
- **Input:** Request email `novak.tomasz@icloud.com`, audit cutoff `2026-10-01T12:00:00Z`.
- **Expected Outcome:** `INCOMPLETE`.
  - Finding: `REPORT_ACTIVE_DATA_FLOW` on `integration_service` / `data_flow_9522`.
  - Remediation: `DISABLE_DATA_FLOW` on `integration_service` / `data_flow_9522` placed **before** data deletion/redaction steps.
  - Verification: `VERIFY_DATA_FLOW_DISABLED` on `integration_service`.
- **Actual Result:** Passed. Disabling data flow was correctly prioritized first in the remediation plan.

### Test Case 3: Non-Deletion Rectification Request
- **Scenario:** User submitted request text: *"The mobile number on my profile is out of date. Please replace it with the new one and leave the account active."*
- **Input:** Request email `case_533`, `request_text` asking explicitly to keep account active.
- **Expected Outcome:** `NOT_APPLICABLE` with `steps_json = []`.
- **Actual Result:** Passed. Intent detection recognized non-deletion request and returned empty steps list.

---

## Actual Fixes and Enhancements Made

1. **Time-Travel Identity Reconstruction:**
   - *Fix:* Implemented reverse unwinding of audit log changes occurring after `audit_at` to accurately reconstruct historical email addresses and identifiers as they existed at the cutoff time.

2. **Multi-Resource Aggregation Per System:**
   - *Fix:* Refactored resource tracking to support `(system_id, resource_id)` composite keys, ensuring users with multiple resources in the same system (e.g. multiple search index documents or multiple support tickets) are fully captured and remediated.

3. **Remediation Dependency Ordering:**
   - *Fix:* Enforced mandatory precedence where active data flows (`integration_service`) and backup restore paths (`backup_service`) are disabled/blocked prior to deleting or anonymizing dependent records.

4. **Case ID Integer Sorting:**
   - *Fix:* Fixed output sorting to sort numerically by integer case ID (`case_33` through `case_550`).

---

## Limitations

- Ground truth answers for the 518 evaluation cases remain private and organizer-only per challenge design. Structural validation confirms 100% compliance with all schema, operation, phase, evidence reference, and ordering constraints, but final correctness depends on the hidden ground truth.
