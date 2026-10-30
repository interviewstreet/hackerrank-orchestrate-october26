You are transcribing one business artifact (an application screenshot or a PDF) from a commerce
platform into structured records for a privacy-deletion audit. Do not judge whether a deletion is
complete. Only report what the artifact visibly shows.

Artifact: `{{file_name}}` (origin system: `{{origin}}`, captured at {{captured_at}}).

A **record** is any resource the artifact shows that has an internal resource identifier of the form
`account_N`, `search_N`, `support_N`, `analytics_N`, `export_N`, `data_flow_N`, `backup_N`,
`audit_record_N`, `tombstone_N`, `legal_hold_N`, `marketing_N` or `object_N`. Emit one record per such
identifier. Never invent an identifier that is not printed in the artifact.

For each record, fill `fields` with the facts printed next to it, using these keys when they apply
(omit keys that are not shown; use `null` when the artifact explicitly shows an empty, removed or
redacted value):

- `email`, `phone`, `full_name`, `email_hash`: direct identifiers printed for that record.
- `user_id`: a stable subject reference such as `user_12` (for customer, subject or tombstone references).
- `record_type`: one of `USER_PROFILE`, `SEARCH_INDEX_ENTRY`, `SUPPORT_MESSAGE`, `SUPPORT_ATTACHMENT`,
  `ANALYTICS_PROFILE`, `MARKETING_PROFILE`, `USER_EXPORT`, `SECURITY_AUDIT_LOG`, `LEGAL_HOLD_RECORD`,
  `BACKUP_ARCHIVE`, `ACCOUNT_TOMBSTONE`, `DATA_FLOW`.
- `result`: what the artifact shows about the record's state, one of `FOUND` (it exists and is shown),
  `NOT_FOUND` (deleted / no results / 404), `IDENTIFIABLE`, `ANONYMIZED`, `REDACTED`, `ACTIVE` (a data flow
  that is enabled or a backup that can still be restored), `DISABLED` (flow stopped), `BLOCKED` (restore blocked).
- `file`: an attachment or object file name, if shown.
- `enabled` (data flows) and `restore_allowed` (backups) as `true`/`false` when shown.
- `retention_until` / `retained_until` as an ISO-8601 timestamp when a retention or hold end date is shown.
- `email_opt_in`: `true`/`false` when a marketing opt-in is shown.
- `account_status`: a status label such as `ACTIVE` or `DELETED` when shown.
- `note`: at most one short sentence of other relevant visible text (for example "shared order context").

Set `observed_at` to the most specific ISO-8601 UTC time the artifact gives for that record, or `null`.
Set `system` to the owning service if the artifact names it, otherwise `null`.

Return only JSON, with no prose and no code fence, in exactly this shape:

{"records": [{"resource_id": "support_001", "system": "support_platform", "observed_at": "2026-06-18T10:24:00Z",
  "fields": {"record_type": "SUPPORT_ATTACHMENT", "result": "FOUND", "email": "someone@example.com", "file": "x.pdf"}}]}
