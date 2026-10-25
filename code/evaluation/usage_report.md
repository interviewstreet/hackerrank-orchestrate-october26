# Usage report: final full-dataset run

This covers the run that produced the submitted `output.csv` (`python3 code/main.py`, 24 Oct 2026).
The token counts come from `response.usage` of every API call, logged to `code/cache/usage_log.jsonl`
(`python3 code/evaluation/usage.py` prints these tables from that log).

## Where the model is used

| Purpose | Inputs sent | Calls |
| --- | --- | ---: |
| `visual_extraction` | each screenshot (11 PNGs, as base64 images) and the text layer of each PDF (4) | 15 |
| `intent_classification` | each request text that does not open with a recurring standard deletion phrasing (33 of the 550 sample and test requests) | 33 |

Everything else (parsing JSON, SQL, logs and text, identity resolution, linking, state at
`audit_at`, policy, step planning) is deterministic code and makes no model calls. 517 of the
550 request texts are classified by rule, without the model.

All calls use structured outputs (`output_config.format` with a JSON schema) and `effort: "low"`.

## Totals

| Provider | Model | Purpose | Calls | Input tokens | Output tokens | Avg tokens / call | Cost (USD) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Anthropic | `claude-opus-5-5` | intent_classification | 33 | 18,057 | 2,372 | 619 | 0.1197 |
| Anthropic | `claude-opus-5-5` | visual_extraction | 15 | 50,938 | 4,885 | 3,722 | 0.3015 |
| Anthropic | `claude-opus-5-5` | **model total** | **48** | **68,995** | **7,257** | **1,589** | **0.4211** |

Only one model was used, so the per-model total is also the overall total.

| Overall | Value |
| --- | ---: |
| Model calls | 48 |
| Input tokens | 68,995 |
| Output tokens | 7,257 |
| Total tokens | 76,252 |
| Average tokens per model call | 1,589 |
| Average tokens per request (518 test requests) | 147 |
| Estimated total cost | $0.42 |
| Estimated cost per request (518 test requests) | $0.00081 |

The per-request averages divide the whole run by the 518 test requests. The run also
classified the free-form texts of the 32 sample requests, because linking is done globally
over all requests. Spread over all 550 requests, the averages are 139 tokens and $0.00077.

## Pricing used

`claude-opus-5-5`: $4.00 per million input tokens, $20.00 per million output tokens (Anthropic list
price). No prompt caching or batch discount was applied in the estimate.

## Reruns

Answers are cached in `code/cache/llm_cache.json`, keyed by sha256 of model, prompt version and
input bytes. A rerun on the same dataset makes 0 calls and produces the same `output.csv`; only new
or changed evidence files or request texts are sent to the model. Switching to `claude-haiku-5-5`
(`AUDIT_MODEL=claude-haiku-5-5`) would cost about $0.01 for the same token volume, but it was not
evaluated.
