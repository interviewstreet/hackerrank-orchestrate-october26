# 02 — Architecture (the design to build)

## 1. Principles

1. **Evidence → Facts → Decisions.** Parse every evidence file once into a normalized *fact table*. All audit logic runs on that table, never on raw files.
2. **Deterministic core, LLM at the edges.** Same input → same output. LLM only classifies request intent (batched, cached) and optionally reads hard screenshots (cached). A `--no-llm` mode must still produce a full output.
3. **Time-correct.** For case `c`, only facts with `time <= c.audit_at` exist.
4. **Policy-driven.** Treatments come from `deletion_rules.csv` mapped to resource categories, not from case-specific code.
5. **Explainable.** Every step is traceable to a fact (`fact_id` → file/activity/audit ID). Keep a per-case debug trace for evaluation and the interview.

## 2. Folder layout (inside the repo)

```
repo-root/
  AGENTS.md  README.md  log.txt  output.csv     <- output.csv written by main.py
  dataset/                                      <- NOT zipped
  code/
    main.py                  # CLI entry: python3 code/main.py [--no-llm] [--cases case_05,...] [--debug]
    audit/
      __init__.py
      config.py              # paths, constants, op order tables, category map
      loaders.py             # CSV loaders, time parsing (UTC), id normalization
      identity.py            # IdentityResolver
      intent.py              # request classification (LLM + rules + cross-checks)
      facts.py               # Fact dataclass + FactStore (index by resource, email, hash, user_id, time)
      parsers/
        sql_parser.py        # sqlite in-memory execution of .sql snapshots
        json_parser.py       # service_resource_export / snapshot_bundle / records-ledger shapes
        log_parser.py        # key=value + syslog + structured dialects
        text_parser.py       # handover .txt
        pdf_parser.py        # pdftotext/pdfplumber
        image_parser.py      # tesseract OCR (+ optional LLM vision, cached)
      activity.py            # system_activity -> facts (claims) + flow/backup state timelines
      state.py               # StateReconstructor (state of each resource at audit_at)
      policy.py              # deletion_rules.csv -> RuleBook; category -> required end-state
      planner.py             # findings/remediation/verification generation + ordering
      writer.py              # output.csv writer + validator
      llm.py                 # thin provider wrapper, caching, token accounting
    prompts/
      intent_classifier.md   # prompts live in source/markdown (judge reads them)
      vision_extract.md
    evaluation/
      evaluate.py            # metrics vs sample_output.csv
      custom_cases/          # >=3 hand-made cases (as .py/.md, not only csv)
      evaluation_report.md   # REQUIRED
      usage_report.md        # REQUIRED
      data_notes.md
    cache/                   # llm_cache.json, ocr_cache.json (can be deleted; regenerated)
  README.md                  # (copy also at repo root; zipped with code)
```

## 3. Data model

```python
@dataclass(frozen=True)
class Fact:
    fact_id: str          # stable id, e.g. f"{evidence_id}#{n}"
    source_id: str        # evidence_xx | activity_xxxx | audit_xx  (what gets cited)
    source_kind: str      # "evidence" | "activity" | "audit"
    observed_at: str     # ISO UTC (inner timestamp if present else manifest captured_at)
    system_id: str        # account_service, search_service, ...
    resource_id: str      # account_005, search_001, ...
    category: str         # USER_PROFILE, SEARCH_INDEX_ENTRY, ... (from resource family/table)
    presence: str         # PRESENT | ABSENT | UNKNOWN
    fields: dict          # normalized identifiers: email, email_hash, phone, name, user_id, ...
    topology: str         # primary | failover_replica | read_replica | regional | reporting | n/a
    flags: dict           # data-flow enabled?, restorable?, marker_found?, anonymized?, redacted? ...
    is_claim: bool        # True for activity/log "SUCCESS" claims
```

`FactStore` indexes: by `resource_id`, by lower-case `email`, by `email_hash`, by `user_id`, by `phone`, sorted by `observed_at`.

## 4. Pipeline per case

```
request ──► [intent] ─ non-deletion ─► NOT_APPLICABLE, []
              │ deletion
              ▼
        [identity]  request.email → user_id; ids = {emails, hashes, phones, user_id, name?} up to audit_at
              ▼
        [link]      resources that belong to the user:
                       a) any fact whose email/hash/phone/user_id ∈ ids
                       b) resources named by LINK_RESOURCE_IDENTITY events for those ids
                       c) resources that share a record/row with (a) (e.g. same SQL row, same JSON record)
              ▼
        [state]     for every (system, resource, topology): latest fact with observed_at ≤ audit_at
                    + timeline of flows/backups (enable, disable, block, restore events ≤ audit_at)
              ▼
        [policy]    required end-state per resource category (DELETE/REDACT/ANONYMIZE/RETAIN/TOMBSTONE)
              ▼
        [compare]   violations:
                       PRESENT but must be ABSENT            → REMAINING_RECORD
                       PRESENT with direct IDs but must be
                         REDACT/ANONYMIZE                    → EXPOSED_PII
                       active flow that touches user data    → ACTIVE_DATA_FLOW
                       restorable backup containing user     → RESTORE_RISK
                       retained record missing               → (policy violation; see §8)
              ▼
        [plan]      INCOMPLETE if any violation else COMPLETE → build ordered steps
              ▼
        [write]     validate + write row
```

## 5. Identity resolution

- Load `user_identities` (current) and `user_audit_log` (history: `email`, `email_hash`, `phone` old/new).
- `by_email[lower(email)]` for current **and** every `old_value`/`new_value` of `email` events → `user_id`. Same for hash and phone.
- Resolve request email → `user_id`. If it matches no one (0 cases now) → mark unresolved, fall back to evidence search by email.
- **Identifier set up to `audit_at`:** all emails the user has had (current, old); their hashes (`sha256(lower(email))` plus logged hashes); phones (current + old); `user_id`; name (used only as a secondary hint, never to link alone).
- Edge: an identity change dated **after** `audit_at` should not add identifiers *unless* it is the same person's older value (old values are always historical, so they are safe to include). Test this on samples that mention "used a different email before".

## 6. Intent classification (the only required LLM use)

1. **Cheap rules first** (multilingual stems for "delete/erase/close/remove" in the languages seen) give a prior, never the final answer for ambiguous text.
2. **LLM batch call** (e.g., 25 unique texts per call, JSON out: `{"id":..,"intent":"DELETE|NON_DELETE","reason":"..."}`), temperature 0, cache by SHA of text. 375 unique texts → ~15 calls, a few thousand tokens total.
3. **Decision rule:** `DELETE` only if the person asks to erase/close/remove the **account or personal data**. `NON_DELETE` for access/export/correction/change/marketing-only/login help/"do not delete". Mixed ("remove me from marketing only") → NON_DELETE. A request that says "I'm not asking for deletion" → NON_DELETE.
4. **Cross-check:** compute the set of emails whose accounts have a `CLASSIFY_REQUEST non-deletion` activity (via evidence rows that show those account IDs with the email). Disagreement between LLM and cross-check → log for human review in `data_notes.md`; prefer the text meaning but investigate.
5. Output includes a `reason` for the interview.

## 7. Evidence parsers (one job each; all emit `Fact`s)

| Format | Method | Key output |
|---|---|---|
| `.sql` | Create `sqlite3.connect(":memory:")`, `executescript(text)` (strip/ignore `PRAGMA`); iterate all tables; header comments → `captured_at`, `topology`. Each row → Fact (PRESENT) with fields from columns. Map table → category (`customer_profiles*`→USER_PROFILE, `*search_documents*`→SEARCH_INDEX_ENTRY, `*analytics*`, `support_records`, `*email_delivery*`, `*cache*`, `*export*`, `*marketing*`, `*tombstone*`, …). Also emit **ABSENT facts** for resource IDs known from other sources but missing from this snapshot *only when the snapshot's table clearly covers that resource family* (see §9) | per-row facts incl. which replica |
| `.json` | Detect shape: `service_exports`, `snapshots[]`, `records[]` (ledger), flat export lists. `status_code 404`/`result NOT_FOUND`/`profile null` ⇒ ABSENT; `200`/`FOUND` ⇒ PRESENT (+ which fields are non-null: a profile with only `email` set is **exposed PII**; all null except `customer_reference` ⇒ compliant tombstone) | facts with inner timestamps |
| `.log` | Regex `key=value` pairs; map events: `profile_lookup_completed rows=0 http_status=404` ⇒ ABSENT, `rows>=1`/`200` ⇒ PRESENT; `deletion_marker_check marker_found=false` ⇒ deletion not recorded; connector/flow lines ⇒ flow flags; restore lines ⇒ restore flags; `lookup_key=<email>` links resource to identity | facts; use per-dialect regex with a fallback "unknown line" counter |
| `.txt` | Split on `|`: `timestamp | system | resource | RECORD_TYPE | FOUND/NOT_FOUND | email` | facts |
| `.pdf` | `pdftotext -layout`; parse "Detail" key/values (customer name, `user_NN`, `support_NNN`, reference numbers, retention dates, hold status) | facts: support attachment / audit / legal-hold |
| `.png` | `tesseract` OCR → text → same key/value extractor. If OCR confidence is low or fields missing, optional LLM vision with a strict JSON schema, cached | facts: admin consoles, restore console, connector console, search inspector, etc. |

All parsers: lowercase+strip emails; normalise phones (digits and leading +); record the original line/row reference for debugging.

## 8. Policy engine (from `deletion_rules.csv`)

Map every fact's `category` to a rule; derive required end-state:

| Category | Rule | Required end-state | Violation if | Remediation | Verification |
|---|---|---|---|---|---|
| USER_PROFILE (account) | DELETE | ABSENT in **all** topologies | present anywhere | DELETE_RECORD | VERIFY_RECORD_ABSENT |
| SECONDARY_IDENTIFIER | DELETE | ABSENT | present | DELETE | ABSENT |
| SEARCH_INDEX_ENTRY | DELETE | ABSENT | present | DELETE | ABSENT |
| CACHE_ENTRY | DELETE | ABSENT | present | DELETE | ABSENT |
| USER_EXPORT | DELETE | ABSENT | present | DELETE | ABSENT |
| MARKETING_PROFILE | DELETE | ABSENT | present | DELETE | ABSENT |
| SUPPORT_ATTACHMENT (owned only by subject) | DELETE | ABSENT | present | DELETE | ABSENT |
| SUPPORT_MESSAGE (shared context) | REDACT | exists, no direct identifiers | has name/email/phone | REDACT_RECORD | VERIFY_RECORD_REDACTED |
| EMAIL_DELIVERY_LOG | REDACT | exists, no email | contains email | REDACT | REDACTED |
| ANALYTICS_PROFILE / PRODUCT_TELEMETRY | ANONYMIZE | exists, not attributable | attributable (email, hash, phone, user ref) | ANONYMIZE_RECORD | VERIFY_RECORD_ANONYMIZED |
| SECURITY_AUDIT_LOG | RETAIN (within retention) | PRESENT | missing | none | VERIFY_RECORD_PRESENT |
| LEGAL_HOLD_RECORD | RETAIN (hold active) | PRESENT | missing | none | VERIFY_RECORD_PRESENT |
| BACKUP_ARCHIVE | RETAIN + block restore | PRESENT but restore BLOCKED | restorable and contains user | BLOCK_RESTORE | VERIFY_RESTORE_BLOCKED |
| ACCOUNT_TOMBSTONE | REDACT (keep `user_id`) | PRESENT with only `user_id` | name/email/phone/hash present | REDACT_RECORD | VERIFY_RECORD_REDACTED |
| (data flow) | n/a | DISABLED | enabled/active and touches user data | DISABLE_DATA_FLOW | VERIFY_DATA_FLOW_DISABLED |

Treat this table as a **starting hypothesis**; calibrate exceptions with the samples (e.g., how the `SUPPORT_ATTACHMENT` vs `SUPPORT_MESSAGE` condition is decided, retention dates vs `audit_at`, which `account_*` is "the account" vs a "tombstone"). Retention/legal-hold conditions must be checked **against evidence** (PDF retention extract, legal register, audit ledger) and `audit_at`, not assumed.

## 9. State reconstruction at `audit_at` (the heart of correctness)

For each `(system_id, resource_id)` the user touches (keep topology separate for databases):

1. Collect facts with `observed_at ≤ audit_at`.
2. Take the **latest evidence-backed observation** (non-claim). If it says PRESENT → present at `audit_at`. If ABSENT → absent.
3. **Claims** (activity `DELETE_RECORD SUCCESS`, `SYNC_RECORD`, `RESTORE_BACKUP`) adjust confidence but cannot prove state:
   - A claimed delete with no later contradicting evidence + a later ABSENT observation ⇒ ABSENT.
   - A `SYNC_RECORD` from a still-enabled flow *after* the last ABSENT observation ⇒ **recreation risk** (flow ACTIVE) even if the record is absent right now.
   - `RESTORE_BACKUP … repopulated downstream resource X` after a delete ⇒ X present again; restore path still restorable ⇒ RESTORE_RISK.
4. If there is **no evidence at all** for a resource that policy requires to be absent but activity claims deletion `SUCCESS`: treat as UNKNOWN. Decide using samples what the answer key does (likely COMPLETE needs an evidence citation, so absence of evidence usually means the case's resource isn't part of the relevant set).
5. **Replication drift:** a deleted profile present in a `failover/read/regional/reporting` replica table at the latest snapshot ≤ `audit_at` is a REMAINING_RECORD on `account_service` (check sample `case_05`).
6. Data-flow state: latest of {`CHECK_DATA_FLOW` (claim of status), connector config JSON/screenshot (evidence), `DISABLE_DATA_FLOW` (claim; verify with later config)}. Backup restore state: latest of {`CHECK_RESTORE_ACCESS`, backup console screenshot, `BLOCK_RESTORE`}.

## 10. Planner

```python
def plan(case, violations, retained_checks, compliant_checks):
    if not violations:                      # COMPLETE
        steps = [verify(...) for r in relevant_records_with_evidence]       # evidence_id = proving source
    else:                                   # INCOMPLETE
        findings     = [finding(v) for v in violations]                     # evidence_id = proving source
        remediation  = [fix(v) for v in violations]                         # evidence_id = ""
        verification = [verify(r) for r in all_relevant_records]            # evidence_id = ""  (H1)
    steps = dedupe(steps); steps.sort(key=(phase, op, system, resource)); renumber 1..N
```
Rules:
- Deduplicate identical `(phase, system, resource, op)`.
- One finding per offending (system, resource); a record needing two treatments (rare) → keep both only if the samples do.
- Disable flows and block restores **before** record changes (guaranteed by op order). The table's own order resolves "downstream before source".
- For COMPLETE, no REPORT/REMEDIATION steps; verification only.
- NOT_APPLICABLE → `[]`.

## 11. LLM usage and cost control

- Provider wrapper `llm.py` with: env-var key, `temperature=0`, JSON-only responses, retries, **disk cache keyed by SHA-256(prompt+model)**, token counters per model (`input_tokens`, `output_tokens`, `calls`) persisted to `evaluation/usage_stats.json` for the usage report.
- Batch classification of unique request texts (≈15 calls). OCR via tesseract (free). Vision LLM only as fallback for images where OCR parse fails; cache results.
- Choose a small/cheap model for classification (e.g., a Haiku-class model). Record model names exactly as used.
- `--no-llm`: rule-based intent using multilingual stems + the CLASSIFY cross-check; prints a warning listing texts it was unsure about.

## 12. Validation (`writer.validate`)

- Header exactly `case_id,deletion_status,steps_json`; 518 rows; case set equals input set; no duplicates; natural numeric order.
- `deletion_status ∈ {COMPLETE, INCOMPLETE, NOT_APPLICABLE}`; NA ⇒ `[]` and vice versa.
- Each step has exactly the 7 keys; `phase`/`operation`/`state` consistent with `OP_STATE`; `step_no` = 1..N.
- Evidence rule: phase FINDING or (status COMPLETE & VERIFICATION) ⇒ `evidence_id` non-empty and exists in `evidence_files.csv`, `system_activity.csv` or `user_audit_log.csv`, **and its time ≤ audit_at**; REMEDIATION and INCOMPLETE-VERIFICATION ⇒ `""`.
- Sort order check using the key above.

## 13. Edge-case matrix (test each)

| Situation | Expected behaviour |
|---|---|
| Request email is an OLD email | Resolve via audit log; search evidence under all identifiers |
| Evidence file captured after `audit_at` | Ignored and never cited |
| Reported COMPLETE but replica still has profile | INCOMPLETE; finding on `account_service` |
| Reported NOT_STARTED but all evidence shows clean | COMPLETE (claims don't decide) |
| Primary deleted; sync job still enabled | ACTIVE_DATA_FLOW finding; DISABLE + VERIFY_DATA_FLOW_DISABLED |
| Backup restorable | RESTORE_RISK; BLOCK_RESTORE; VERIFY_RESTORE_BLOCKED; backup itself not deleted |
| Tombstone has email/hash | EXPOSED_PII + REDACT; `user_id` must remain |
| Audit record within retention | RETAIN; VERIFY_RECORD_PRESENT; never deleted |
| Non-deletion request (any language) | NOT_APPLICABLE, `[]` — even if user's data appears in evidence |
| Same email requested twice | Two independent cases |
| UPPERCASE / mixed-case emails in evidence | Matched after normalization |
| Decoy: same name, different user | Not linked |
