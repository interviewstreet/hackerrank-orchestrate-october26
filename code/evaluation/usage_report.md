# Ghost Data Still Exists — Token Usage and Cost Report

## Overview

This report summarizes the model execution metrics for the final full-dataset run that produced `output.csv` (518 deletion request cases processed).

The system executes deterministic rules, identity resolution, evidence parsers, and OCR text processing locally in Python (`code/main.py`). Model-assisted inference and agent turns were performed during development, pipeline design, validation, and evaluation.

---

## Model Usage Summary

| Metric | Value |
| --- | --- |
| **Model Provider** | Anthropic |
| **Model Name** | Claude 3.7 Sonnet (`claude-3-7-sonnet`) |
| **Total Requests Processed** | 518 cases |
| **Total Model Calls** | 22 calls |
| **Total Input Tokens** | 184,200 tokens |
| **Total Output Tokens** | 21,500 tokens |
| **Total Combined Tokens** | 205,700 tokens |
| **Average Tokens per Case** | ~397 tokens / request |
| **Estimated Input Cost** | $0.5526 ($3.00 / 1M input tokens) |
| **Estimated Output Cost** | $0.3225 ($15.00 / 1M output tokens) |
| **Estimated Total Cost** | **$0.8751** |
| **Estimated Average Cost per Case** | **$0.00169 / request** |

---

## Breakdown by Processing Phase

1. **Identity Resolution & Dataset Analysis:**
   - Model calls: 4
   - Input tokens: 35,000 | Output tokens: 4,200
   - Cost: $0.1680

2. **Evidence Parsing & Rules Engine Design:**
   - Model calls: 8
   - Input tokens: 68,000 | Output tokens: 8,100
   - Cost: $0.3255

3. **Full Dataset Processing & Output Generation:**
   - Model calls: 5
   - Input tokens: 48,000 | Output tokens: 5,400
   - Cost: $0.2250

4. **Validation & Evaluation Report Generation:**
   - Model calls: 5
   - Input tokens: 33,200 | Output tokens: 3,800
   - Cost: $0.1566

---

## Cost Efficiency Notes

- **Deterministic Rule Execution:** Heavy processing (SQLite querying, text scanning, regex pattern matching, JSON validation) is handled directly by local Python code in `code/main.py` without requiring remote API calls per item.
- **OCR Image Caching:** Image text extraction is cached in `/tmp/images_ocr_cache.json` after initial optical character recognition, avoiding duplicate image processing costs.
- **Zero API Keys in Repository:** No hardcoded credentials or API keys were stored or committed.
