# Ghost Data Still Exists — Deletion Audit Agent

## Overview

AI-powered deletion audit agent for the HackerRank Orchestrate "Ghost Data Still Exists" challenge. The agent processes 518 deletion requests, resolves user identities across historical records, searches evidence files (SQL, JSON, logs, TXT), applies 15 deletion rules, and produces `output.csv` with findings, remediation steps, and verification checks.

## Project Structure

```
code/
├── main.py              # Main solution entry point
├── README.md            # This file
└── evaluation/
    ├── evaluation_report.md   # Case-level, step-level, field-level, and sequence accuracy
    └── usage_report.md        # Model provider, call counts, token usage, cost estimates
```

## Setup

### Prerequisites

- Python 3.8 or higher
- No external dependencies required (uses only standard library: `csv`, `json`, `re`, `sqlite3`, `pathlib`, `datetime`)

### Installation

No installation required. The solution uses only Python standard library modules.

## Execution

### Run the Solution

From the repository root:

```bash
cd code
python main.py
```

This will:

1. Load all 6 CSV dataset files from `dataset/`
2. Parse all 94 evidence files from `dataset/evidence/`
3. Process all 518 deletion requests
4. Write `output.csv` to the repository root

### Output Format

`output.csv` contains exactly 518 data rows (plus header), sorted by `case_id`:

| Column | Description |
|--------|-------------|
| `case_id` | Unique case identifier |
| `deletion_status` | `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE` |
| `steps_json` | JSON array of audit steps (FINDING → REMEDIATION → VERIFICATION) |

Each step contains: `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`.

### Expected Output Statistics

- **NOT_APPLICABLE**: 240 cases (46.3%) — request text does not authorize deletion
- **COMPLETE**: 85 cases (16.4%) — no remaining evidence at audit_at
- **INCOMPLETE**: 193 cases (37.3%) — remaining records, data flows, or restore risks found

## How It Works

### 1. Request Classification

Determines whether `request_text` authorizes deletion using multilingual keyword detection (English, Spanish, French, German, Chinese, Korean, Portuguese, Russian, Japanese). Non-deletion requests (access, correction, export, marketing opt-out) are classified as `NOT_APPLICABLE`.

### 2. Identity Resolution

Resolves current and historical identifiers for each user:
- Current identity from `user_identities.csv`
- Historical identifiers from `user_audit_log.csv` (emails, names, phones, email hashes) up to the case's `audit_at` cutoff

### 3. Evidence Search

Parses evidence files in multiple formats:
- **SQL** (`.sql`): Executed via `sqlite3` in-memory database; extracts records from `record_json` columns
- **JSON** (`.json`): Parses snapshot bundles with `data_store`, `collection`, and `records`
- **TXT** (`.txt`): Parses pipe-delimited handover reports
- **Log** (`.log`): Regex-based field extraction for service, resource_id, event, matched values

Evidence is filtered by `captured_at <= audit_at` to reconstruct state at the audit time.

### 4. Rule Application

Applies `deletion_rules.csv` (15 rules) to map data categories to required actions:
- `DELETE` → `DELETE_RECORD` / `VERIFY_RECORD_ABSENT`
- `REDACT` → `REDACT_RECORD` / `VERIFY_RECORD_REDACTED`
- `ANONYMIZE` → `ANONYMIZE_RECORD` / `VERIFY_RECORD_ANONYMIZED`
- `RETAIN` → `VERIFY_RECORD_PRESENT` (security audit logs preserved)

### 5. Step Generation

Generates ordered audit steps:
1. **FINDING**: `REPORT_REMAINING_RECORD`, `REPORT_EXPOSED_PII`, `REPORT_ACTIVE_DATA_FLOW`, `REPORT_RESTORE_RISK`
2. **REMEDIATION**: `DELETE_RECORD`, `REDACT_RECORD`, `ANONYMIZE_RECORD`, `DISABLE_DATA_FLOW`, `BLOCK_RESTORE`
3. **VERIFICATION**: `VERIFY_RECORD_ABSENT`, `VERIFY_RECORD_REDACTED`, `VERIFY_RECORD_ANONYMIZED`, `VERIFY_RECORD_PRESENT`, `VERIFY_DATA_FLOW_DISABLED`, `VERIFY_RESTORE_BLOCKED`

Steps within each phase are sorted ascending by `(system_id, resource_id)`. Step numbers are consecutive starting at 1.

### 6. Evidence ID Rules

- **FINDING steps**: Cite valid `file_id` from `evidence_files.csv`
- **COMPLETE VERIFICATION steps**: Cite participant-visible `evidence_id`
- **REMEDIATION steps**: Empty `evidence_id` (future work)
- **INCOMPLETE VERIFICATION steps**: Empty `evidence_id` (future work)

## Evaluation Reports

- `code/evaluation/evaluation_report.md`: Case-level, step-level, field-level, and sequence accuracy metrics plus 3 custom evaluation test cases
- `code/evaluation/usage_report.md`: Model provider, call counts, token usage, and cost estimates

## Submission Artifacts

| Item | Path |
|------|------|
| Solution code | `code/main.py` |
| Output predictions | `output.csv` (repository root) |
| Evaluation report | `code/evaluation/evaluation_report.md` |
| Usage report | `code/evaluation/usage_report.md` |
| Agent log | `log.txt` (repository root) |

## Notes

- The production run makes zero LLM model calls; all logic is rule-based and deterministic.
- CSV files may use cp1252 encoding; the solution handles automatic encoding detection.
- No API keys or credentials are required.
- All data is read from `dataset/` and written to `output.csv` at the repository root.
