# Usage report (final run)

The final run produced the submitted `output.csv` (round 5, after the four fixes in
`evaluation_report.md` section 17). All numbers below are measured. There are no estimates.

The run used a **new** cache directory, seeded with the 34 validated results of
`code/llm_snapshot.py` (the round-4 snapshot). A call whose prompt did not change is a cache hit
and reports the usage of the call that made it. A call whose prompt changed would go live; in
this run no call went live.

```text
ZENMUX_CACHE_DIR=<new dir seeded from llm_snapshot.py> python code/main.py --out output.csv --trace ... --usage ... --export-snapshot
```

| Item | Value |
| --- | --- |
| Time (UTC) | 2026-10-25 06:37:26 to 06:37:30, together with the sample run after it |
| Requests | 518 (`dataset/deletion_requests.csv`) |
| Cache | seeded with 34 results: 11 calls, 11 cache hits, 0 live calls |
| Output | `output.csv`, SHA-256 `c40d985c1b510d5e8f891ce00ef3e71fecce0b7db9b62a1fa54840a477df9bff` |
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
| agent | 0 | 0 | 0 | 0 | 0 s | 0.0000000 |
| intent (ambiguous request texts) | 0 | 0 | 0 | 0 | 0 s | 0.0000000 |
| **Overall (one model)** | **11** | **46,874** | **11,463** | **58,337** | **52.7 s** | **0.0069800** |

New (live) calls in this run: **0** (0 input tokens, 0 output tokens, $0).

- Cost = input x $0.10/M + output x $0.20/M.
- Retries: 0 schema, 0 transport. Fallbacks: none. Flags: none.
- Intent: the deterministic rules left 0 of the 518 request texts ambiguous, so no intent call was made.
- Vision: the round-5 fixes do not change the vision prompt, so all 11 calls are cache hits.
- Agent: 0 runs. In round 4 the agent ran on 4 items (case_46, case_53, case_55, case_390,
  15 turns). The round-5 fixes decide these 4 items in code, so no item is left undecided and
  the agent does not run. The 15 agent results stay in the snapshot, unused.
- Total spend for the submitted output: the cold run ($0.0113647, 29 calls), the round-4 live
  calls ($0.0012823, 5 calls) and this run ($0), $0.0126470 in all.

## 3. Per-request averages (518 requests)

| Metric | Value |
| --- | --- |
| Model calls per request | 11 / 518 = 0.021 |
| Tokens per request | 58,337 / 518 = 112.6 |
| Cost per request | $0.0069800 / 518 = $0.0000135 |
| Live tokens per request | 0 / 518 = 0 |
| Live cost per request | $0 |

Most cases need no model call: deterministic code parses the evidence. Vision runs once per
screenshot, shared by all cases. The agent runs only for items that code leaves undecided.

## 4. Replay

`export-snapshot` wrote 34 validated results to `code/llm_snapshot.py`: the 11 that this run
used and 23 results of earlier runs that it no longer uses (the snapshot merge keeps them).
The file did not change. It also wrote the 22 OCR readings (11 images x 2 readings, at 2x
scale) to `code/ocr_snapshot.json`, also unchanged. Each snapshot entry keeps the usage of the
call that made it.

`ZENMUX_OFFLINE=1 python code/main.py` makes 0 network calls. Its output has the same SHA-256
as the final run (`c40d985c...9bff` for the 518, `d59f689e...5e45` for the 32 samples). The
replay reports the stored usage (46,874 / 11,463 tokens, $0.0069800) and 0 live tokens.

## 5. The sample run

The 32 samples ran right after the final run with the same cache: 11 calls, all cache hits
(the vision results of the same screenshots), 0 new tokens. Their stored usage is
46,874 / 11,463 tokens.

## 6. Not in this report

Development runs of earlier phases used other prompt versions. Their results are not in
the snapshot and did not produce `output.csv`.
