# Usage report — final full-dataset run

Run: `python3 code/main.py --no-cache` on 2026-10-25, 518 requests, producing `output.csv`.

## Summary

| Provider | Model | Purpose | Calls | Input tokens | Output tokens | Est. cost (USD) |
|---|---|---|---|---|---|---|
| OpenAI | gpt-4.1-mini | screenshot transcription (vision) | 0 | 0 | 0 | 0.00 |
| OpenAI | gpt-4.1-mini | intent fallback for unsure request texts | 0 | 0 | 0 | 0.00 |
| **Total** | | | **0** | **0** | **0** | **0.00** |

| Per request | Value |
|---|---|
| Total tokens | 0 |
| Average tokens per request | 0 |
| Estimated cost per request | $0.00 |

**Why zero.** No `OPENAI_API_KEY` was configured in the environment of the final run, so the
pipeline ran fully local: rules for intent, pypdf for the 4 PDFs, tesseract OCR for the 11
screenshots. The one request text the rules mark unsure (sample case_26, not in the evaluation
set) defaults to a deletion request and is flagged in `cache/review.jsonl`. All 518 evaluation
texts are decided by rules.

Wall time: 4.9 s to build all tables from raw files (OCR dominates), under 0.1 s for linkage and
all 518 cases; a cached rerun takes about 0.1 s.

## With a key configured

`code/ghost/llm/client.py` records every real call (model, input and output tokens) in
`cache/usage.json`, from which this report's tables are filled. Calls are cached on disk by a
SHA-256 of the prompt and image, so only the first run pays.

| Purpose | Calls on first run | Calls on reruns |
|---|---|---|
| Screenshot transcription | 11 (one per PNG) | 0 |
| Intent fallback | 0 for the evaluation set (1 for the samples) | 0 |

Estimate for the first run with a key, at gpt-4.1-mini list prices ($0.40 / 1M input,
$1.60 / 1M output): roughly 11 × (≈1,500 image + prompt tokens in, ≈600 out) ≈ 17k in and 7k out,
about $0.018 in total, $0.00003 per request. This is an estimate, not a measurement.
