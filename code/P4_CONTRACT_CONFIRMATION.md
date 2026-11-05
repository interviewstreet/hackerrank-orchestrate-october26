# P3 → P4 contract confirmation (P4)

**Status: P3 CONFIRMATION COMPLETE.** P3 reviewed commit `e72909a` and
approved the implementation and tests. One item is still an **OPEN TEAM
QUESTION**: a retained record missing at `audit_at` (§6 item 5).

This document records what the code does today
(`policy_engine.decide()` → `step_builder.build_steps()`) and how that
compares with the proposal in `CONTRACTS.md` sections 2 and 3. Those sections
are still marked "PROPOSAL, P3 and P4 to confirm" because `CONTRACTS.md` has
not been changed yet.

### Decisions confirmed by P3

1. **`decide()` owns all policy decisions.** It decides which records, flows and restore paths are relevant, which operation each one gets, the `deletion_status`, the evidence cited, and the order inside each phase.
2. **`build_steps()` only constructs, validates and numbers steps.** It must not make policy decisions or independently reorder policy results.
3. **Numeric natural sorting of `resource_id` is confirmed.** For example, `account_9` comes before `account_10`.
4. **`decide()` returns only `COMPLETE` or `INCOMPLETE`.** `NOT_APPLICABLE` comes from P1's classifier in `main.py`. `decide()` is not called for those requests.
5. **Every `INCOMPLETE` case has at least one finding.**

Checked against: `AGENTS.md` §6.3–6.6, `code/CONTRACTS.md`,
`code/policy_engine.py`, `code/step_builder.py`, `code/main.py`,
`code/validate_output.py`, `code/tests/test_policy_engine.py`,
`code/test_main.py`. Implementation at commit `cafd103`.

## 1. Input and output

The implemented interface is **not** the one in the `CONTRACTS.md` §2 proposal.

| | `CONTRACTS.md` proposal | Implemented |
|---|---|---|
| Who chooses operations | P4 maps `resources` / `flows` / `restore_risks` to operations | P3 (`decide()`) chooses every operation |
| Who orders steps | P4 sorts | P3 orders inside each phase (`_ordered()`) |
| What P4 reads | `resources`, `flows`, `restore_risks` | `deletion_status`, `findings`, `remediation`, `verification` |
| What P4 does | Maps, filters, sorts, numbers | Validates, fills in `evidence_id` rules, numbers |

`decide()` returns a dict. `build_steps()` reads only these keys:

```python
{
  "deletion_status": "COMPLETE" | "INCOMPLETE",   # NOT_APPLICABLE is also accepted
  "findings":     [{system_id, resource_id, operation, state, evidence_id}, ...],
  "remediation":  [...same shape...],
  "verification": [...same shape...],
}
```

The other keys (`resources`, `flows`, `restore_risks`, `timeline`,
`conflicts`, `unverified`, `identity`, `notes`, `case_id`) are for the audit
trail and the evaluation report. P4 ignores them. Their shapes differ from the
proposal. For example, `resources` items carry `rule_id`, `action`, `finding`,
`remediation`, `verification` and `copies` instead of `required_treatment`,
`state_at_audit` and `satisfied`. `timeline` is always `[]`.

`build_steps()` returns `list[dict]`. Each dict has exactly the AGENTS.md §6.3
fields: `step_no, phase, system_id, resource_id, operation, state, evidence_id`.
`main.py` serialises the list with `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`.

## 2. Operation and state mappings

P3 sets the operation. `build_steps()` checks that it belongs to the phase
and that its state matches. If `state` is missing, it fills it in. If the
state is wrong, it raises `ValueError`.

| Phase | Operation → required state |
|---|---|
| FINDING | `REPORT_REMAINING_RECORD`→`PRESENT`, `REPORT_EXPOSED_PII`→`PRESENT`, `REPORT_ACTIVE_DATA_FLOW`→`ACTIVE`, `REPORT_RESTORE_RISK`→`ACTIVE` |
| REMEDIATION | `DISABLE_DATA_FLOW`→`DISABLED`, `BLOCK_RESTORE`→`BLOCKED`, `DELETE_RECORD`→`ABSENT`, `REDACT_RECORD`→`REDACTED`, `ANONYMIZE_RECORD`→`ANONYMIZED` |
| VERIFICATION | `VERIFY_RECORD_ABSENT`→`ABSENT`, `VERIFY_RECORD_PRESENT`→`PRESENT`, `VERIFY_RECORD_REDACTED`→`REDACTED`, `VERIFY_RECORD_ANONYMIZED`→`ANONYMIZED`, `VERIFY_DATA_FLOW_DISABLED`→`DISABLED`, `VERIFY_RESTORE_BLOCKED`→`BLOCKED` |

This matches AGENTS.md §6.4 exactly. No other phases, operations or states
are possible.

The proposal's treatment table (`DELETE` → `REPORT_REMAINING_RECORD` /
`DELETE_RECORD` / `VERIFY_RECORD_ABSENT`, `TOMBSTONE` → redact and verify
redacted, `RETAIN` → verify present only, and so on) is now applied inside
`policy_engine.py` rather than in P4.

## 3. Which steps are written

| Status | FINDING | REMEDIATION | VERIFICATION |
|---|---|---|---|
| `INCOMPLETE` | One per unsatisfied record or active flow/restore. **Must** cite evidence | One per finding. `evidence_id=""` | One per assessed item, including items that were already compliant. `evidence_id=""` |
| `COMPLETE` | None (`build_steps()` raises if any) | None (raises if any) | Only items whose compliant state is proven at `audit_at`. **Must** cite evidence |
| `NOT_APPLICABLE` | — | — | — (`build_steps()` returns `[]`) |

- `decide()` sets `INCOMPLETE` when there is at least one finding, and `COMPLETE` otherwise.
- For a `COMPLETE` case, a required state that no evidence proves is left out of the steps and listed in `decision["unverified"]`, so it never produces an unbacked step.
- `NOT_APPLICABLE` is decided by P1's classifier in `main.py`. `decide()` is not called and the row is written as `NOT_APPLICABLE, []`. `build_steps()` also returns `[]` for that status, as a safeguard.
- If `audit_at` is empty or the email cannot be resolved, `main.py` writes `INCOMPLETE, []` without calling P3 or P4. In the current 518-case run this happens 0 times.

## 4. Evidence ID rules

- **FINDING**: a non-empty `evidence_id` is required (the `file_id`, `activity_id` or `audit_id` that P3 chose). If it is empty, `ValueError` is raised.
- **REMEDIATION and VERIFICATION in an `INCOMPLETE` case**: P4 forces `evidence_id=""` even if P3 supplied one, because these steps describe future work.
- **VERIFICATION in a `COMPLETE` case**: a non-empty `evidence_id` is required. If it is empty, `ValueError` is raised.
- P4 does **not** re-check that a cited id exists or was captured at or before `audit_at`. P3 selects only evidence available at `audit_at`. `validate_output.py` checks the existence and capture time of every cited id across the whole `output.csv`.

## 5. Ordering and step numbering

- Phases are written in the order FINDING, then REMEDIATION, then VERIFICATION (`_PHASE_KEYS` in `step_builder.py`).
- Inside each phase, P3 sorts by the position of the operation in the AGENTS.md §6.4 table, then by `system_id`, then by `resource_id`. Within REMEDIATION, this puts `DISABLE_DATA_FLOW` and `BLOCK_RESTORE` before `DELETE`, `REDACT` and `ANONYMIZE`.
- **`resource_id` uses numeric natural ordering, not lexical ordering.** P3's `_rid_key()` in `policy_engine.py` splits the id into a prefix and a trailing number and compares the number as an integer, so `account_9` comes before `account_10`. This is existing P3 behaviour, and P3 has confirmed it. `tests/test_policy_engine.py::test_resource_ids_use_numeric_natural_sorting` covers it as a regression test. The test checks both `decide()`'s findings and the FINDING steps that `build_steps()` produces.
- P3 removes duplicate `(system_id, resource_id.lower(), operation)` entries.
- `step_no` runs consecutively from 1 across the whole case. P4 assigns it, and any input `step_no` is ignored.
- P4 keeps P3's order, including the natural `resource_id` order, and does not re-sort.
- The result is the same as the proposal's single global sort, because the operation table is already grouped by phase.

## 6. Ambiguities and open points, with P3's answers

1. **Interface change: CONFIRMED by P3.** `decide()` owns all policy decisions, and `build_steps()` only constructs, validates and numbers steps (see "Decisions confirmed by P3"). Section 1 of this document describes the real contract. `CONTRACTS.md` §2–3 still describes the old proposal (P4 maps resources to operations and sorts), so it should be updated to match.
2. **`resource_id` tie-break: CONFIRMED by P3 as numeric natural ordering.** The `CONTRACTS.md` proposal says only "sort by `resource_id`", which could be read as lexical order. The confirmed behaviour is numeric natural ordering through P3's `_rid_key()` (`account_9` before `account_10`; see section 5). A regression test covers it. The 32 samples contain no ordering comparison where numeric natural sorting and alphabetical sorting would produce different results: no sample case has two steps with the same operation and `system_id`. In the current 518-case output, 10 such groups have more than one `resource_id`, and none of them orders differently under the two methods. So no current row depends on this choice.
3. **Status mismatch guard: ANSWERED by P3, confirmation complete.** P3 confirmed that `decide()` returns only `COMPLETE` or `INCOMPLETE`, and that `NOT_APPLICABLE` comes from P1's classifier. The theoretical case where `main.py` replaces an unexpected status with `INCOMPLETE` while `build_steps()` still sees the original status therefore cannot occur under the confirmed contract. P4 needs no change.
4. **At least one finding per `INCOMPLETE` case: ANSWERED by P3, confirmation complete.** P3 confirmed that every `INCOMPLETE` case has at least one finding. `decide()` guarantees this by construction (status is `INCOMPLETE` only when findings exist), and `validate_output.py` checks it across `output.csv`. As agreed, `build_steps()` does not make this policy decision.
5. **OPEN TEAM QUESTION: a missing retained record is silently ignored (possible gap against AGENTS.md §6.5).** `CONTRACTS.md` §4 Q3 asks what should happen when a `RETAIN` record is missing at `audit_at`. In `_assess()` (`policy_engine.py`, the "no copy present at audit_at" branch), a `RETAIN` or `ACCOUNT_TOMBSTONE` resource with no present copy returns `None`. It produces no step and does not affect the status. AGENTS.md §6.5 says a case is `COMPLETE` only when "every required retained record remains available". No allowed operation can restore such a record. Possible options:
   - mark the case `INCOMPLETE` with a `VERIFY_RECORD_PRESENT` step;
   - keep the current behaviour and record the case in `notes` / `unverified`.

   This is still unresolved. The team (P3 first) needs to decide. P4 has not changed this policy.
6. **The other open questions in `CONTRACTS.md` §4 are answered by the implementation, but nobody has confirmed the answers:**
   - Q1: `system_activity.csv` is read by `activity.py`, which P3 uses.
   - Q2: replica copies are kept separately inside a resource (`copies`). The strictest required action across the copies that are present decides the resource, and one step is emitted per `(system_id, resource_id)`. An absence is only verified when every copy that was ever seen present has a later proven absence.
   - Q4: `rule_id` and replica details are included in `resources`.

## 7. Evidence that the implementation works

- `tests/test_policy_engine.py::test_step_builder_numbers_phases_and_blanks_future_evidence`, `::test_step_builder_rejects_values_outside_contract`, `::test_active_sync_and_restore_risks_and_safe_order` and `::test_resource_ids_use_numeric_natural_sorting`, plus the determinism and public-sample tests, all pass.
- The full suite gives 476 passed, 1 skipped and 592 subtests passed. Command: `cd code && python -m pytest -q tests test_identity_resolver.py test_main.py test_request_classifier.py test_utils.py`.
- `python code/main.py && python code/validate_output.py` gives **VALID** for 518 rows. The regenerated `output.csv` is byte-identical to the committed file after line-ending normalisation (SHA-256 `a215494b…97b6ef`).

## 8. Message to send to P3

*Sent to P3. P3's answers are recorded in "Decisions confirmed by P3" and §6. Question 4 is still an open team question. The original message is kept below for reference.*

> Hi P3, P4 here. I've checked the P3→P4 hand-over against the code at
> `cafd103`. The details are in `code/P4_CONTRACT_CONFIRMATION.md`. Could you
> confirm or correct these points?
>
> 1. The real contract is: `decide()` returns `deletion_status` plus ordered
>    `findings` / `remediation` / `verification` lists of
>    `{system_id, resource_id, operation, state, evidence_id}`. `build_steps()`
>    only validates, applies the evidence-id rules and numbers the steps. Do
>    you agree that we replace the §2–3 PROPOSAL in `CONTRACTS.md` with this?
> 2. I've documented that `resource_id` is sorted in numeric natural order by
>    your `_rid_key()` (`account_9` before `account_10`), and I've added a
>    regression test for it. P4 keeps that order. Please shout if lexical
>    order was intended.
> 3. Can you confirm that `decide()` only ever returns `COMPLETE` or
>    `INCOMPLETE`, and that an `INCOMPLETE` decision always has at least one
>    finding?
> 4. When a `RETAIN` or tombstone record is missing at `audit_at`, `_assess()`
>    currently drops it. It produces no step and does not change the status.
>    AGENTS.md §6.5 says COMPLETE requires every retained record to remain
>    available. Should such a case be INCOMPLETE (`CONTRACTS.md` §4 Q3)? This
>    is an open team question.
>
> Once you reply, I'll update `CONTRACTS.md` and remove the PROPOSAL labels.
