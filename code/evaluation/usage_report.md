# Usage report (draft)

This draft uses the **Phase 4 cold run**: the full 518-case run with an empty model cache
(`python code/main.py --usage ...`). The final numbers come from the Phase 6 full run that
produces the submitted `output.csv`.

## Model

| Item | Value |
| --- | --- |
| Provider | ZenMux (OpenAI-compatible chat completions, `https://zenmux.ai/api/v1`) |
| Model id | `meta/muse-spark-1.3-contributor` |
| Why this id | Muse Spark 1.3 was chosen for multimodal (image) input. The base id `meta/muse-spark-1.3` returned HTTP 403 for this account; the `-contributor` tier of the same model is available, so we use it. |
| Price (ZenMux list) | $0.10 / M input tokens, $0.20 / M output tokens (the base 1.3 tier: $1.25 / $4.25) |
| Settings | temperature 0, JSON-schema output, 1 schema retry, 2 transport retries |

Only one model is used, for every purpose.

## Calls and tokens per purpose (518 requests, cold cache)

| Purpose | Calls | Input tokens | Output tokens | Total tokens | Cost (USD) |
| --- | --- | --- | --- | --- | --- |
| vision (11 PNG screenshots) | 11 | 45,708 | 10,736 | 56,444 | 0.006718 |
| agent (3 investigations, 11 turns) | 11 | 19,652 | 3,051 | 22,703 | 0.002575 |
| intent (ambiguous request texts) | 0 | 0 | 0 | 0 | 0.000000 |
| **Overall** | **22** | **65,360** | **13,787** | **79,147** | **0.009293** |

- Intent: 0 calls, because the deterministic intent rules left 0 of the 518 texts ambiguous.
- Retries: 0 schema retries, 0 transport retries. Fallbacks: none.
- Cost = input x $0.10/M + output x $0.20/M.

## Per-request averages (518 requests)

| Metric | Value |
| --- | --- |
| Model calls per request | 22 / 518 = 0.042 |
| Tokens per request | 79,147 / 518 = 152.8 |
| Cost per request | $0.0092934 / 518 = $0.0000179 |

Most cases need no model call: evidence is parsed by deterministic code. Vision runs once
per screenshot (shared by all cases), and the agent runs only for undecided items.

## Replay runs

Later runs read the cache or `code/llm_snapshot.py` (validated model output only):
`ZENMUX_OFFLINE=1 python code/main.py` makes 0 network calls and gives the same output hash.

## Development calls in Phase 5 (not part of the final run)

- Vision prompt v2 (`vision_extract_v2`): 11 new vision calls, 46,874 input / 11,760 output
  tokens (about $0.0070).
- One agent investigation for case_61 during step A: 4 calls.

These are cached; the Phase 6 cold run will report the final totals.
