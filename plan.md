# Plan: Ghost Data Still Exists (HackerRank Orchestrate, October 2026)

Version: v4 (2026-10-24), after review rounds R1 and R2. Status: plan only, no code written yet.

---

## 0. How to use this document (read first if you are a reviewer agent)

This file is the single brief for the project. Reviewer agents get it to critique the plan.
It must give the full picture without other context.

- Local repo: `D:\Coding\hackerrank-orchestrate-october26` (git, branch `main`).
  Remote reviewers: the public upstream is `https://github.com/interviewstreet/hackerrank-orchestrate-october26`
  (same `dataset/` and docs). Claims marked **[verified]** were checked by script on the local copy.
- Do NOT write `log.txt` or any log file. `AGENTS.md` asks agents to log each turn; the user paused that for now.
- Do NOT modify repo files. Do NOT use organizer-only files (anything outside `dataset/`, for example `generator/`).
- Return your critique in this format:
  1. **Score**: 1-10 for the plan's ability to score well, with one line of reason.
  2. **Wrong or unverified assumptions**: plan section, claim, evidence (`path:line`, `case_id`, `file_id`), fix.
  3. **Missing items**: what is missing and where it goes in the plan.
  4. **Simpler or better designs**: change, benefit, cost.
  5. **Open questions you resolved** (section 13), with evidence.
- Keep critique compact. Cite evidence. Do not paste large file contents.
- Section 15 keeps the review history. The plan owner merges accepted changes and records them there.

---

## 1. The challenge

Northstar Shop (fictional) lost money because a "deleted" customer still existed in secondary systems.
Build an AI deletion-audit agent. For each request in `dataset/deletion_requests.csv` (518 rows), it must:

1. Decide if `request_text` authorizes deletion. If not: `NOT_APPLICABLE` with `[]`.
2. Resolve the subject's current and historical identifiers (email, phone, email hash, name, `user_id`).
3. Rebuild the true state of every related record at `audit_at`, from evidence only.
   `reported_status` and activity `reported_result` are claims, not proof.
4. Apply `dataset/deletion_rules.csv` to each record.
5. Output `COMPLETE` or `INCOMPLETE` and the ordered steps.

A deletion is `COMPLETE` only when:
- every relevant copy has the treatment that the rules require;
- no active sync, import or restore path can recreate the data;
- retained records hold only the permitted identifiers;
- records that must be retained are still available.

Scoring (hidden answers): status accuracy, identity resolution, found records and risks, cited evidence,
policy decisions, completeness and order of `steps_json`.

---

## 2. Repo map and deliverables

| Path | Content |
| --- | --- |
| `problem_statement.md` | Full contract (162 lines). Source of truth |
| `README.md` | Setup, packaging, submission checklist |
| `AGENTS.md` | Agent rules: logging to `log.txt` (sections 2-5), contract copy (section 6), dataset rules (section 7) |
| `CLAUDE.md` | Only `@AGENTS.md` |
| `agent_trace_instructions.md` | How to submit the chat transcript |
| `code/main.py` | Empty. Intended entry point: `python3 code/main.py` |
| `code/evaluation/main.py` | Empty. Intended evaluation entry point |
| `dataset/` | All input data (section 4) |

Deliverables: root `output.csv`; `code.zip` (code, prompts, `README.md`, `code/evaluation/evaluation_report.md`,
`code/evaluation/usage_report.md`; no `dataset/`, no nested archives, no secrets); `log.txt` as chat transcript; an AI interview.

Runtime and packaging assumptions (R2):
- The code judge ignores `.csv/.tsv/.json/.jsonl/.sql/.log` files. Metrics, prompts and any committed extraction
  results must be in `.md` or `.py` files.
- The final run calls `meta/muse-spark-1.3` (ZenMux) live with a cache (D18, section 7.3). The code must also run
  **offline with no API key**, by replaying the committed `code/llm_snapshot.py`.
- One failing case must not stop the run: catch errors per case, log them, and still write all 518 rows.

---

## 3. Output contract (exact)

`output.csv` header: `case_id,deletion_status,steps_json`. 518 rows.

**Row order [verified]**: ids are `case_33` .. `case_550` with mixed width (7 and 8 chars).
`deletion_requests.csv` is in **numeric** order, which is not lexicographic order (`case_100` < `case_33` as text).
Sort by the integer suffix (same as the input file order). Samples are `case_01`..`case_32`, where both orders agree.

Step object (exact keys): `step_no, phase, system_id, resource_id, operation, state, evidence_id`.

| Phase | Operation (this order is the sort order) | State |
| --- | --- | --- |
| FINDING | REPORT_REMAINING_RECORD | PRESENT |
| FINDING | REPORT_EXPOSED_PII | PRESENT |
| FINDING | REPORT_ACTIVE_DATA_FLOW | ACTIVE |
| FINDING | REPORT_RESTORE_RISK | ACTIVE |
| REMEDIATION | DISABLE_DATA_FLOW | DISABLED |
| REMEDIATION | BLOCK_RESTORE | BLOCKED |
| REMEDIATION | DELETE_RECORD | ABSENT |
| REMEDIATION | REDACT_RECORD | REDACTED |
| REMEDIATION | ANONYMIZE_RECORD | ANONYMIZED |
| VERIFICATION | VERIFY_RECORD_ABSENT | ABSENT |
| VERIFICATION | VERIFY_RECORD_PRESENT | PRESENT |
| VERIFICATION | VERIFY_RECORD_REDACTED | REDACTED |
| VERIFICATION | VERIFY_RECORD_ANONYMIZED | ANONYMIZED |
| VERIFICATION | VERIFY_DATA_FLOW_DISABLED | DISABLED |
| VERIFICATION | VERIFY_RESTORE_BLOCKED | BLOCKED |

- **Sort is mandated** by `problem_statement.md` ("Within each phase, follow the operation order in the table above,
  followed by `system_id` and `resource_id` in ascending order"). All 32 samples follow it [verified].
  The AGENTS.md 6.5 safety order ("disable flows and block restores before changing records") is already satisfied by
  the operation order. "Downstream copies before sources" stays an internal dependency check only; if a real case ever
  conflicts with the mandated sort, keep the mandated sort and record the conflict in the evaluation report.
- `step_no` from 1, consecutive.
- `COMPLETE`: only VERIFICATION steps, each cites evidence (`file_id`, `activity_id` or `audit_id`).
- `INCOMPLETE`: FINDING steps cite evidence. REMEDIATION and VERIFICATION steps use `evidence_id: ""`.
- `NOT_APPLICABLE`: `[]`.
- Use only information at or before `audit_at`. Never cite evidence captured after `audit_at`.
- One step per logical target `(system_id, resource_id)`, even when the record survives in several physical copies.

---

## 4. Dataset facts [verified]

| File | Rows | Columns / notes |
| --- | --- | --- |
| `deletion_requests.csv` | 518 | `case_id,email,requested_at,reported_status,reported_at,audit_at,request_text`. Status claim: COMPLETE 254, PARTIALLY_COMPLETE 152, NOT_STARTED 112 |
| `sample_deletion_requests.csv` / `sample_output.csv` | 32 / 32 | Truth for samples: INCOMPLETE 22, COMPLETE 10, NOT_APPLICABLE 0. Steps per case 1-14, 193 steps total |
| `user_identities.csv` | 850 | `user_id,name,email,phone,email_hash,updated_at` (current snapshot) |
| `user_audit_log.csv` | 306 | `audit_id,user_id,event_time,field_name,old_value,new_value`. Fields: email 107, email_hash 107, phone 92 |
| `system_activity.csv` | 4011 | `activity_id,event_time,event_type,source_system,target_system,resource_id,reported_result,details` |
| `deletion_rules.csv` | 15 | `rule_id,data_category,condition,required_action` |
| `evidence_files.csv` | 94 | `file_id,file_path,origin,captured_at` |
| `output.csv` | 0 | Blank template |

Requests and identity:
- 418 request emails match a current email; 100 match only a historical email. One email appears in 2 cases:
  state is computed per `(user_id, audit_at)`, so the two cases can differ.
- All 518 emails resolve to exactly one `user_id`. case_10 needs a 2-step email chain.
- No case has an identity snapshot `updated_at` or an audit-log change after its `audit_at` (0 of 550). So the
  current snapshot is safe to use; keep an as-of assertion in code anyway.
- `email_hash` = SHA-256 of the trimmed, lower-case email (all 850 current, all 107 historical pairs).
- `request_text`: 27 distinct opening sentences, **375 distinct full texts**, about 8 languages.
- About 10 requests are not deletion (phone update, stop promo emails, data download, login help, surname fix,
  marketing-only removal, "what data do you hold", invoice copy, email change, data copy). Some include deletion words
  with a negation: case_534 "...so I am not asking for deletion."; case_538 "remove me from marketing lists only".
- **Verify/audit requests are deletion-authorized**: case_25 ("tell me whether the account and identifiable analytics
  data have already been removed") and case_27 ("Please audit the deletion as it stood...") are COMPLETE with steps.
- Mixed requests exist: case_04 "I'm deleting my account. You can keep anonymous statistics..." is a deletion.

Activity (`system_activity.csv`):
- Event types: DELETE_RECORD 890, UPDATE_RECORD 672, SYNC_RECORD 447, INDEX_RECORD 400, SEND_EMAIL 368, REFRESH_CACHE 284,
  RETAIN_RECORD 206, ANONYMIZE_RECORD 204, REDACT_RECORD 173, CREATE_EXPORT 155, CHECK_DATA_FLOW 89, DISABLE_DATA_FLOW 36,
  BLOCK_RESTORE 36, CHECK_RESTORE_ACCESS 28, LINK_RESOURCE_IDENTITY 12, CLASSIFY_REQUEST 10, RESTORE_BACKUP 1.
- Results: SUCCESS 2914, FAILED 721, PARTIAL 376.
- Resource prefixes: account, search, analytics, support, email_delivery, cache, audit_record, export, data_flow, backup,
  tombstone (11), legal_hold (10), object, marketing.
- Many rows concern other users (decoys). Details often do not name the user.
- Rows carry different kinds of assertions: operation claims ("reported as completed"), ownership links
  (`activity_4007`: "object_19 ... belongs only to priya.raman@gmail.com and user_07"), state read-backs
  (`CHECK_DATA_FLOW`: "confirmed that data flow ... remains enabled"), sync facts ("Active connector repopulated ... search_6302").

Rules (`deletion_rules.csv`): see the truth table in section 9.5.

---

## 5. Evidence catalog (`dataset/evidence/`, 94 files, 2.9 MB)

| Family | File ids | Captured | Format notes |
| --- | --- | --- | --- |
| `databases/customer_data_inventory_*.sql` | 63,66,...,93 (11) | 02-13..09-16 | Tables: `snapshot_scope, customer_profiles, customer_search_documents, customer_analytics_profiles, support_records, customer_exports, connector_subscriptions, backup_restore_entries, security_audit_records`. `snapshot_scope` lists covered origin systems |
| `databases/customer_data_read_replica_*.sql` | 05,10,15,20,24 | 06-13..09-21 | `customer_data_primary` + `customer_data_read_replica` |
| `databases/customer_data_regional_replicas_*.sql` | 29,33,38 | 03-30..05-19 | primary + `replica_ap_south` + `replica_eu_west` |
| `databases/customer_data_reporting_replica_*.sql` | 43,47 | 02-08..03-05 | primary + reporting replica |
| `databases/customer_data_failover_replica_20260920.sql` | 52 | 09-20 | primary + failover |
| `databases/customer_accounts_failover_replica_20260902.sql` | 54 | 09-02 | `customer_profiles_primary` + `customer_profiles_failover_replica` |
| `databases/customer_search_primary_20260910.sql` | 57 | 09-10 | `search_documents_primary` |
| `records/customer_data_snapshot_bundle_*.json` | 02,07,...,51 (12) | 01-31..09-17 | JSON shape `snapshots` (inner `captured_at`, `data_store`, `collection`, `records`) |
| `records/service_resource_export_*.json` | 62..92 (11) | 01-29..09-15 | JSON shape `service_exports` (per region; rows have `observed_at`) |
| `records/connector_configurations`, `customer_export_jobs`, `customer_export_manifest`, `customer_analytics_report`, `security_audit_ledger` | 13,59,36,56,50 | various | JSON shapes `records` / `collection` |
| `records/customer_account_handover_20261001.txt` | 03 | 10-01 | Lines: `time | system | resource | record_type | result | subject` |
| `logs/*.log` | 26 files | 02-03..09-30 | Several formats: quoted `key="value"`, JSON payloads, syslog, bracketed, pipe, escaped messages |
| `images/*.png` | 04,09,14,19,23,28,32,37,42,46,60 | 02-13..09-26 | Product consoles: account admin, search index, connector, analytics, export, support ticket, backup restore, security audit, deleted account reference, object storage, marketing |
| `documents/*.pdf` | 18,27,55,58 | 05-29..09-12 | Account history report, legal retention register, security retention extract, delivery correction attachment |

Record vocabularies: `record_type` (USER_PROFILE, SECURITY_AUDIT_LOG, SEARCH_INDEX_ENTRY, ANALYTICS_PROFILE,
SUPPORT_MESSAGE, DATA_FLOW, BACKUP_ARCHIVE, USER_EXPORT, LEGAL_HOLD_RECORD); `result` (FOUND, NOT_FOUND, IDENTIFIABLE,
ACTIVE, ANONYMIZED, REDACTED, DISABLED, BLOCKED); `subject_reference` (email or `user_id`).
32 text evidence files carry `retention_until` fields (for example 2031-12-31 on `audit_record_451`).

Traps [verified]:
- Emails can be upper case in evidence (`CHOI.JIHOON94@GMAIL.COM`).
- Near-duplicate decoys (`g.silva76@gmail.com` user_13 vs `g.silva76.jr@gmail.com` in `evidence_09`).
- Replica drift: `evidence_54` has `account_005` only in the failover table.
- Three different times: file `captured_at` (manifest), inner snapshot time (`evidence_02` captured 09-17 holds
  09-09..09-15 snapshots), and row `updated_at` (in `evidence_54` rows say 22:45, snapshot is 23:00).
- `evidence_90` (inventory 09-05) has only one INSERT: `snapshot_scope = account_service`, and zero data rows.
  Empty tables there prove nothing outside that scope.
- Capture times can sit minutes before `audit_at` (`evidence_56` 35 min, `evidence_92` 15 min). Compare full UTC timestamps, never dates.
- Compliant records can have **all identifiers null** (`analytics_901` in `evidence_56`, `analytics_1895` in
  `evidence_92`), so the record itself cannot show its owner.
- Tools on the dev machine: Python 3.14, `sqlite3`, Tesseract, `pdftotext`. `pypdf` missing in the base Python.

---

## 6. Worked sample cases

**case_01** (reported COMPLETE, truth COMPLETE). `amina.elmasri@gmail.com` -> `user_01`. audit_at 2026-09-03T11:30Z.
- `activity_3342` (08-20 16:41:43): DELETE_RECORD account_001 SUCCESS (claim). `reported_at` is 16:42:00.
- Answer: `VERIFICATION VERIFY_RECORD_ABSENT account_service account_001 evidence_54`.
- `evidence_54` (09-02) has no `account_001` in either table. Absence in an in-scope snapshot is proof.

**case_02** (reported PARTIALLY_COMPLETE, truth COMPLETE). Spanish. `activity_3376` is PARTIAL, but `evidence_54` proves absence.

**case_04** (truth COMPLETE). Answer: `account_004` ABSENT via `evidence_54`; `analytics_901` ANONYMIZED via `evidence_56`.
`account_004` occurs in no text evidence, no activity row, no PDF and no OCR text [verified]. `analytics_901` occurs only in
`evidence_56` (all identifiers null) and `activity_3463` (ANONYMIZE, 08-27 08:47, 7 minutes before `reported_at`).
The ownership link is not visible (open question 1).

**case_05** (truth INCOMPLETE). `account_005` survives in the failover replica of `evidence_54`. The finding cites
`evidence_54`, not the newer `evidence_90` (09-05, empty, scope `account_service` only). A positive observation of the
non-compliant copy wins over a scoped empty table.

**case_07** (truth INCOMPLETE). Request: "delete my account and the identity document I sent to support".
Answer: `support_001` REMAINING via `evidence_58` (PDF) -> DELETE -> verify; `account_007` verify ABSENT.
`object_19` is not in the answer, although `activity_4007` (02-13, before audit) says it belongs only to user_07 and
`evidence_46` shows it. `object_19` is `delivery_confirmation_19.pdf` in `object_storage`; no rule has an object-storage category.

**case_11** (reported COMPLETE, truth INCOMPLETE). `user_32`, audit_at 2026-10-01T12:00Z.
`evidence_03` (handover TXT, captured exactly at audit_at) shows: account_4248 NOT_FOUND, search_052 FOUND,
analytics_2034 IDENTIFIABLE, support_864 IDENTIFIABLE, data_flow_9522 ACTIVE, audit_record_9394 FOUND (subject `user_32`).
```
FIND REPORT_REMAINING_RECORD   search_service      search_052        evidence_03
FIND REPORT_EXPOSED_PII        analytics_platform  analytics_2034    evidence_03
FIND REPORT_EXPOSED_PII        support_platform    support_864       evidence_03
FIND REPORT_ACTIVE_DATA_FLOW   integration_service data_flow_9522    evidence_03
REME DISABLE_DATA_FLOW         integration_service data_flow_9522
REME DELETE_RECORD             search_service      search_052
REME REDACT_RECORD             support_platform    support_864
REME ANONYMIZE_RECORD          analytics_platform  analytics_2034
VERI VERIFY_RECORD_ABSENT      account_service     account_4248
VERI VERIFY_RECORD_ABSENT      search_service      search_052
VERI VERIFY_RECORD_PRESENT     security_service    audit_record_9394
VERI VERIFY_RECORD_REDACTED    support_platform    support_864
VERI VERIFY_RECORD_ANONYMIZED  analytics_platform  analytics_2034
VERI VERIFY_DATA_FLOW_DISABLED integration_service data_flow_9522
```

**case_25** (truth COMPLETE, verify-only request). `account_3136` ABSENT, `audit_record_451` PRESENT (retention until
2031-12-31), `analytics_1895` ANONYMIZED, all cite `evidence_92` (captured 15 min before audit_at).

Sample-wide [verified]: 75 cited ids, all `evidence_*`; 118 empty ids. Security-audit verification appears in
cases 03, 09, 11-32 and not in 01, 02, 04-08, 10. Systems in answers: account_service, search_service,
support_platform, analytics_platform, security_service, integration_service, backup_service, export_service, identity_service.

---

## 7. Approach choice

### 7.1 Options

| Option | Verdict |
| --- | --- |
| Deterministic rule engine (decision tables) over a global evidence fact store | **Core of the solution** |
| LLM agent that reads all evidence per case | Rejected as core: costly, non-deterministic, hard to order exactly. LLM only for offline extraction help (7.3) |
| Learned decision models (trees, boosting, neural / JEPA-style) | Rejected (7.2) |
| Typed decision-model API (Jev, TypeSafe AI) | Rejected for v1 (appendix A). Considered-and-rejected story for the interview |

### 7.2 Why not learned decision models

1. Only 32 labeled samples, 0 NOT_APPLICABLE. Too few to learn 15 rules, 9 systems, 15 operations.
2. The answer is an ordered list of steps with exact ids, not one label. Status follows from the steps.
3. `deletion_rules.csv` is already an explicit decision table. Encoding it is exact; learning it adds error.
4. Most score comes from retrieval: identity, ownership links, parsing, time cutoff. A classifier does not do this.
5. The contract wants deterministic, explainable output (AGENTS.md 6.7; AI interview).

A DMN-style decision table is used: `policy.py` holds the rules as data.

### 7.3 LLM use: live + cached (decision D18, supersedes the earlier "0 calls" rule)

- **Model**: `meta/muse-spark-1.3` (multimodal) via ZenMux, OpenAI-compatible API. Key from `ZENMUX_API_KEY` only.
  Base URL and model id are config values in `code/config.py`; never hardcode the key.
- **Images (11 PNG) and PDFs (4)**: the final run sends each file to muse-spark with a strict JSON-schema prompt
  (rows of `system_id, resource_id, category, state, identifier, observed_at`). Local text extraction
  (`pdftotext` / PDF text layer) runs first and is sent with the PDF as a cross-check. Output is validated
  (ids match known patterns, states in an enum); invalid output is retried once, then flagged.
- **Intent**: deterministic clause rules decide first. Only texts the rules mark AMBIGUOUS go to muse-spark,
  batched, with an enum answer (`DELETE`, `VERIFY_DELETE`, `NOT_DELETION`). No per-text label table (AGENTS.md 6.7).
- **Cache**: key = SHA-256(source bytes or text) + prompt version + model id. The final full run starts from a cold
  cache so `usage_report.md` shows real calls, tokens and cost. The run then exports the validated results to
  `code/llm_snapshot.py` (Python data, visible to the judge). With no key, `main.py` replays that snapshot, so the
  judge can still run offline. A human reviews the image/PDF rows once before the final run.
- **Decisions stay deterministic**: the LLM only turns pixels/text into facts or labels. The rule engine decides
  every state, status and step. `usage_report.md` lists calls per purpose (vision, intent) and overall totals.

### 7.4 Bounded investigator agent (D19) and safety (D20)

Grading context (research, 2026-10-24): code ZIP 30% (agent architecture 30%, prompt/tool craft 30%, robustness 25%,
rigor 15%; only observable code counts), output 30% (+ one safety score), interview 30%, transcript 10%.
Past winners: "the model reads and proposes; deterministic code decides and validates". One agent, 2-4 narrow tools.

- **Investigator agent** (`code/agent/`): one muse-spark tool loop, run only for items the deterministic pass leaves
  `UNKNOWN` (unlinked resources, conflicting observations, AMBIGUOUS intent). Tools:
  `search_evidence(query)` (BM25 + exact-id grep over raw text and facts), `read_evidence(file_id)` (parsed rows;
  vision rows for PNG/PDF), `query_facts(resource_id | identifier)`, `submit_proposal(...)` (typed: link / state / intent).
- **Code owns the verdict**: a proposal is accepted only if every cited id was opened in this loop, and the cited
  row really contains the resource id plus a user identifier or typed link. Accepted proposals add medium edges;
  the resolver and policy still decide. Caps: 4 tool iterations, 2 retries, timeout per call, per-case budget.
- **Ablation**: the evaluation report scores the samples with agent off/on. Keep it on only if F1 is not worse.
- **Safety (D20)**: all dataset text is untrusted data. Screen request texts and extracted evidence text for
  injection patterns before any model call; wrap data in delimiters; the model never sets status or steps;
  output that fails the schema falls back to the deterministic result. Adversarial tests in the evaluation suite.
  No injection text found in CSV/JSON/log/SQL/TXT (grep, 2026-10-24); PNG/PDF checked in milestone 4.
- **Single contract (D21)**: `code/schema.py` holds enums, the operation table, sort order and Pydantic v2 models.
  Prompts, LLM-output validation, the planner and `validate.py` all import it.
- **Traces (D22)**: per-case JSONL trace (rules fired, facts, model calls, tokens, retries); summaries in `.md` reports.

---

## 8. Architecture

Stages: `extract (global, once) -> index -> per case: intent -> identity -> discover -> ownership -> resolve state ->
policy -> cite -> plan -> serialize -> validate`.

```
code/
  main.py               # entry: python code/main.py -> ./output.csv (live+cache, or snapshot replay with no key)
  config.py             # ZenMux base URL, model id, prompt versions, paths (no secrets)
  llm_client.py         # OpenAI-compatible ZenMux client; usage accounting per call
  llm_cache.py          # content-hash cache; export/replay of llm_snapshot.py
  llm_snapshot.py       # committed, validated LLM results (generated by the final run)
  loaders.py            # CSV loading, UTC time parsing, normalization
  facts.py              # global fact store (in-memory SQLite), built once from all extractors
  evidence/
    extract_sql.py      # sqlite3 executescript per file; table -> (system_id, physical_copy); snapshot_scope
    extract_json.py     # 4 JSON shapes -> observations
    extract_log.py      # format dispatcher per line: key="value", JSON payload, syslog, bracketed, pipe
    extract_text.py     # TXT handover; PDF text layer (cross-check input)
    extract_vision.py   # muse-spark image/PDF -> validated rows (schema + id patterns)
  coverage.py           # per-file parse accounting; fails loudly on unparsed lines
  intent.py             # clause-level deletion-intent rules
  identity.py           # as-of identifier resolution
  links.py              # typed, time-stamped ownership graph
  resolver.py           # state per physical copy at audit_at (incl. UNKNOWN / CONFLICT)
  policy.py             # rule truth table (section 9.5)
  citation.py           # evidence selection, separate from state
  planner.py            # step generation and canonical sort
  trace.py              # per-case decision trace (subject edge -> resource -> observation -> rule -> step)
  validate.py           # output and packaging validator
  prompts/              # prompt Markdown files (vision extraction, ambiguous intent)
  evaluation/
    main.py             # scorer + conformance + metamorphic tests
    custom_cases/       # hand-made cases (also described in the report)
    evaluation_report.md
    usage_report.md
  README.md
```

### 8.1 Fact model

```
Observation(obs_id, file_id,
            available_at,       # manifest captured_at: the cutoff filter uses this
            state_observed_at,  # when the state was inspected (snapshot time, observed_at, log line time)
            record_updated_at,  # last mutation inside the row (updated_at), may be earlier
            system_id,          # logical service (account_service), not the replica name
            physical_copy,      # primary | failover_replica | read_replica | replica_eu_west | ...
            resource_id, record_type,
            exists,             # PRESENT | ABSENT | UNKNOWN
            identifiers,        # emails, user_ids, phones, hashes, names in the row (null-aware)
            fields,             # raw fields for rule conditions (status, email_opt_in, retention_until, ...)
            flow_state,         # ACTIVE | DISABLED | None
            restore_state,      # OPEN | BLOCKED | None
            scope,              # what the file claims to cover (snapshot_scope / subject list / table)
            assertion_type,     # state_readback | scoped_absence | ownership_link | operation_claim | policy_fact
            source_detail)      # table / JSON path / line number
```

- Each extractor defines its own time semantics. Inner times after `audit_at` are dropped too.
- Absence is emitted only for a resource known to the case and only inside the file's declared scope.
- Identifier exposure is separate from existence: a PRESENT retained record can still break policy.

### 8.2 Ownership graph (`links.py`)

Edges `(subject identifier) -> (resource)` and `(resource) -> (resource)`, each with type, time and source id:
- strong: `user_id` or email/hash/phone in the same row; `subject_reference`; `LINK_RESOURCE_IDENTITY` rows;
  `source_resource_id`; search-query and lookup traces where `lookup_key` = an email of the subject;
- medium: same trace id in a log; sync rows ("repopulated downstream resource X") from a linked flow;
- never: numeric suffix, file proximity, names alone, row position.
Only edges with time `<= audit_at` count. Build the graph once, globally; per case it is a neighborhood query.

---

## 9. Algorithm per case

1. **Intent** (`intent.py`), clause-level:
   - positive: delete/erase/close account (multilingual: eliminar, exclusão, suppression, 削除, 삭제, ...);
     also "verify/complete/audit a prior deletion" (case_25, case_27).
   - negative applies to its own clause only: "not asking for deletion", "marketing lists only", export, copy,
     access, correction, login, invoice. A clause that keeps something ("keep anonymous statistics", case_04) is an
     exception inside a deletion, not a rejection.
   - Undecidable text -> log as `UNKNOWN_INTENT` in the trace and fix the rules during development.
2. **Identity** (`identity.py`): normalize email (trim, lower). Resolve `user_id` via current snapshot and audit log,
   following chains (case_10). Collect all emails, phones, name, SHA-256 of every email. As-of `audit_at`; assert no future value is used.
3. **Discover**: neighborhood of the subject in the ownership graph (8.2), bounded closure over strong/medium edges.
4. **Resolve state** (`resolver.py`):
   - Drop facts with `available_at > audit_at`, then inner times `> audit_at`.
   - Resolve **each physical copy separately**. A missing primary row never hides a surviving replica row.
     Report with the logical `system_id` and original `resource_id` (case_05, case_16).
   - Dominance within one physical copy: in-scope state read-back > scoped absence > activity read-back > operation claim;
     newest `state_observed_at` wins only inside the same tier. Different scopes never supersede each other.
   - Outcome per target: compliant, violating, `UNKNOWN` (no admissible proof) or `CONFLICT` (equal-tier disagreement).
   - Delete followed by sync (case_05: `activity_3482` then `activity_3483`): the surviving copy is the proof; add a
     data-flow target only when evidence shows an active flow.
   - Data flows: `CHECK_DATA_FLOW` read-backs and connector evidence. Backups: restore risk needs evidence that restore
     is open (case_09 needs BLOCK_RESTORE; cases 26-28 verify BLOCKED only); backup existence alone is not a risk.
5. **Policy** (`policy.py`): category from record content, not id prefix (case_12: `analytics_9914` is a contact lookup with
   `email_opt_in` -> delete, not anonymize). Rule truth table:

   | Rule | Category | Condition (proof needed) | True -> action / verify | False | Unknown |
   | --- | --- | --- | --- | --- | --- |
   | 01 | USER_PROFILE | Always | DELETE / ABSENT | - | - |
   | 02 | SECONDARY_IDENTIFIER | Always | DELETE / ABSENT | - | - |
   | 03 | SEARCH_INDEX_ENTRY | Always | DELETE / ABSENT | - | - |
   | 04 | CACHE_ENTRY | Always | DELETE / ABSENT | - | - |
   | 05 | SUPPORT_MESSAGE | Shared customer/agent/order context (message fields) | REDACT / REDACTED | DELETE (H) | REDACT (H) |
   | 06 | SUPPORT_ATTACHMENT | Belongs only to subject (ownership link, e.g. `evidence_58`) | DELETE / ABSENT | REDACT (H) | trace flag |
   | 07 | ANALYTICS_PROFILE | Still attributable (identifiers non-null) | ANONYMIZE / ANONYMIZED | compliant | trace flag |
   | 08 | PRODUCT_TELEMETRY | Still attributable | ANONYMIZE / ANONYMIZED | compliant | trace flag |
   | 09 | USER_EXPORT | Always | DELETE / ABSENT | - | - |
   | 10 | MARKETING_PROFILE | Always | DELETE / ABSENT | - | - |
   | 11 | EMAIL_DELIVERY_LOG | Contains a user email | REDACT / REDACTED | compliant | trace flag |
   | 12 | SECURITY_AUDIT_LOG | `retention_until > audit_at` | RETAIN / PRESENT | DELETE (H) | RETAIN (H) |
   | 13 | LEGAL_HOLD_RECORD | Hold active at `audit_at` (register PDF `evidence_27`, activity) | RETAIN / PRESENT | DELETE (H) | RETAIN (H) |
   | 14 | BACKUP_ARCHIVE | Restore access can be blocked | RETAIN + BLOCK_RESTORE / BLOCKED | trace flag | trace flag |
   | 15 | ACCOUNT_TOMBSTONE | Account deleted, only `user_id` needed | REDACT / REDACTED (keep `user_id`, clear name/email/phone/hash) | - | - |
   | - | DATA_FLOW | Active sync/import for the subject | DISABLE / DISABLED | compliant | trace flag |
   | - | Out of rules (e.g. `object_storage`) | - | not a target (case_07 `object_19`) | - | - |

   (H) = hypothesis: no sample shows this branch; implement it, flag it in the trace, and list it in the evaluation report.
   Retained record missing at `audit_at`: no allowed finding expresses it. Hypothesis: INCOMPLETE +
   `VERIFY_RECORD_PRESENT` with `""` and no finding step.
   Tombstone (cases 31/32, `evidence_51`): `subject_reference` kept and identifiers cleared = compliant;
   `account_status="DELETED"` with identifiers -> REPORT_EXPOSED_PII -> REDACT_RECORD.
6. **Decision**: COMPLETE only if every target is compliant **and** has admissible proof. An empty target set, or any
   `UNKNOWN`/`CONFLICT` target, never yields COMPLETE silently: it goes to the trace and the evaluation failure list.
7. **Cite** (`citation.py`, separate from state): after the state is fixed, pick the evidence among the observations that
   support it, for that physical copy. Order: positive in-scope file observation > scoped absence file > activity read-back
   (`activity_id`) > audit-log fact (`audit_id`). Newest inside a tier; equal-time tie -> lowest `file_id` (H).
   Samples cite only files; activity/audit ids are allowed by the contract and used only when no file proves the state.
   Keep this module swappable so two policies can be compared on the samples.
8. **Plan** (`planner.py`):
   - FINDING per violation; REMEDIATION per violation (`""`); VERIFICATION exactly one per target
     (compliant ones too: 36 such steps in the samples). INCOMPLETE -> `""`; COMPLETE -> citation.
   - Canonical sort (section 3), fixed key order, `json.dumps(separators=(",", ":"))`.

---

## 10. Evaluation plan

`code/evaluation/main.py`:
- **Conformance**: all 32 samples (they shaped the design, so they are a development set, not a hold-out).
- Metrics: status accuracy; exact whole-answer accuracy; step-level precision/recall/F1 (multiset, without `step_no`);
  field-level accuracy over aligned steps; citation accuracy; target-discovery recall; sequence accuracy (exact + LCS).
- Per-case diff of missing/extra steps with the decision trace. Sample mismatches are findings; no case-specific patches.
- **Metamorphic tests**: shuffle input rows -> same output; add post-`audit_at` evidence -> same output; change email case
  -> same output; add a near-match decoy -> same output; add an out-of-scope empty table -> no absence; add a surviving
  replica -> status becomes INCOMPLETE.
- **Custom cases** (at least 3 in the report; frozen before tuning): negated deletion text; non-English non-deletion;
  verify-only request; historical email chain + delete then sync; same email in two cases with different `audit_at`;
  record in two replicas (one step); evidence after `audit_at`; equal-time contradiction; expired retention; missing
  ownership link.
- **Coverage report**: per evidence file: format, rows parsed, rows rejected, unresolved fields.
- **Validator**: 518 rows in numeric case order, valid JSON (CSV quoting round-trip), consecutive `step_no`, allowed
  phase/operation/state pairs, empty `evidence_id` in INCOMPLETE remediation/verification, no cited evidence after `audit_at`.
- **Clean-room test**: unzip `code.zip` elsewhere, add only `dataset/`, no API key, no network, run the README command,
  compare the output hash with the dev run.

---

## 11. Milestones (vertical slice first)

Event: 2026-10-24 18:00 IST to 2026-10-25 18:00 IST. Target submit by 15:30 IST, then the interview. Sleep 3 h.

| # | Milestone | Budget | Cut line |
| --- | --- | --- | --- |
| 1 | Loaders, identity, intent rules, validator; NOT_APPLICABLE + empty outputs for all 518 | 2 h | - |
| 2 | Vertical slice: JSON + TXT + SQL extractors, fact store, resolver, policy, planner on case_01/05/11 | 5 h | - |
| 3 | Logs dispatcher + coverage report; ownership graph | 4 h | Drop medium edges if not stable |
| 4 | ZenMux client + cache; muse-spark vision + ambiguous intent; investigator agent (7.4) + ablation; injection screen; `llm_snapshot.py` replay | 4 h | Agent off if ablation is worse |
| 5 | Iterate on 32 samples + metamorphic tests | 5 h | Stop tuning at hour 20 |
| 6 | Full run, clean-room test, reports, README, `code.zip` | 3 h | - |
| 7 | Interview prep from decision traces | 1 h | - |

Logging: `log.txt` is a required deliverable. The main Claude Code build chat logs per AGENTS.md from milestone 1. The separate prompt-writing chat is never logged.
Git: feature branch, one commit per milestone after its checks pass. Codex (`gpt-5.6-sol`, high) reviews after milestone 5.

---

## 12. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Missing ownership links (null-identifier records) | Missed targets -> wrong status on COMPLETE cases | Global ownership graph; `UNKNOWN` never becomes COMPLETE silently |
| Wrong citation choice | Lost evidence points | Separate `citation.py`; compare two policies on samples |
| Lexicographic row sort | Whole file misaligned | Numeric sort + validator check |
| Image/PDF misread | Missed records | Reviewed static module + source hashes |
| Time leakage | Wrong state | Three time fields; one cutoff function; metamorphic test |
| Judge has no network/keys | Crash or empty output | Snapshot replay without key; per-case error isolation; clean-room test |
| muse-spark misreads ids / invalid JSON | Wrong or missing facts | Schema + id-pattern validation, one retry, PDF text cross-check, human review |
| Untested policy branches (H) | Wrong action on hidden cases | Flag in trace; list in report |
| Logging gap in `log.txt` | Transcript weaker in judging | Start logging at milestone 1 (user decision) |

---

## 13. Open questions (ranked by score impact)

1. **Ownership links for records with no identifiers.** case_04: `account_004` occurs nowhere in participant text,
   activity, PDF or OCR output; `analytics_901` only in `evidence_56` (null ids) and `activity_3463`. case_01: `account_001`
   only in `activity_3342`. case_25: `analytics_1895` only in null-id rows (`evidence_92`, `evidence_02`) and `activity_3602`.
   Facts: the worker activity for these resources falls just before the case's `reported_at`
   (case_01: 17 s; case_04: 7 min; case_25: 29 min). But a pure `[requested_at, reported_at]` worker window
   recalls only 44 of 111 sample targets and adds 539 extra resources, so it is not a safe link alone.
   Next: OCR the images with `_`-tolerant matching; check if the request -> worker-job link (time + `reported_at` +
   same job burst) is precise enough as a medium edge; otherwise accept the miss.
2. **Target inclusion.** What makes a security-audit record a target (present in 24 cases, absent in 01, 02, 04-08, 10)?
   Is it just "an admissible record with `subject_reference` = user exists before `audit_at`"?
3. **Citation ties** for same-tier, same-time observations, and when activity/audit ids are preferred.
4. **Untested policy branches** (H rows in 9.5), and a retained record that is missing.
5. **`object_19` exclusion** (case_07): out-of-rules category is the leading reason; request scope ("identity document")
   is the alternative. Check other `object_*` rows.

---

## 14. Decision log

| # | Decision | Reason |
| --- | --- | --- |
| D1 | Deterministic rule engine as the core | Explicit rules, exact ordered output, 32 labels only |
| D2 | Superseded by D18 | - |
| D3 | No learned decision model | Section 7.2 |
| D4 | Activity rows are typed by assertion; operation claims are never state proof | Contract: results are claims; read-backs and links are still useful |
| D5 | Inclusive `audit_at` cutoff, full UTC timestamps | case_11; captures minutes before cutoff |
| D6 | Jev dropped for v1 | 4 of 5 R2 reviewers; does not help retrieval; extra provider (appendix A) |
| D7 | Resolve each physical copy separately; report logical system + original id; one step per target | cases 05/16 |
| D8 | Three time fields; cutoff on `available_at` and inner times | `evidence_02`, `evidence_54` |
| D9 | Absence only inside declared scope | `evidence_90` vs case_05 |
| D10 | Category from record content | case_12 |
| D11 | Untested policy branches implemented as flagged hypotheses | Rules/samples silent; reviewers asked for defined behavior |
| D12 | Mandated canonical sort; dependency order internal only | `problem_statement.md` |
| D13 | Numeric `case_id` order | Input file order; lexicographic differs |
| D14 | `UNKNOWN`/`CONFLICT` internal states; no silent COMPLETE | R2 |
| D15 | Validated LLM results committed as `code/llm_snapshot.py` | Judge ignores `.json`; offline replay |
| D16 | Intent: clause-level rules; verify/audit requests are deletion | case_25, case_27, case_534, case_538 |
| D17 | Separate `resolver.py` and `citation.py` | Citation choice must not change state |
| D18 | `meta/muse-spark-1.3` via ZenMux, live + cached in final run | User decision; real usage report; multimodal |
| D19 | Bounded investigator agent for UNKNOWN items; code validates every proposal | Agent-architecture rubric; open question 1 |
| D20 | Injection screen before model calls; model never sets status/steps | Output safety score |
| D21 | `schema.py` single source of truth (Pydantic v2) | Prevents prompt/validator drift |
| D22 | Per-case JSONL traces + `.md` summaries | Interview, robustness evidence |

---

## 15. Review history

| Round | Reviewer | Status | Accepted changes |
| --- | --- | --- | --- |
| R1 | Codex `gpt-6.1-sol` (high), read-only check of 32 samples / 193 steps | Done | D7-D12 (v3) |
| R2 | 5 external reviewers (A-E), scores 8.5 / 8 / 7 / 8 / 7 | Done | See below |
| R3 | Next reviewers | Open | Focus on section 13 items 1-2 and the (H) branches |

R2 accepted: numeric row order (C, verified); mandated sort cited from the contract (D, E); assertion-typed activity (A, B);
citation module with tiers and activity/audit fallback (A, B, D, E); `UNKNOWN`/`CONFLICT` + coverage (B); three time fields (B);
clause-level intent + verify/audit class (B, D, verified); global fact store and ownership graph (A, B, C, D, E);
rule truth table incl. false/unknown branches (A, D, E); retention via `retention_until` (D, verified);
offline runtime, committed static extractions, clean-room test, per-case isolation (A, B, C, E);
metamorphic tests and honest dev-set reporting (B, E); time-boxed milestones (C); one step per multi-copy target (C);
Jev dropped (A, B, C, D, E majority).

R2 rejected or changed: topological override of the sort (E) - contract mandates the sort; committed per-text intent lookup (A) -
risks "hardcoded labels", rules fixed instead; resume `log.txt` now (A) - user decision, scheduled for milestone 1;
`object_19` excluded by time (A, D) - false, `activity_4007` is 02-13 and `evidence_46` 02-13, both before case_07 audit_at;
identity future-leak risk (A, B, E) - checked, 0 cases affected, kept as an assertion only.

---

## Appendix A. Jev (TypeSafe AI) - considered and rejected for v1

- Non-generative "decision model": returns typed answers only (Choice up to 255 options with probabilities, Score,
  Yes/No; Box from 1.14). Early access about 2026-09-15.
- Jev 1.14 (2026-10-14): experimental PNG/JPEG input behind `TypeSafe-Danger-Zone-Images: true` (reviewers report
  image input also works on 1.13; limits 280-1568 px per side per docs.typesafe.ai, one blog says 256; <= 16 MiB per file;
  about 4 images per request), Box type, longer context (sources disagree: 32K / 64K / 262K opt-in).
  TypeSafe says it is not for production and weaker on images than text.
- Why rejected: it cannot transcribe ids or emails from screenshots; retrieval, ownership and step building are the hard
  parts and it does none of them; intent is solved by rules; extra provider, key and failure mode.
- Possible later experiment: a Yes/No gate for rule conditions (5, 6, 11) on extracted text.

Sources: https://docs.typesafe.ai/images , https://typesafe.ai/blog/jev-1-14 ,
https://www.marktechpost.com/2026/10/14/typesafe-ai-jev-1-14-images-box-long-context/ ,
https://pasqualepillitteri.it/en/news/26048/jev-1-14-image-input-box-typesafe-warns ,
https://datanorth.ai/blog/jev-what-it-is-and-why-this-new-model-matters
