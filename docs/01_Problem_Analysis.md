# 01 — Problem Analysis (verified against the real dataset)

Everything below marked **[VERIFIED]** I checked by running code on `dataset/`. Items marked **[HYPOTHESIS]** are patterns inferred from the 32 sample answers; your build must test them against `sample_output.csv` before relying on them.

## 1. Corrections to the Gemini plan

| Gemini said | Reality | Impact |
|---|---|---|
| `NOT_APPLICABLE` = person absent from `deletion_requests.csv` or requested after `audit_at` | **[VERIFIED]** Every case is in the file and `requested_at <= audit_at` always. Non-deletion is decided by the **meaning of `request_text`** | Need text understanding, not a lookup |
| Findings order: REMAINING, EXPOSED_PII, ACTIVE_DATA_FLOW | Also `REPORT_RESTORE_RISK` (4th). Order is the table order in the problem statement | Use the exact operation order below |
| Remediation: "DISABLE then DELETE/REDACT" | Exact order: DISABLE_DATA_FLOW → BLOCK_RESTORE → DELETE_RECORD → REDACT_RECORD → ANONYMIZE_RECORD | Sorting key must be the operation table order |
| Verification: ABSENT, REDACTED, DISABLED | Exact order: ABSENT → PRESENT → REDACTED → ANONYMIZED → DATA_FLOW_DISABLED → RESTORE_BLOCKED | Same |
| Scan only SQL/PDF | Evidence is **SQL, JSON (3+ shapes), logs, txt, PDF, PNG** | Need OCR for 11 PNGs |
| One lookup per user | Resources are not labeled by case; link through email, hash, user_id, phone, name, plus `LINK_RESOURCE_IDENTITY` events | Need a fact table + linking step |

## 2. Dataset facts

**[VERIFIED]**
- `deletion_requests.csv`: 518 rows, `case_id` like `case_33`…`case_550` (unique, **not** zero-padded → sort carefully; see §6). `reported_status`: 254 COMPLETE, 152 PARTIALLY_COMPLETE, 112 NOT_STARTED. `audit_at` ranges 2026-01-29 → 2026-10-01.
- `sample_deletion_requests.csv`: 32 cases `case_01…case_32`; `sample_output.csv`: 22 INCOMPLETE, 10 COMPLETE, **0 NOT_APPLICABLE** (so NA format comes only from the problem statement: `[]`).
- Identity: 850 users in `user_identities.csv`; `email_hash = sha256(lowercase email)` (checked). `user_audit_log.csv` has 306 rows: fields `email` (107), `email_hash` (107), `phone` (92) with `old_value/new_value`.
- Request email match: **418 current email, 100 historical-only (old email), 0 unmatched, 0 matching both.** So ~19% of cases require the audit log. One email appears twice among requests (duplicate request email → two cases for the same person; handle each by its own `audit_at`).
- `request_text`: 375 unique strings in 518 rows; multiple languages (English, Spanish, French, Portuguese, Korean, Japanese, …). A keyword filter on English words misses 43 genuine deletion requests written in other languages. **Use an LLM (or multilingual rules), not an English keyword list.**
- Non-deletion requests exist: e.g. "send a copy of my invoices", "tell me what data you hold", "stop marketing emails only", "correct my surname", "change my email", "reset my login", "download my data". In the real file these are a small block of cases (about 10, contiguous high case numbers). `system_activity.csv` contains exactly 10 `CLASSIFY_REQUEST` events ("classified request for account_X as non-deletion; no destructive action was authorized"). Use them as a **cross-check**, never as the only signal. Do not hardcode case IDs.
- `system_activity.csv`: 4011 rows. Event types: DELETE_RECORD, UPDATE_RECORD, SYNC_RECORD, INDEX_RECORD, SEND_EMAIL, REFRESH_CACHE, RETAIN_RECORD, ANONYMIZE_RECORD, REDACT_RECORD, CREATE_EXPORT, CHECK_DATA_FLOW, DISABLE_DATA_FLOW, BLOCK_RESTORE, CHECK_RESTORE_ACCESS, LINK_RESOURCE_IDENTITY (12), CLASSIFY_REQUEST (10), RESTORE_BACKUP (1). `reported_result` SUCCESS/FAILED/PARTIAL are **claims**. Rows are global and mostly decoys for other people.
- Resource ID families (prefix → category): `account_*` (profile / tombstone), `search_*` (SEARCH_INDEX_ENTRY), `support_*` (message or attachment), `analytics_*` (ANALYTICS_PROFILE), `email_delivery_*` (EMAIL_DELIVERY_LOG), `cache_*`, `audit_record_*` (SECURITY_AUDIT_LOG), `export_*` (USER_EXPORT), `data_flow_*` (integration connector), `backup_*`, `tombstone_*`, `legal_hold_*`, plus one-offs for object storage and marketing.
- Evidence manifest: 94 files / 30 origins. Listing in the zip shows folders `databases/` (24 SQL), `documents/` (4 PDF, all have a text layer), `images/` (11 PNG, need OCR), `logs/` (26), `records/` (29 JSON/txt). Manifest has `file_id, file_path, origin, captured_at`. **The manifest does not say which case a file belongs to.**
- Evidence shapes seen:
  - SQL: `-- Captured at:` header, `-- Database topology: failover_replica|read_replica|regional|reporting|primary`; tables like `customer_profiles_primary` and `customer_profiles_failover_replica` with `(resource_id, user_id, full_name, email, phone, account_status, updated_at)`. Run with `sqlite3` in memory. **Replication drift**: a record may be gone in primary but present in a replica.
  - JSON `service_resource_export_*`: `service_exports.<service>.profile_lookups[] {resource_id, status_code 404/200, profile{email,full_name,phone,email_hash,customer_reference}}`.
  - JSON `customer_data_snapshot_bundle_*`: `snapshots[] {captured_at, data_store, collection, records[]}`; the `captured_at` **inside** a snapshot can differ from the file's manifest time.
  - JSON `connector_configurations_*`, `security_audit_ledger_*`: `records[] {recorded_at, system, resource_id, record_type, result FOUND/NOT_FOUND, subject_reference(email, may be UPPERCASE)}`.
  - TXT handover: pipe lines `timestamp | system | resource_id | RECORD_TYPE | NOT_FOUND/FOUND | email`.
  - LOG: key=value lines (`event=profile_lookup_completed resource_id=... rows=0 http_status=404`, `deletion_marker_check ... marker_found=false`, `lookup_key=<email>`); several log dialects (syslog, structured JSON-ish, cloud export).
- Emails in evidence can be UPPERCASE or reformatted → **always lowercase/strip before matching**.

## 3. Patterns in the 32 sample answers **[VERIFIED counts, HYPOTHESIS meaning]**

Operation counts across samples: VERIFY_RECORD_ABSENT 50, VERIFY_RECORD_PRESENT 24, REPORT_REMAINING_RECORD 21, DELETE_RECORD 21, VERIFY_RECORD_ANONYMIZED 12, REPORT_EXPOSED_PII 11, VERIFY_RECORD_REDACTED 10, VERIFY_DATA_FLOW_DISABLED 9, VERIFY_RESTORE_BLOCKED 6, REPORT_ACTIVE_DATA_FLOW 6, DISABLE_DATA_FLOW 6, REDACT_RECORD 6, ANONYMIZE_RECORD 5, REPORT_RESTORE_RISK 3, BLOCK_RESTORE 3. Systems used: account_service, search_service, support_platform, analytics_platform, security_service, integration_service, backup_service, export_service, identity_service.

Observed shapes:

```
COMPLETE (simple):   VERIFY_RECORD_ABSENT account_service account_001  [evidence_54]
COMPLETE (+analytics): ABSENT account_004 [evidence_54], ANONYMIZED analytics_901 [evidence_56]
INCOMPLETE (simple, case_05): FINDING REMAINING account_service account_005 [evidence_54]
                              REMEDIATION DELETE account_005 ""   VERIFICATION ABSENT account_005 ""
INCOMPLETE (search, case_06): FINDING REMAINING search_001 [evidence_57]; DELETE search_001;
                              VERIFY ABSENT account_006 ; VERIFY ABSENT search_001
INCOMPLETE (full, case_30):   FINDINGS: search REMAINING, analytics EXPOSED_PII, support EXPOSED_PII,
                                         integration ACTIVE_DATA_FLOW   (all cite one evidence file)
                              REMEDIATION: DISABLE flow, DELETE search, REDACT support, ANONYMIZE analytics
                              VERIFICATION: ABSENT account, ABSENT search, PRESENT security audit_record,
                                         REDACTED support, ANONYMIZED analytics, FLOW_DISABLED
```

Hypotheses to test:
- **H1** Verification list covers *every relevant record of the user* (also ones already compliant, e.g. the deleted account → ABSENT, the retained `audit_record_*` → PRESENT), not only the ones remediated.
- **H2** Finding `evidence_id` = the **latest evidence file with captured time ≤ `audit_at` that shows that resource in the offending state.** For COMPLETE cases, verification cites the latest evidence showing the compliant state.
- **H3** Account found in a failover/read replica while primary is clean ⇒ INCOMPLETE with REPORT_REMAINING_RECORD on `account_service`.
- **H4** Category → treatment: `search_*`, `cache_*`, `export_*`, marketing, profile → DELETE; `support_*` message with shared context → REDACT, attachment owned only by user → DELETE; `analytics_*` and telemetry still attributable → ANONYMIZE; `email_delivery_*` containing email → REDACT; `audit_record_*` within retention → RETAIN (verify PRESENT, no remediation); legal hold → RETAIN; `backup_*` → RETAIN but BLOCK_RESTORE if restorable; tombstone → keep `user_id`, REDACT name/email/phone/email_hash.
- **H5** Remediation list = actions for findings only; verification = outcome for each finding + retained checks.

Test each against the samples; when a hypothesis fails, look at the failing sample's evidence and update the rule (never special-case the case ID).

## 4. Hard rules from `AGENTS.md` (the judge enforces these)

1. Use only `dataset/`. No organizer files, no copying `sample_output` into predictions.
2. Evidence or activity dated **after `audit_at`** must not influence the case or be cited.
3. `reported_status` and `reported_result` are **claims**, not proof.
4. `NOT_APPLICABLE` → `steps_json = []` (exact text `[]`).
5. Findings and COMPLETE-verification steps cite a real `file_id` / `activity_id` / `audit_id`. Remediation and future verification in INCOMPLETE use `""`.
6. Deterministic output, step numbers 1..N consecutive, sorted by phase → operation order → `system_id` → `resource_id`.
7. Secrets from env vars only; never in `log.txt` or `code.zip`. Keep `code.zip` free of `dataset/`, `.venv`, `__pycache__`, and **nested archives**.
8. Log every turn to root `log.txt` in the AGENTS.md format with correct `tool=` and `model=` lines.

## 5. Operation order tables (use exactly these as sort keys)

```python
PHASE_ORDER = {"FINDING":0, "REMEDIATION":1, "VERIFICATION":2}
OP_ORDER = {
 "REPORT_REMAINING_RECORD":0, "REPORT_EXPOSED_PII":1, "REPORT_ACTIVE_DATA_FLOW":2, "REPORT_RESTORE_RISK":3,
 "DISABLE_DATA_FLOW":0, "BLOCK_RESTORE":1, "DELETE_RECORD":2, "REDACT_RECORD":3, "ANONYMIZE_RECORD":4,
 "VERIFY_RECORD_ABSENT":0, "VERIFY_RECORD_PRESENT":1, "VERIFY_RECORD_REDACTED":2,
 "VERIFY_RECORD_ANONYMIZED":3, "VERIFY_DATA_FLOW_DISABLED":4, "VERIFY_RESTORE_BLOCKED":5}
OP_STATE = {"REPORT_REMAINING_RECORD":"PRESENT","REPORT_EXPOSED_PII":"PRESENT","REPORT_ACTIVE_DATA_FLOW":"ACTIVE",
 "REPORT_RESTORE_RISK":"ACTIVE","DISABLE_DATA_FLOW":"DISABLED","BLOCK_RESTORE":"BLOCKED","DELETE_RECORD":"ABSENT",
 "REDACT_RECORD":"REDACTED","ANONYMIZE_RECORD":"ANONYMIZED","VERIFY_RECORD_ABSENT":"ABSENT","VERIFY_RECORD_PRESENT":"PRESENT",
 "VERIFY_RECORD_REDACTED":"REDACTED","VERIFY_RECORD_ANONYMIZED":"ANONYMIZED","VERIFY_DATA_FLOW_DISABLED":"DISABLED",
 "VERIFY_RESTORE_BLOCKED":"BLOCKED"}
# sort key: (PHASE_ORDER[phase], OP_ORDER[op], system_id, resource_id)  -- string compare for ids
```
Samples show the system tie-break is plain ascending string order (`account_service` < `analytics_platform` < `integration_service` < `search_service` < `security_service` < `support_platform`). Verify on a multi-resource sample.

## 6. Pitfalls checklist

- **Sorting `case_id`:** **[VERIFIED]** the 518 IDs are contiguous `case_33 … case_550`; `deletion_requests.csv` is already in *natural numeric* order, and `dataset/output.csv` is header-only. A plain string sort would put `case_100` before `case_33`. **Decision: sort by the numeric part of the ID (natural order), identical to the input file.** The grader almost certainly joins on `case_id`, so row order is low-risk either way; state the choice in the README and have the validator also confirm the set of IDs equals the input set exactly.
- **Time filter on activity too**, not only evidence.
- **Snapshot-internal times:** use the inner `captured_at`/`recorded_at`, falling back to manifest `captured_at`.
- **Multi-table SQL snapshots** include the primary and replicas; each table is its own observation with its own `system_id`/topology.
- **Duplicated request email** → two cases; each independent.
- **Decoys:** same name, similar email, different `user_id`. Match on email/hash/user_id/phone, never on name alone.
- **Case sensitivity** of emails, whitespace, `+` phone formats.
- **Failed deletion claims**: `reported_result=FAILED` is a hint to look, not a finding by itself; a `SUCCESS` delete can be undone by a later `SYNC_RECORD`/`RESTORE_BACKUP`.
- **JSON output:** write with `json.dumps(steps, separators=(",",":"), ensure_ascii=False)` and `csv.writer` (quotes handled).
