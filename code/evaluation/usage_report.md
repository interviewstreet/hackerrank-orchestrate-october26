# Usage report (final run)

The final run produced the submitted `output.csv` (round 4, after the OCR change in
`evaluation_report.md` section 16). All numbers below are measured. There are no estimates.

The run used a **new** cache directory, seeded with the 29 validated results of the previous
final run (a cold run from an empty cache, 2026-10-25 00:36 UTC). A call whose prompt did not
change is a cache hit and reports the usage of the call that made it. A call whose prompt
changed went live.

```text
ZENMUX_CACHE_DIR=<new dir seeded from llm_snapshot.py> python code/main.py --out output.csv --trace ... --usage ... --export-snapshot
```

| Item | Value |
| --- | --- |
| Time (UTC) | 2026-10-25 06:01:22 to 06:01:40, together with the sample run after it |
| Requests | 518 (`dataset/deletion_requests.csv`) |
| Cache | seeded with 29 results: 26 calls, 21 cache hits, 5 live calls |
| Output | `output.csv`, SHA-256 `4a1d1c3f23303ab9f0891fd5ddd15d40ba7861b5f037538130f17187a4aaa132` |
| Exit code | 0 (0 failed cases, strict validation 0 errors) |

## 1. Model

| Item | Value |
| --- | --- |
| Provider | ZenMux (OpenAI-compatible chat completions, `https://zenmux.ai/api/v1`) |
| Model id | `meta/muse-spark-1.3-contributor` |
| Why this id | Muse Spark 1.3 was chosen for image input. The base id `meta/muse-spark-1.3` returned HTTP 403 for this account; the `-contributor` tier of the same model is available, so we use it. |
| Price (ZenMux model list, 2026-10-24) | $0.10 / M input tokens, $0.20 / M output tokens |
| Settings | temperature 0, JSON output validated by `schema.py`, 1 schema retry, 2 transport retries |
| Prompts | `vision_extract_v3`, `agent_v2`, `intent_v1` |

One model is used for every purpose, so the per-model totals are the overall totals.

## 2. Calls and tokens per purpose (518 requests)

Usage of every call in the run (a cache hit counts the usage of the call that made it):

| Purpose | Calls | Input tokens | Output tokens | Total tokens | Latency (sum) | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| vision (11 PNG screenshots, one call each) | 11 | 46,874 | 11,463 | 58,337 | 52.7 s | 0.0069800 |
| agent (4 investigations, 15 turns) | 15 | 32,294 | 2,602 | 34,896 | 26.6 s | 0.0037498 |
| intent (ambiguous request texts) | 0 | 0 | 0 | 0 | 0 s | 0.0000000 |
| **Overall (one model)** | **26** | **79,168** | **14,065** | **93,233** | **79.3 s** | **0.0107298** |

New (live) calls in this run:

| Purpose | Live calls | Input tokens | Output tokens | Total tokens | Cost (USD) |
| --- | --- | --- | --- | --- | --- |
| vision | 0 | 0 | 0 | 0 | 0.0000000 |
| agent | 5 | 10,639 | 1,092 | 11,731 | 0.0012823 |
| **Overall** | **5** | **10,639** | **1,092** | **11,731** | **0.0012823** |

- Cost = input x $0.10/M + output x $0.20/M.
- Retries: 0 schema, 0 transport. Fallbacks: none. Flags: none.
- Intent: the deterministic rules left 0 of the 518 request texts ambiguous, so no intent call was made.
- Vision: the OCR change does not change the vision prompt, so all 11 calls are cache hits.
- Agent: the OCR text is part of the agent tool results, so 5 agent turns changed and went
  live. 4 runs (case_46, case_53, case_55, case_390), 15 turns, 2 proposals, 2 accepted,
  0 rejected. Two runs ended at the 4-turn cap with no proposal. No run reached the
  40,000-token case budget. case_39 no longer needs the agent.
- Total spend for the submitted output: the previous cold run ($0.0113647, 29 calls) plus the
  5 live calls of this run ($0.0012823), $0.0126470 in all.

## 3. Per-request averages (518 requests)

| Metric | Value |
| --- | --- |
| Model calls per request | 26 / 518 = 0.050 |
| Tokens per request | 93,233 / 518 = 180.0 |
| Cost per request | $0.0107298 / 518 = $0.0000207 |
| Live tokens per request | 11,731 / 518 = 22.6 |
| Live cost per request | $0.0012823 / 518 = $0.0000025 |

Most cases need no model call: deterministic code parses the evidence. Vision runs once per
screenshot, shared by all cases. The agent runs only for items that code leaves undecided.

## 4. Replay

`export-snapshot` wrote 34 validated results to `code/llm_snapshot.py`: the 26 that this run
used and 8 results of the previous run that it no longer uses (the snapshot merge keeps
them). It also wrote the 22 OCR readings (11 images x 2 readings, at 2x scale) to
`code/ocr_snapshot.json`. Each snapshot entry keeps the usage of the call that made it.

`ZENMUX_OFFLINE=1 python code/main.py` makes 0 network calls. Its output has the same SHA-256
as the final run (`4a1d1c3f...a132` for the 518, `d59f689e...5e45` for the 32 samples). The
replay reports the stored usage (79,168 / 14,065 tokens, $0.0107298) and 0 live tokens.

## 5. The sample run

The 32 samples ran right after the final run with the same cache: 11 calls, all cache hits
(the vision results of the same screenshots), 0 new tokens. Their stored usage is
46,874 / 11,463 tokens.

## 6. Not in this report

Development runs of earlier phases used other prompt versions. Their results are not in
the snapshot and did not produce `output.csv`.
