# Ghost Data Still Exists — implementation design

Working plan for the solution in `code/`. The narrative design (goal, tables, worked
examples, edge cases, scale) lives in the design page; this file is the build plan the
code follows. Keep it current: when a milestone lands, tick it and note what changed.

## 1. Shape of the solution

Batch job, two phases, no per-case file reads.

```
startup (once per run, skipped when cache/tables.sqlite is fresh)
  dataset/*.csv + dataset/evidence/** ──► tables: files, identities, observations, activities
                                        ──► cache/tables.sqlite

per case (518 times, dictionary lookups only)
  1 intent → 2 subject → 3 discovery → 4 state → 5 policy → 6 write
  outputs: output.csv, review.jsonl, usage.json
```

Principles, in priority order: accuracy, then cost, then latency. Rules before models.
Every model call cached. Deterministic output: fixed sort keys, no set iteration on
output paths, `json.dumps(..., separators=(",", ":"))` with keys in contract order.

## 2. Package layout

```
code/
  main.py                      entry point: python3 code/main.py [--limit N] [--no-cache] [--offline]
  ghost/
    __init__.py
    config.py                  paths, env vars, enums, constants (operation order, status map)
    logging_setup.py           one logger, stage timers, log file under cache/
    errors.py                  ParseError, LinkageAmbiguous, ModelUnavailable
    models.py                  dataclasses: Request, Subject, Observation, Activity, Step, CaseResult
    tables/
      build.py                 build_all() / load_cached(); orchestration + timing
      cache.py                 SQLite schema, save/load, freshness check (dataset hash)
      identities.py            user_identities + user_audit_log → identifier → user_id
      activities.py            system_activity → by_resource, deletion-worker window index
      observations.py          runs parsers, builds link index + state index
    parsers/
      base.py                  Parser protocol: parse(path, evidence_id, captured_at) → (rows, scope)
      sql_snapshot.py          .sql files via in-memory sqlite3 (3 schema families)
      json_records.py          snapshot bundles, service exports, ledgers/manifests, reports
      handover_txt.py          pipe-delimited handover
      service_logs.py          key=value and JSON-line traces, record_lookup lines
      pdf_text.py              pypdf text → same line parser as handover/logs
      image_vision.py          tesseract OCR + vision model → rows; OCR cross-check
    llm/
      client.py                OpenAI wrapper: disk cache by sha256(prompt+file), token counters, retries
      intent_rules.py          multilingual verb/object/negation scorer
      intent_fallback.py       one yes/no question to the model for UNSURE texts
      vision_prompt.py         prompt + JSON schema for screenshot extraction
    pipeline/
      intent.py                step 1
      subject.py               step 2
      discovery.py             step 3 (identifier links + window candidates + tie-break)
      state.py                 step 4 (newest observation ≤ audit_at, absence by scope)
      policy.py                step 5 (deletion_rules.csv → findings / required end state)
      writer.py                step 6 (ordering, step_no, CSV/JSON serialisation)
    run.py                     run_case(), run_all(), review.jsonl + usage.json writers
  evaluation/
    main.py                    scorer: output vs sample_output.csv (case, step, field, sequence)
    custom_cases/              ≥3 participant-made cases with expected output
    evaluation_report.md       required deliverable
    usage_report.md            required deliverable (filled from usage.json)
code/requirements.txt          pypdf, openai (core pipeline is stdlib only)
code/.env.example              OPENAI_API_KEY=
```

Stdlib everywhere it can be: csv, json, sqlite3, hashlib, logging, dataclasses, argparse,
concurrent.futures (vision calls only).

## 3. Tables (schema)

All four tables are built once per run by `tables/build.py` and persisted to
`cache/tables.sqlite`. Per-case code never reads a raw file.

| table | columns | keys / indexes |
|---|---|---|
| files | evidence_id PK, path, kind (sql/json/txt/log/png/pdf), captured_at, scope (JSON list of system_ids covered), sha256 | — |
| identities | identifier PK (lower-cased email / email_hash / phone / user_id), user_id, kind, current (0/1), audit_id NULL | idx user_id |
| observations | id PK, evidence_id, captured_at, system_id, resource_id, category, result, subjects (JSON list), retention_until NULL, raw_ref | idx (resource_id, captured_at); subject index built in RAM |
| activities | activity_id PK, event_time, event_type, source_system, target_system, resource_id, result | idx resource_id; idx (target_system, event_type, event_time) |

`result` enum: FOUND, NOT_FOUND, IDENTIFIABLE, ANONYMIZED, REDACTED, ACTIVE, DISABLED,
RESTORE_ALLOWED, RESTORE_BLOCKED.

In RAM the same data is held as dictionaries: `identities[identifier] → user_id`,
`obs_by_subject[identifier] → [Observation]`, `obs_by_resource[resource_id] → [Observation]`
(sorted by captured_at), `acts_by_resource[resource_id] → [Activity]`, plus a time-sorted
list of deletion-worker account deletes for binary-search windows.

Cache freshness: sha256 over the sorted list of (path, size, mtime) of `dataset/`;
mismatch or `--no-cache` rebuilds.

## 4. Per-case rules (what the code must do)

1. **Intent.** Dedupe request texts (375 distinct). Rule scorer → DELETE / OTHER / UNSURE.
   UNSURE → one model call, cached. OTHER → `NOT_APPLICABLE`, `[]`, stop.
2. **Subject.** `identities[email.lower()]` → user_id; collect every identifier of that user.
3. **Discovery.**
   - Link view (no time filter): every observation whose subjects intersect the identifiers.
   - Window candidates: deletion-worker rows in `[requested_at, reported_at]`, result matching
     reported_status (COMPLETE→SUCCESS, PARTIALLY_COMPLETE→PARTIAL, NOT_STARTED→FAILED),
     minus resources any other person is linked to, keeping those present in the case's
     evidence file(s) ≤ audit_at. Tie-break order TBD, validated on samples 11-32; unresolved
     ties go to review.jsonl and the earliest candidate is taken.
   - A resource known only from activities (no observation) is still verified, evidence "".
4. **State.** For each resource take the newest observation with captured_at ≤ audit_at.
   Missing from a file whose scope covers its system ⇒ NOT_FOUND from that file.
   Conflicts at equal time: prefer readback traces over observability exports.
5. **Policy.** Category → required action from deletion_rules.csv. Compare with result:
   FOUND under DELETE ⇒ REPORT_REMAINING_RECORD; IDENTIFIABLE under REDACT/ANONYMIZE ⇒
   REPORT_EXPOSED_PII; ACTIVE ⇒ REPORT_ACTIVE_DATA_FLOW; RESTORE_ALLOWED ⇒ REPORT_RESTORE_RISK.
   SECURITY_AUDIT_LOG retained only while retention_until > audit_at. Unknown category ⇒
   review.jsonl, no step.
6. **Write.** COMPLETE: verifications citing evidence. INCOMPLETE: findings (cite) +
   remediations ("") + verifications (""). Sort: phase, operation order, system_id, resource_id.

## 5. Engineering rules

- **Logging.** `logging` with one logger per module, INFO to console, DEBUG to
  `cache/run.log`. Every stage logs row counts and elapsed time. Every case logs one line.
- **Exceptions.** Parsers raise `ParseError`; `observations.py` catches per file, logs, writes
  the failure to review.jsonl, continues. Model errors retry 3× with backoff, then
  `ModelUnavailable` → UNSURE texts default to DELETE (safer for an audit) and the case is
  flagged. Nothing is silently skipped.
- **No N+1.** All per-case access is through prebuilt dictionaries. SQLite is read with one
  SELECT per table at load. Evidence `.sql` files are executed once into an in-memory
  sqlite3 and queried once per table. Request texts are classified once per distinct text.
- **DB hygiene.** Explicit schema, PRIMARY KEY and indexes as above, `executemany` inserts
  inside one transaction, `PRAGMA journal_mode=WAL` off (single writer), VACUUM not needed.
- **Determinism.** Fixed sort keys everywhere; `sort_keys=True` JSON; no dict/set order
  dependence on output paths; same input ⇒ byte-identical output.csv.
- **Secrets.** `OPENAI_API_KEY` from the environment only; `.env` is git-ignored;
  `--offline` runs with rules + cache only and reports which cases were affected.
- **Usage accounting.** `llm/client.py` records model, call count, input/output tokens per
  call into `cache/usage.json`; `usage_report.md` is generated from it.
- **Tests.** `python3 code/evaluation/main.py` is the test: it must print case, step, field
  and sequence accuracy for samples 01-10 and 11-32 separately. Run after every milestone.

## 6. Milestones and estimates

Estimates are hands-on hours with an AI pair; wall-clock will be longer.

| # | Milestone | Done when | Est. |
|---|---|---|---|
| M0 | Scaffold: package layout, config, logging, errors, models, `main.py` skeleton, scorer against sample_output.csv | `python3 code/main.py --limit 0` runs; scorer prints 0% cleanly | 1.0 h |
| M1 | identities + activities tables, SQLite cache, freshness check | 518/518 request emails resolve; window index returns the case_21 six | 1.0 h |
| M2 | observations: text parsers (handover txt, json families, logs, sql families), scope per file, link + state indexes | case_30 yields its 4 remnant rows; case_01 absence via scope | 3.0 h |
| M3 | pipeline steps 1-6 with identifier links only; first score | samples 11-32 ≥ 60% case accuracy without vision | 2.0 h |
| M4 | window candidates + tie-break, resources known only from activities | samples 11-32 account steps 22/22 | 1.5 h |
| M5 | pypdf + tesseract + vision model with cache and OCR cross-check | cases 45/61/63 produce steps; images cached | 1.5 h |
| M6 | full 518 run, review.jsonl triage, fixes, determinism check (two runs diff-identical) | output.csv 518 rows, validator passes | 2.0 h |
| M7 | evaluation_report.md (metrics + 3 custom cases + failures/fixes), usage_report.md, README run instructions, code.zip | all submission items present | 1.5 h |

Total ≈ 13.5 h hands-on. Order is fixed: accuracy-bearing work (M1–M4) before vision (M5),
reports last but started from M6's numbers.

## 7. Progress log

- **M0 done (2026-10-25).** Package skeleton, config with contract enums, logging to console +
  `cache/run.log`, error types, dataclasses, atomic CSV writer with validation, `main.py`
  (`--input eval|sample`, `--limit`, `--no-cache`, `--offline`, `-v`), scorer in
  `code/evaluation/main.py`. Checks: gold scored against itself = 100%; ordering + serialisation
  rebuilt from gold steps reproduce all 32 labeled answers (parsed JSON equal). Baseline with an
  empty pipeline (always INCOMPLETE): case accuracy 68.8%, everything else 0%. Note: labeled file
  mixes two key orders (01-10 alphabetical, 11-32 contract order); we emit contract order.

- **M1 done (2026-10-25).** `identifiers.py` (shared normalisation: lower-case emails/hashes,
  digits-only phones, word-boundary user ids), `tables/identities.py` (3,706 identifiers for 850
  users, old-email hashes derived, collision = fatal), `tables/activities.py`, `tables/files.py`
  (94 files with sha256), `tables/cache.py` (SQLite schema with PKs and indexes, one transaction,
  temp-file swap, fingerprint over dataset + table code), `tables/context.py` (dict indexes,
  binary-search worker window). Checks: 518/518 and 32/32 request emails resolve; case_40 →
  user_38 with 6 identifiers; case_21 window returns its 6 accounts. Cold build 0.07 s, warm 0.02 s.

- **M2 done (2026-10-25).** Parsers for every text family: `sql_snapshot.py` (inventory tables with
  `snapshot_scope`, record-JSON replicas, one-off primary/failover tables), `json_records.py`
  (service exports, snapshot bundles incl. embedded ledger rows, ledgers, single collections),
  `handover_txt.py` (pipe ledger lines, reusable for PDFs), `service_logs.py` (six line formats,
  trace grouping so `lookup_key` on a started line links the person to a 404 on the completed
  line, explicit event table). `parsers/base.py` holds the result enum (NOT_FOUND, IDENTIFIABLE,
  REFERENCED, REDACTED, ANONYMIZED, ACTIVE, DISABLED, RESTORE_ALLOWED, RESTORE_BLOCKED), record
  classification and same-moment merge (worst state wins). Observations now carry both
  `captured_at` (manifest, citation eligibility) and `observed_at` (inner time, ordering); scope is
  (system, observed_at). Result: 79/79 text files parse, 2,516 observations; 15 png/pdf deferred to
  M5. Checks: case_30 yields its 4 remnants in evidence_92; evidence_54 scope = account_service.
  Bug found and fixed: 64-hex `integrity_seal` was read as an email hash.

- **M3 done (2026-10-25).** `llm/intent_rules.py` (multilingual delete signals + account-protection
  clauses; 539 DELETE, 10 OTHER = cases 533-542, 1 UNSURE = sample case_26 for the model), steps in
  `pipeline/{intent,discovery,state,policy,case}.py`. Score on samples with identifier links only:
  case accuracy 96.9% (11-32: 100%), step precision 99.4%, recall 81.9%. Lessons from the labeled
  answers: (1) a snapshot's omission never overrides an explicit observation, scope-based absence
  is a fallback for resources with no eligible observation; (2) the support replica's legacy
  contact index is a SECONDARY_IDENTIFIER copy (DELETE), not a support message (REDACT).
  Correction to earlier notes: case_534 ("stop the promotional emails… not asking for deletion") is
  NOT_APPLICABLE, so there are 10 non-deletion cases, 533-542.

- **M4 done (2026-10-25).** `pipeline/linkage.py`: global window assignment over all requests
  (evaluation + sample files share the activity stream). Accounts: worker DELETE_RECORD in
  [requested_at, reported_at + 15 min], result matching reported status (fallback any), not tied to
  anyone else; iterative elimination; remaining conflicts by hour-rounded proximity to reported_at
  in (reported_at, case number) order, each recorded in review notes. Downstream records: linked only
  when exactly one request can claim them and they appear in that request's own evidence files.
  Measured alternatives on the samples before choosing: job-ordering for downstream records was
  wrong (jobs interleave), unique-only accounts were too timid (6 of 28 found). Resources known only
  from activity: absent via the newest covering snapshot <= audit_at, else verify-only without
  evidence. Score: case 96.9%, step precision 97.8%, recall 92.2%, sequence 59.4%.

- **M5 done (2026-10-25).** `parsers/media.py` (pypdf for PDFs; vision model when a key is set,
  tesseract OCR otherwise; emails accepted only if they exactly match a known identity),
  `llm/client.py` (OpenAI, sha256 disk cache, 3 retries, token/cost accounting to usage.json),
  `llm/intent_fallback.py`. Found that system_activity.csv carries 12 data-catalog
  LINK_RESOURCE_IDENTITY rows, each written minutes after one media file is captured, naming the
  resource, its alias in the document (statement number, file name, user ref) and the person;
  and one RESTORE_BACKUP row (backup_9287 recreated search_4882). Both are parsed in
  `tables/catalog.py`. Catalog links count only inside the case's [request, audit] window
  (samples 03, 07, 17); restored copies inherit the backup's owner; a violation seen only in files
  after audit_at becomes verification-only (a finding must cite evidence). No API key in this
  environment, so screenshots ran through OCR. Score: case 100%, precision 98.9%, recall 94.3%,
  F1 96.6%, sequence 65.6%. Full run: 518 rows, 0 contract violations, byte-identical reruns.

- **M6 done (2026-10-25).** Full 518 run triaged from `cache/review.jsonl`: 18 COMPLETE cases
  had an uncited verification for records seen only in later files; deletable records now take the
  covering snapshot before audit_at, retained records never (18 -> 1, no sample change). Intent
  negation extended to es/pt/fr/ja/ko. Final: 151 COMPLETE, 357 INCOMPLETE, 10 NOT_APPLICABLE.
- **M7 done (2026-10-25).** `code/evaluation/evaluation_report.md` (metrics, 4 custom cases,
  failure/improvement log, rejected alternatives, limitations), `code/evaluation/usage_report.md`
  (0 model calls in the final run: no key configured), README setup/run section, `code.zip`.

## 8. Open questions carried into code

1. Resolved: crowded windows use elimination then hour-rounded proximity (14/18 correct).
2. Resolved: activity-only resources are verified; covering snapshot before audit_at cites absence.
3. Resolved: same-moment rows merge with the worse state winning.
4. Open: vision output is validated against known identities; the OCR cross-check is not wired
   (OCR is the fallback instead). Downstream records in shared windows remain unlinked.
