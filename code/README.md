# Ghost Data Still Exists: deletion-audit agent

For every request in `dataset/deletion_requests.csv` the agent decides whether the person
asked for deletion. For a deletion request it finds the subject's current and historical
identifiers, links the records that belong to the subject, reconstructs each copy's state at
`audit_at`, applies `deletion_rules.csv`, and writes `output.csv`
(`case_id,deletion_status,steps_json`): `COMPLETE` with evidence-backed verification steps,
`INCOMPLETE` with findings, an ordered remediation plan and verification checks, or
`NOT_APPLICABLE` with `[]`.

## Architecture: the model reads and proposes, code decides

```text
request text --> intent (rules; model label only for ambiguous texts)
             --> identity (current snapshot + audit log, as of audit_at)
             --> links (strong identifier / catalog edges; medium heuristics, flagged)
             --> resolver (state per physical copy, newest admissible statement wins)
             --> policy (deletion_rules.csv: compliant / violation / unproven / retained)
             --> citation (strongest tier, then newest evidence)
             --> planner (status + ordered FINDING / REMEDIATION / VERIFICATION steps)
             --> output.csv (strict validation before success)
```

- Deterministic extractors parse SQL snapshots, JSON, logs, text records, PDFs (pypdf) and
  `system_activity.csv` into one fact store with a time cutoff.
- The model (ZenMux, `meta/muse-spark-1.3-contributor`) is used for three things only:
  reading PNG screenshots (vision rows), labeling request texts the rules find ambiguous, and
  the investigator agent below. Every model result is validated by `schema.py`. A vision row
  is kept only when Tesseract OCR of the same image grounds its id, state cue and identifier
  in one layout block. The model never sets a status or writes a step.
- Rule ids and required actions come from `deletion_rules.csv` (`policy.bind_rules`).

See `DESIGN.md` for the module list, the policy readings and the failure-mode guards.

## The investigator agent loop

It runs only for an item that code leaves undecided (no admissible statement, or a conflict).
In the final run (round 5) code decides every item, so the agent makes 0 calls; the loop stays
for data where code cannot decide.

- Tools: `search_evidence` (BM25 over evidence visible at `audit_at`), `read_evidence`,
  `query_facts`, `submit_proposal`, `stop`. One tool call per turn.
- Caps: 4 turns per item (`config.AGENT_MAX_ITERATIONS`), 40,000 tokens per case
  (`config.AGENT_TOKEN_BUDGET`), 1 schema retry and 2 transport retries per call.
- A proposal is a STATE (the record's state) or a LINK (the record belongs to the subject).
  Code accepts it only when every cited file was opened in this loop and exists at
  `audit_at`, a quote names the resource (and, for LINK, a subject identifier), and the
  state matches the parsed rows of the cited file. An accepted proposal only adds an
  observation or a medium edge; the resolver and the policy still decide.

## Safety

- Request texts and OCR text are screened for injection patterns before any model call; a
  hit is never sent. Data goes to the model inside delimiters as data.
- Policy invariants in code: a retained category is never deleted; a record linked only to
  another user is never acted on; a missing identifier link gives no step (ids are never
  invented).
- Evidence after `audit_at` is never used or cited.
- The API key is read from the environment or `.env` only, and is never printed, logged,
  traced or cached. `code/llm_snapshot.py` holds validated model output only.

## Setup

Python 3.11 or newer.

```text
python -m venv .venv
.venv/Scripts/activate            (Windows)   |   source .venv/bin/activate   (macOS / Linux)
python -m pip install -r code/requirements.txt
```

Directory layout (run every command from the directory that holds `code/`):

```text
<root>/
  code/        this folder
  dataset/     the challenge dataset (deletion_requests.csv, evidence/, ...)
  .env         optional, copied from .env.example
```

For live model calls copy `.env.example` to `.env` and set `ZENMUX_API_KEY`. With no key the
run replays the snapshot (below).

Tesseract OCR is optional. `code/ocr_snapshot.json` holds the OCR readings of the 11 dataset
screenshots at 2x scale (keyed by image SHA-256, reading and scale). Tesseract and Pillow are
needed only for images that are not in the snapshot; without Tesseract such an image gives
no vision rows.

## Run

```text
python code/main.py                       # dataset/deletion_requests.csv -> <root>/output.csv
python code/main.py --requests dataset/sample_deletion_requests.csv --out sample_output_pred.csv
```

Options: `--trace PATH` (per-case JSONL trace), `--usage PATH` (model usage JSON),
`--offline`, `--no-vision`, `--no-agent`, `--no-llm`, `--export-snapshot`.

Every row is always written. A case that raises gets a conservative row and is listed in
`<out>_failures.csv`. The exit code is 1 when any case failed or the strict contract check of
the written file fails.

## Offline replay

```text
ZENMUX_OFFLINE=1 python code/main.py      (PowerShell: $env:ZENMUX_OFFLINE="1"; python code/main.py)
```

Replay makes no network call. It reads `code/llm_snapshot.py` (34 validated results; the final
run uses 11 of them) and `code/ocr_snapshot.json`, and gives the same `output.csv` as the final run:
SHA-256 `c40d985c1b510d5e8f891ce00ef3e71fecce0b7db9b62a1fa54840a477df9bff`.

## Evaluation

```text
python code/evaluation/main.py            # sample scores, 7 custom cases, 19 metamorphic checks
python code/validate.py output.csv        # strict contract check
python -m pytest code/tests               # 190 tests (they always replay; no network)
python code/package.py                    # builds code.zip with a secret scan
```

Reports: `evaluation/evaluation_report.md` and `evaluation/usage_report.md`.

## Known limits

- Records linked to the subject only by a worker claim in `system_activity.csv` get no step
  (the main recall loss on the samples: 28 of 193 gold steps).
- OCR misreads drop some vision rows that the image supports (1 of 24 in the final run).
- A legal hold with no stated status and no end date counts as active (rule_13 text: "A supplied
  legal hold is active"), and a catalog link of a tombstone to an email counts as an exposure
  (rule_15). No sample tests these two readings (evaluation report, section 17).
- A new live run can give different model output (seen once on a screenshot); the snapshot
  fixes the submitted output.
- Rules that rest on few samples are listed in the evaluation report, section 13.
