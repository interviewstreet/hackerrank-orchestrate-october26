# Token Usage and Cost Report (final full-dataset run)

Run: `python3 code/main.py` on 518 requests, 2026-10-25, cold cache
(`code/cache/` deleted before the run; OCR cache rebuilt during it).
The run completed in ~46 s cold-cache (~3 s warm) and produced
`output.csv` with sha256
`8a1a07ab0c3e01bb3d814f714e36e373941735a440a221faebfe907f967812b3`.

**The final run made zero LLM API calls.** No `ANTHROPIC_API_KEY` (or any
other provider key) was present in the environment, so request-intent
classification used the built-in rule-based classifier — exactly the
`--no-llm` path. The resulting `output.csv` is byte-identical to the
`--no-llm` run, so the submitted predictions do not depend on any model
call.

## Models
| Provider | Model | Purpose | Calls | Input tokens | Output tokens | Total tokens | Est. cost (USD) |
|---|---|---|---|---|---|---|---|
| — | none (rule-based classifier) | request-intent classification | 0 | 0 | 0 | 0 | $0.0000 |
| local | Tesseract OCR 5.5 (via pytesseract) | screenshot text extraction, 11 images | 0 LLM calls | 0 | 0 | 0 | $0 |

## Overall
| Metric | Value |
|---|---|
| Total model calls | 0 |
| Total input tokens | 0 |
| Total output tokens | 0 |
| Total tokens | 0 |
| Requests processed | 518 |
| Average tokens per request | 0 |
| Estimated total cost | $0.0000 |
| Estimated cost per request | $0.000000 |
| Cache hits (not billed) | 0 (no LLM cache used) |

## Pricing used
Not applicable — no billable model was called. If an API key is configured
(`ANTHROPIC_API_KEY`, optionally `LLM_PROVIDER` / `LLM_MODEL`, default
model `claude-haiku-4-5`), the only LLM use is batched intent
classification of the 375 unique request texts (~25 texts per call,
temperature 0, SHA-256 disk cache in `code/cache/`); token accounting for
such a run is written to `code/evaluation/usage_stats.json` by the client.
No such file exists for the final run because no call was made.

## Token-efficiency design
- All evidence parsing is deterministic local code (SQL/JSON/log/text/PDF)
  plus local OCR for images: zero tokens regardless of LLM configuration.
- The LLM, when enabled, sees only request *texts* (batched, cached),
  never evidence, and can only influence the DELETE / NON_DELETE intent —
  never resource states, steps, or citations.
- `--no-llm` produces the complete 518-row output with 0 tokens, so the
  pipeline is fully reproducible offline.
- No API keys or credentials appear in this report or anywhere in the
  submitted code; keys are read from environment variables only.
