# Evaluation report

## 1. Sample regression (public labelled cases)

Pipeline run on `sample_deletion_requests.csv` and scored against `sample_output.csv`. Dev = case_01–22 (used while building), holdout = case_23–32 (looked at only at milestones). Caveat: the late-export fix (§5 #11) was found on all 32 samples and 4 of its 5 hits are holdout cases, so the holdout is no longer an unbiased estimate; expect hidden-set exact sequence below it.

| Split | Cases | Status acc. | Step P | Step R | Step F1 | Sequence acc. | Citation acc. |
|---|---|---|---|---|---|---|---|
| all | 32 | 100.0% | 97.9% | 96.9% | 97.4% | 84.4% | 97.3% |
| dev | 22 | 100.0% | 96.6% | 95.0% | 95.8% | 77.3% | 94.7% |
| holdout | 10 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

Field-level accuracy: each gold step is paired with a predicted step of the same case (exact matches first, then the unused step agreeing on most fields, >= 2), so every field, the resource included, is scored on its own; an unpaired gold step counts as wrong on every field.

| Field | phase | system_id | resource_id | operation | state | evidence_id |
|---|---|---|---|---|---|---|
| all | 98.4% | 98.4% | 96.9% | 98.4% | 98.4% | 97.9% |

Per-operation alignment (gold operation -> predicted operation at the same resource/phase):

| gold -> predicted | count |
|---|---|
| <none> -> VERIFY_RECORD_ABSENT | 4 |
| ANONYMIZE_RECORD -> ANONYMIZE_RECORD | 5 |
| BLOCK_RESTORE -> BLOCK_RESTORE | 3 |
| DELETE_RECORD -> DELETE_RECORD | 21 |
| DISABLE_DATA_FLOW -> DISABLE_DATA_FLOW | 6 |
| REDACT_RECORD -> REDACT_RECORD | 6 |
| REPORT_ACTIVE_DATA_FLOW -> REPORT_ACTIVE_DATA_FLOW | 6 |
| REPORT_EXPOSED_PII -> REPORT_EXPOSED_PII | 11 |
| REPORT_REMAINING_RECORD -> REPORT_REMAINING_RECORD | 21 |
| REPORT_RESTORE_RISK -> REPORT_RESTORE_RISK | 3 |
| VERIFY_DATA_FLOW_DISABLED -> VERIFY_DATA_FLOW_DISABLED | 9 |
| VERIFY_RECORD_ABSENT -> <missing> | 3 |
| VERIFY_RECORD_ABSENT -> VERIFY_RECORD_ABSENT | 47 |
| VERIFY_RECORD_ANONYMIZED -> <missing> | 1 |
| VERIFY_RECORD_ANONYMIZED -> VERIFY_RECORD_ANONYMIZED | 11 |
| VERIFY_RECORD_PRESENT -> <missing> | 2 |
| VERIFY_RECORD_PRESENT -> VERIFY_RECORD_PRESENT | 22 |
| VERIFY_RECORD_REDACTED -> VERIFY_RECORD_REDACTED | 10 |
| VERIFY_RESTORE_BLOCKED -> VERIFY_RESTORE_BLOCKED | 6 |

Cases whose step list is not an exact match (5):

- `case_04` status COMPLETE (gold COMPLETE); missing `account_004`, `analytics_901`; extra `account_3865`
- `case_08` status INCOMPLETE (gold INCOMPLETE); missing `account_008`; extra `account_5482`, `support_2351`
- `case_10` status INCOMPLETE (gold INCOMPLETE); missing `account_010`; extra `account_007`
- `case_18` status INCOMPLETE (gold INCOMPLETE); missing `audit_record_6645`; extra –
- `case_20` status INCOMPLETE (gold INCOMPLETE); missing `audit_record_5569`; extra –

## 2. Intent classification

Labelled set: `code/evaluation/intent_cases.md` (62 own multilingual texts) + 32 public samples.

| Classifier | n | Accuracy | NON_DELETE precision | NON_DELETE recall |
|---|---|---|---|---|
| llm | 94 | 100.0% | 100.0% | 100.0% |
| heuristic | 94 | 100.0% | 100.0% | 100.0% |

Confusion (expected->predicted): **llm** DELETE->DELETE=61, NON_DELETE->NON_DELETE=33; **heuristic** DELETE->DELETE=61, NON_DELETE->NON_DELETE=33

Evaluation texts: 375 unique, 375 labelled by the LLM; LLM/heuristic agreement **100.0%**, 0 disagreement(s). NOT_APPLICABLE cases: case_533, case_534, case_535, case_536, case_537, case_538, case_539, case_540, case_541, case_542.

## 3. Custom end-to-end evaluation cases

25/25 hand-labelled scenarios pass. Each writes a miniature dataset in the real file formats, runs `main.py` as a subprocess and compares every output step (code: `code/tests/e2e/`).

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | `historical_email_only` | case_01: INCOMPLETE | pass |
| 2 | `near_miss_decoys` | case_02: COMPLETE | pass |
| 3 | `evidence_after_audit_is_ignored` | case_03: COMPLETE | pass |
| 4 | `korean_non_deletion_request` | case_04: NOT_APPLICABLE | pass |
| 5 | `success_claim_is_not_proof` | case_05: INCOMPLETE | pass |
| 6 | `failover_replica_drift` | case_06: INCOMPLETE | pass |
| 7 | `connector_recreates_deleted_entry` | case_07: INCOMPLETE | pass |
| 8 | `restorable_backup` | case_08: INCOMPLETE | pass |
| 9 | `tombstones_exposed_and_clean` | case_09: INCOMPLETE, case_10: COMPLETE | pass |
| 10 | `support_message_vs_attachment` | case_11: INCOMPLETE | pass |
| 11 | `retained_audit_and_legal_hold` | case_12: COMPLETE | pass |
| 12 | `analytics_profile_vs_marketing_contact` | case_13: INCOMPLETE | pass |
| 13 | `complete_cites_latest_evidence` | case_14: COMPLETE | pass |
| 14 | `identifiers_joined_across_trace_lines` | case_15: INCOMPLETE | pass |
| 15 | `unknown_identity_uses_bare_email` | case_16: INCOMPLETE | pass |
| 16 | `retained_record_from_late_export` | case_17: INCOMPLETE | pass |
| 17 | `late_export_never_supports_complete` | case_18: COMPLETE | pass |
| 18 | `unknown_email_gets_no_timing_link` | case_19: COMPLETE | pass |
| 19 | `earlier_request_owns_its_leftovers` | case_20: INCOMPLETE, case_21: COMPLETE | pass |
| 20 | `recent_leftover_of_earlier_request_is_reported` | case_23: INCOMPLETE | pass |
| 21 | `tombstone_status_on_profile_rows` | case_24: COMPLETE, case_25: INCOMPLETE | pass |
| 22 | `unlisted_resource_prefixes` | case_26: INCOMPLETE | pass |
| 23 | `cyrillic_deletion_request` | case_27: INCOMPLETE | pass |
| 24 | `other_recreation_and_check_wordings` | case_28: INCOMPLETE | pass |
| 25 | `archive_without_visible_block_is_a_restore_risk` | case_29: INCOMPLETE | pass |

## 4. Invariants on the 518-case run (no labels needed)

| Check | Result |
|---|---|
| contract | pass |
| citations | pass |
| policy_sanity | pass |
| determinism | pass |
| identifier_invariance | pass |
| time_travel | pass |
| visual_grounding | pass |
| time-travel cases re-run with later evidence physically removed | 518 |
| vision records checked against local OCR (15 real + 3 edge images; VISION_SPEC step 2) | 38, 38 grounded |

## 5. Failures found and improvements made

Each row is a failure a test layer caught during development, in the order it happened, and the change that fixed it.
Sample numbers are on all 32 public cases (status accuracy / exact sequence accuracy).

| # | Caught by | Failure | Fix | Effect |
|---|---|---|---|---|
| 1 | Sample regression | First end-to-end run: 94% status, 41% sequence. Absence inferred from *any* later snapshot that lacked a record overrode an explicit PRESENT row (case_05's profile left on a failover replica was reported deleted because a later, unrelated inventory had no rows). | Absence inferred from a full snapshot is now only a fallback when nothing explicit ever observed the record. | case_05, case_24 fixed |
| 2 | Sample regression | Workflow steps were attached to the wrong person: any deletion-worker step whose 30-second phase matched was accepted. | Learned *per step class* cadences ("Policy action completed" steps at phase 9–11 s, "final result"/check steps at 20–22 s) from workflows whose account and steps are both identifier-linked. | precision 0.81 → 0.90 |
| 3 | Sample regression | Profile deletions were assigned to cases arbitrarily inside overlapping request windows (case_21/25/27/29 swapped accounts). | Account inherits the owner of its chain's identifiable steps; learned "deletion precedes reported_at by 46–74 min" prior; minute-phase of the first identifiable step; global one-to-one assignment, most decisive first. | sequence 44% → 62% |
| 4 | Sample regression | Failed workflow steps (search entries of *other* people) linked by timing alone (case_18, case_32). | Only successful policy actions may be linked by timing alone: a failed step leaves identifiers behind and must link by identifier. | status 97% → 100% |
| 5 | Trace review (L6) | 10 retained audit records reported ABSENT: a `cache_lookup result="miss"` line in the same log trace overwrote the readback's `rows=1`. | Lines without a resource id contribute only lookup keys to the trace merge. | regression test `split_trace_log` scenario |
| 6 | Invariants (contract) | case_61 produced COMPLETE with no steps (invalid row): the subject's only footprint is an attachment shown in an object-storage screenshot by file name. | Second visual pass that transcribes file listings; data-catalog LINK activities map `object_19 (delivery_confirmation_19.pdf)`; defined fallback for subjects with no observable footprint. | 0 contract errors |
| 7 | Invariants (time travel) | 6/51 rows changed when later evidence was physically removed: the workflow cadence was re-learned from the truncated data, and workflow elimination used other cases' later evidence. | Workflow assignment is computed per audit cutoff with only evidence available then; the learned workflow cadence is a frozen artifact (`code/cache/workflow_model.json`) describing the deletion worker, not any person. | 0 time-travel failures |
| 8 | Sample regression | An attachment last seen 199 days before case_07's request (it belongs to the same person's earlier February request) was attached to the September request. | Records last seen more than 90 days before the request are treated as an earlier lifecycle. | precision 0.963 → 0.978 |
| 9 | Intent eval (L2) | The LLM labelled sample case_27 ("please audit the deletion … confirm the account was fully removed") NON_DELETE when batched with the own intent set. | Prompt states that requests to audit/confirm a removal reaffirm an erasure request. | LLM accuracy 98.9% → 100% on 94 texts |
| 10 | Unit test | The budget allowed one more zero-estimate call after the cap was reached exactly. | `reserve` refuses when committed spend already equals the cap. | budget tests green |
| 11 | External review (independent scorer) | 7 sample `VERIFY_RECORD_PRESENT` steps on retained security audit records were missing. Four of those records appear only in a records bundle *exported* two days after the audit, but its `security_audit_events` snapshot was *taken* at the audit instant; one appears in a later log export on a line timestamped before the audit. | A retained record that the subject's identifiers link to, seen only in a later export whose own snapshot/line time is at or before `audit_at`, adds an uncited post-remediation `VERIFY_RECORD_PRESENT` to an INCOMPLETE case. It never adds a finding or citation, never supports a COMPLETE verdict, and never changes a status. The time-travel invariant allows exactly this difference. | sequence 68.8% → 84.4% (holdout 60% → 100%); 116 eval rows gain the check |
| 12 | External review (probe) | A request with an unknown email and copied timestamps was answered COMPLETE, citing an account attached only by workflow timing. | A subject that resolves to no identity gets no timing-only workflow link, so no verdict can rest on timing alone. | e2e `unknown_email_gets_no_timing_link`; 0 eval rows change |
| 13 | External review (robustness) | Unreadable visual evidence (no cache or no vision backend) silently counted as "no records", which turns INCOMPLETE into COMPLETE. A requests CSV saved with a UTF-8 BOM crashed with `KeyError: 'case_id'`, and a wrong `--dataset-dir` printed a traceback. | Unreadable files are tracked; every COMPLETE verdict that could depend on one is marked `unverified_evidence` in its trace and counted on stderr, and `GDA_STRICT_EVIDENCE=1` turns this into exit code 4. CSVs are read as `utf-8-sig` with trimmed headers. Missing inputs give a one-line error and exit 1. | unit tests `test_byte_order_mark_and_padded_header`, `test_unreadable_visual_evidence_is_tracked` |
| 14 | External review (metrics) | The field-level table was degenerate: steps were aligned on `(phase, system_id, resource_id)`, so those fields matched by construction. | Steps are paired by best field agreement (exact first). | non-degenerate field table |
| 15 | External review (design) | The 90-day staleness cut-off of #8 was a tuned constant that could hide a real leftover on its own. | A record is now left to an earlier lifecycle only if it was *also* last seen no later than the audit of the same person's earlier deletion request. Both sample precedents (case_61 → case_07, case_46 → case_17) satisfy both conditions. Using the earlier-request condition alone turned case_33 into a false COMPLETE (its export was last seen PRESENT four weeks before), which a second independent review caught, so the 90-day age stays as a safety margin. | samples and eval unchanged; e2e `earlier_request_owns_its_leftovers` and `recent_leftover_of_earlier_request_is_reported` |
| 16 | Second independent review | Without the LLM cache the default run still exited 0 with 7 cases flipped to COMPLETE, and the unverified flag marked every COMPLETE row. | A flag now marks only COMPLETE cases during whose request (`requested_at`..`audit_at`) an unreadable file was captured; this catches all 8 offline flips. The run exits 4 by default after writing every row; `GDA_STRICT_EVIDENCE=0` accepts the verdicts. | offline: 120 instead of 158 flagged rows, 8/8 flips caught; replay unaffected |
| 17 | External QA judge (own 28-case fixture, no LLM) | Status 0.643, step F1 0.476 on a fixture with the same contract but other spellings. Five causes: (a) resource ids outside the known prefixes (`cust_`, `log_`) were dropped; (b) `account_*` rows with `account_status='TOMBSTONE'` were deleted instead of redacted; (c) user ids outside the `user_<n>` scheme (`u_2008`) did not link; (d) the offline intent fallback missed Russian (and some Spanish/English) erasure requests; (e) other activity wordings ("Reindex job recreated …", "check confirmed X can restore …") and a bracket log layout without a trace id were not read. Also: no Unicode normalisation of emails, manifest paths not confined to the dataset. | System from the evidence's own `origin_system` / log service for unknown prefixes, category from the collection / event name; TOMBSTONE status → `ACCOUNT_TOMBSTONE`; reference fields link any id-shaped value; deletion verbs for ru/uk/pl/it/nl/tr/zh/ar/hi and the Spanish/English gaps; broader recreation/check patterns; NFKC + casefold; paths resolved under the dataset root. Expected steps re-derived from the judge's quoted evidence only (never its answers). | 6 of the judge's failing cases rebuilt from its quotes now match its expected steps exactly; offline intent 56/62 → 62/62 and now agrees with the LLM on all 518 eval texts; real `output.csv` byte-identical; e2e `tombstone_status_on_profile_rows`, `unlisted_resource_prefixes`, `cyrillic_deletion_request`, `other_recreation_and_check_wordings` |
| 18 | Vision review (VISION_SPEC) | Nothing checked that a vision transcription is faithful (a local VLM invented `export_001/002` for e15), and with no vision result a screenshot/PDF was skipped entirely. | OCR grounding guard (Tesseract / `pdftotext`, cached by sha256): ungrounded ids are dropped, ungrounded emails/phones removed; OCR-only fallback that can report findings but never prove absence. Both switchable, on by default. e15 transcribed by Sonnet ($0.147). | 38/38 vision records grounded (34 real + 4 edge); e15 passes (relabelled from known-limitation); offline flips 8 → 5; `output.csv` byte-identical; invariant `visual_grounding` |
| 19 | Cross-model run (Kimi K3 via Ollama cloud, all 34 calls live) | 517/518 rows identical; case_55 flipped because Kimi read the subject's archive `backup_9287` on the backup console as `ACTIVE` where Sonnet read `FOUND`. The screenshot shows the archive (linked to the subject by a data-catalog activity before `audit_at`) but no restore state; the code ignored an archive whose restore state was not shown, so the verdict depended on one transcribed word. | A subject's archive that evidence shows to exist, with nothing showing its restore blocked, is a restore path (the contract: COMPLETE only when no restore path can recreate the data). | case_55 COMPLETE → INCOMPLETE (now the same under both models); 0 other eval rows; samples unchanged; e2e `archive_without_visible_block_is_a_restore_risk` |
| 20 | Owner's test (invoice PDF for case_111's person registered in the manifest, no vision result) | No row changed, but the run exited 4 because case_41, a different person whose window contained the capture time, was flagged as resting on the unread file. With an earlier capture time 13 unrelated requests were flagged. | With OCR text, an unread file counts only for requests whose person (identifiers, resource ids) it shows, with OCR tolerance; with no OCR text it still counts for all of them. Reproduced first by a test committed on its own (`test_unread_evidence.py`, expectedFailure), then fixed. | owner's setup: exit 4 → 0 (and 13 → 1 flagged for an in-window capture); offline: every wrong COMPLETE still flagged (6/6 with OCR, 9/9 without), flagged total 120 → 22 with OCR; `output.csv` byte-identical |
| 21 | Owner's removal test (connector screenshot `evidence_14` deleted, manifest row kept) | case_39's only finding was in the file; the missing file was skipped without a trace, so case_39 turned COMPLETE with exit 0. | A listed but missing file counts as unread (contents unknown): COMPLETE requests in its window are flagged, exit 4, and a warning names the file. Test first (`test_unread_evidence.py`, expectedFailure), then the fix. | removal: exit 0 → 4 with case_39 flagged; `output.csv` unchanged |
| 22 | Same test, file and manifest row removed | The no-footprint fallback "verified" `account_8819` ABSENT citing `activity_3114`, a `DELETE_RECORD … FAILED` event; in a two-person reproduction it even gave each person the other's account. A workflow-only account also got the deletion event as its citation in the main path. | Workflow results are claims: an account nothing observed is an *unproven* absence (an uncited post-remediation check in INCOMPLETE cases, omitted from COMPLETE ones), and the fallback only notes the workflow in the trace (`unproven_workflow`). Test first (`test_claims_not_proof.py`, expectedFailure), then the fix. | no verification step cites an activity; samples, edge suite and `output.csv` unchanged |

## 6. Known limitations

- A data flow or backup that evidence links to the person (an identifier, or a data-catalog `LINK_RESOURCE_IDENTITY`
  activity) but whose state no evidence shows is ignored: only an observed "enabled / restore allowed" makes it a
  finding. Example from the owner's removal test: without the connector screenshot `evidence_14`, the only trace of
  `data_flow_1121` before case_39's audit is the catalog link `activity_4002`, so case_39 ends `COMPLETE []` instead of
  reporting the flow. Treating such a resource as an open path (as the backup rule of #19 does for an archive shown
  without a restore state) was measured and **not adopted**, by the owner's decision: it changes 0 of the 518
  evaluation rows and leaves the samples unchanged, but its finding could only cite the catalog link, which proves the
  flow exists and belongs to the person, not that it runs. A broader variant (any linked flow/backup, timing links
  included) changed 3 evaluation rows and lowered sample step F1 from 0.974 to 0.966, so labelled data contradicts it.
- From the external QA fixture (#17), cases that remain open: a system id the evidence never names (`log_archive`
  for a line logged by `notification_service`); a reindex job reported as recreating the very resource it names
  (no separate flow to disable); flow and backup resources that only an activity row mentions, with no identifier
  linking them to the subject; and subjects with no linked resource at all, which still return `COMPLETE []`.
- Two sample verification steps (case_18 `audit_record_6645`, case_20 `audit_record_5569`) name security audit records
  that appear in no participant file at all, so they cannot be derived.
- Five hand-written sample cases (case_02/04/07/08/10) have accounts whose deletion activity sits outside the reported
  window or has no activity at all; the generic workflow linker sometimes picks a neighbouring account for them.
- Accuracy of timing (workflow) links on the samples: **18/18** on the generated cases case_11–32 and 6/10 on the
  hand-written cases case_01–10 (all 4 wrong links are case_04/08/10). Identifier links are 76/76 and late-export
  links 5/5. The hand-written deletions use a different activity wording ("reported the requested operation as
  completed") and are logged within ±10 min of `reported_at`. All 6 such events are sample cases; none appears among
  the 518 evaluation requests.
- When several requests share one reporting window and no identifier links any of their accounts, the assignment of
  deletion workflows to requests is resolved by elimination and can swap two accounts. Status is unaffected; only the
  account `resource_id` of a verification step changes.

## 7. How to reproduce

```bash
python3 code/main.py                       # 518 rows -> output.csv (replay cache, no API key)
python3 code/evaluation/main.py            # regenerates this report and usage_report.md
python3 code/evaluation/check_all.py       # gate: unit + e2e tests, sample regression, invariants
```
