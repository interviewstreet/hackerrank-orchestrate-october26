# Northstar Shop — AI-Powered Deletion-Audit Agent
Challenge: **Ghost Data Still Exists** (HackerRank Orchestrate October 2026)

## Overview
Northstar Shop lost $2.4M when a supposedly deleted customer resurfaced in downstream systems due to ghost data in secondary databases, analytics exports, support attachments, search indexes, and active sync workflows.

This repository provides an automated, deterministic, AI-powered deletion-audit system that inspects all participant-visible evidence, tracks current and historical identities across systems, enforces `deletion_rules.csv`, and generates ordered findings, remediation plans, and verification checks.

## Key Features & Architecture
1. **Identity Resolution**:
   - Resolves subjects across current identifiers (`user_identities.csv`) and historical changes (`user_audit_log.csv`).
   - Links names, email aliases, phone numbers, and SHA-256 email hashes to stable internal `user_id`s.

2. **Multi-Modal Evidence Indexing**:
   - In-memory SQLite relational queries over database snapshots (`.sql`).
   - Deep recursive parsing of JSON exports and state dumps (`.json`).
   - Regex-based key-value and trace ID correlation across service logs (`.log`).
   - Document analysis for invoices, support exports, and handover notes (`.pdf`, `.txt`).
   - Operational event mapping across global workflows (`system_activity.csv`).

3. **Temporal State Reconstruction**:
   - Reconstructs resource state at `audit_at`.
   - Rejects stale evidence captured before `requested_at` or future claims captured after `audit_at`.

4. **Policy Enforcement & Tombstone Handling**:
   - Applies `deletion_rules.csv` to each data category.
   - Accurately distinguishes records requiring full deletion (search indexes, support attachments, marketing profiles) from records requiring redaction/tombstone preservation (account tombstones keeping stable `user_id` only) or anonymization (aggregated analytics).
   - Preserves mandatory compliance records (security audit logs, legal retention holds).

5. **Deterministic Remediation Planning**:
   - Strictly numbers steps consecutively starting at 1.
   - Orders by phase (`FINDING` -> `REMEDIATION` -> `VERIFICATION`), operation rank (`OP_RANK`), `system_id`, and `resource_id`.
   - Enforces evidence citation rules: participant-visible `evidence_id` on findings and `COMPLETE` verification checks; empty string `""` on proposed remediation and future verification.

## Setup & Dependencies
- Python 3.10+
- Dependencies: `pypdf`, `pytest`
```bash
pip install pypdf pytest
```

## Running the Agent
To run the deletion audit on the dataset:
```bash
# Default (reads dataset/deletion_requests.csv, writes output.csv at repo root)
python code/main.py dataset output.csv

# Or specify custom dataset directory and output location
python code/main.py path/to/dataset path/to/output.csv
```

## Running Tests & Validation
```bash
# Run unit and synthetic edge case tests
cd code
python -m pytest tests

# Validate output schema, ordering, and consistency
python -m audit.validate ../output.csv ../dataset/deletion_requests.csv

# Evaluate sample metrics against public ground truth
python evaluation/evaluate.py ../sample_test_out.csv ../dataset/sample_output.csv
```

## Deliverables
- `output.csv`: Complete predictions for all 518 evaluation requests.
- `code.zip`: Runnable package including code, tests, documentation, and `evaluation/` reports.
- `evaluation/evaluation_report.md`: Detailed performance metrics, custom test cases, and error analysis.
- `evaluation/usage_report.md`: Full model call, token usage, and cost analysis.
