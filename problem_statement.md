# Ghost Data Still Exists

Northstar Shop (an imaginary company) lost **$2.4 million** after one supposedly deleted customer came back as a ghost in its systems. Every internal dashboard showed the deletion request as **“Complete.”** Weeks later, the same customer tried to create a new account. The platform refused: **“This email is already registered.”**

What looked like a simple signup bug exposed a much larger failure. The investigation uncovered personal data across secondary databases, support attachments, search indexes, analytics exports, logs, archives, and backups. A synchronization job had even recreated information that the primary account service had successfully deleted.

Northstar Shop now needs an AI-powered deletion audit agent that can prove whether a user's personal data is truly gone before another failure causes financial and reputational damage.

For deletion requests, the agent must investigate the supplied records, determine the user's current and historical identifiers, reconstruct what happened across systems, and decide whether the deletion is actually complete.

When data remains, the agent must produce the ordered remediation steps required to remove, redact, or anonymize it. When deletion has already been completed, the agent must produce the checks that prove it. The agent must also preserve records that the supplied policy requires the organization to retain.

Some systems preserve an account tombstone so permitted records can continue to reference the same internal `user_id`. In these records, the stable user reference may remain, but direct identifiers such as name, email, phone, and email hash must be removed.

## What You Need to Build

For each request, build a system that determines:

- whether the deletion is `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE` because the person did not request deletion;
- which records or identifiers still expose the user;
- which active processes can recreate deleted data;
- the ordered remediation steps required to complete the request.

A deletion is complete only when:

- every relevant copy has received the treatment required by `deletion_rules.csv`;
- no active sync, import, or restore path can recreate the data;
- retained records contain only the identifiers permitted by the rules; and
- records that must be retained remain available.

## Files Provided

All participant-facing files are inside `dataset/`.

| File | Contents |
| --- | --- |
| `deletion_requests.csv` | Requests that must be audited |
| `sample_deletion_requests.csv` | Sample requests |
| `sample_output.csv` | Correct answers for the sample requests |
| `user_identities.csv` | Current user identities |
| `user_audit_log.csv` | Historical identity changes |
| `system_activity.csv` | Deletion, sync, export, backup, restore, indexing, and related operational activity |
| `deletion_rules.csv` | Required treatment for each data category |
| `evidence_files.csv` | Manifest of the supplied evidence files |
| `output.csv` | Blank submission template |

Evidence may be stored as PDFs, images, logs, JSON, or SQLite-compatible SQL snapshot exports under `dataset/evidence/`.

## Input

Each row in `deletion_requests.csv` is one case:

```text
case_id,email,requested_at,reported_status,reported_at,audit_at,request_text
```

`reported_status` may be `COMPLETE`, `PARTIALLY_COMPLETE`, or `NOT_STARTED`. It is a claim from the existing deletion workflow, not proof of the true state.

## Required Output

Produce exactly one row in `output.csv` for every case in `deletion_requests.csv`:

```text
case_id,deletion_status,steps_json
```

| Column | Meaning |
| --- | --- |
| `case_id` | Case being audited |
| `deletion_status` | `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE` |
| `steps_json` | Ordered JSON array of findings, remediation actions, and verification checks |

The final file must contain one data row per public request (518 in this checkout). Local preparation matches IDs irrespective of CSV row order; step-array order remains significant.

Each object in `steps_json` must contain:

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

`phase` must be `FINDING`, `REMEDIATION`, or `VERIFICATION`. Step numbers start at `1` and increase consecutively. Array order is significant.

For `COMPLETE`, include only verification steps proving the current state. For `INCOMPLETE`, include findings, the complete remediation plan, and the checks that must pass afterward. For `NOT_APPLICABLE`, use an empty JSON array (`[]`) because no deletion or deletion verification is authorized.

A non-deletion row therefore has this form:

```csv
case_000,NOT_APPLICABLE,[]
```

The grader parses `steps_json` as JSON. JSON object-key order and whitespace are ignored; array order is not.

## Allowed Operations

| Phase | Operation | State | Meaning |
| --- | --- | --- | --- |
| `FINDING` | `REPORT_REMAINING_RECORD` | `PRESENT` | A record that should have been deleted still exists. |
| `FINDING` | `REPORT_EXPOSED_PII` | `PRESENT` | A record may remain, but it still contains identifiers that should have been redacted or anonymized. |
| `FINDING` | `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` | An active process can copy or recreate the user's data. |
| `FINDING` | `REPORT_RESTORE_RISK` | `ACTIVE` | A backup or restore path can bring deleted data back. |
| `REMEDIATION` | `DISABLE_DATA_FLOW` | `DISABLED` | Stop the process that can copy or recreate the data. |
| `REMEDIATION` | `BLOCK_RESTORE` | `BLOCKED` | Prevent the affected backup from restoring the user's data. |
| `REMEDIATION` | `DELETE_RECORD` | `ABSENT` | Remove the entire record. |
| `REMEDIATION` | `REDACT_RECORD` | `REDACTED` | Keep the record but remove the identifying fields required by policy. |
| `REMEDIATION` | `ANONYMIZE_RECORD` | `ANONYMIZED` | Keep the record after irreversibly unlinking it from the user. |
| `VERIFICATION` | `VERIFY_RECORD_ABSENT` | `ABSENT` | Confirm that a record no longer exists. |
| `VERIFICATION` | `VERIFY_RECORD_PRESENT` | `PRESENT` | Confirm that a policy-required retained record still exists. |
| `VERIFICATION` | `VERIFY_RECORD_REDACTED` | `REDACTED` | Confirm that required identifying fields have been removed. |
| `VERIFICATION` | `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` | Confirm that the record can no longer be linked to the user. |
| `VERIFICATION` | `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` | Confirm that the relevant data flow is inactive. |
| `VERIFICATION` | `VERIFY_RESTORE_BLOCKED` | `BLOCKED` | Confirm that the affected data cannot be restored. |

## Rules

- Resolve the user’s current and historical identifiers.
- Determine the resource state at `audit_at` using the available evidence. Reported workflow statuses and operation results are claims.
- Apply `deletion_rules.csv` to every relevant record, including account tombstones, active data flows, and restore risks.
- Order steps by phase: findings, remediation, then verification. Within each phase, follow the operation order in the table above, followed by `system_id` and `resource_id` in ascending order.
- Findings and verification steps for `COMPLETE` cases must cite a `file_id`, `activity_id`, or `audit_id`. Proposed remediation and future verification steps for `INCOMPLETE` cases use an empty `evidence_id`.

## Evaluation

`output.csv` will be compared with hidden canonical answers. Scoring will consider the correctness of `deletion_status`, identity resolution, discovered records and risks, cited evidence, policy decisions, and the completeness and order of `steps_json`.

Your `code.zip` must include `code/evaluation/evaluation_report.md` containing:

- case-level status accuracy;
- step-level and field-level accuracy;
- sequence accuracy;
- at least three additional evaluation cases created by your team; and
- failures found and improvements made.

## Submission

After your first coding-agent interaction, run `python3 orchestrate.py check` (Windows: `py orchestrate.py check`). Before upload, finish generating inputs and run `python3 orchestrate.py prepare` (Windows: `py orchestrate.py prepare`). Python 3.10+ is required. Upload the three files in `submission/` separately; see README for the mapping. CSV rows are matched by ID for local checks; step-array order remains required.

| Item | Description |
| --- | --- |
| `code.zip` | Runnable solution, prompts, configuration, README, and `code/evaluation/` folder |
| `output.csv` | One answer row for every request |
| `chat_transcript` | Transcript showing how the system was developed or used |
| AI interview | Explanation of the approach and evaluation |

### Token Usage and Cost Analysis

Your `code.zip` must include one token-usage file:

```text
code/evaluation/usage_report.md
```

The report must summarize the final full-dataset run that produced `output.csv`, including model providers and names, model calls, input and output tokens, total and average tokens per request, and estimated total and per-request cost. If multiple models are used, include both per-model and overall totals in the same file.

Do not include API keys, credentials, or sensitive configuration values in the submission.

These are the required deliverables. Participants are encouraged to improve retrieval, multimodal interpretation, identity and deletion-state reconstruction, remediation planning, deterministic verification, batching, caching, and token efficiency.
