# Ghost Data Still Exists — deletion-audit agent

HackerRank Orchestrate (October 2026). For each request in `dataset/deletion_requests.csv` the agent decides
whether deletion was authorized, reconstructs the subject's identifiers, finds every copy of their data at
`audit_at`, applies `deletion_rules.csv`, and writes `COMPLETE` / `INCOMPLETE` / `NOT_APPLICABLE` with an ordered
FINDING → REMEDIATION → VERIFICATION plan to `output.csv`.

Challenge contract: `problem_statement.md` (organizer file in the challenge repository, not shipped in `code.zip`) · Design spec: [`code/docs/SPEC.md`](./code/docs/SPEC.md) ·
Results: [`code/evaluation/evaluation_report.md`](./code/evaluation/evaluation_report.md),
[`code/evaluation/usage_report.md`](./code/evaluation/usage_report.md)

## Quick start (no API key needed)

Requirements: Python ≥ 3.10, standard library only (SQLite ships with Python).

```bash
python3 code/main.py                    # 518 requests -> ./output.csv   (~12 s)
python3 code/main.py --cases sample     # 32 public samples -> ./sample_predictions.csv
python3 code/evaluation/main.py         # metrics + regenerate both reports (~1.5 min)
python3 code/evaluation/check_all.py    # quality gate: tests, sample regression, invariants, 11 checks (~40 s)
python3 -m unittest discover -s code/tests -t code   # 32 unit + 31 end-to-end tests (25 scenarios + 6 evidence-safety tests)
python3 code/package.py                 # build code.zip (README.md + code/ + evaluation/ report copies, no dataset)
```

The default backend is `replay`: every LLM result the pipeline needs is committed in `code/cache/llm_cache.jsonl`,
so a clean clone reproduces `output.csv` byte-for-byte with no network access and no key.

## Running the LLM live

| `GDA_LLM_BACKEND` | What it does | Needs |
|---|---|---|
| `replay` (default) | committed cache only; on a miss, falls back to the deterministic heuristic | nothing |
| `offline` | ignores the LLM cache; heuristic intent; screenshots/PDFs only through the OCR fallback (findings only) | nothing |
| `claude_cli` | `claude -p --output-format json` with the logged-in Claude subscription (used for development and for producing the cache) | `claude` CLI logged in |
| `anthropic` | Anthropic Messages API through the official SDK | `pip install anthropic`, `ANTHROPIC_API_KEY` |
| `openai` | OpenAI Chat Completions through the official SDK | `pip install openai`, `OPENAI_API_KEY`, `GDA_PRICE_OVERRIDE_<ALIAS>="in,out"` |
| `ollama` | Local (or `:cloud`) models through the Ollama HTTP API, $0 for local models. Defaults: `qwen3:8b` for intent, `qwen2.5vl:7b` for vision (override with `GDA_MODEL_FAST` / `GDA_MODEL_VISION`). JSON mode, thinking off, temperature 0, seed 7. PDFs are sent as page images rendered by `pdftoppm`. Results are cached under their own `ollama:<model>` key; in replay the Sonnet entries win | Ollama server (`OLLAMA_HOST`, default `http://127.0.0.1:11434`) with the models pulled; `poppler-utils` for PDFs |

Other settings: `GDA_MODEL_FAST` (default `claude-haiku-5-5`, intent), `GDA_MODEL_VISION` (default `claude-sonnet-5-5`,
PNG/PDF evidence), `GDA_VISION` (default `1`; `0` never calls a vision model, so screenshots/PDFs are read by OCR or stay
unread), `GDA_LLM_CACHE` / `GDA_OCR_CACHE` (other LLM / OCR cache files, for experiments that must not touch the committed ones),
`GDA_VISION_GROUNDING` (default `1`: drop vision-model records that the image's OCR text does not
show), `GDA_VISION_OCR_FALLBACK` (default `1`: read a screenshot/PDF by OCR when no vision result exists; such records
can only report what is still there, never prove absence), `GDA_BUDGET_USD` (default `3.00`, `0` = cache only), `GDA_BUDGET_SCOPE` (`total` | `run`),
`GDA_BUDGET_ON_EXCEED` (`fallback` | `abort`, exit code 3), `GDA_STRICT_EVIDENCE` (default `1`: exit code 4, after writing every row, when a
screenshot/PDF captured during a request could not be read and that request's COMPLETE verdict could depend on it;
`0` accepts such verdicts). Secrets are read from the environment only; keep them
in an uncommitted `.env` and `export` them. Example: `GDA_LLM_BACKEND=claude_cli python3 code/main.py`.

CLI options of `code/main.py`: `--dataset-dir DIR`, `--requests FILE`, `--out PATH`, `--trace-dir DIR` (one JSON
decision trace per case: identifiers, owned resources, how each was linked, the observations and the rule applied),
`--backend NAME`, `--workflow-model PATH`, `--relearn-workflow-model`, `-v`.

Exit codes (named constants `EXIT_*` in `code/ghostaudit/config.py`): `0` ok · `1` dataset input missing (one-line message naming the files) · `2` output failed contract
validation · `3` budget exceeded with `GDA_BUDGET_ON_EXCEED=abort` · `4` a COMPLETE verdict rests on unread
visual evidence (default; `GDA_STRICT_EVIDENCE=0` to accept). Rows are sorted by `case_id` in natural order (`case_99` before `case_100`), which is the order of
`deletion_requests.csv`; graders that join on `case_id` are unaffected either way. CSV inputs saved with a UTF-8 byte-order mark (spreadsheet exports) are accepted. Emails and names are matched after Unicode NFKC normalisation and casefolding, and manifest paths that point outside `--dataset-dir` are skipped.

## How it works

```
dataset/ ─► loaders ─► IdentityResolver (current + historical email/phone/hash, user_id)
             │
             ├─► evidence extractors ─► ObservationStore  (facts, never judgements)
             │     SQL snapshots (typed tables + JSON-in-table replicas, via sqlite3) · JSON bundles / service
             │     exports / ledgers · handover TXT · 5 log layouts joined by trace id · activity stream ·
             │     PNG/PDF via a cached vision-LLM transcription, checked against local OCR (cached)
             │
             ├─► IntentClassifier (LLM, batched + cached; multilingual heuristic fallback)
             │
             └─► per case, as of audit_at:
                   1. ownership: identifier links + deletion-workflow links
                   2. state: latest observation ≤ audit_at (replicas: most exposing location wins;
                      sync/restore "repopulated" events re-create; inferred snapshot absence only as a fallback)
                   3. policy: data category → DELETE / REDACT / ANONYMIZE / RETAIN / block restore / disable flow
                   4. plan: findings + ordered remediation (flows/restores first) + verification, with citations
                 ─► serializer + contract validator ─► output.csv
```

- **The LLM never chooses steps.** It only (a) labels request intent and (b) transcribes the 15 screenshots/PDFs into
  typed records. Prompts: `code/ghostaudit/llm/prompts/*.md`; the visual transcriptions are auditable in the cache.
- **Claims are not proof.** Workflow results (`DELETE_RECORD SUCCESS`, `reported_status`) never decide a state;
  readbacks, snapshots, check events and recreation events do.
- **Workflow linking.** Profile deletions and successful policy actions in `system_activity.csv` usually carry no
  identifier (a 404 account, an anonymized analytics profile). The deletion worker runs each request's steps on a
  fixed sub-minute cadence after the profile deletion; that cadence is learned from workflows whose resources are
  identifier-linked (`code/cache/workflow_model.json`) and used to attach un-linked steps and to assign each
  profile deletion to exactly one request by elimination — only with information available at the case's `audit_at`.
  Timing is never enough on its own: a request whose email resolves to no known person gets no workflow link.
- **Vision output is grounded.** Every record the vision model returns must be visible in a local OCR reading of the
  same image (Tesseract for screenshots, `pdftotext`/`pdftoppm` for PDFs), tolerant of OCR slips (`_` read as a space,
  Cyrillic look-alikes, one or two misread characters). An ID the OCR text doesn't show is dropped; an email or phone it
  doesn't show is removed from the record. OCR text is cached by file sha256 in `code/cache/ocr_cache.jsonl`, so the
  check is reproducible without Tesseract installed; with no OCR text nothing is dropped. On the 15 real images 34/34
  Sonnet records are grounded; on the edge screenshots it drops the IDs a local VLM invented (`export_001/002`).
  Optional tools: `sudo apt install tesseract-ocr tesseract-ocr-rus poppler-utils`.
- **Unread evidence is never silent.** If a screenshot/PDF cannot be transcribed (empty cache, no vision backend), or a
  file listed in `evidence_files.csv` is missing,
  every COMPLETE verdict of a request during which it was captured is marked `unverified_evidence` in its trace,
  counted on stderr, and the run exits 4 (opt out with `GDA_STRICT_EVIDENCE=0`). When the file's OCR text is known
  and shows none of the person's identifiers or resource ids, it is about somebody else and does not count for that
  request (`unread_evidence_about_others` in the trace); with no OCR text it counts for every request in the window.
- **No time travel.** Every observation, activity and cross-case elimination is cut at `audit_at`; the invariant
  suite re-runs cases with later evidence physically deleted and requires identical rows. One narrow exception: a
  retained record (e.g. a security audit event) that appears only in a file *exported* after the audit, inside a
  snapshot or on a log line *taken* at or before `audit_at`, existed at the audit. It adds an uncited post-remediation
  `VERIFY_RECORD_PRESENT` to an INCOMPLETE case. It is never cited, never a finding, and never changes a status.

## Evaluation (details in the report)

| Measure | Result |
|---|---|
| Sample status accuracy (dev / holdout) | 100% / 100% |
| Sample step F1 · exact sequence | 97.4% · 84.4% (holdout 100%); the rest are 2 audit records absent from every file and 3 hand-written accounts |
| Intent: own 62-text multilingual set + 32 samples (LLM) | 100% accuracy, NON_DELETE recall 100% |
| Custom end-to-end scenarios | 25 / 25 |
| Vision records grounded by local OCR (15 real + 3 edge images) | 38 / 38 |
| Invariants on the 518-case run | contract, citations ≤ audit_at, policy sanity, determinism, identifier invariance, time travel, visual grounding: all pass |
| LLM cost to build the cache used by the final run | ≈ $1.37 (34 calls via `claude -p`; ≈ $0.20 estimated via the direct API), $0 marginal for replay runs |

## Repository layout

```
code/main.py                 CLI entry point
code/ghostaudit/             pipeline: models, loaders, identity, intent, evidence/, llm/, engine/, output
code/cache/                  committed LLM cache + frozen workflow model
code/evaluation/             scorer, invariants, harness, check_all gate, intent set, reports
code/tests/                  unit tests + e2e scenario builder (miniature datasets in every evidence format)
code/docs/SPEC.md            design spec and decisions
```

Submission link: https://wwww.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
