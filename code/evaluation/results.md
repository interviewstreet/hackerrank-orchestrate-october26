| Metric | Value |
| --- | --- |
| Cases | 32 |
| Status accuracy | 32/32 = 1.000 |
| Sequence accuracy (exact steps) | 15/32 = 0.469 |
| Row accuracy (status + steps) | 15/32 = 0.469 |
| Steps gold / pred / matched | 193 / 165 / 165 |
| Step precision / recall / F1 | 1.000 / 0.855 / 0.922 |
| Field accuracy `step_no` | 165/193 = 0.855 |
| Field accuracy `phase` | 165/193 = 0.855 |
| Field accuracy `system_id` | 126/193 = 0.653 |
| Field accuracy `resource_id` | 126/193 = 0.653 |
| Field accuracy `operation` | 133/193 = 0.689 |
| Field accuracy `state` | 133/193 = 0.689 |
| Field accuracy `evidence_id` | 164/193 = 0.850 |

Status confusion (rows: gold, columns: predicted):

| gold \ pred | COMPLETE | INCOMPLETE | NOT_APPLICABLE |
| --- | --- | --- | --- |
| COMPLETE | 10 | 0 | 0 |
| INCOMPLETE | 0 | 22 | 0 |
| NOT_APPLICABLE | 0 | 0 | 0 |

Custom cases (frozen, expected rows written from the rules):

| case | result | status | problems |
| --- | --- | --- | --- |
| cc01_negated_request | PASS | NOT_APPLICABLE | - |
| cc02_verify_delete | PASS | COMPLETE | - |
| cc03_injection_request | PASS | INCOMPLETE | - |
| cc04_retained_audit_record | PASS | COMPLETE | - |
| cc05_flow_and_restore_risk | PASS | INCOMPLETE | - |
| cc06_agent_text_only_state | PASS | INCOMPLETE | - |
| cc07_historical_email | PASS | INCOMPLETE | - |

Metamorphic checks:

| check | result |
| --- | --- |
| shuffle_rows:samples | PASS |
| email_case_space:samples | PASS |
| shuffle_rows:custom | PASS |
| email_case_space:custom | PASS |
| older_contradiction:cc02_verify_delete | PASS |
| audit_before_key:cc02_verify_delete | PASS |
| audit_at_key:cc02_verify_delete | PASS |
| older_contradiction:cc03_injection_request | PASS |
| audit_before_key:cc03_injection_request | PASS |
| audit_at_key:cc03_injection_request | PASS |
| older_contradiction:cc04_retained_audit_record | PASS |
| audit_before_key:cc04_retained_audit_record | PASS |
| audit_at_key:cc04_retained_audit_record | PASS |
| older_contradiction:cc05_flow_and_restore_risk | PASS |
| audit_before_key:cc05_flow_and_restore_risk | PASS |
| audit_at_key:cc05_flow_and_restore_risk | PASS |
| older_contradiction:cc07_historical_email | PASS |
| audit_before_key:cc07_historical_email | PASS |
| audit_at_key:cc07_historical_email | PASS |

Agent on the scored requests: runs=0, proposals=0, accepted=0, rejected={}
