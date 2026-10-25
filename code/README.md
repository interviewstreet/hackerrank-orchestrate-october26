# Ghost Data Still Exists audit agent

This submission uses TypeScript and Node.js to inspect deletion requests, resolve current and historical identities, index participant-facing evidence, apply the supplied deletion rules, and write the required CSV.

## Requirements

- Node.js 24.12 or newer
- npm
- Poppler's `pdftotext` on `PATH` for PDF evidence

Image evidence uses Tesseract.js with the English trained data installed through npm. The runtime does not call an external LLM or require network access after dependencies are installed.

## Install and run

From the repository root:

```bash
npm --prefix code install
npm --prefix code run dev
```

The full run reads `dataset/deletion_requests.csv` and writes `output.csv` in the repository root. Paths are resolved relative to the checkout. To generate predictions for the public sample set without replacing the final output:

```bash
npm --prefix code run dev -- --requests sample_deletion_requests.csv --output sample_predictions.csv
```

## Evaluation

Run the three participant-created checks:

```bash
npm --prefix code run evaluate:custom
npm --prefix code run validate:output
```

Compare a generated public-sample file with the participant-facing reference:

```bash
python3 code/evaluation/evaluate_samples.py --predictions sample_predictions.csv
```

The sample evaluator reports status accuracy, exact ordered-sequence accuracy, field accuracy, and step precision/recall/F1. The final public-sample metrics and the full-run usage report are in `evaluation/evaluation_report.md` and `evaluation/usage_report.md`.

## Implementation notes

- Request intent is classified before identity resolution; non-deletion requests return `NOT_APPLICABLE` with `[]`.
- Identity matching includes historical email, phone, name, and email-hash values available by `audit_at`.
- Evidence is read from the manifest and inspected as JSON, SQLite-compatible SQL, logs, text, PDFs, and images. Observations captured or recorded after `audit_at` are excluded.
- A uniquely timed account deletion event may locate a profile resource near `reported_at`; the activity result is never treated as the resulting state. A SQL profile snapshot captured afterward must establish whether that resource is present or absent. Ambiguous activity clusters are left unresolved.
- Findings and complete-case verifications cite participant-visible evidence. Proposed remediation and future verification steps have empty evidence IDs.
- Steps use the allowed operations and states, are grouped by phase, and are numbered consecutively.

## Submission packaging

Include this directory and `output.csv` separately. Do not include `dataset/`, `node_modules/`, `dist/`, trained-data cache files, or the generated `output.csv` inside the code archive. The project-root README documents a zip command and the required submission checks.
