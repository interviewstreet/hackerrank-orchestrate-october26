# How it works: Ghost Data Still Exists, end to end

This document explains how the deletion-audit agent turns `dataset/` into `output.csv`. It
follows one request through every stage, then covers model use, safety, failure handling,
evaluation and reproducibility.

- `README.md` (this folder) gives setup and run commands.
- `DESIGN.md` gives the module table, the policy readings and the failure-mode guards.
- This file connects them: what each stage does, why, and where the code is.

---

## 1. The problem in one paragraph

For each of the 518 requests, the agent answers three questions:

1. Did the person ask for deletion? If not: `NOT_APPLICABLE,[]`.
2. Which records, copies and processes belong to that person at `audit_at`?
3. Does each of them have the treatment that `deletion_rules.csv` requires?

All yes: `COMPLETE`, with verification steps that cite the proof. Any gap: `INCOMPLETE`, with
findings, an ordered remediation plan and the checks that must pass afterwards.

The trap in the dataset: `reported_status`, worker "delete completed" lines and
`reported_result` values are **claims**. Replicas, backups, sync jobs and screenshots often
contradict them. The agent must find the real state at `audit_at`.

---

## 2. The core rule

> **The model reads and proposes. Deterministic code decides and writes `output.csv`.**

| Task | Who does it |
| --- | --- |
| Parse SQL, JSON, logs, text, PDF text layer, activity CSV | Code |
| Read PNG screenshots into rows | Model, then grounded against Tesseract OCR by code |
| Label a request text the rules call AMBIGUOUS | Model (enum only), then checked by code |
| Investigate an item code cannot decide | Model agent proposes; code accepts or rejects |
| Status, steps, citations, order, serialization | Code only, always |

Why: the grader checks exact ids, operations and order. A model that writes steps can invent
an id or trust a claim. Code that decides gives the same answer on every run and can be tested.

---

## 3. Pipeline overview

```text
                        build once per run (main.build_context)
 dataset/ ──► loaders ──► extractors ──► FactStore (observations + scopes + id index)
                │                           │
                └──► IdentityIndex          └──► LinkIndex (owner of every identifier)
                                                  │
                         per case (main.run_case) ▼
 request ──► intent ──► identity(as of audit_at) ──► links/targets ──► resolver
                                                                         │
            output.csv ◄── validate ◄── serialize ◄── planner ◄── citation ◄── policy
```

| Stage | Module | Input | Output |
| --- | --- | --- | --- |
| Load | `loaders.py` | CSV files | Typed rows, UTC times, normalized emails/phones |
| Extract | `evidence/extract_*.py` | 94 evidence files + `system_activity.csv` | `Observation` and `Scope` objects |
| Store | `facts.py` | Observations | In-memory SQLite index with a time cutoff |
| Intent | `intent.py`, `intent_model.py` | `request_text` | DELETE / VERIFY_DELETE / NOT_DELETION / AMBIGUOUS |
| Identity | `identity.py` | request email, `audit_at` | `SubjectIdentity` (all emails, phones, hashes) |
| Links | `links.py` | subject identifiers | `Target` per (system, resource), with typed edges |
| Resolve | `resolver.py` | target + store | State per physical copy |
| Policy | `policy.py` | resolved state | `Decision`: compliant / violation / unproven / retained |
| Cite | `citation.py` | state + decision | One `evidence_id` |
| Plan | `planner.py` | items | Status + sorted, numbered steps |
| Write | `main.py`, `validate.py` | results | `output.csv`, strict contract check |

---

## 4. Stage by stage

### 4.1 Load (`loaders.py`)

- Every timestamp becomes a timezone-aware UTC `datetime`.
- Emails are lower-cased and trimmed. Phones become digits only.
- `email_hash` is SHA-256 of the normalized email. The code computes it for historical emails
  too, so a hash in old evidence still links.
- Paths resolve from the repository root, so the run works on Windows, macOS and Linux.

### 4.2 Extract evidence into one fact store (`evidence/`, `facts.py`)

Each extractor turns a file into **observations**. An observation is one statement a file
makes about one resource:

| Field | Meaning |
| --- | --- |
| `system_id`, `resource_id`, `physical_copy` | Which copy (`primary`, `read_replica`, `failover_replica`, ...) |
| `available_at` | When the file existed (manifest `captured_at`, or activity `event_time`) |
| `state_observed_at` | When the state was inspected (inner timestamp) |
| `assertion` | What kind of statement it is (table below) |
| `exists`, `treatment`, `flow_state`, `restore_state`, `exposed_ids` | The stated values |
| `link_ids` | Identifiers in the row (emails, user ids, phones, hashes) |

Assertion types and their strength:

| Assertion | Source | Sets state? | Rank |
| --- | --- | --- | --- |
| `snapshot_row` | SQL/JSON/text row | Yes | 3 |
| `state_readback` | Explicit FOUND / NOT_FOUND / ACTIVE read-back | Yes | 3 |
| scoped absence | A full listing that lacks the record | Yes (ABSENT) | 2 |
| `vision_row` | Grounded screenshot row | Yes | 2 |
| `activity_readback` | Activity row that reports an observed state | Yes | 1 |
| `agent_readback` | Accepted agent STATE proposal | Yes | 1 |
| `ownership_link` | `LINK_RESOURCE_IDENTITY` catalog row | No (links only) | - |
| `operation_claim` | "worker reported success" | **Never** | - |

**Scopes.** A SQL snapshot of a full table is a `Scope`. When a known resource is missing from
that scope, the copy is ABSENT at that time. Scope rules stop false absences:

- A subject-scoped listing proves absence only for the subjects it covers.
- A listing of one collection says nothing about a record of another collection.
- A listing of one system says nothing about a sibling system in the same file.

**Formats.**

| Format | Extractor | Notes |
| --- | --- | --- |
| `.sql` | `extract_sql.py` | Executed in SQLite; one copy per replica table |
| `.json` | `extract_json.py` | Nested records, identifiers found by key and pattern |
| `.log` | `extract_log.py`, `log_lines.py` | Six known line shapes; an unknown shape is a coverage error |
| `.txt` | `extract_text.py` | Key/value records |
| `.pdf` | `extract_text.py` (pypdf) | Text layer gives facts |
| `.png` | `extract_vision.py` | Model rows, grounded in OCR text (section 5.1) |
| activity | `extract_activity.py` | Claims, read-backs and catalog links |

`parse_coverage.py` counts every file. A file that no extractor understands stops the build,
so silent data loss cannot happen.

The `FactStore` keeps an in-memory SQLite index for two queries: "which observations carry
this identifier" and "which observations mention this resource". Both take a cutoff. An
observation counts only when `available_at <= audit_at` and `state_observed_at <= audit_at`.

### 4.3 Intent (`intent.py`)

The text is split into sentences, then clauses ("but", "so", commas, semicolons). Each clause
gives signals:

| Signal | Example |
| --- | --- |
| `delete` | "please erase my account", "eliminar mi cuenta", "アカウントを削除" |
| `verify` | "confirm that my data was deleted" |
| `negated` | "I am not asking for deletion" |
| `keep` | "leave the account active" |
| `marketing` | "remove me from marketing lists only" |
| `other` | "please correct my address", "send me a copy" |
| `deleted_context` + `remnant` | "it was deleted but I can still find traces" (means DELETE) |

Decision:

- Positive and negative signals together: AMBIGUOUS.
- `delete`: DELETE. `verify` only: VERIFY_DELETE (counts as deletion).
- Negative signals only: NOT_DELETION, so the row is `NOT_APPLICABLE,[]`.
- A text with an instruction pattern ("ignore previous instructions", role markers): AMBIGUOUS.

The lexicon covers English, Spanish, Portuguese, French, German, Italian, Dutch, Japanese,
Korean and Chinese.

AMBIGUOUS texts go to the model in one batch (`intent_model.py`, prompt `intent_v1.md`). An
injection-screened, invalid or missing label stays AMBIGUOUS. `treat_as_deletion` counts
AMBIGUOUS as deletion. Reason: an unclear or injected text must not suppress a real request,
and the evidence still decides the status. In the final run the rules decided every text, so
the model got 0 intent calls.

### 4.4 Identity as of `audit_at` (`identity.py`)

1. Find every user whose email, current or historical, equals the request email.
2. For each field (`email`, `phone`, `email_hash`), rebuild the value at `audit_at`:
   - a change after `audit_at` is ignored; the value at `audit_at` is its `old_value`;
   - every value known up to `audit_at` is kept (current first, then historical).
3. Add SHA-256 hashes of every known email.
4. Prefer a user whose *current* email matches; else take the historical match. Two candidates
   add the flag `ambiguous_email:...`.

Guard: if any audit row after `audit_at` would be used, `FutureDataError` is raised. No later
data can leak into a case.

### 4.5 Ownership links: which records are the subject's (`links.py`)

A **target** is a `(system_id, resource_id)` pair linked to the subject by at least one
**edge**. Only edges at or before `audit_at` count.

| Edge | Tier | Rule |
| --- | --- | --- |
| `identifier` | strong | A row carries the subject's email, user id, phone or hash |
| `catalog_link` | strong | A `LINK_RESOURCE_IDENTITY` activity names the subject |
| `derived_from` | strong | A record names a linked resource as `source_resource_id` |
| `vision_identifier` | medium | A grounded screenshot row carries a subject identifier |
| `agent_link` | medium | An accepted agent LINK proposal |
| `job_burst` | medium | The deletion worker touched exactly one resource in a system within 10 min of this case's `reported_at`, and no other request reported in that window |

Rules that keep links honest:

- **Names never link.** Numeric suffixes and row positions never link.
- **Foreign records are dropped.** A record whose identifiers belong only to other users is
  not a target (`dropped_foreign:<id>`). A record linked to the subject *and* others is
  `shared_with` them, and code never acts on it from a foreign link alone.
- **Stale links.** When every edge predates `requested_at`, the record describes the subject
  before the request. It gets no step (`stale_link:<id>`).
- **Ambiguous bursts.** A job burst that touches two resources in one system gives no edge.

`LinkIndex` builds an owner map of every identifier (current snapshot plus audit log), so it
can tell which user owns each value.

### 4.6 State per physical copy at `audit_at` (`resolver.py`)

For each target, the resolver collects admissible **statements** per physical copy:

- rows and read-backs about the resource (claims are excluded);
- scoped absences from listings that apply to the subject and lack the record.

Then, per copy and per attribute (`exists`, `treatment`, `flow_state`, `restore_state`,
`exposed_ids`), one dominance rule picks the value:

1. **Newest wins.** The newest `state_observed_at` decides. State changes over time: a delete
   after a snapshot is the common case.
2. **Tier breaks ties.** Only at the same timestamp, rank 3 beats rank 2 beats rank 1.
3. **Conflict.** Same time, same rank, different values: `CONFLICT`.
4. **No statement:** `UNKNOWN`.

A newer ABSENT makes older treatment or identifier statements moot.

`exists_rollup`: PRESENT if any copy is PRESENT; ABSENT only if every known copy is ABSENT.
This is how a surviving replica keeps a case `INCOMPLETE` although the primary row is gone.

Screenshots: a present vision row with no identifier of its own keeps its OCR region. If the
subject's email, phone or hash appears in that region, the record exposes it
(`shown_identifiers`). A name alone does not count.

### 4.7 Policy (`policy.py`)

`deletion_rules.csv` is loaded and bound to a treatment table at import time. A rule whose
action does not fit its check stops the run (`bind_rules`). The rule ids come from the CSV.

**Category.** The first source that names a category wins:

1. a stated `record_type` / `data_category` in the evidence (two different ones: ambiguous);
2. the collection (`support_platform/ticket_attachments` -> `SUPPORT_ATTACHMENT`);
3. catalog-link words ("Attachment catalog confirmed ..." -> `SUPPORT_ATTACHMENT`);
4. the system default (`account_service` -> `USER_PROFILE`, ...).

An ambiguous category gives `UNPROVEN`, never the first match.

**Checks.**

| Check | Categories (examples) | Violation when | Finding / Remediation / Verification |
| --- | --- | --- | --- |
| `exists` | USER_PROFILE, SEARCH_INDEX_ENTRY, CACHE_ENTRY, USER_EXPORT, MARKETING_PROFILE, SUPPORT_ATTACHMENT | any copy PRESENT | REPORT_REMAINING_RECORD / DELETE_RECORD / VERIFY_RECORD_ABSENT |
| `direct` | SUPPORT_MESSAGE, EMAIL_DELIVERY_LOG, ACCOUNT_TOMBSTONE | a present copy shows email, phone, hash or name | REPORT_EXPOSED_PII / REDACT_RECORD / VERIFY_RECORD_REDACTED |
| `linked` | ANALYTICS_PROFILE, PRODUCT_TELEMETRY | a present copy is attributable (user id counts too) | REPORT_EXPOSED_PII / ANONYMIZE_RECORD / VERIFY_RECORD_ANONYMIZED |
| `retain` | SECURITY_AUDIT_LOG, LEGAL_HOLD_RECORD | the record is missing | - / - / VERIFY_RECORD_PRESENT |
| `restore` | BACKUP_ARCHIVE | any copy OPEN for restore | REPORT_RESTORE_RISK / BLOCK_RESTORE / VERIFY_RESTORE_BLOCKED |
| `flow` | DATA_FLOW (process, not a rule row) | any copy ACTIVE | REPORT_ACTIVE_DATA_FLOW / DISABLE_DATA_FLOW / VERIFY_DATA_FLOW_DISABLED |

**Outcomes.** `compliant`, `violation`, `unproven` (no admissible proof, or a conflict),
`missing_retained`, `not_target` (no rule applies).

**Readings where the evidence does not state the rule condition** (full table in `DESIGN.md`):

- Support attachment (rule_06): delete only when it is proven to belong *only* to the subject
  (catalog says so, or a strong identifier edge and no other user). Else unproven.
- Legal hold (rule_13): an explicit status decides. With no status, the end date decides. With
  neither, a supplied hold is active, so it is retained.
- Retention: a retained record whose stated end date is at or before `audit_at` switches to the
  delete path. Contradicting dates give unproven, never a delete.
- Backup (rule_14): no restore state on any copy, and a present copy holds the subject's
  identifiers: restore risk.
- Tombstone (rule_15): only the stable `user_id` may stay. A catalog link inside the request
  window that binds the record to a direct identifier is an exposure, cited from the
  `activity_id`.

**Safety invariants** (`check_safety`, run on every planned step):

- Never DELETE or ANONYMIZE a retained category unless its retention is proven expired.
- Never act on a record linked only to another user.
- Never use an operation claim as proof.

A breach raises `SafetyViolation`, so the case falls back (section 7) instead of writing a
wrong step.

### 4.8 Citation (`citation.py`)

Citation runs after state and policy are fixed. It never changes them.

Among statements that support the decided state, with no newer contradicting statement in the
same copy:

1. strongest tier;
2. then newest;
3. then the id that supports the state in the most copies;
4. then the lowest id in natural order.

A violation is cited only from a copy in the violating state. A tombstone catalog exposure
cites the catalog `activity_id`. Evidence after `audit_at` is never a candidate, because the resolver
already dropped it.

### 4.9 Status and steps (`planner.py`)

**Status rule** (the only one):

> `COMPLETE` only when there is at least one target and every target is proven compliant with
> a citation. Anything else is `INCOMPLETE`.

So an unproven or conflicting target never gives a silent `COMPLETE`.

**Steps.**

| Status | Per target |
| --- | --- |
| COMPLETE | One VERIFICATION step that cites the proof |
| INCOMPLETE, violation | FINDING (cited) + REMEDIATION (`""`) + VERIFICATION (`""`) |
| INCOMPLETE, compliant / unproven / retained | VERIFICATION (`""`) only |
| NOT_APPLICABLE | `[]` |

**Order** (`schema.step_sort_key`): phase (FINDING, REMEDIATION, VERIFICATION), then the
operation table order, then `system_id`, then `resource_id`. The operation table lists
DISABLE_DATA_FLOW and BLOCK_RESTORE before DELETE / REDACT / ANONYMIZE, so flows and restores
are stopped before records change. Then `step_no` runs 1..n.

### 4.10 Serialize and validate (`main.py`, `validate.py`, `schema.py`)

- `schema.py` is the single source of truth for enums, the operation table, the sort key and
  the Pydantic `Step` / `OutputRow` models.
- Every row passes `OutputRow.model_validate` before it is kept.
- JSON uses sorted keys and compact separators, so the output is byte-stable.
- Rows are sorted by numeric `case_id`.
- After writing, `validate.validate_file` checks the whole file: header, 518 rows, enums,
  operation/state/phase pairs, step numbering, phase order, empty evidence on future steps,
  and no citation after `audit_at`. Any error gives exit code 1.

---

## 5. Where the model is used

Provider: ZenMux (OpenAI-compatible). Model: `meta/muse-spark-1.3-contributor`. Settings and
prices: `config.py`. Key: env `ZENMUX_API_KEY` or the uncommitted `.env`.

### 5.1 Screenshots (`extract_vision.py`, prompt `vision_extract_v3.md`)

1. Tesseract OCR reads the PNG at 2x scale (block layout `--psm 3` plus line layout `--psm 6`).
2. The model gets the image, the OCR text and the catalog alias table (file name or statement
   number -> resource id). It returns rows in a strict JSON schema.
3. Code accepts a row only when **one OCR block** holds the resource id (or a visible alias)
   and its state cue, and the identifier is in that block (or anywhere on a page that names no
   other record). In a table, the cue must be on the record's own line.
4. Matching allows only OCR noise: case, `_ - . ,` and spaces between id tokens, `o/0`,
   `l/i/|/!/1`. Ids need a boundary on both sides. Phones compare digits.
5. An accepted row becomes a `vision_row` observation (rank 2) at the file's `captured_at`.

Final run: 11 screenshots, 11 calls, 24 rows returned, 1 dropped by grounding.

### 5.2 Ambiguous intent (`intent_model.py`, prompt `intent_v1.md`)

Batched label for AMBIGUOUS texts only. Enum output. 0 calls in the final run.

### 5.3 Investigator agent (`agent/loop.py`, `agent/tools.py`, prompt `agent_v2.md`)

Runs only for a target that code leaves `UNPROVEN` or in `CONFLICT`.

| Tool | Does |
| --- | --- |
| `search_evidence(query)` | Exact-id grep, then BM25 over evidence visible at `audit_at` |
| `read_evidence(file_id)` | Parsed rows of one file |
| `query_facts(id)` | Fact-store rows and ownership edges |
| `submit_proposal(...)` | A typed `LINK` or `STATE` proposal |
| `stop` | End with no proposal |

Caps: 4 turns per item, 40,000 tokens per case, 1 schema retry, 2 transport retries.

**Acceptance check (code):** every cited file was opened in this loop and exists at
`audit_at`; the quote names the resource (and a subject identifier, for LINK); the claimed
state matches the parsed rows of the cited file. An accepted proposal only adds a medium edge
or a rank-1 observation. The resolver and policy run again and still decide.

Final run: 0 agent runs, because code decided every item. The loop stays for data where code
cannot decide; custom case `cc06` tests it with a scripted model.

### 5.4 Cache and offline replay (`llm_client.py`, `llm_cache.py`, `llm_snapshot.py`)

- Cache key: SHA-256 of the input bytes + prompt version + model id.
- Every reply is parsed through a `schema.py` contract (`extra="forbid"`). One retry with the
  validation error, then a deterministic fallback with a flag.
- `llm_snapshot.py` holds validated results; `ocr_snapshot.json` holds OCR readings.
- No key, `--offline` or `ZENMUX_OFFLINE=1`: replay only, no network. A snapshot miss gives the
  deterministic result and the flag `snapshot_miss`.

---

## 6. Safety against prompt injection (`safety.py`)

1. Request texts and OCR text are screened before any model call (role markers, "ignore
   previous instructions", tool or status commands, hidden Unicode).
2. A screened hit is never sent raw. Code logs it and keeps the deterministic result.
3. Data goes to the model inside delimiters, under a system prompt that defines it as data.
4. Model output is parsed only through schema models. Free text is discarded.
5. The model has no tool that writes output, sets a status or deletes anything.
6. Tests: injected request text, forged "deletion complete" log line, decoy near-match email,
   instruction text inside an evidence file (`tests/test_adversarial.py`).

---

## 7. Failure handling

| Failure | Behaviour |
| --- | --- |
| One case raises | `fallback_result`: `INCOMPLETE` with an empty-evidence verification step per known target; listed in `output_failures.csv`; exit code 1; the batch goes on |
| A row breaks the contract | Rejected by `OutputRow` before it is kept |
| Unknown file or line shape | Coverage error stops the build (PNG OCR failure: that image only) |
| No network / no key | Snapshot replay |
| Later evidence | One cutoff function; `FutureDataError`; validator rejects late citations |

Final run: 0 failed cases, 0 contract errors, exit code 0.

---

## 8. Worked example: sample `case_15`

Request: *"I disconnected my account last week, but one of the integrations still seems
active. Close the account completely and make sure it can no longer send ..."*
`reported_status = COMPLETE`, `requested_at = 2026-08-21T12:00Z`, `audit_at = 2026-09-15T12:00Z`.

**Intent.** "Close the account" gives `delete`. No negative signal. Label DELETE.

**Identity.** The email resolves to one user. All emails, phones and hashes known at `audit_at`
form the subject keys.

**Links.** Three targets, all with strong `identifier` edges from `evidence_01` (an
observability log captured 2026-09-15T11:59:39Z, before `audit_at`):

| Target | Category (source) | Edges |
| --- | --- | --- |
| `account_service/account_4745` | USER_PROFILE (system default) | identifier |
| `integration_service/data_flow_9846` | DATA_FLOW (system default) | identifier + vision_identifier (`evidence_14`) |
| `security_service/audit_record_1596` | SECURITY_AUDIT_LOG (system default) | identifier |

**Resolve.**

- `account_4745`: every copy (primary, read replica, two regional replicas, reporting and
  failover replicas) is ABSENT. The newest primary statement is the `evidence_01` read-back.
- `data_flow_9846`: the primary copy went PRESENT/ACTIVE in the screenshot `evidence_14`
  (2026-08-07), an activity read-back (2026-08-22) and the `evidence_01` read-back
  (2026-09-15 11:58). Newest wins: ACTIVE.
- `audit_record_1596`: the newest primary statement (`evidence_01`) says PRESENT.

**Policy.**

| Target | Rule | Outcome |
| --- | --- | --- |
| account_4745 | rule_01 DELETE (`exists`) | compliant (ABSENT everywhere) |
| data_flow_9846 | flow | **violation** (ACTIVE) |
| audit_record_1596 | rule_12 RETAIN | compliant (PRESENT; no end date, so retained) |

**Status.** One violation, so `INCOMPLETE`, although the workflow claimed `COMPLETE`.

**Steps** (identical to the gold row in `sample_output.csv`):

| # | Phase | Target | Operation | Evidence |
| --- | --- | --- | --- | --- |
| 1 | FINDING | data_flow_9846 | REPORT_ACTIVE_DATA_FLOW | `evidence_01` |
| 2 | REMEDIATION | data_flow_9846 | DISABLE_DATA_FLOW | `""` |
| 3 | VERIFICATION | account_4745 | VERIFY_RECORD_ABSENT | `""` |
| 4 | VERIFICATION | audit_record_1596 | VERIFY_RECORD_PRESENT | `""` |
| 5 | VERIFICATION | data_flow_9846 | VERIFY_DATA_FLOW_DISABLED | `""` |

Notes:

- The account and audit record are already compliant, so they get no finding. They still get
  a verification step, because the case is `INCOMPLETE` and every target's final state must be
  checked after remediation.
- The audit record is retained, never deleted (safety invariant).
- Verification steps sort by operation order, then system id.

To see this trace yourself:

```text
python code/main.py --offline --requests dataset/sample_deletion_requests.csv --out sample_pred.csv --trace trace.jsonl
```

Each line of `trace.jsonl` holds one case: intent, flags, targets, edges, per-copy statements,
the proof per attribute, the decision and the steps.

---

## 9. Evaluation

Commands:

```text
python code/evaluation/main.py            # samples + custom cases + metamorphic checks
python code/validate.py output.csv        # strict contract check
python -m pytest code/tests               # unit, adversarial and contract tests (replay only)
```

Sample results (32 public cases; they are a development set, so these numbers are optimistic):

| Metric | Value |
| --- | --- |
| Status accuracy | 32/32 = 1.000 |
| Exact row (status + all steps) | 15/32 = 0.469 |
| Step content match (6 fields), P / R / F1 | 1.000 / 0.855 / 0.922 |
| Exact step (7 fields incl. `step_no`), P / R / F1 | 0.764 / 0.653 / 0.704 |
| Field accuracy `evidence_id` | 0.850 |

- Precision 1.000 on content: the agent invents no step.
- Recall 0.855: the main loss is records linked only by a worker claim (28 of 193 gold steps).
  Code does not trust a claim as a link, by design.
- 7 custom cases (`evaluation/custom_cases/`, frozen before tuning) pass: negated request,
  verify-only request, injection in request text, retained audit record, flow + restore risk,
  scripted agent run, historical email.
- 19 metamorphic checks pass: shuffled rows, email case and spaces, an older contradicting
  read-back, `audit_at` 1 s before the key file (it must drop out), `audit_at` exactly at it
  (inclusive cutoff).

Full run on 518 requests: 355 `INCOMPLETE`, 153 `COMPLETE`, 10 `NOT_APPLICABLE`.
Details: `evaluation/evaluation_report.md` and `evaluation/usage_report.md`.

---

## 10. Cost and reproducibility

| Item | Final run |
| --- | --- |
| Model calls | 11 (vision only), all cache hits from the snapshot |
| Tokens | 46,874 in / 11,463 out (58,337 total, ~113 per request) |
| Cost | $0.00698 total, ~$0.0000135 per request |
| Output SHA-256 | `c40d985c1b510d5e8f891ce00ef3e71fecce0b7db9b62a1fa54840a477df9bff` |

Reproduce with no key and no network:

```text
ZENMUX_OFFLINE=1 python code/main.py
```

The run takes a few seconds and gives the same `output.csv` byte for byte.

---

## 11. Known limits

- A record linked to the subject only by a worker claim gets no step.
- OCR misreads drop some screenshot rows (1 of 24 in the final run).
- Legal hold with no status and no end date, and tombstone catalog exposure, are rule-text
  readings that no sample tests.
- A new live model run can return different screenshot rows; the snapshot fixes the submitted
  output.

---

## 12. File map

```text
code/
  main.py              CLI, per-case loop, fallback, serialization
  schema.py            Contract: enums, operation table, sort key, Pydantic models
  loaders.py           CSV loading, UTC times, normalization, hashes
  identity.py          As-of identity resolution
  intent.py            Clause-level intent rules
  intent_model.py      Model label for AMBIGUOUS texts
  facts.py             Global fact store and catalog aliases
  parse_coverage.py    Per-file parse accounting
  links.py             Ownership graph (targets and edges)
  resolver.py          State per physical copy at audit_at
  policy.py            deletion_rules.csv as a truth table + safety invariants
  citation.py          Evidence choice
  planner.py           Status rule and ordered steps
  validate.py          Strict output-file validator
  safety.py            Injection screen and delimiting
  llm_client.py        Model client with schema retry
  llm_cache.py         Content-addressed cache
  llm_snapshot.py      Committed validated model results (replay)
  ocr_snapshot.json    Committed OCR readings (replay)
  audit_trace.py       Per-case JSONL trace
  config.py            Model id, base URL, prices, caps
  package.py           Builds code.zip with a secret scan
  agent/               Investigator loop and tools
  evidence/            Extractors per format
  prompts/             vision_extract_v3, intent_v1, agent_v2
  evaluation/          Scorer, custom cases, metamorphic checks, reports
  tests/               Pytest suite
```
