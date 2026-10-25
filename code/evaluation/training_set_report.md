# Self-Supervised Lineage Training-Set Report

No canonical output, case labels, organizer truth, or post-audit mappings are
used. Exact edge rows remain in memory and are not persisted.

## Dataset Summary

- Examples: **7,103**
- Positive grounded edges: **1,925**
- Hard negatives: **5,178**
- Subjects represented: **835**
- Excluded ambiguous contexts: **0**
- Grounded workflow edges added: **179**

## User-Disjoint Split

| Split | Users | Examples |
|---|---:|---:|
| Train | 658 | 5,656 |
| Validation | 177 | 1,447 |

No user ID occurs in both splits.

## Positive Source Coverage

| Source | Edge observations |
|---|---:|
| `activity` | 12 |
| `evidence_json` | 672 |
| `evidence_log` | 783 |
| `evidence_png` | 2 |
| `evidence_sql` | 461 |
| `evidence_txt` | 39 |
| `workflow_dependency` | 283 |

## Stage 2 Gate

The examples are suitable for deterministic Stage 3 weight training only.
Candidate generation remains bounded by the separate observability gate;
training cannot recover canonical IDs absent before their audit cutoffs.
