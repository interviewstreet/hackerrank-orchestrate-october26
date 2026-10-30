You are transcribing a file or object listing from a business application screenshot or document
(artifact `{{file_name}}`, origin `{{origin}}`, captured at {{captured_at}}). The artifact shows stored
files (attachments, exports, labels, invoices) by **file name** rather than by an internal resource id.

List every stored file or object the artifact shows. For each one, give:

- `file`: the exact file name as printed (for example `delivery_confirmation_19.pdf`).
- `result`: `FOUND` if the artifact shows the file as stored, `NOT_FOUND` if it is shown as deleted or missing.
- `observed_at`: the most specific ISO-8601 UTC timestamp printed for that file (modified / uploaded), or `null`.
- `note`: at most one short sentence with other printed details (size, version, uploader, folder).

Never invent a file that is not printed. Return only JSON, with no prose and no code fence:

{"files": [{"file": "example.pdf", "result": "FOUND", "observed_at": "2026-02-12T18:42:00Z", "note": "684 KB, v3"}]}
