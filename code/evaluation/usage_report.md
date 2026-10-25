# Usage Report

This report describes the final attempted 518-case run on 2026-10-25. The run accounted for every input, processed **517**, and deliberately failed closed on **1** contradictory-evidence case. It did **not** generate a fresh root `output.csv`; therefore this is a validation-run usage report, not a claim that a releasable final output was produced.

## Model Providers and Model Names

| Provider | Model | Configured purpose | Used in final attempted run |
|---|---|---|---|
| Google | `gemini-2.5-flash` | Ambiguous request-intent classification | No |
| Google | `gemini-2.5-pro` | Vision transcription fallback | No |
| Local | RapidOCR 3.10.0 with ONNX Runtime 1.23.2 | CPU screenshot OCR when Tesseract is unavailable | Yes; local non-generative inference |

`GOOGLE_API_KEY` was not configured. Clear requests were handled by deterministic multilingual authorization rules. Screenshot text was extracted locally with RapidOCR after the external Tesseract executable proved unavailable.

## Model Call Counts

| Model | Requests | Successful calls | Failed calls | Cache hits |
|---|---:|---:|---:|---:|
| `gemini-2.5-flash` | 0 | 0 | 0 | 0 |
| `gemini-2.5-pro` | 0 | 0 | 0 | 0 |
| **Generative-model overall** | **0** | **0** | **0** | **0** |

RapidOCR is local OCR and does not expose provider token accounting. Its extracted text is cached in process memory by evidence path.

## Input and Output Tokens

| Model | Input tokens | Output tokens |
|---|---:|---:|
| `gemini-2.5-flash` | 0 | 0 |
| `gemini-2.5-pro` | 0 | 0 |
| **Overall** | **0** | **0** |

No token estimate is substituted for measured usage because no provider request occurred.

## Total and Average Tokens Per Request

- Total generative-model tokens: **0**
- Average model tokens per accounted dataset request: **0 / 518 = 0.00**
- Average input tokens per model request: **not applicable; zero model requests**
- Average output tokens per model request: **not applicable; zero model requests**

## Estimated Total and Per-Request Cost

- Estimated generative-model cost: **$0.00**
- Estimated model cost per accounted request: **$0.000000**
- Local CPU OCR cost: not a model-provider charge and excluded

## Per-Model and Overall Totals

| Model | Calls | Total tokens | Estimated provider cost |
|---|---:|---:|---:|
| `gemini-2.5-flash` | 0 | 0 | $0.00 |
| `gemini-2.5-pro` | 0 | 0 | $0.00 |
| **Overall** | **0** | **0** | **$0.00** |

If a later run configures Gemini and makes provider calls, this report must be regenerated from measured usage before packaging. A package must not be represented as final until all 518 rows are evidence-supported and preflight passes.
