# Public Benchmark Diagnostics

This report is evaluation-only. Public labels are never imported by prediction modules.

## Exact Step Precision, Recall, and F1

- Exact-step true positives: **167**
- Predicted steps: **171**
- Expected steps: **193**
- Precision: **97.7%**
- Recall: **86.5%**
- F1: **91.8%**

## Root-Cause Matrix

| Generalizable cause | Affected sample cases |
|---|---:|
| additional evidence-grounded resource not in canonical sequence | 2 |
| resource lineage/retrieval gap | 13 |
| unavailable canonical resource (ABSENT_GLOBALLY) | 3 |
| unavailable canonical resource (POST_AUDIT_ONLY) | 5 |

## Complete Remaining Case Diagnostics

| Case | Status correct | Missing exact steps | Extra exact steps | Causes |
|---|---:|---:|---:|---|
| `case_04` | yes | 1 | 0 | unavailable canonical resource (ABSENT_GLOBALLY) |
| `case_06` | yes | 1 | 0 | resource lineage/retrieval gap |
| `case_07` | yes | 0 | 3 | additional evidence-grounded resource not in canonical sequence |
| `case_08` | yes | 1 | 0 | resource lineage/retrieval gap |
| `case_09` | yes | 1 | 0 | unavailable canonical resource (POST_AUDIT_ONLY) |
| `case_10` | yes | 1 | 0 | resource lineage/retrieval gap |
| `case_17` | yes | 0 | 1 | additional evidence-grounded resource not in canonical sequence |
| `case_18` | yes | 2 | 0 | resource lineage/retrieval gap, unavailable canonical resource (ABSENT_GLOBALLY) |
| `case_20` | yes | 2 | 0 | resource lineage/retrieval gap, unavailable canonical resource (ABSENT_GLOBALLY) |
| `case_21` | yes | 2 | 0 | resource lineage/retrieval gap |
| `case_22` | yes | 1 | 0 | resource lineage/retrieval gap |
| `case_23` | yes | 2 | 0 | resource lineage/retrieval gap, unavailable canonical resource (POST_AUDIT_ONLY) |
| `case_24` | yes | 1 | 0 | unavailable canonical resource (POST_AUDIT_ONLY) |
| `case_25` | yes | 2 | 0 | resource lineage/retrieval gap |
| `case_26` | yes | 2 | 0 | resource lineage/retrieval gap |
| `case_27` | yes | 2 | 0 | resource lineage/retrieval gap |
| `case_28` | yes | 2 | 0 | resource lineage/retrieval gap |
| `case_29` | yes | 2 | 0 | resource lineage/retrieval gap, unavailable canonical resource (POST_AUDIT_ONLY) |
| `case_30` | yes | 1 | 0 | unavailable canonical resource (POST_AUDIT_ONLY) |

## Evidence-Limitation Detail

See `observability_report.md` for each canonical resource that is absent globally or appears only after its case's audit cutoff.
