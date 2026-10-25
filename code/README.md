# Deletion audit agent

Audits whether each deletion request in `dataset/deletion_requests.csv` was really carried out,
and writes `output.csv` (one row per case: `case_id,deletion_status,steps_json`).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional, keep it outside code/
pip install -r code/requirements.txt
export ANTHROPIC_API_KEY=...                           # read from the environment only, never stored
```

## Run

From the repository root:

```bash
python3 code/main.py                    # full run -> ./output.csv (518 rows)
python3 code/main.py --offline          # no API calls; uses the cached model answers in code/cache/
python3 code/evaluation/main.py         # sample metrics + custom cases
```

Model answers are cached in `code/cache/llm_cache.json`, keyed by a hash of the model, the prompt
version and the input bytes, so a rerun costs nothing and gives identical output. Every call that
reached the API is logged (token counts only) to `code/cache/usage_log.jsonl`; `usage_report.md`
is built from that log. Set `AUDIT_MODEL` to use a different Claude model.

## How it works

The audit is a deterministic pipeline. Claude is used only where the evidence needs reading
rather than parsing.

1. **Evidence parsing** (`audit/evidence.py`). Every manifest file becomes a list of
   observations `(file, captured_at, observed_at, system, resource, category, state, identifiers)`.
   JSON bundles and exports, flat lookup records, a text handover note, SQL snapshot dumps
   (primary, regional, reporting and failover replicas), and multi-format logs grouped by trace id
   are parsed by code. Snapshots also record *coverage* (which systems a full dump covers), so
   absence can be proven, not assumed.
2. **Screenshots and PDFs** (`audit/visual.py`). Claude transcribes each image (and each PDF's
   text layer) into a fixed JSON schema: the record reference as displayed, visible identifiers,
   which kinds of personal data are shown in clear text, and a normalized condition (exists,
   deleted, flow active/disabled, restore allowed/blocked, retained). Turning that into an audit
   state, and resolving displayed aliases (a file name, a statement number) to resource ids via
   the data-catalog link activities, is done in code.
3. **Request intent** (`audit/intent.py`). Requests that open with one of the recurring standard
   deletion phrasings are deletion requests. Free-form texts are classified by Claude as
   `ACCOUNT_DELETION` or `NOT_DELETION`; the latter become `NOT_APPLICABLE` with `[]`.
4. **Identity** (`audit/data.py`). Current and historical emails (from the identity audit log),
   their sha256 hashes, phone numbers and the user id. Matching is exact and case-insensitive;
   names are never used to link.
5. **Linking and state** (`audit/engine.py`, `audit/activity_links.py`). A resource belongs to the
   case when evidence captured inside `[requested_at, audit_at]` carries one of the subject's
   identifiers, or a catalog link activity ties it to them. Deleted accounts and already
   anonymized records carry no identifiers, so they are linked through the deletion worker's
   activity stream, matched globally across all cases that share a deletion batch. The state of
   each resource is its latest observation by `audit_at`; reported statuses and activity results
   are treated as claims, not evidence.
6. **Plan** (`audit/engine.py`). `deletion_rules.csv` gives the required treatment per category
   (delete, redact, anonymize, retain, disable flow, block restore). A case is `COMPLETE` only when
   every linked resource is in its required state; its verification steps cite the evidence that
   proves it. Otherwise findings, remediation and verification steps are emitted in the required
   phase and operation order, sorted by system and resource id, with empty evidence for proposed
   steps.

## Files

| Path | Purpose |
| --- | --- |
| `main.py` | entry point |
| `audit/evidence.py` | parsers for every evidence format |
| `audit/visual.py` | Claude prompt + schema for screenshots/PDFs, alias resolution, state mapping |
| `audit/intent.py` | Claude prompt + schema for request intent |
| `audit/llm.py` | Claude client, cache, usage ledger, pricing |
| `audit/engine.py`, `audit/activity_links.py` | linking, state at audit time, step planning |
| `audit/scoring.py` | metrics used by the evaluation |
| `evaluation/main.py` | sample scoring and custom cases |
| `evaluation/evaluation_report.md`, `evaluation/usage_report.md` | reports |
