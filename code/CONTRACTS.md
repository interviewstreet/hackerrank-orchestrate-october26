# Team contracts: P1 → P2 → P3 → P4

How data moves between the pipeline stages in `code/main.py`:

```text
classify_request(text)                      P1  request_classifier.py
IdentityResolver.resolve(...) -> identity   P1  identity_resolver.py   (see README_identity.md)
find_records(identity, case) -> evidence    P2  evidence_search.py     section 1
decide(identity, evidence, case) -> decision P3  policy_engine.py      section 2 (PROPOSAL)
build_steps(decision) -> steps              P4  step_builder.py        section 3 (PROPOSAL)
```

`main.py` checks each hand-over. If a stage raises an error or returns the
wrong type, that case is written as `INCOMPLETE, []` and listed at the end
of the run, so one bug never stops `output.csv` from being written.

All times are aware UTC `datetime`s. Parse CSV/evidence strings with
`utils.parse_ts()`. Never use anything captured after the case's `audit_at`.

---

## 1. P2 → P3: `find_records(identity, case) -> dict`

**Input.** `main.py` passes a *copy* of the CSV row in which
`case["audit_at"]` is already an aware UTC `datetime` (from
`utils.parse_ts()`), never the raw string. A CSV value without a timezone
becomes UTC. If `audit_at` is empty, `main.py` writes `INCOMPLETE, []` and
does **not** call `find_records()` at all, so P2 never has to search
without a cut-off. The other fields stay strings.

**Status: agreed shape, enforced by `main.py`.** The keys live in
`models.EVIDENCE_KEYS`, and `models.empty_evidence()` returns an empty
example. A missing key makes the case fail (`INCOMPLETE, []`). An extra key
only prints a warning.

| Key | Type | Meaning | From P2's `EvidenceScanner` |
|---|---|---|---|
| `records` | `list[ObservedRecord]` | Every observation linked to the subject and available at `audit_at`, claims included, nothing collapsed | `find_records(subject, audit_at)` |
| `latest_by_resource` | `dict[(system_id, resource_id, replica_or_table), ObservedRecord]` | Latest **authoritative** observation per copy. Replicas are separate keys | `latest_by_resource(subject, audit_at)` |
| `referenced_resources` | `list[dict]` | Resources tied to the subject **without** a direct identifier, e.g. an `analytics_9406` that only `system_activity.csv` links to the user. Each item: `{system_id, resource_id, via, source_id}`, where `via` is `"system_activity"` or `"linked_record"` and `source_id` is the `activity_id` / `file_id` that links it | `records_for_resource(...)` for these |
| `absence_proofs` | `dict[(system_id, resource_id), list[AbsenceProof]]` | Complete snapshots (at or before `audit_at`) that prove a resource is **not** there, newest first. Only `COMPLETE` proofs | `absence_proofs(system_id, resource_id, audit_at)` |
| `identifier_provenance` | `dict[str, list[str]]` | Which subject identifier matched in which evidence: `"email:x@y.com" -> ["evidence_12", ...]`. Keys use P2's `kind:value` terms | from `ObservedRecord.identifiers_matched` |

How P2 builds `subject` from P1's bundle:
`SubjectIdentifiers(**identity.as_subject_kwargs())` (see README_identity.md, "For P2 and P3 – adapter").

Placeholder today (`evidence_search.py`): all five keys present, all empty.

---

## 2. P3 → P4: `decide(identity, evidence, case) -> dict`

> **PROPOSAL, P3 and P4 to confirm.**
> Today `main.py` enforces only `deletion_status`. The other keys are a
> proposal derived from `problem_statement.md` and the 32 sample answers.

```python
{
  "deletion_status": "COMPLETE" | "INCOMPLETE",
  "resources":     [ {system_id, resource_id, category, required_treatment,
                      state_at_audit, satisfied, evidence_ids} ],
  "flows":         [ {system_id, resource_id, kind, active_at_audit, evidence_id} ],
  "restore_risks": [ {system_id, resource_id, active_at_audit, evidence_id} ],
  "timeline":      [ {time, system_id, resource_id, event, state_after, evidence_id} ],
}
```

### `resources` — one per relevant record

| Field | Type | Meaning |
|---|---|---|
| `system_id` | `str` | e.g. `account_service` |
| `resource_id` | `str` | e.g. `account_005` |
| `category` | `str` | `data_category` from `deletion_rules.csv`, e.g. `USER_PROFILE` |
| `required_treatment` | `str` | `DELETE` / `REDACT` / `ANONYMIZE` / `RETAIN` / `TOMBSTONE` (from the rule's `required_action`; `ACCOUNT_TOMBSTONE` is `TOMBSTONE`) |
| `state_at_audit` | `str` | `PRESENT` / `ABSENT` / `REDACTED` / `ANONYMIZED` / `UNKNOWN`, the true state at `audit_at` from evidence, not from claims |
| `satisfied` | `bool` | `True` if `state_at_audit` already meets `required_treatment` |
| `evidence_ids` | `list[str]` | `file_id` / `activity_id` / `audit_id` proving `state_at_audit`, best first. P4 cites `evidence_ids[0]` |

### `flows` — processes that can copy or recreate data (sync, import, export, indexing)

| Field | Type | Meaning |
|---|---|---|
| `system_id`, `resource_id` | `str` | the flow / connector |
| `kind` | `str` | e.g. `SYNC`, `IMPORT`, `EXPORT`, `INDEX` |
| `active_at_audit` | `bool` | can it still run at `audit_at`? |
| `evidence_id` | `str` | proof of that state |

### `restore_risks` — backups that could bring data back

Same as `flows` without `kind`. `active_at_audit=True` means restore is not blocked.

### `timeline` — what happened, oldest first

`time` (ISO-8601 UTC string), `system_id`, `resource_id`, `event` (e.g.
`DELETE`, `SYNC`, `RESTORE`), `state_after`, `evidence_id`. P4 does not need
it to build steps. It is for debugging and the evaluation report.

`deletion_status` should be `COMPLETE` only if every resource is
`satisfied`, no flow and no restore risk is `active_at_audit`, and every
`RETAIN` record is `PRESENT`.

---

## 3. P4: turning the decision into `steps_json`

> **PROPOSAL, P3 and P4 to confirm.**

### Operation for each item

| Item | Finding (only if not satisfied / active) | Remediation | Verification |
|---|---|---|---|
| resource, `DELETE` | `REPORT_REMAINING_RECORD` / `PRESENT` | `DELETE_RECORD` / `ABSENT` | `VERIFY_RECORD_ABSENT` / `ABSENT` |
| resource, `REDACT` | `REPORT_EXPOSED_PII` / `PRESENT` | `REDACT_RECORD` / `REDACTED` | `VERIFY_RECORD_REDACTED` / `REDACTED` |
| resource, `TOMBSTONE` | `REPORT_EXPOSED_PII` / `PRESENT` | `REDACT_RECORD` / `REDACTED` (keep `user_id` only) | `VERIFY_RECORD_REDACTED` / `REDACTED` |
| resource, `ANONYMIZE` | `REPORT_EXPOSED_PII` / `PRESENT` | `ANONYMIZE_RECORD` / `ANONYMIZED` | `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED` |
| resource, `RETAIN` | none | none | `VERIFY_RECORD_PRESENT` / `PRESENT` |
| flow, active | `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE` | `DISABLE_DATA_FLOW` / `DISABLED` | `VERIFY_DATA_FLOW_DISABLED` / `DISABLED` |
| restore risk, active | `REPORT_RESTORE_RISK` / `ACTIVE` | `BLOCK_RESTORE` / `BLOCKED` | `VERIFY_RESTORE_BLOCKED` / `BLOCKED` |

### Which steps to write

- **`INCOMPLETE`**:
  - FINDING + REMEDIATION for every unsatisfied resource and every active flow or restore risk.
  - VERIFICATION for every resource (satisfied or not), and for every flow or restore risk that was remediated.
  - Findings cite `evidence_ids[0]` / `evidence_id`. Remediation and verification use `""`.
- **`COMPLETE`**: VERIFICATION only, one per resource, flow and restore risk, each citing its evidence.

The 32 sample answers support this:
- In `INCOMPLETE` samples, 19 `VERIFY_RECORD_ABSENT` steps belong to records that were already deleted and have no finding.
- Every flow, restore, redact and anonymize verification in an `INCOMPLETE` sample has a matching remediation.
- `COMPLETE` samples verify disabled flows (3) and blocked restores (3) with evidence.
- Every finding cites evidence. No remediation step does, and no `INCOMPLETE` verification step does.

### Order

Sort all steps by **(position of the operation in the table in
`problem_statement.md`, `system_id`, `resource_id`)**, then number them from 1.
The operation table order is:

```text
REPORT_REMAINING_RECORD, REPORT_EXPOSED_PII, REPORT_ACTIVE_DATA_FLOW, REPORT_RESTORE_RISK,
DISABLE_DATA_FLOW, BLOCK_RESTORE, DELETE_RECORD, REDACT_RECORD, ANONYMIZE_RECORD,
VERIFY_RECORD_ABSENT, VERIFY_RECORD_PRESENT, VERIFY_RECORD_REDACTED, VERIFY_RECORD_ANONYMIZED,
VERIFY_DATA_FLOW_DISABLED, VERIFY_RESTORE_BLOCKED
```

This puts findings first, then remediation, then verification, and it
disables flows and blocks restores before records are changed. All 32
sample answers are sorted exactly this way.

### Example: sample case_06

`decide()` would return (only the relevant parts):

```python
{
  "deletion_status": "INCOMPLETE",
  "resources": [
    {"system_id": "account_service", "resource_id": "account_006", "category": "USER_PROFILE",
     "required_treatment": "DELETE", "state_at_audit": "ABSENT", "satisfied": True,
     "evidence_ids": ["<file_id that proves account_006 is absent>"]},
    {"system_id": "search_service", "resource_id": "search_001", "category": "SEARCH_INDEX_ENTRY",
     "required_treatment": "DELETE", "state_at_audit": "PRESENT", "satisfied": False,
     "evidence_ids": ["evidence_57"]},
  ],
  "flows": [], "restore_risks": [], "timeline": [...],
}
```

`search_001` is `DELETE` with `satisfied=False`, so it becomes
`REPORT_REMAINING_RECORD → DELETE_RECORD → VERIFY_RECORD_ABSENT`.
`account_006` is already satisfied, so it gets only `VERIFY_RECORD_ABSENT`.
After sorting, `build_steps()` returns exactly the sample answer:

```json
[
  {"step_no": 1, "phase": "FINDING",      "system_id": "search_service",  "resource_id": "search_001",  "operation": "REPORT_REMAINING_RECORD", "state": "PRESENT", "evidence_id": "evidence_57"},
  {"step_no": 2, "phase": "REMEDIATION",  "system_id": "search_service",  "resource_id": "search_001",  "operation": "DELETE_RECORD",           "state": "ABSENT",  "evidence_id": ""},
  {"step_no": 3, "phase": "VERIFICATION", "system_id": "account_service", "resource_id": "account_006", "operation": "VERIFY_RECORD_ABSENT",    "state": "ABSENT",  "evidence_id": ""},
  {"step_no": 4, "phase": "VERIFICATION", "system_id": "search_service",  "resource_id": "search_001",  "operation": "VERIFY_RECORD_ABSENT",    "state": "ABSENT",  "evidence_id": ""}
]
```

Note that step 3 (`account_service`) comes before step 4 (`search_service`):
within `VERIFY_RECORD_ABSENT`, steps are sorted by `system_id`.

---

## 4. Open questions

1. **Who reads `system_activity.csv`?** P2's scanner reads only the
   evidence files. Flows, restore risks, `activity_id` citations and
   `referenced_resources` need the activity stream. P2 or P3 should own it.
2. **Replicas.** P2 keys `latest_by_resource` by `replica_or_table`, but a
   step has no replica field. Does P3 merge all copies of one
   `resource_id` into one resource (unsatisfied if any copy is), or keep
   them apart?
3. **`RETAIN` record missing at `audit_at`.** No allowed operation can fix
   that. Should it make the case `INCOMPLETE` with only a verification step?
4. **Extra fields.** Should `resources` also carry `rule_id` (to explain the
   decision in the evaluation report) and `replica_or_table`?
