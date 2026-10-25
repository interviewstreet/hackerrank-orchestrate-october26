# Usage report (final run)

The final run produced the submitted `output.csv`. It ran live from an **empty** cache
directory, so every model result in it was a new call. All numbers below are measured in
this run. There are no estimates.

```text
ZENMUX_CACHE_DIR=<new empty dir> python code/main.py --out output.csv --trace ... --usage ... --export-snapshot
```

| Item | Value |
| --- | --- |
| Time (UTC) | 2026-10-25 00:36:24 to 00:37:54, together with the sample run after it |
| Requests | 518 (`dataset/deletion_requests.csv`) |
| Cache | empty directory at the start: 0 cache hits, 29 live calls |
| Output | `output.csv`, SHA-256 `1d19e51212cf4e294de420928564a2869b87d91a189b09051842be19b26f786b` |
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

| Purpose | Calls | Input tokens | Output tokens | Total tokens | Latency (sum) | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| vision (11 PNG screenshots, one call each) | 11 | 46,874 | 11,463 | 58,337 | 52.7 s | 0.0069800 |
| agent (5 investigations, 18 turns) | 18 | 37,149 | 3,349 | 40,498 | 30.6 s | 0.0043847 |
| intent (ambiguous request texts) | 0 | 0 | 0 | 0 | 0 s | 0.0000000 |
| **Overall (one model)** | **29** | **84,023** | **14,812** | **98,835** | **83.3 s** | **0.0113647** |

- Cost = input x $0.10/M + output x $0.20/M.
- Retries: 0 schema, 0 transport. Fallbacks: none. Flags: none.
- Intent: the deterministic rules left 0 of the 518 request texts ambiguous, so no intent call was made.
- Agent: 5 runs (case_39, case_46, case_53, case_55, case_390), 18 turns, 3 proposals,
  2 accepted, 1 rejected (`state_mismatch`). Two runs ended at the 4-turn cap with no
  proposal. No run reached the 40,000-token case budget.

## 3. Per-request averages (518 requests)

| Metric | Value |
| --- | --- |
| Model calls per request | 29 / 518 = 0.056 |
| Tokens per request | 98,835 / 518 = 190.8 |
| Cost per request | $0.0113647 / 518 = $0.0000219 |
| Cache hits | 0 |

Most cases need no model call: deterministic code parses the evidence. Vision runs once per
screenshot, shared by all cases. The agent runs only for items that code leaves undecided.

## 4. Replay

`export-snapshot` wrote the 29 validated results to `code/llm_snapshot.py` and the 22 OCR
readings (11 images x 2 readings) to `code/ocr_snapshot.json`. Each snapshot entry keeps the
usage of the call that made it.

`ZENMUX_OFFLINE=1 python code/main.py` makes 0 network calls. Its output has the same SHA-256
as the final run (`1d19e512...786b` for the 518, `d59f689e...5e45` for the 32 samples). The
replay reports the original usage (84,023 / 14,812 tokens, $0.0113647) and 0 live tokens.

## 5. The sample run

The 32 samples ran right after the final run with the same cache: 11 calls, all cache hits
(the vision results of the same screenshots), 0 new tokens. Their stored usage is
46,874 / 11,463 tokens.

## 6. Not in this report

Development runs of earlier phases used other prompt versions. Their results are not in
the snapshot and did not produce `output.csv`.
