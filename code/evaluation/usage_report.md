# Usage report (Phase 6 final run)

The final full run produced the submitted `output.csv`:

```text
python code/main.py --out output.csv --trace ... --usage ... --export-snapshot
```

It ran in live mode with the model cache from earlier phases. 26 of its 30 model results
came from the cache, and 4 were new live calls. Section 3 gives the tokens billed in this
run. Section 2 gives the cold-cache cost of all 30 results that the run used.

## 1. Model

| Item | Value |
| --- | --- |
| Provider | ZenMux (OpenAI-compatible chat completions, `https://zenmux.ai/api/v1`) |
| Model id | `meta/muse-spark-1.3-contributor` |
| Why this id | Muse Spark 1.3 was chosen for multimodal (image) input. The base id `meta/muse-spark-1.3` returned HTTP 403 for this account; the `-contributor` tier of the same model is available, so we use it. |
| Price (ZenMux list) | $0.10 / M input tokens, $0.20 / M output tokens (the base 1.3 tier: $1.25 / $4.25) |
| Settings | temperature 0, JSON-schema output, 1 schema retry, 2 transport retries |

Only one model is used, for every purpose. So the per-model totals equal the overall totals.

## 2. Calls and tokens per purpose (518 requests, cold-cache equivalent)

| Purpose | Calls | Input tokens | Output tokens | Total tokens | Cost (USD) | Source of the numbers |
| --- | --- | --- | --- | --- | --- | --- |
| vision (11 PNG screenshots, prompt v2) | 11 | 46,874 | 11,760 | 58,634 | 0.007039 | measured when the cached v2 results were made (Phase 5) |
| agent: case_39, case_46, case_55 (11 turns) | 11 | 19,652 | 3,051 | 22,703 | 0.002575 | measured in the Phase 4 cold run (prompt `agent_v1`, unchanged) |
| agent: case_390 (4 calls, 1 schema retry) | 4 | 17,127 | 3,099 | 20,226 | 0.002333 | measured in this run (live) |
| agent: case_61 (4 calls) | 4 | ~17,127 | ~3,099 | ~20,226 | ~0.002333 | **estimate**: tokens were not recorded in Phase 5; set equal to case_390 |
| intent (ambiguous request texts) | 0 | 0 | 0 | 0 | 0.000000 | the rules left 0 of the 518 texts ambiguous |
| **Overall (one model)** | **30** | **~100,780** | **~21,009** | **~121,789** | **~0.014280** | |

- Cost = input x $0.10/M + output x $0.20/M.
- Retries: 1 schema retry (case_390), 0 transport retries. Fallbacks: none. Flags: none.
- The cache stores validated results only, not token counts. This is why the case_61 row is an estimate.

## 3. Tokens billed in the final run

| Metric | Value |
| --- | --- |
| Model calls | 30 (26 cache hits, 4 live) |
| Input / output tokens billed | 17,127 / 3,099 (all from the 4 live agent calls, case_390) |
| Total tokens billed | 20,226 |
| Cost billed | $0.0023325 |

## 4. Per-request averages (518 requests)

| Metric | Cold-cache equivalent | Billed in the final run |
| --- | --- | --- |
| Model calls per request | 30 / 518 = 0.058 | 4 / 518 = 0.008 (live) |
| Tokens per request | ~121,789 / 518 = ~235.1 | 20,226 / 518 = 39.0 |
| Cost per request | ~$0.01428 / 518 = ~$0.0000276 | $0.0023325 / 518 = $0.0000045 |

Most cases need no model call: deterministic code parses the evidence. Vision runs once
per screenshot (shared by all cases). The agent runs only for undecided items (5 runs on
the 518: 4 proposals, 2 accepted, 2 rejected `state_mismatch`, 1 stop).

## 5. Replay runs

Later runs read the cache or `code/llm_snapshot.py` (validated model output only):
`ZENMUX_OFFLINE=1 python code/main.py` makes 0 network calls. Its output has the same
SHA-256 as the final live run (`4f63cd85...e590` for the 518, `d59f689e...5e45` for the samples).

## 6. Development calls (not part of the final run)

- Phase 5: vision prompt v2 (11 calls, 46,874 / 11,760 tokens) and one agent investigation
  for case_61 (4 calls). Both results are reused by the final run (section 2).
- Phase 6: the 4 live calls of section 3 were the only new calls.
