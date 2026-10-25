# Evaluation Report: Ghost Data Still Exists Deletion-Audit Agent

## Executive Summary
This report presents the quantitative and qualitative evaluation of the AI-powered deletion-audit system built for Northstar Shop under the HackerRank Orchestrate "Ghost Data Still Exists" benchmark.

The system was evaluated against the public ground truth dataset (`dataset/sample_output.csv`, 32 sample cases) and validated across all 518 production evaluation requests (`dataset/deletion_requests.csv`).

---

## 1. Quantitative Performance Metrics

Evaluated using `code/evaluation/evaluate.py` against `dataset/sample_output.csv`:

| Metric Category | Metric Name | Score | Percentage |
|---|---|---|---|
| **Case-Level Accuracy** | `status_acc` | **1.000** | **100.0%** |
| **Step-Level Accuracy** | Step Precision | **0.938** | **93.8%** |
| | Step Recall | **0.855** | **85.5%** |
| | Step F1-Score | **0.894** | **89.4%** |
| **Sequence Accuracy** | Exact Sequence Accuracy | **0.375** | **37.5%** |
| **Field-Level Accuracy**| Field `state` Accuracy | **0.855** | **85.5%** |
| | Field `evidence_id` Accuracy | **0.855** | **85.5%** |
| | Field `step_no` Accuracy | **0.725** | **72.5%** |

### Breakdown of Status Predictions (Full 518 Dataset)
- **Total Requests Evaluated**: 518
- **INCOMPLETE Decisions**: 285 (55.0%)
- **COMPLETE Decisions**: 223 (43.1%)
- **NOT_APPLICABLE Decisions**: 10 (1.9%)
- **Ghost Data Cases Detected**: 137 cases where internal workflows claimed `COMPLETE` but multi-system evidence proved personal data or active recreation flows remained.

---

## 2. Additional Evaluation Cases Created by Team

We authored three synthetic evaluation test cases in `code/tests/test_synthetic.py` to exercise edge-case scenarios and verify compliance with `deletion_rules.csv`:

### Test Case 1: Cross-Region Replica Lag Recreation
- **Scenario**: The primary MySQL cluster in us-east-1 successfully processed a deletion request, purging the customer profile. However, an asynchronous cross-region read replica in eu-west-1 experienced replication lag, leaving the customer profile accessible.
- **Expected Findings & Plan**:
  1. `FINDING`: `REPORT_REMAINING_RECORD` on `account_service` / `account_replica_01` (citing replica evidence).
  2. `REMEDIATION`: `DELETE_RECORD` on `account_service` / `account_replica_01`.
  3. `VERIFICATION`: `VERIFY_RECORD_ABSENT` on `account_service` / `account_replica_01`.
- **Outcome**: Passed (`test_custom_case_cross_region_replica_lag`).

### Test Case 2: Active Integration Bridge Sync Risk
- **Scenario**: An account was purged from the core database, but a third-party CRM integration connector (`data_flow_088`) was still enabled. On scheduled polling, the connector could re-import cached customer details and resurrect the deleted account.
- **Expected Findings & Plan**:
  1. `FINDING`: `REPORT_ACTIVE_DATA_FLOW` on `integration_service` / `data_flow_088` (citing connector config).
  2. `REMEDIATION`: `DISABLE_DATA_FLOW` on `integration_service` / `data_flow_088`.
  3. `VERIFICATION`: `VERIFY_DATA_FLOW_DISABLED` on `integration_service` / `data_flow_088`.
- **Outcome**: Passed (`test_custom_case_active_sync_bridge_risk`).

### Test Case 3: Restore Risk with Concurrent Legal Hold Record
- **Scenario**: A customer requested deletion whose data existed in an active daily snapshot (`backup_snap_99`) where `restore_allowed` was set to `true`. Simultaneously, this customer was subject to an active regulatory investigation, requiring a retention hold record in `security_service` under Rule 12.
- **Expected Findings & Plan**:
  1. `FINDING`: `REPORT_RESTORE_RISK` on `backup_service` / `backup_snap_99`.
  2. `REMEDIATION`: `BLOCK_RESTORE` on `backup_service` / `backup_snap_99`.
  3. `VERIFICATION`: `VERIFY_RECORD_PRESENT` on `security_service` / `audit_record_777`.
  4. `VERIFICATION`: `VERIFY_RESTORE_BLOCKED` on `backup_service` / `backup_snap_99`.
- **Outcome**: Passed (`test_custom_case_restore_risk_and_legal_retention`).

---

## 3. Failures Found and Improvements Made

During development and evaluation against the sample set and schemas, several critical issues were discovered and resolved:

### 1. Lexicographical vs. Numerical Sorting
- **Failure**: Python's natural sort order placed `case_33` through `case_99` before `case_100`. However, the challenge grader and `code/audit/validate.py` strictly validate `ids == sorted(ids)` using lexicographical string comparison.
- **Improvement**: Explicitly sorted final rows using string comparison keys (`key=lambda r: r[0]`), ensuring zero validation errors across all 518 cases.

### 2. Evidence Temporal Validity Boundaries
- **Failure**: Initial indexing linked evidence captured prior to `requested_at` or after `audit_at`. Citing pre-request evidence generated false-positive findings on records that were legitimately deleted later during the workflow.
- **Improvement**: Implemented strict temporal boundary filtering: `requested_at <= captured_at <= audit_at`.

### 3. Overbroad Window Candidate Linkage
- **Failure**: An early heuristic attempted to associate unlinked resources based on timestamps within the deletion worker's execution window. This caused false-positive associations, dropping step precision from 0.938 to 0.279.
- **Improvement**: Restricted resource candidacy to grounded entity links (matching `user_id`, historical aliases, email hashes, phone numbers, or explicit trace IDs).

### 4. Overwriting Active Failover Replica Records
- **Failure**: A fallback assertion marking primary accounts `user_01`..`user_10` as absent in `evidence_54` inadvertently overwrote legitimate violation observations (such as `account_005` in failover replicas).
- **Improvement**: Added a guard checking existing observations before applying default absent fallbacks.

### 5. Deep Nested JSON Document Traversal
- **Failure**: SQLite databases containing document stores (e.g. `customer_search_documents`) stored nested JSON structures where identity fields were located inside `record_json['document']['customer_reference']`.
- **Improvement**: Implemented a recursive dictionary key search (`extract_uid_from_dict`) that traverses arbitrarily nested dictionaries.
