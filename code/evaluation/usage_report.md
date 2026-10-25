# Usage Report — Ghost Data Still Exists

## Model Information

| Field | Value |
|-------|-------|
| Model provider | NVIDIA NIM (via Copilot LLM Gateway) |
| Model name | nemotron-3.5-super-vl-120b-a12b |
| Coding harness | GitHub Copilot VS Code Agent |
| Language | Python 3.10 |

## Model Call Counts

This solution uses a deterministic, rule-based approach implemented in Python. No LLM model calls are made during the execution of `code/main.py`. The model was used only during development (code authoring, debugging, and refinement), not during the production run.

| Phase | Model Calls |
|-------|-------------|
| Development (authoring/debugging) | ~20 (estimated, interactive) |
| Production run (`python code/main.py`) | 0 |
| **Total** | **~20** |

## Token Usage

| Phase | Input Tokens | Output Tokens | Total Tokens |
|-------|-------------|---------------|--------------|
| Development (estimated) | ~60,000 | ~40,000 | ~100,000 |
| Production run | 0 | 0 | 0 |
| **Total** | **~60,000** | **~40,000** | **~100,000** |

For the 518 production requests, measured production usage is zero:

| Metric | Value |
|--------|------:|
| Average input tokens per request | 0 |
| Average output tokens per request | 0 |
| Average total tokens per request | 0 |

If the estimated development totals are allocated across 518 requests for
reference, the averages are approximately 115.83 input tokens, 77.22 output
tokens, and 193.05 total tokens per request. These are not runtime
measurements; the deterministic production process makes no model calls.

## Cost Estimate

| Metric | Value |
|--------|-------|
| Estimated total cost | $0.00 (development calls within Copilot subscription) |
| Cost per request (production) | $0.00 |
| Average estimated cost per request (518-case run) | $0.00 |
| Cost per 1K tokens (estimated) | N/A (no API billing for Copilot development) |

## Per-Model Totals

| Model | Calls | Input Tokens | Output Tokens | Total Tokens |
|-------|-------|-------------|---------------|--------------|
| nemotron-3.5-super-vl-120b-a12b | ~20 | ~60,000 | ~40,000 | ~100,000 |
| **Overall** | **~20** | **~60,000** | **~40,000** | **~100,000** |

## Production Run Summary

- **Command**: `python code/main.py`
- **Working directory**: `d:/Projects/Hacker Rank/hackerrank-orchestrate-october26/`
- **Input files processed**: 6 CSV files + 94 evidence files
- **Cases processed**: 518 deletion requests
- **Output**: `output.csv` at repository root
- **Runtime**: Deterministic, single-pass, no external API calls during execution
- **Status distribution**: 240 NOT_APPLICABLE, 85 COMPLETE, 193 INCOMPLETE

## Notes

- The production run makes zero LLM model calls; all logic is rule-based and deterministic.
- Token counts above are estimates for the interactive development phase only.
- No API keys or credentials are required to run `code/main.py`.
- All data is read from `dataset/` and written to `output.csv` at the repository root.
- CSV files use cp1252 encoding; the solution handles this with automatic encoding detection.
