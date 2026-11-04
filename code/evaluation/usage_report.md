# ERASIGHT Token Usage and Cost Report

This report covers the final full-dataset run that produced `output.csv` (518 requests).

## Summary
The decisions behind `output.csv` come from the deterministic engine and make **no model calls**. The optional advisory layer (`python code/advise.py --model`) asked **Groq / openai/gpt-oss-120b** for a second opinion on cases the deterministic triggers flagged. It only writes `explanations.json`; it cannot change `output.csv`.

| Item | Value |
|---|---|
| Model providers and names used at run time | Groq: openai/gpt-oss-120b (advisory layer only) |
| Model calls | 9 |
| Input tokens | 2429 |
| Output tokens | 2427 |
| Total tokens | 4856 |
| Average tokens per request | 9.4 |
| Estimated total cost | not reported (no price supplied) |
| Estimated cost per request | not reported (no price supplied) |

## Per-model breakdown
Model: Groq openai/gpt-oss-120b

| Run | Calls | Input tokens | Output tokens |
|---|---|---|---|
| full dataset run (flagged requests) | 6 | 1514 | 1757 |
| lookalike demo on the mini dataset | 3 | 915 | 670 |
| **Overall** | 9 | 2429 | 2427 |

## Run characteristics (measured)
| Item | Value |
|---|---|
| Requests | 518 |
| Dataset and evidence load | 1.2 s |
| Analysis of all requests | 1.4 s (2.8 ms per request) |
| Network access by the decision pipeline | None |

## Note on development tooling
The code was written with an AI coding assistant (Claude Code). That usage is development tooling, not part of the
submitted agent's run, and is recorded in the session transcript (`log.txt`) rather than measured here.
To refresh this file after a model run: `python code/advise.py --model` then `python code/evaluation/generate_reports.py`.
