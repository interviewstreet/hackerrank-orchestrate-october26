# LLM usage report

Final full-dataset run: `python3 code/main.py` (backend `replay`) over the 518 requests in `dataset/deletion_requests.csv`, producing `output.csv`. That run is served entirely from the committed LLM cache, so its marginal cost is $0; the table attributes every cached result it used to the live call that produced it (Claude subscription through `claude -p`, cost = the CLI's API-equivalent `total_cost_usd`).

- Requests processed: **518**
- Cached LLM results used by the final run: **34** unique results, served by 49 cache lookups (the visual prefetch and the extraction pass look the same result up twice; the run log's "cache hits" counts lookups). Live calls during the final run: 0
- Replay output byte-identical to the submitted `output.csv`: **True**
- Spending cap (`GDA_BUDGET_USD`): $3.00; live spend recorded in this checkout's development ledgers (`code/cache/ledger/`, all trial runs included): $1.59

| Provider | Model | Tasks | Calls | Input tokens | Output tokens | Total tokens | Cost (USD) |
|---|---|---|---|---|---|---|---|
| anthropic (claude_cli) | `claude-haiku-5-5` | intent×15 | 15 | 373,261 | 29,593 | 402,854 | $0.0594 |
| anthropic (claude_cli) | `claude-sonnet-5-5` | extract_files×4, extract_visual×15 | 19 | 858,510 | 6,968 | 865,478 | $1.3103 |
| **all** | | | **34** | **1,231,771** | **36,561** | **1,268,332** | **$1.3697** |

Direct-API estimate (`GDA_LLM_BACKEND=anthropic`, same prompts, same outputs). Input = the request's own payload: prompt characters / 4 plus the image allowance (<= 1,600 tokens per screenshot, ~2,100 per PDF page); no CLI system prompt, no prompt-cache traffic. An estimate, not a measured run.

| Model | Calls | Est. input tokens | Output tokens | Est. total tokens | Est. cost (USD) |
|---|---|---|---|---|---|
| `claude-haiku-5-5` | 15 | 27,068 | 29,593 | 56,661 | $0.0175 |
| `claude-sonnet-5-5` | 19 | 55,193 | 6,968 | 62,161 | $0.1801 |
| **all** | **34** | **82,261** | **36,561** | **118,822** | **$0.1976** |

Direct API per request: ~229.4 tokens, ~$0.00038.

Per request (518 requests, measured `claude -p` counts):

- Average tokens per request: **2,448.5** (2,377.9 in / 70.6 out)
- Estimated cost per request: **$0.00264**; estimated total: **$1.3697**

Notes:

- Intent: unique request texts are classified in batches of 25 by the `fast` alias (Claude Haiku 5.5).
- Visual evidence: each of the 15 PNG/PDF files is read once by the `vision` alias (Claude Sonnet 5.5); screenshots that print no resource id get a second, file-listing pass.
- Input token counts include prompt-cache reads/writes reported by the CLI (the CLI adds its own system prompt), which is why visual calls show large input counts at a small cost.
- Everything else (parsing, linking, state reconstruction, policy, planning) is deterministic code: 0 tokens.
- Re-running with an empty cache costs about the measured total above through `claude -p`, or about the direct-API estimate through `GDA_LLM_BACKEND=anthropic`; `GDA_BUDGET_USD` caps either (default $3.00).
- The committed cache also keeps 3 `qwen2.5vl:7b` entries: the only transcriptions of the synthetic edge-dataset screenshots (`code/evaluation/edge_cases.py run` replays them). The final run never reads them.
- Development runs are separate from these final-run figures: the ledgers record every development call, including prompt iterations whose cache entries were later pruned.
