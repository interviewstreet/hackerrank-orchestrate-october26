# ERASIGHT Token Usage and Cost Report

This report covers the final full-dataset run that produced `output.csv` (518 requests).

## Summary
**The shipped agent makes zero model calls.** It is a deterministic pipeline (rules, parsers, local `pdftotext` and `tesseract`
OCR); it does not call any language-model API, so there are no input or output tokens and no per-token cost.

| Item | Value |
|---|---|
| Model providers and names used at run time | None |
| Model calls | 0 |
| Input tokens | 0 |
| Output tokens | 0 |
| Total tokens | 0 |
| Average tokens per request | 0 |
| Estimated total cost | $0.00 |
| Estimated cost per request | $0.00 |

## Per-model breakdown
No models were used, so there is no per-model table.

## Run characteristics (measured)
| Item | Value |
|---|---|
| Requests | 518 |
| Dataset and evidence load | 1.7 s |
| Analysis of all requests | 2.0 s (3.8 ms per request) |
| Network access during the run | None |

## Note on development tooling
The code was written with an AI coding assistant (Claude Code). That usage is development tooling, not part of the
submitted agent's run, and is recorded in the session transcript (`log.txt`) rather than measured here.
If a language-model layer is added later, this file must be regenerated with its real call and token counts.
