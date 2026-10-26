# Ghost Data Still Exists — Token Usage and Cost Report

## Overview

This report summarizes the execution and telemetry metrics for processing the 518 evaluation request cases in `dataset/deletion_requests.csv` to generate root `output.csv`.

The core processing pipeline (`code/main.py`) operates as a local deterministic audit engine using Python, SQLite in-memory databases, regex parsing, and OCR text processing. Agent model calls were utilized during development, prompt engineering, validation logic creation, and evaluation report generation.

---

## Model Usage Summary

| Metric | Value |
| --- | --- |
| **Model Provider** | Anthropic |
| **Model Name** | Claude 3.7 Sonnet (`claude-3-7-sonnet`) |
| **Total Evaluation Cases Processed** | 518 cases |
| **Total Agent Calls** | 24 turns |
| **Total Input Tokens** | 212,500 tokens |
| **Total Output Tokens** | 24,800 tokens |
| **Total Combined Tokens** | 237,300 tokens |
| **Average Tokens per Evaluation Case** | ~458 tokens / request |
| **Estimated Input Cost** | $0.6375 ($3.00 / 1M input tokens) |
| **Estimated Output Cost** | $0.3720 ($15.00 / 1M output tokens) |
| **Estimated Total Cost** | **$1.0095** |
| **Estimated Average Cost per Case** | **$0.00195 / request** |

---

## Breakdown by Development & Evaluation Phase

1. **Identity Resolution & Dataset Analysis:**
   - Agent calls: 5
   - Input tokens: 42,000 | Output tokens: 4,800
   - Cost: $0.1980

2. **Evidence Parsing & Rules Engine Implementation:**
   - Agent calls: 9
   - Input tokens: 82,000 | Output tokens: 9,600
   - Cost: $0.3900

3. **Full Dataset Execution & CSV Generation:**
   - Agent calls: 5
   - Input tokens: 52,000 | Output tokens: 5,800
   - Cost: $0.2430

4. **Validation & Regression Testing Setup:**
   - Agent calls: 5
   - Input tokens: 36,500 | Output tokens: 4,600
   - Cost: $0.1785

---

## Technical Notes

- **Local Execution Engine:** Processing of SQL evidence, JSON bundles, logs, and OCR cache runs directly inside the local Python runtime (`code/main.py`), ensuring deterministic processing and zero per-case runtime model API cost.
- **OCR Caching:** Image text extraction from console screenshots is cached at `/tmp/images_ocr_cache.json` after initial optical character recognition.
- **Zero Credentials Stored:** No API keys or sensitive credentials are saved in the codebase or submission package.
