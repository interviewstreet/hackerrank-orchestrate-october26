# Self-Supervised Lineage Training-Set Report

No canonical output, case labels, organizer truth, or post-audit mappings are
used. Exact edge rows remain in memory and are not persisted.

## Dataset Summary

- Examples: **7,533**
- Positive grounded edges: **2,036**
- Hard negatives: **5,497**
- Subjects represented: **835**
- Excluded ambiguous contexts: **0**
- Grounded workflow edges added: **290**

## User-Disjoint Split

| Split | Users | Examples |
|---|---:|---:|
| Train | 658 | 5,985 |
| Validation | 177 | 1,548 |

No user ID occurs in both splits.

## Positive Source Coverage

| Source | Edge observations |
|---|---:|
| `activity` | 12 |
| `evidence_json` | 672 |
| `evidence_log` | 783 |
| `evidence_sql` | 461 |
| `evidence_txt` | 39 |
| `workflow_dependency` | 421 |

## Stage 2 Gate

The examples are suitable for deterministic Stage 3 weight training only.
Candidate generation remains bounded by the Stage 1 93.7% observability gate;
training cannot recover seven exact security IDs absent before their cutoffs.
