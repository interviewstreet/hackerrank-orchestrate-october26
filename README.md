# Ghost Data Still Exists - Deletion Audit Agent

HackerRank Orchestrate October 2026 Challenge Solution

## Overview

This solution implements an AI-powered deletion audit agent that determines whether a user's personal data has been truly deleted across all systems, replicas, logs, backups, and evidence sources. The agent processes 518 deletion requests and produces an `output.csv` with the required format.

## Requirements

- Python 3.10+
- Dependencies: `pymupdf` (for PDF parsing), `pytesseract` + `tesseract-ocr` (for image OCR), `pillow` (for image handling)

## Installation

```bash
pip install pymupdf pytesseract pillow
```

Note: For OCR support, you also need to install tesseract-ocr system package:
- Ubuntu/Debian: `apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

## Running the Solution

```bash
cd code
python main.py
```

This will:
1. Load all dataset files from `../dataset/`
2. Process all 518 deletion requests
3. Parse evidence files (SQL, JSON, logs, PDFs, images, text)
4. Apply deletion rules from `deletion_rules.csv`
5. Generate `output.csv` in the repository root with 518 rows

## Output Format

The `output.csv` contains exactly 518 rows (one per case in `deletion_requests.csv`):

```csv
case_id,deletion_status,steps_json
```

- `deletion_status`: `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`
- `steps_json`: JSON array of steps ordered by phase (FINDING → REMEDIATION → VERIFICATION)

Each step contains:
```json
{
  "step_no": 1,
  "phase": "FINDING|REMEDIATION|VERIFICATION",
  "system_id": "system_identifier",
  "resource_id": "resource_identifier",
  "operation": "OPERATION_NAME",
  "state": "STATE_NAME",
  "evidence_id": "evidence_file_id_or_activity_id"
}
```

## Approach

1. **Identity Resolution**: Maps request emails to user_ids using current identities (`user_identities.csv`) and historical changes (`user_audit_log.csv`)

2. **Evidence Parsing**: Handles multiple formats:
   - SQL files (SQLite-compatible) - executed in-memory to query tables
   - JSON files - parsed for structured records
   - Log files - searched for identifiers
   - PDF documents - text extracted with PyMuPDF
   - Images - OCR with Tesseract
   - Text files - direct string search

3. **State Reconstruction**: Uses evidence captured at or before `audit_at` to determine true state, ignoring reported workflow statuses

4. **Rule Application**: Applies `deletion_rules.csv` to each data category:
   - DELETE: Record must be removed
   - REDACT: Identifiers removed, record retained
   - ANONYMIZE: Record unlinked from user
   - RETAIN: Record kept (legal hold, security audit)

5. **Step Generation**:
   - FINDING: Reports remaining records, exposed PII, active data flows, restore risks
   - REMEDIATION: Ordered plan to disable flows, block restores, delete/redact/anonymize
   - VERIFICATION: Checks proving compliant state

## Files

- `code/main.py` - Main solution entry point
- `dataset/` - All participant-facing data files
- `output.csv` - Generated submission file (518 rows)

## Evaluation

The solution produces deterministic output with proper step ordering, valid JSON, and evidence-backed findings for COMPLETE cases.