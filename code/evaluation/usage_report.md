# Usage Report

This report describes the final Phase 4 518-case run that generated the root `output.csv` on 2026-10-24. The run completed in approximately **235 seconds**, produced 518 sorted data rows, and returned zero contract-validation errors.

## Model Providers and Model Names

| Provider | Model | Configured purpose | Used in final run |
| --- | --- | --- | --- |
| Google | `gemini-2.5-flash` | Ambiguous request-intent classification | No |
| Google | `gemini-2.5-pro` | Vision transcription fallback when Tesseract is empty or cannot ground an identifier | No |

Clear requests are handled by deterministic multilingual rules before model fallback. Evidence is parsed locally with SQLite, JSON and regular expressions, pdfminer/pypdf, Pillow, and Tesseract. The final dataset contained no intent text left ambiguous after deterministic classification, and local OCR did not require a successful Gemini fallback. `GOOGLE_API_KEY` was not set for the final run.

## Model Call Counts

| Model | Requests | Successful calls | Failed calls | Cache hits |
| --- | ---: | ---: | ---: | ---: |
| `gemini-2.5-flash` | 0 | 0 | 0 | 0 |
| `gemini-2.5-pro` | 0 | 0 | 0 | 0 |
| **Overall** | **0** | **0** | **0** | **0** |

Intent fast-path counts were 512 deletion requests and 6 non-deletion requests. All 518 were classified deterministically.

## Input and Output Tokens

| Model | Input tokens | Output tokens |
| --- | ---: | ---: |
| `gemini-2.5-flash` | 0 | 0 |
| `gemini-2.5-pro` | 0 | 0 |
| **Overall** | **0** | **0** |

No token estimate is substituted for measured usage because no provider request occurred.

## Total and Average Tokens Per Request

- Total model tokens: **0**
- Average model tokens per dataset request: **0 / 518 = 0.00**
- Average input tokens per model request: **not applicable; zero model requests**
- Average output tokens per model request: **not applicable; zero model requests**

## Estimated Total and Per-Request Cost

- Estimated total model cost: **$0.00**
- Estimated model cost per dataset request: **$0.000000**
- Estimated cost per model request: **not applicable; zero model requests**

Local CPU work, storage, and OCR runtime are not model-provider charges and are excluded.

## Per-Model and Overall Totals

| Model | Calls | Total tokens | Estimated cost |
| --- | ---: | ---: | ---: |
| `gemini-2.5-flash` | 0 | 0 | $0.00 |
| `gemini-2.5-pro` | 0 | 0 | $0.00 |
| **Overall** | **0** | **0** | **$0.00** |

If a future run encounters ambiguous intent or ambiguous OCR and has `GOOGLE_API_KEY` configured, those calls are cached in `code/cache.json` using a SHA-256 key derived from the case ID and prompt content. That future run must replace this report with its measured provider usage before submission.
