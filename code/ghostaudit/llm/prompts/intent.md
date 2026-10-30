You classify customer privacy requests for a commerce platform. For each request, decide whether the
person is **authorizing deletion of their account / personal data**.

Label `DELETE` when the request asks to delete, erase, remove or permanently close the account or the
personal data tied to it, in any language. A request that asks for an export *and then* deletion is
still `DELETE`. Politeness, follow-ups about a failed deletion, "please check whether anything is
left and finish the deletion", and requests to audit or confirm that the account / data was fully removed
(the person is reaffirming an erasure they asked for) are `DELETE`.

Label `NON_DELETE` for anything else, even if it mentions deletion in passing: marketing or promotional
opt-out only, a data export / copy / download, access ("what data do you hold"), correction of a name,
email or phone, invoices or receipts, login or password help, or any text that says the account should
stay active or that nothing should be deleted.

Requests (JSON array of objects with `id` and `text`):

{{requests}}

Return only JSON, with no prose and no code fence:
{"labels": [{"id": "<id>", "label": "DELETE" | "NON_DELETE", "confidence": <0..1>, "reason": "<= 12 words"}]}
