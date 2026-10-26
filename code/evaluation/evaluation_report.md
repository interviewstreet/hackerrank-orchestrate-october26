# Ghost Data Still Exists: Evaluation Report

## 1. Executive Summary

This report documents the performance evaluation of the autonomous deletion-audit agent developed for Northstar Shop under the HackerRank Orchestrate "Ghost Data Still Exists" challenge. The agent deterministically audits personal data deletion requests against global platform evidence, system activity logs, SQL snapshot databases, and policy rules (`deletion_rules.csv`).

---

## 2. Quantitative Benchmark Metrics

Evaluation was performed against all 32 publicly provided benchmark cases in `dataset/sample_deletion_requests.csv` and verified against the ground-truth decisions in `dataset/sample_output.csv`.

| Metric | Measured Score | Target Contract |
|---|---|---|
| **Case-Level Deletion-Status Accuracy** | **100.00%** (32 / 32) | Categorization into `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE` |
| **Field-Level Accuracy** | **100.00%** | Strict equality across all 7 step fields (`step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`) |
| **Step-Level Accuracy** | **100.00%** (193 / 193) | Exact 5-tuple match (`phase`, `system_id`, `resource_id`, `operation`, `state`) |
| **Sequence Accuracy** | **100.00%** (32 / 32) | Exact full-array step sequence match per case |

---

## 3. Additional Participant-Created Evaluation Cases

Per AGENTS.md §6.8, three synthetic evaluation test cases were designed to validate edge-case behaviors not fully exercised in simple requests:

### Custom Case 1: Historical Email + Active Data Flow Recreation Risk
- **Case ID:** `custom_01`
- **Subject Email:** `alex.t99@example.com` (Request submitted using historical email `alex.turner_old@example.com`)
- **Request Text:** *"I am requesting complete erasure of my account and data."*
- **Scenario:** The user updated their email identity 6 months ago. The primary database deleted the current profile, but an unmanaged event connector `data_flow_9011` remains active in `integration_service`, continuously synchronizing historical user events to external replicas.
- **Expected Status:** `INCOMPLETE`
- **Audit Steps:**
  1. `[FINDING]` `integration_service` / `data_flow_9011` / `REPORT_ACTIVE_DATA_FLOW` (State: `ACTIVE`, Evidence: `evidence_94`)
  2. `[REMEDIATION]` `integration_service` / `data_flow_9011` / `DISABLE_DATA_FLOW` (State: `DISABLED`, Evidence: `""`)
  3. `[VERIFICATION]` `account_service` / `account_9011` / `VERIFY_RECORD_ABSENT` (State: `ABSENT`, Evidence: `""`)
  4. `[VERIFICATION]` `integration_service` / `data_flow_9011` / `VERIFY_DATA_FLOW_DISABLED` (State: `DISABLED`, Evidence: `""`)

### Custom Case 2: Residual Tombstone with Exposed PII Hash and Phone
- **Case ID:** `custom_02`
- **Subject Email:** `elena.rostova@example.com`
- **Request Text:** *"Please delete my account and ensure no identifying details remain."*
- **Scenario:** An account deletion was reported complete. However, inspection of `identity_service` tombstone record `tombstone_7720` shows that while `name` and `email` were removed, the SHA-256 `email_hash` and `phone` direct identifiers remain stored in the tombstone, violating policy `ACCOUNT_TOMBSTONE` redaction requirements.
- **Expected Status:** `INCOMPLETE`
- **Audit Steps:**
  1. `[FINDING]` `identity_service` / `tombstone_7720` / `REPORT_EXPOSED_PII` (State: `PRESENT`, Evidence: `evidence_50`)
  2. `[REMEDIATION]` `identity_service` / `tombstone_7720` / `REDACT_RECORD` (State: `REDACTED`, Evidence: `""`)
  3. `[VERIFICATION]` `account_service` / `account_7720` / `VERIFY_RECORD_ABSENT` (State: `ABSENT`, Evidence: `""`)
  4. `[VERIFICATION]` `security_service` / `audit_record_7720` / `VERIFY_RECORD_PRESENT` (State: `PRESENT`, Evidence: `""`)
  5. `[VERIFICATION]` `identity_service` / `tombstone_7720` / `VERIFY_RECORD_REDACTED` (State: `REDACTED`, Evidence: `""`)

### Custom Case 3: Legal Retention Hold Compliance for Disputed Order
- **Case ID:** `custom_03`
- **Subject Email:** `lucas.silva@example.com`
- **Request Text:** *"Please erase my personal profile and account completely."*
- **Scenario:** The user requested full deletion. `account_service` properly deleted `account_5510`, and `security_service` retained `audit_record_5510`. Under rule `FINANCIAL_TAX_TRANSACTION`, a disputed charge order `legal_hold_5510` in `legal_service` must be retained until 2033. The audit agent must verify that the profile is absent while the legal record is properly preserved.
- **Expected Status:** `COMPLETE`
- **Audit Steps:**
  1. `[VERIFICATION]` `account_service` / `account_5510` / `VERIFY_RECORD_ABSENT` (State: `ABSENT`, Evidence: `evidence_21`)
  2. `[VERIFICATION]` `legal_service` / `legal_hold_5510` / `VERIFY_RECORD_PRESENT` (State: `PRESENT`, Evidence: `evidence_21`)
  3. `[VERIFICATION]` `security_service` / `audit_record_5510` / `VERIFY_RECORD_PRESENT` (State: `PRESENT`, Evidence: `evidence_21`)

---

## 4. Failures Found & Improvements Made

During diagnostic diffing and benchmarking against ground truth, 5 root causes were identified and systematically resolved:

1. **Nested SQL Document Structure (`case_16, 22`):**
   - *Problem:* In `customer_data_read_replica_20260921.sql` (`evidence_05`), customer search entries store metadata inside nested `document` JSON objects (`record_json -> document -> customer_reference`). Flat dictionary parsing left identifiers unextracted.
   - *Improvement:* Enhanced SQLite JSON row unpacker to recursively flatten nested `document` and `profile` sub-dictionaries into `r_dict`, recovering search index findings (`search_1007`, `search_8911`).

2. **JSON-Formatted Structured Log Regex Matching (`case_09`):**
   - *Problem:* Log parsers assumed key-value pairs formatted as `key=val` or `key: val`. In JSON-structured logs (`structured_service_events_eu_west_20260918.log`), keys are quoted (`"trace_id":"tr-9028396"`, `"resource_id":"audit_record_4902"`), causing regex misses.
   - *Improvement:* Upgraded regexes to `(?:trace_id[\"']?\s*[:=]\s*[\"']?|\[)` and `resource_id[\"']?\s*[:=]\s*[\"']?`, correctly linking traces to audit records. Furthermore, extracted line-level event timestamps rather than batch export timestamps so pre-audit records are preserved.

3. **Multi-Account Lifetime Resolution (`case_17`):**
   - *Problem:* Users with long account histories (e.g., `user_17`) possessed older archived accounts (`account_6523` in March) and modern active accounts (`account_4092` in September). The agent emitted verification steps for both.
   - *Improvement:* Constrained `account_service` observation aggregation to track strictly the latest primary account at or before `audit_at`, eliminating legacy duplicate accounts.

4. **Service Resource Export Attribution Cascade (`case_03, 04, 21, 25, 26, 27, 28`):**
   - *Problem:* In `service_resource_export_20260915_114455.json` (`evidence_92`), 404 account lookups and anonymized analytics profiles had `profile: None` or `email: None`, causing them to be discarded. This caused missing analytics verifications and caused `account_service` to fall back to older evidence (`evidence_51` instead of `evidence_92`).
   - *Improvement:* Pre-correlated `deletion_worker` execution streams and data catalog links in `system_activity.csv` to map anonymized analytics records and 404 profile lookups to their respective users. This simultaneously resolved missing analytics steps and aligned canonical evidence citations.

5. **Chronological Deletion Worker Account Disambiguation (`case_18, 20, 23, 31`):**
   - *Problem:* When multiple deletion requests were processed concurrently within the same operational window, the agent previously defaulted to the latest candidate in the batch, causing duplicate account assignments.
   - *Improvement:* Preserved strict chronological order of deletion worker activities, assigning the $k$-th request in a batch to the corresponding $k$-th execution activity.
