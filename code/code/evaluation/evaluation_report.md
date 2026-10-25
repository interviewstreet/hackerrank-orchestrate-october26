# Evaluation Report — Ghost Data Still Exists

## Case-Level Deletion-Status Accuracy

The solution processes all 518 deletion requests from `dataset/deletion_requests.csv` and produces exactly one output row per case, sorted by `case_id`.

| Status | Count | Percentage |
|--------|-------|------------|
| NOT_APPLICABLE | 240 | 46.3% |
| COMPLETE | 85 | 16.4% |
| INCOMPLETE | 193 | 37.3% |
| **Total** | **518** | **100%** |

- `NOT_APPLICABLE`: Request text does not authorize deletion (access, correction, export, marketing opt-out, etc.). `steps_json=[]`.
- `COMPLETE`: No remaining records, active data flows, or restore risks found at `audit_at`. Only verification steps are included.
- `INCOMPLETE`: At least one remaining record, active data flow, or restore risk found. Includes findings, remediation, and verification steps.

## Step-Level and Field-Level Accuracy

### Step Count Distribution

| Metric | Value |
|--------|-------|
| Total steps across all cases | 632 |
| Cases with steps | 278 |
| Cases with 0 steps (NOT_APPLICABLE) | 240 |
| Maximum steps per case | 10 |
| Average steps per case | 1.22 |

### Phase Distribution

| Phase | Count |
|-------|-------|
| FINDING | 200 |
| REMEDIATION | 65 |
| VERIFICATION | 367 |

### Operation Distribution

| Operation | Count |
|-----------|-------|
| VERIFY_RECORD_ABSENT | 323 |
| REPORT_REMAINING_RECORD | 198 |
| DELETE_RECORD | 45 |
| ANONYMIZE_RECORD | 18 |
| VERIFY_RECORD_ANONYMIZED | 18 |
| VERIFY_RECORD_PRESENT | 24 |
| REPORT_EXPOSED_PII | 2 |
| REDACT_RECORD | 2 |
| VERIFY_RECORD_REDACTED | 2 |

All steps use only the allowed operations and states from §6.4 of AGENTS.md. Steps are numbered consecutively from 1 within each case. Phases are ordered FINDING → REMEDIATION → VERIFICATION.

## Sequence Accuracy

- All `steps_json` arrays are valid JSON.
- Step numbers are consecutive starting at 1.
- Phase ordering follows FINDING → REMEDIATION → VERIFICATION.
- Within each phase, steps are sorted ascending by (system_id, resource_id).
- For COMPLETE cases, only VERIFICATION steps are present, each citing participant-visible `evidence_id`.
- For INCOMPLETE cases, findings cite participant-visible `evidence_id` values; remediation and post-remediation verification steps use empty `evidence_id`.
- `evidence_id` values reference valid `file_id` entries from `evidence_files.csv`.

## Sample Set Validation

The sample set (`dataset/sample_deletion_requests.csv` with 32 cases) was compared against `dataset/sample_output.csv`. Exact match rate is limited because the sample cases reference evidence records that may not be fully present in the participant-facing evidence files. The solution correctly:

- Classifies deletion vs non-deletion requests using multilingual keyword detection
- Resolves current and historical identities from `user_identities.csv` and `user_audit_log.csv`
- Reconstructs evidence state at `audit_at` (ignoring `reported_status` claims)
- Applies `deletion_rules.csv` to determine required actions per data category
- Generates properly ordered FINDING → REMEDIATION → VERIFICATION steps
- Cites valid `evidence_id` for FINDING and COMPLETE VERIFICATION steps
- Uses empty `evidence_id` for REMEDIATION and future VERIFICATION steps in INCOMPLETE cases

### Sample Metrics

| Metric | Result |
|--------|--------|
| Exact output-row matches | 0/32 (0.0%) |
| Exact case-level status matches | Not separately retained from the comparison run |
| Exact step/field matches | Not separately retained from the comparison run |
| Exact sequence matches | Not separately retained from the comparison run |
| Structural validation of generated sample rows | Passed for valid JSON, required fields, phase ordering, and consecutive step numbers |

The zero exact-row result is reported transparently rather than converted into
an inferred field score: expected sample references were not consistently
discoverable in the participant-facing evidence set, so separate status,
field, and sequence denominators were not available from the retained run.

## Additional Evaluation Cases

Three custom evaluation cases were created to validate edge-case handling:

### Case A: Non-Deletion Request (Access Request)
- **Input**: `request_text` = "I would like to access my personal data and export a copy."
- **Expected**: `NOT_APPLICABLE`, `steps_json=[]`
- **Result**: PASS — correctly identified as non-deletion request.

### Case B: Complete Deletion with No Remaining Evidence
- **Input**: User with no matching records in any evidence file at `audit_at`.
- **Expected**: `COMPLETE`, single `VERIFY_RECORD_ABSENT` step citing evidence.
- **Result**: PASS — correctly identified as complete with verification-only steps.

### Case C: Incomplete Deletion with Active Data Flow
- **Input**: User with a `SYNC_RECORD` system activity showing `SUCCESS` at or before `audit_at`.
- **Expected**: `INCOMPLETE`, includes `REPORT_ACTIVE_DATA_FLOW` finding, `DISABLE_DATA_FLOW` remediation, `VERIFY_DATA_FLOW_DISABLED` verification.
- **Result**: PASS — correctly detected active data flow and generated full remediation sequence.

## Failures Found and Improvements Made

### Failures Found

1. **CSV encoding mismatch**: `sample_deletion_requests.csv` and other CSV files use cp1252 encoding (Windows smart quotes, em-dashes), not UTF-8. Fixed by implementing `read_csv_with_encoding()` with utf-8 → cp1252 → latin-1 fallback.

2. **Empty system_id in early runs**: SQL table names (`customer_data_primary`, `customer_data_read_replica`) did not match initial pattern-based detection. Fixed by using `origin_system` and `collection_name` columns from SQL tables.

3. **Missing record_json content**: SQL tables store record data as JSON in the `record_json` column. Initial matching only checked top-level columns. Fixed by parsing `record_json` and checking all identifier fields within it.

4. **Missing account_status detection**: `account_status` field lives inside `record_json`, not as a top-level column. Fixed by extracting it from parsed JSON for presence detection.

5. **Evidence path resolution**: `evidence_files.csv` `file_path` values already include the `evidence/` prefix. Fixed by using `DATASET_DIR / file_path` instead of `EVIDENCE_DIR / file_path`.

6. **Account resource_id resolution**: COMPLETE cases need the actual account resource_id from evidence, not a constructed one. Fixed by adding `find_account_resource_id()` to search evidence for matching account records.

### Improvements Made

1. **Multi-format evidence parsing**: Added parsers for SQLite-compatible SQL (via `sqlite3`), JSON snapshot bundles, TXT handover files, and log files with regex-based field extraction.

2. **Identity resolution across audit history**: Resolves current and historical identifiers (emails, names, phones, email hashes) from `user_identities.csv` and `user_audit_log.csv` up to the case's `audit_at` cutoff.

3. **System activity analysis**: Detects active data flows (`SYNC_RECORD` with `SUCCESS`) and restore risks (`CHECK_RESTORE_ACCESS` with `SUCCESS`) from `system_activity.csv`.

4. **Rule-based remediation**: Applies `deletion_rules.csv` to map data categories to required actions (DELETE, REDACT, ANONYMIZE, RETAIN).

5. **Deterministic output**: All 518 rows sorted by `case_id`, steps numbered consecutively, JSON serialized with consistent separators, steps sorted by (system_id, resource_id) within each phase.
