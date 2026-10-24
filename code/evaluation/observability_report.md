# Candidate Observability Report

This is an evaluation-only diagnostic. It may compare against public canonical
output, but none of its expected-resource data may enter prediction or training.

## Gate Result

- Pre-audit candidate recall: **104/111 (93.7%)**
- 100% observability gate: **FAIL**

## Classification Counts

| Classification | Case-resource pairs |
|---|---:|
| `ABSENT_GLOBALLY` | 2 |
| `POST_AUDIT_ONLY` | 5 |
| `PRE_AUDIT_RETRIEVABLE` | 83 |
| `PRE_AUDIT_UNLINKED` | 21 |

## Blocked Canonical Resources

| Case | Resource | Audit cutoff | Classification | Later sources |
|---|---|---|---|---|
| `case_09` | `audit_record_4902` | `2026-09-16T09:00:00Z` | `POST_AUDIT_ONLY` | evidence_06 |
| `case_18` | `audit_record_6645` | `2026-09-26T11:00:00Z` | `ABSENT_GLOBALLY` | — |
| `case_20` | `audit_record_5569` | `2026-09-26T11:00:00Z` | `ABSENT_GLOBALLY` | — |
| `case_23` | `audit_record_4128` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_24` | `audit_record_7095` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_29` | `audit_record_3954` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_30` | `audit_record_1707` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |

## Decision

Training is blocked from claiming a lawful 100% result while this gate fails.
Post-audit artifacts and absent resource IDs must not become runtime mappings.
The remedy is pre-audit lineage in participant data or an evaluator correction.
