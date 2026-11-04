# Identity resolution and request classification (Person 1)

Two functions for the first pipeline stages. Both are pure Python, need no
API key and give the same result every run. Import them from inside `code/`.

```python
from identity_resolver import IdentityResolver
from request_classifier import classify_request
```

## `classify_request(request_text) -> ClassificationResult`

Decides whether a request actually asks for deletion. Call it first: a
`NOT_APPLICABLE` result means output `NOT_APPLICABLE` with `steps_json=[]`
and skip the rest of the pipeline.

**Input:** `request_text` (str), any of English, Spanish, Portuguese, French,
Japanese, Korean.

**Output:** `ClassificationResult` (from `models.py`):

| Field | Value |
|---|---|
| `label` | `IS_DELETION`, `NOT_APPLICABLE` or `UNCERTAIN` |
| `confidence` | `HIGH` (clear decision) or `LOW` (only for `UNCERTAIN`) |
| `matched_keywords` | matched phrases, tagged `DELETION:`, `NEGATION:`, `KEEP:` or `OTHER:` |
| `note` | one-line reason |
| `is_deletion()` | `True` only for `IS_DELETION` |

**Rules:** `IS_DELETION` only if it asks for deletion with no negation
("don't delete", "ne supprimez pas", "삭제하지 마") and no keep-the-account
phrase ("keep the account", "continue using"). A negation or keep phrase
with no other deletion request gives `NOT_APPLICABLE`, and so does a
non-deletion intent on its own (access, copy, correct, update, opt-out,
login help). Conflicting signals, or no signal at all, give `UNCERTAIN`, so
review those by hand.

**Example:**

```python
r = classify_request("I can't access my profile and need help resetting the login. Do not close the account.")
r.label             # 'NOT_APPLICABLE'
r.matched_keywords  # ['NEGATION:Do not close', "OTHER:can't access", 'OTHER:resetting', 'OTHER:login']
```

On the real data: case_533 to case_542 are `NOT_APPLICABLE`, the other 508
are `IS_DELETION`, and no case is `UNCERTAIN`.

## `IdentityResolver(identities_path, audit_log_path).resolve(email, audit_at=None) -> IdentityBundle | None`

Maps the request email (current or historical, any letter case) to the user
and gives every identifier you need to search evidence for.

**Inputs:**
- `identities_path`, `audit_log_path`: paths to `dataset/user_identities.csv`
  and `dataset/user_audit_log.csv` (loaded once, in the constructor)
- `email`: the request's `email` field
- `audit_at`: a timezone-aware `datetime`. Always pass the case's `audit_at`,
  so that identifiers that only appeared after it are left out.

**Output:** `IdentityBundle` (from `models.py`), or `None` if the email is unknown:

| Field / method | Meaning |
|---|---|
| `user_id` | stable user reference, e.g. `user_41` |
| `current_email`, `current_phone`, `current_email_hash` | values held **at `audit_at`** |
| `current_name` | name from the snapshot |
| `historical_emails`, `historical_phones`, `historical_email_hashes` | earlier values up to `audit_at` |
| `all_emails()`, `all_phones()`, `all_email_hashes()` | current + historical, no duplicates. Use these to search evidence |
| `request_email` | the email exactly as given in the request |

`email_hash` is SHA-256 of the lowercased email. Hashes of all historical
emails are included.

**Example:**

```python
from datetime import datetime, timezone
resolver = IdentityResolver("../dataset/user_identities.csv", "../dataset/user_audit_log.csv")
b = resolver.resolve("javier.r940897@outlook.com",
                     audit_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
b.user_id            # 'user_41'
b.current_email      # 'javier.r9408@outlook.com'
b.historical_emails  # ['javier.r940897@outlook.com']
```

`resolver.resolve_all(request_rows)` does the same for a list of CSV row
dicts (it reads `email` and `audit_at` from each row) and returns
`(row, bundle)` pairs. All 518 requests resolve.

## Tests

```text
python3 code/test_identity_resolver.py    # 40 tests
python3 code/test_request_classifier.py   # 12 tests, 22 made-up sentences
```
