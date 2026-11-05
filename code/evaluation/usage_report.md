# ERASIGHT Token Usage and Cost Report

This report covers the final full-dataset run that produced `output.csv` (518 requests).

## Summary
The decisions behind `output.csv` come from the deterministic engine and make **no model calls**. The optional advisory layer (`python code/advise.py --model`) asked **Groq / openai/gpt-oss-120b** for a second opinion on cases the deterministic triggers flagged. It only writes `explanations.json`; it cannot change `output.csv`. The figures below are for that single full-dataset advisory run; the mini-dataset demo is listed separately and excluded.

| Item | Value |
|---|---|
| Model providers and names used at run time | Groq: openai/gpt-oss-120b (advisory layer only) |
| Model calls | 6 |
| Input tokens | 1514 |
| Output tokens | 1757 |
| Total tokens | 3271 |
| Average tokens per request (total tokens / 518 requests) | 6.3 |
| Average tokens per model call | 545 |
| Estimated total cost | $0.0013 |
| Price assumption (USD per million tokens) | input 0.15, output 0.6 |
| Estimated cost per request | $0.000002 |

## Per-model breakdown
| Model | Calls | Input tokens | Output tokens | Total tokens | Estimated cost |
|---|---|---|---|---|---|
| Groq openai/gpt-oss-120b (full-dataset run) | 6 | 1514 | 1757 | 3271 | $0.0013 |
| **Overall (full-dataset run)** | 6 | 1514 | 1757 | 3271 | $0.0013 |

## Separate: mini-dataset demo (NOT part of the totals above)
A lookalike-email demo on the small mini dataset, used only to show the advisory layer working. 3 calls, 915 input and 670 output tokens (1585 total, about $0.0005).

## Run characteristics (measured)
| Item | Value |
|---|---|
| Requests | 518 |
| Dataset and evidence load | 0.1 s |
| Analysis of all requests | 1.1 s (2.2 ms per request) |
| Network access by the decision pipeline | None |

## Note on development tooling
The code was written with an AI coding assistant (Claude Code). That usage is development tooling, not part of the
submitted agent's run, and is recorded in the session transcript (`log.txt`) rather than measured here.
To refresh this file after a model run: `python code/advise.py --model` then `python code/evaluation/generate_reports.py`.
