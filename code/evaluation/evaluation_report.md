# Evaluation report

Reproduce with `python3 code/evaluation/main.py` (add `--offline` to use only cached model
answers). Metric definitions are in `code/audit/scoring.py`.

## 1. Sample accuracy (32 published sample cases)

Scored against `dataset/sample_output.csv`, on the final pipeline with Claude reading the
screenshots and PDFs.

| Metric | Value |
| --- | ---: |
| Case accuracy (`deletion_status` correct) | **32 / 32 = 100.0%** |
| Row accuracy (status and every step field, in order, exactly equal) | 28 / 32 = 87.5% |
| Sequence accuracy (ordered `(phase, system, resource, operation)` list equal) | 28 / 32 = 87.5% |
| Step precision (whole-step tuples, order ignored) | 99.5% |
| Step recall | 97.9% |
| Step F1 | 98.7% |

Field-level accuracy compares step *i* of the prediction with step *i* of the reference
(193 reference steps):

| Field | Accuracy |
| --- | ---: |
| `phase` | 98.4% |
| `system_id` | 95.9% |
| `resource_id` | 95.3% |
| `operation` | 95.9% |
| `state` | 95.9% |
| `evidence_id` | 97.9% |

Positional field accuracy is lower than step F1 because one missing step shifts every later
step of that case by one position.

### Remaining sample differences

| Case | Difference | Why |
| --- | --- | --- |
| case_04 | missing `VERIFY_RECORD_ABSENT account_004` | No file or activity row mentions `account_004` or ties a deleted account to this user, so it cannot be discovered from participant-visible data. |
| case_18 | missing `VERIFY_RECORD_PRESENT audit_record_6645` | `audit_record_6645` appears in no evidence file or activity row. |
| case_20 | missing `VERIFY_RECORD_PRESENT audit_record_5569` | Same as case_18 (`audit_record_5569`). |
| case_23 | picked `account_7015` instead of `account_410` | Two account-deletion activities in the same batch fit this case equally well (same result, same timing). The tie-break picks the wrong one. |

We did not special-case any of these: the fixes would need either labels or a rule that only
fits these rows.

## 2. Custom evaluation cases

These are test requests (no published answer) whose correct handling we worked out by hand from
the evidence. Each one targets one behaviour, so it checks the steps that behaviour determines
rather than a full reference row. They are encoded in `CUSTOM_CASES` in `evaluation/main.py`.

| # | Case | What it tests | Expected | Result |
| --- | --- | --- | --- | --- |
| 1 | case_46 | Account tombstone screenshot that keeps only `user_17` and no name, email, phone or hash. Policy allows the stable reference, so it is compliant. | `COMPLETE`, `VERIFY_RECORD_REDACTED tombstone_17` citing `evidence_42` | PASS |
| 2 | case_61 | Object-storage screenshot shows only a file name. The catalog alias `delivery_confirmation_19.pdf` maps it to `object_19`. A SQL replica holds another customer's attachment with the same file name (`support_3802`), which must not be linked. | `INCOMPLETE`, `REPORT_REMAINING_RECORD object_19` (`evidence_46`), `DELETE_RECORD object_19`, no `support_3802` | PASS |
| 3 | case_33 | A PDF customer statement (`NST-2026-0718-1842`) rendered by `account_history_service` is the export `export_1842` in `export_service`. This needs cross-system alias resolution. | `INCOMPLETE`, `REPORT_REMAINING_RECORD export_1842` citing `evidence_18` | PASS |
| 4 | case_55 | Backup console screenshot shows the subject's archive with no restore block. This is a restore risk, not a deletion. | `REPORT_RESTORE_RISK backup_9287` (`evidence_32`), `BLOCK_RESTORE` | PASS |
| 5 | case_50 | Analytics profile screenshot still shows `user_20` and the email. Analytics policy is anonymize, not delete. | `REPORT_EXPOSED_PII analytics_7438` (`evidence_19`), `ANONYMIZE_RECORD` | PASS |
| 6 | case_539 | "Can you tell me what personal information you hold about me? This is an information request, not a request to erase it." | `NOT_APPLICABLE`, `[]` | PASS |
| 7 | case_45 | Six signed security audit events read from a screenshot are retained records and must be verified as kept, not deleted. | `COMPLETE`, `VERIFY_RECORD_PRESENT audit_record_003` | PASS |

**7 / 7 pass** with the model answers. With `--offline` and an empty cache (no API key), cases 2 to 6
fail. That is the measured value of the model in this pipeline.

### Intent check

Claude labelled 10 of the 33 free-form texts `NOT_DELETION`: a data copy, a portable export, an
information request, invoices, login help, a surname correction, a phone change, an email change,
and two marketing opt-outs. These are exactly the 10 accounts that the `privacy_intake`
`CLASSIFY_REQUEST` activities mark as non-deletion. The pipeline does not read those activities
for intent, so they act as an independent check. Complaints about an earlier deletion ("I deleted
my account but…", "the privacy page still says my request failed") were correctly kept as deletion
requests.

## 3. Failures found and improvements made

The sample metrics after each change (step F1 / case accuracy):

| Step | Change | Step F1 | Case acc. |
| --- | --- | ---: | ---: |
| 1 | First end-to-end engine: evidence parsers and identifier matching | 0.88 | – |
| 2 | Limit evidence to `[requested_at, audit_at]`. Repeat requesters (case_17) had been pulling in an earlier request's account and tombstone. | ↑ | ↑ |
| 3 | Evaluate log traces line by line. A trace's last event (`deletion_marker_check`) had been overwriting the state shown by earlier lines. | ↑ | ↑ |
| 4 | Link deleted accounts and anonymized records through the deletion worker's activity stream, matched globally per batch | ↑ | ↑ |
| 5 | Separate hand-written workflow notes from batch-worker rows. Batch analytics had been assigned to story cases (case_10 got `analytics_1895`). | ↑ | ↑ |
| 6 | Account tie-breaks: names from later exports, prefer accounts observed absent for compliant cases, match the reported status | 0.974 | 96.9% |
| 7 | Claude vision for 11 screenshots and 4 PDFs, mapping to states in code | 0.971 | 100% |
| 8 | Treat a PDF that describes its own uploaded file as the ticket's attachment (`SUPPORT_ATTACHMENT`, so delete rather than redact). This fixed case_07. | **0.987** | **100%** |
| 9 | A retained record known only from the activity stream cites that activity in a `COMPLETE` case. Before, it had an empty evidence id, which the contract forbids. | 0.987 | 100% |

Design decisions made while checking the visual cases:

- **State is decided by code, not the model.** At first the schema asked Claude for a verdict
  (`PRESENT_WITH_PERSONAL_DATA` / `PRESENT_DEIDENTIFIED`). That was ambiguous for tombstones,
  where a user id is allowed but a name is not. Now Claude only reports which kinds of personal
  data are visible (`name`, `email`, `phone`, `postal_address`, `email_hash`, `user_id`). The same
  per-category rules used for JSON and SQL records then decide the state.
- **Aliases come from the data catalog.** A file name or statement number is resolved through the
  `LINK_RESOURCE_IDENTITY` activities. A bare `user_N` alias is accepted only from its own system,
  so a user id printed on some other screen is never mistaken for a tombstone.
- **Checked against the output contract:**
  - 518 rows, sorted by case number.
  - Steps numbered from 1.
  - Every `COMPLETE` step cites evidence.
  - Every proposed `INCOMPLETE` step has an empty evidence id.

### Known risks in the test set

- **marketing_001 (case_63).** The data catalog links it to the requester, but the screenshot shows
  a different name and email. We follow the catalog, as for the other ten visual records, all of
  which agree with their catalog links. If the screenshot is meant to override the catalog, this
  case should not report the marketing profile.
- **Account ties.** Like case_23, a few test cases share a deletion batch with an equally good
  account candidate. The deterministic tie-break may pick the wrong account.
- **Missing records.** Records that appear in no participant-visible file (as in case_04, 18 and
  20) cannot be found.
