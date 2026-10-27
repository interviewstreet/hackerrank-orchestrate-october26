# Ghost Data Still Exists - Deletion Audit Agent

**HackerRank Orchestrate - October 2026**

An AI-powered deletion audit system that verifies whether personal data deletion requests were actually completed.

## Solution Overview

This solution audits 518 deletion requests by:
1. Classifying request intent (deletion vs. access/export/opt-out)
2. Resolving current and historical user identities
3. Discovering evidence of remaining data across databases, logs, PDFs, and images
4. Applying deletion policy rules
5. Generating remediation steps when incomplete

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Fast Deletion Audit Agent                  │
│  (Hybrid rule-based + LLM approach)                     │
└────────────────────┬────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┬──────────────┐
     │               │               │              │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
│Request  │    │Identity │    │Evidence │   │ Policy  │
│Classifier│    │Resolver │    │Discovery│   │ Engine  │
└─────────┘    └─────────┘    └─────────┘   └─────────┘
```

### Components

- **RequestClassifier**: Detects deletion requests (multilingual support)
- **IdentityResolver**: Tracks current + historical identifiers from audit logs
- **FastEvidenceDiscovery**: Text-based search with selective LLM analysis
- **Policy Engine**: Applies 15 deletion rules and generates steps

## Technology Stack

- **Language:** Python 3.8+
- **LLM Model:** Claude Haiku 5.5 (via Experiential Labs Gateway)
- **Dependencies:** None (pure Python stdlib, no pip required)
- **Data Processing:** CSV, SQL (SQLite), JSON, PDF, images

## Setup Instructions

### 1. Environment Variables

Create `.env` file in project root:

```bash
EXPLABS_API_KEY=your_api_key_here
```

### 2. Directory Structure

```
hackerrank-orchestrate-october26/
├── .env                          # API key (gitignored)
├── dataset/                      # Input data
│   ├── deletion_requests.csv    # 518 cases to audit
│   ├── user_identities.csv      # Current user data
│   ├── user_audit_log.csv       # Historical changes
│   ├── system_activity.csv      # Deletion operations
│   ├── deletion_rules.csv       # Policy rules
│   ├── evidence_files.csv       # Evidence manifest
│   └── evidence/                # SQL, PDF, JSON, images
├── code/
│   ├── main_fast.py             # Fast entry point ⭐
│   ├── config.py                # Configuration
│   ├── models/                  # Agent modules
│   │   ├── fast_agent.py        # Main orchestrator
│   │   ├── classifiers.py       # Request classification
│   │   ├── identity.py          # Identity resolution
│   │   ├── evidence_fast.py     # Evidence discovery
│   │   └── policy.py            # Policy application
│   ├── utils/                   # Utilities
│   │   ├── llm_client.py        # API wrapper
│   │   └── loaders.py           # Data loaders
│   └── evaluation/              # Reports
│       ├── evaluation_report.md
│       └── usage_report.md
└── output.csv                   # Generated output
```

## Running the Solution

### Process All 518 Cases

```bash
cd code
python3 main_fast.py
```

**Expected:**
- Time: ~9-10 minutes
- Cost: ~$0.02 (2 cents)
- Output: `../output.csv` with 518 rows

### Process Specific Range

```bash
python3 main_fast.py START_INDEX END_INDEX

# Examples:
python3 main_fast.py 0 10     # First 10 cases
python3 main_fast.py 50 100   # Cases 50-100
python3 main_fast.py 0 518    # All cases
```

### Test Run (First 5 Cases)

```bash
python3 main_fast.py 0 5
```

## Output Format

The system generates `output.csv` with:

```csv
case_id,deletion_status,steps_json
case_33,INCOMPLETE,"[{\"step_no\":1,\"phase\":\"FINDING\",...}]"
case_34,COMPLETE,"[{\"step_no\":1,\"phase\":\"VERIFICATION\",...}]"
case_35,NOT_APPLICABLE,"[]"
```

### Deletion Status

- `COMPLETE`: Deletion verified with evidence
- `INCOMPLETE`: Records remain, remediation needed
- `NOT_APPLICABLE`: Not a deletion request

### Steps JSON

Each step contains:

```json
{
  "step_no": 1,
  "phase": "FINDING|REMEDIATION|VERIFICATION",
  "system_id": "account_service",
  "resource_id": "account_123",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

## Performance

Based on 50-case test run:

| Metric | Value |
|--------|-------|
| **Processing Time** | 1.1 seconds per case |
| **API Calls** | 0.32 per case |
| **Tokens Used** | 170 per case |
| **Cost** | $0.000033 per case |

**Full dataset (518 cases):**
- Time: ~9.5 minutes
- Cost: ~$0.017 (under 2 cents)

## Key Features

### 1. Multilingual Support

Handles requests in English, Spanish, Portuguese, Japanese, Korean, and more:
- "Please delete my account..."
- "Solicito la eliminación..."
- "このアカウントを削除..."
- "계정 삭제를 요청합니다..."

### 2. Historical Identity Tracking

Resolves users even when they've changed:
- Email addresses
- Phone numbers  
- Names

Uses `user_audit_log.csv` to track historical values.

### 3. Smart Evidence Discovery

- Text-based prefiltering before expensive LLM calls
- Analyzes only recent, relevant evidence files
- Supports SQL, JSON, PDF, images, logs

### 4. Policy-Driven Steps

Applies 15 deletion rules:
- DELETE: Complete removal
- REDACT: Remove PII, keep record
- ANONYMIZE: Irreversibly unlink from user
- RETAIN: Legal/security requirements

### 5. Cost Optimization

- Rule-based classification for 80% of cases
- Selective LLM usage only when needed
- Text search before deep analysis
- Limited evidence scope

## Evaluation

See detailed reports:
- `code/evaluation/evaluation_report.md` - Accuracy analysis
- `code/evaluation/usage_report.md` - Token usage and costs

### Key Results

- ✅ Handles 518 cases in 10 minutes
- ✅ Costs under 2 cents total
- ✅ Correctly identifies deletion vs. non-deletion requests
- ✅ Resolves historical identities from audit logs
- ✅ Generates properly formatted, ordered steps
- ✅ Multilingual request support

## Troubleshooting

### No API Key Error

```
EXPLABS_API_KEY not found in environment
```

**Fix:** Create `.env` file with your API key

### Import Errors

```
ModuleNotFoundError: No module named 'code'
```

**Fix:** Run from `code/` directory, not project root

### Timeout Issues

For very large batches, increase timeout:

```bash
timeout 1800 python3 main_fast.py 0 518  # 30 min timeout
```

## Development

### Running Tests

```bash
# Quick test (5 cases)
python3 main_fast.py 0 5

# Medium test (50 cases)
python3 main_fast.py 0 50

# Full run (518 cases)
python3 main_fast.py
```

### Adding Features

1. **Enhanced Evidence Analysis**: Modify `models/evidence_fast.py`
2. **Better Classification**: Update `models/classifiers.py`
3. **Custom Policy Rules**: Extend `models/policy.py`
4. **Different Models**: Change `MODEL_NAME` in `config.py`

## Submission Package

Generate `code.zip` with:

```bash
# From repository root
zip -r code.zip README.md code -x "*/__pycache__/*" "*/.venv/*" "*/venv/*" "*/.git/*"
```

Submit:
1. `code.zip` - Solution code and evaluation reports
2. `output.csv` - 518 prediction rows
3. `log.txt` - Session transcript

## License

This is a HackerRank Orchestrate challenge solution.

## Contact

For questions about this solution, refer to the evaluation reports or review the inline code comments.
