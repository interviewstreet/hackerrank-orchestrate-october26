# Usage report

## Final full-dataset run

The run processed 518 requests and indexed 94 participant-facing evidence files. No hosted language model or other metered AI API was called by the prediction program.

| Provider / model | Runtime calls | Input tokens | Output tokens | Estimated runtime cost |
| --- | ---: | ---: | ---: | ---: |
| Hosted LLMs | 0 | 0 | 0 | $0.00 |
| Local Tesseract.js 7.0.0, English trained data via `@tesseract.js-data/eng` 1.0.0 | 11 image-recognition calls | N/A | N/A | $0.00 API cost |
| **Overall prediction run** | **11 local OCR calls; 0 hosted model calls** | **0 token-billed** | **0 token-billed** | **$0.00 API cost** |

PDFs were text-extracted with Poppler's `pdftotext`; SQL snapshots were read by Node.js SQLite. Neither operation sends data to a model provider. The manifest contains 11 images and 4 PDFs. Tesseract input is image data and its output is extracted text, so token counts do not apply to those 11 local OCR calls.

## Token totals and averages

- LLM/API input tokens: **0**
- LLM/API output tokens: **0**
- Total token-billed tokens: **0**
- Average token-billed tokens per request: **0 / 518 = 0**
- Estimated token-based cost for the full run: **$0.00**
- Estimated token-based cost per request: **$0.00 / 518 = $0.00**

The coding assistant used during development was Codex with GPT-6, but the submitted TypeScript program does not invoke Codex. Development-session token usage is not part of this prediction-run report and is not available from the local batch process.
