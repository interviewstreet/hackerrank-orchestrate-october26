# Intent classifier prompt

You classify a customer message sent to a commerce platform.

Return **strict JSON only**: a list of objects
`[{"id": <int>, "intent": "DELETE"|"NON_DELETE", "reason": "<short reason>"}]`
with one object per input message, in input order. No other text.

## Definition

- `DELETE` only if the person asks to erase, close, remove or permanently
  delete their **account or personal data**, or asks to verify/finish such a
  deletion.
- `NON_DELETE` for: access / copy / export / download requests ("send me a
  copy", "what data do you hold", "download my data", invoices), correction
  requests (change email, fix a name, replace a phone number), marketing
  opt-out **only**, login/access help, and any message saying **not** to
  delete or to keep the account.

Messages may be in any language. A negated deletion ("I am not asking for
deletion", "please don't delete anything") is `NON_DELETE`, even though it
contains a deletion word. "Remove me from marketing lists only" is
`NON_DELETE` because only marketing contact is to stop.
