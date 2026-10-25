# Ghost Data Still Exists — Deletion Audit Agent

## What it does
For each of the 518 deletion requests in `dataset/`, the agent decides
whether the request was really a deletion request, reconstructs from
evidence what personal data still existed at the case's `audit_at`, and
emits `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE` plus the ordered
finding / remediation / verification steps needed to finish the deletion
safely. Workflow claims (`reported_status`, activity `SUCCESS` results)
are never trusted as proof — every step is backed by parsed evidence, and
the cited file is one that proves the verdict.

```
deletion_requests ─► intent ─► identity ─► evidence parsers ─► fact store
   (DELETE?)        (current +   (SQL/JSON/logs/text/PDF/OCR)     │
                     historical                                  ▼
                     identifiers)              state at audit_at ─► policy
                                                              (deletion_rules)
                                                                   │
output.csv ◄─ validator ◄─ writer ◄─ planner (ordered steps) ◄─────┘
```

## Setup
Python 3.10+ (developed on 3.13). From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r code/requirements.txt
```

Optional, for screenshot OCR: install Tesseract
(`sudo apt install tesseract-ocr` on Debian/Ubuntu, `brew install
tesseract` on macOS). Without it the image parser degrades gracefully;
all other evidence is still parsed.

Optional LLM (intent classification only): `export ANTHROPIC_API_KEY=...`
(never commit keys). `LLM_PROVIDER` / `LLM_MODEL` may override the
defaults. With no key set, a rule-based classifier is used — the output
is identical.

## Run
- Full run: `python3 code/main.py` → writes `./output.csv` (518 rows)
- Deterministic, no LLM: `python3 code/main.py --no-llm`
- Debug specific cases: `python3 code/main.py --cases case_05,case_06 --debug`
- Sample evaluation: `python3 code/evaluation/evaluate.py`
- Custom cases: `python3 code/evaluation/custom_cases/run_custom_cases.py`

## Design (short)
Evidence parsers normalize every file (SQL dumps, JSON exports/bundles/
ledgers, five log dialects, text records, PDFs, OCR'd screenshots) into
timestamped facts. Identity resolution merges current and historical
emails, `sha256(email)` hashes, phones, and user ids, so records filed
under an old address are still found. State at `audit_at` uses only facts
whose own timestamp is ≤ `audit_at` (a later-exported file may contain an
earlier snapshot; citations prefer a file captured by `audit_at` that
proves the same verdict). Presence in any replica counts as remaining;
absence requires an explicit miss (404 / rows=0 / NOT_FOUND). The policy
engine applies `deletion_rules.csv` per data category (delete / redact /
anonymize / retain / retain-and-block-restore / disable-flow), including
recreation paths: active data flows and restorable backups. Steps are
ordered FINDING → REMEDIATION → VERIFICATION, then by operation, system,
and resource; `steps_json` is serialized with
`json.dumps(separators=(",", ":"))`.

Results on the 32 public samples: status accuracy 32/32, step
precision/recall/F1 0.988/0.855/0.917, evidence accuracy on matched steps
1.000 — see `code/evaluation/evaluation_report.md`.

## Repository layout
```
code/
  main.py                  entry point
  requirements.txt
  audit/                   config, loaders, identity, intent, facts,
                           activity, state, policy, planner, writer, llm
  audit/parsers/           json / sql / log / text / pdf / image parsers
  prompts/                 intent + vision prompt templates
  evaluation/              evaluate.py, tests, custom_cases/,
                           evaluation_report.md, usage_report.md
dataset/                   provided challenge data (read-only for the agent)
output.csv                 generated predictions (518 rows)
```

## Determinism & no hardcoding
Repeated full runs (warm or cold cache) produce a byte-identical
`output.csv` (sha256 in the evaluation report). No case, resource, user,
or evidence ID and no sample answer is hardcoded anywhere in `code/`
(grep-verified); ordering uses stable sorts throughout, and a shuffled
request order yields the same rows because output is re-sorted by
natural `case_id`.

## Limitations
Records carrying no identifier in any evidence file cannot be attributed
to a subject without guessing, so a small number of verification steps
are missed rather than invented (see the evaluation report). Two
requests audited in early 2026 predate all evidence for their subjects
and are reported COMPLETE with empty steps. OCR quality bounds what can
be recovered from screenshots alone.
