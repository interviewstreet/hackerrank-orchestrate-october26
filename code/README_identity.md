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

**Rules:** `IS_DELETION` only if it asks for deletion with no negated
*instruction* ("don't delete", "not asking for deletion", "ne supprimez pas",
"삭제하지 마"). A negated *description* such as "was not removed" or "do not
hesitate to delete" is still a deletion request. It also needs no keep-the-account
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

## `IdentityResolver(identities_path, audit_log_path).resolve(email, audit_at=None, requested_at=None, case_id="") -> IdentityBundle | None`

Maps the request email (current or historical, any letter case) to the user
and gives every identifier you need to search evidence for.

**Inputs:**
- `identities_path`, `audit_log_path`: paths to `dataset/user_identities.csv`
  and `dataset/user_audit_log.csv` (loaded once, in the constructor)
- `email`: the request's `email` field
- `requested_at`: the request's `requested_at` as a `datetime`. The email
  resolves to whoever owned it at this time (see "For P3", section 4).
- `case_id`: only used to label warnings
- `audit_at`: a `datetime`; parse the CSV string with `utils.parse_ts()`. A
  naive datetime is treated as UTC. Always pass the case's `audit_at`, so
  that identifiers that only appeared after it are left out.

**Timestamps:** use `utils.parse_ts(value, context)` everywhere. It returns
an aware UTC `datetime`, treats a missing timezone as UTC, returns `None`
with a warning for an empty value, and raises a clear `ValueError` for text
that isn't a date. An audit-log row with an empty `event_time` is kept as
if it happened before `audit_at`.

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
python3 -m unittest discover -s code -p "test_*.py" -v   # all 108 tests

python3 code/test_utils.py                # 13 tests
python3 code/test_identity_resolver.py    # 66 tests
python3 code/test_request_classifier.py   # 20 tests, 47 made-up sentences
python3 code/test_main.py                 # 9 tests: one bad case never stops the run
```

## For P3

### 1. The exact `IdentityBundle` structure

Defined in `code/models.py`. Every field:

| Field | Type | Meaning |
|---|---|---|
| `user_id` | `str` | Stable user reference, e.g. `"user_41"`. Never changes, and it is the reference an `ACCOUNT_TOMBSTONE` keeps. |
| `current_email` | `str` | Email held **at `audit_at`**, as written in the data |
| `current_name` | `str` | Name from `user_identities.csv`. The audit log has no name changes, so this is never rolled back. |
| `current_phone` | `str` | Phone held at `audit_at` |
| `current_email_hash` | `str` | SHA-256 of the lowercased email, held at `audit_at` |
| `historical_emails` | `list[str]` | Earlier emails (lowercased), from changes at or before `audit_at` |
| `historical_phones` | `list[str]` | Earlier phones, same rule |
| `historical_email_hashes` | `list[str]` | Earlier hashes: stored `email_hash` changes, plus the SHA-256 of every historical email |
| `request_email` | `str` | The request's `email`, exactly as given (not lowercased) |
| `history` | `list[IdentityChange]` | Every audit-log change at or before `audit_at`, oldest first (ties broken by `audit_id`) |

Methods: `all_emails() -> list[str]`, `all_phones() -> list[str]`,
`all_email_hashes() -> list[str]`. Each returns the current value first,
then the historical ones, with no duplicates (`all_emails()` lowercases).

`IdentityChange` (also in `models.py`) is a frozen dataclass:

| Field | Type | Meaning |
|---|---|---|
| `audit_id` | `str` | Row ID in `user_audit_log.csv`, e.g. `"audit_293"` |
| `field_name` | `str` | `"email"`, `"phone"` or `"email_hash"` |
| `old_value` | `str` | Value before the change |
| `new_value` | `str` | Value after the change |
| `event_time` | `str` | ISO-8601 UTC string exactly as in the CSV, e.g. `"2026-05-28T19:48:13Z"` |

### 2. How current and historical identifiers are represented

- **Current** identifiers are single strings: `current_email`,
  `current_phone`, `current_email_hash`.
- **Historical** identifiers are plain lists of the `old_value`s of past
  changes: `historical_emails`, `historical_phones`, `historical_email_hashes`.
- To search evidence, use `all_emails()`, `all_phones()` and
  `all_email_hashes()`, which combine both. Compare emails in lowercase.
  Phones are kept exactly as written (e.g. `"+34 695 783 595"`), so
  normalise them yourself if evidence formats phones differently.

### 3. How historical changes link to `audit_id`, `old_value`, `new_value` and `event_time`

Each entry in `bundle.history` is one row of `user_audit_log.csv`, with all
five fields. The lists in section 2 hold only the `old_value`s. To find
which change produced an old identifier, or to cite it as `evidence_id`,
search `history`:

```python
change = next(c for c in bundle.history
              if c.field_name == "email" and c.old_value.lower() == some_email)
change.audit_id    # 'audit_293'
change.event_time  # '2026-05-28T19:48:13Z'  (stopped being current at this time)
```

Hash changes are separate rows (`field_name="email_hash"`). In this dataset
they always have the same `event_time` as the email change they belong to.
Changes with an empty `old_value` stay in `history` but don't add anything
to the historical lists.

### 4. How identifiers are resolved as of `audit_at`

`resolve(email, audit_at, requested_at, case_id)` does this:

1. **Find who owned the email when the request was sent.** From
   `user_identities.csv` and the email changes in `user_audit_log.csv`, it
   knows the periods each user owned each email (a change's `event_time`
   is when the new value starts). The lowercased request email resolves to
   the user who owned it at `requested_at`, or at `audit_at` if
   `requested_at` is missing, or the current owner if neither is given.
   So if an email moved from user A to user B, a request sent before the
   move resolves to A.
   - If several users could have owned it at that time (e.g. two users
     list the same old email with unknown start dates), it prints a
     warning with the `case_id` and picks the user who gave the email up
     first, assuming the email passed from one user to the next.
   - If nobody owned it at that exact time, it warns and picks the nearest
     owner in time (the last owner before, otherwise the first after).
   - In today's dataset no email ever belonged to two users, so this never
     triggers and every case resolves exactly as it did before.
2. **Roll the snapshot back to `audit_at`.** `user_identities.csv` shows
   the latest state. Every change with `event_time > audit_at` is undone,
   newest first: email, phone and hash are set back to that change's
   `old_value`. So `current_*` shows what the user actually had at
   `audit_at`, and a value that only appeared later is not in the bundle
   at all. If an email is rolled back with no matching hash row, the hash
   is recalculated as SHA-256.
3. **Keep only past history.** `history` and the `historical_*` lists
   contain only changes with `event_time <= audit_at`. A change exactly at
   `audit_at` is included.

If you call it without `audit_at`, there is no roll-back and the full
history is used. Always pass `audit_at` for a case.

In today's dataset no case has a change after its `audit_at`, so the
roll-back never triggers. It is there for hidden or edge-case data.

### 5. The function to call for a deletion request

`main.py` already calls this and passes the bundle to `find_records()` and
then `decide()`, so you receive it as the `identity` argument. To call it
yourself:

```python
from identity_resolver import IdentityResolver
from utils import parse_ts

resolver = IdentityResolver("dataset/user_identities.csv",   # build once
                            "dataset/user_audit_log.csv")

audit_at = parse_ts(case["audit_at"], context=f"{case['case_id']} audit_at")
requested_at = parse_ts(case["requested_at"], context=f"{case['case_id']} requested_at")
identity = resolver.resolve(case["email"], audit_at=audit_at,
                            requested_at=requested_at, case_id=case["case_id"])
if identity is None:
    ...  # unknown email (doesn't happen in the current data)
```

Use `parse_ts()` for every timestamp (`audit_at`, `event_time`, evidence
capture times) so all comparisons are between aware UTC datetimes.
If you raise an exception, `main.py` writes that case as `INCOMPLETE, []`
and lists it at the end of the run, so check the summary.

### 6. Real sample: case_43

Input row from `deletion_requests.csv`:

```text
case_id=case_43  email=javier.r940897@outlook.com
requested_at=2026-09-15T11:00:00Z  audit_at=2026-09-26T11:00:00Z
```

The request uses an **old** email. The actual printed result of
`resolver.resolve(case["email"], audit_at=audit_at)`:

```text
IdentityBundle(user_id='user_41',
               current_email='javier.r9408@outlook.com',
               current_name='Javier Ríos',
               current_phone='+34 695 783 595',
               current_email_hash='5e3b9b928e5c07b78012b06e451a02a26789e1639766588b7b706b8bbecf89bd',
               historical_emails=['javier.r940897@outlook.com'],
               historical_phones=[],
               historical_email_hashes=['2e0aabf7d2e6c922c1d59fe49b69d3d9874d2f83ccaf826538f48e84e0ef9515'],
               request_email='javier.r940897@outlook.com',
               history=[IdentityChange(audit_id='audit_293',
                                       field_name='email',
                                       old_value='javier.r940897@outlook.com',
                                       new_value='javier.r9408@outlook.com',
                                       event_time='2026-05-28T19:48:13Z'),
                        IdentityChange(audit_id='audit_294',
                                       field_name='email_hash',
                                       old_value='2e0aabf7d2e6c922c1d59fe49b69d3d9874d2f83ccaf826538f48e84e0ef9515',
                                       new_value='5e3b9b928e5c07b78012b06e451a02a26789e1639766588b7b706b8bbecf89bd',
                                       event_time='2026-05-28T19:48:13Z')])

all_emails()       -> ['javier.r9408@outlook.com', 'javier.r940897@outlook.com']
all_phones()       -> ['+34 695 783 595']
all_email_hashes() -> ['5e3b9b92…bf89bd', '2e0aabf7…ef9515']
```

Both emails (and both hashes) must be searched in evidence for this case.
`audit_293` and `audit_294` (2026-05-28) are before `audit_at`
(2026-09-26), so they are included.

## For P2 and P3 – adapter

`IdentityBundle.as_subject_kwargs()` turns the bundle into the keyword
arguments of P2's `SubjectIdentifiers` (`code/evidence/models.py` on P2's
branch). This branch does not import P2's code: the method returns a
plain `dict`.

### Usage for P2 (one line)

```python
subject = SubjectIdentifiers(**identity.as_subject_kwargs())
```

`identity` is the `IdentityBundle` that `main.py` passes to
`find_records(identity, case)`.

### Mapping

| `SubjectIdentifiers` field | Type | Taken from `IdentityBundle` |
|---|---|---|
| `user_id` | `Optional[str]` | `user_id` |
| `emails` | `frozenset[str]` | `all_emails()`: current + historical, lowercased |
| `phones` | `frozenset[str]` | `all_phones()`: current + historical, exactly as written |
| `email_hashes` | `frozenset[str]` | `all_email_hashes()`: current + historical SHA-256 |
| `names` | `frozenset[str]` | `{current_name}`, or empty if there is no name |
| `resource_ids` | `frozenset[str]` | always empty. P2 fills these from evidence |

Every value is "as of `audit_at`": identifiers that only appeared after
`audit_at` are not included. Empty strings are dropped, so a missing phone
or name never becomes a search term that matches blank fields in evidence.

### Note for P3: dates and evidence IDs

`SubjectIdentifiers` has no `valid_from` / `valid_to`, so it can't tell you
**when** an identifier was in use or **which audit row** proves it. For
that, use `identity.history` (a list of `IdentityChange`, oldest first,
only changes at or before `audit_at`):

| Field | Use it for |
|---|---|
| `audit_id` | the `evidence_id` to cite for an identity change |
| `old_value` | the identifier used **until** `event_time` |
| `new_value` | the identifier used **from** `event_time` |
| `event_time` | the date of the change (ISO-8601 UTC string; parse with `utils.parse_ts()`) |

For example, an old email in `subject.emails` was in use until the
`event_time` of the `history` entry whose `old_value` is that email.

### Real example: case_43

```python
identity = resolver.resolve(case["email"], audit_at=audit_at,
                            requested_at=requested_at, case_id="case_43")
identity.as_subject_kwargs()
```

Actual output (sets shown sorted):

```text
{'user_id':      'user_41',
 'emails':       frozenset({'javier.r940897@outlook.com',      # old, used in the request
                            'javier.r9408@outlook.com'}),      # current
 'phones':       frozenset({'+34 695 783 595'}),
 'email_hashes': frozenset({'2e0aabf7d2e6c922c1d59fe49b69d3d9874d2f83ccaf826538f48e84e0ef9515',   # old
                            '5e3b9b928e5c07b78012b06e451a02a26789e1639766588b7b706b8bbecf89bd'}), # current
 'names':        frozenset({'Javier Ríos'}),
 'resource_ids': frozenset()}
```

Both the old and the current email and hash are included. The dates and
evidence IDs for the change are in `identity.history`: `audit_293`
(email) and `audit_294` (email_hash), both at `2026-05-28T19:48:13Z`.
