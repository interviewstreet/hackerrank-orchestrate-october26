# Ghost Data Still Exists — Case-Level Evidence Audit Report

## Executive Summary

Every generated case in `output.csv` (518 evaluation requests) was audited against admissible evidence captured at or before each case's `audit_at` timestamp. All claimed findings and verifications were verified for exact resource grounding, identity match, and temporal admissibility.

### Summary Metrics

- **Total Requests Audited:** 518 cases
- **COMPLETE Cases:** 5 cases
- **INCOMPLETE Cases:** 508 cases
- **NOT_APPLICABLE Cases:** 5 cases
- **Unsupported Evidence Citations:** 0 (0.0% error rate)

---

## Case-by-Case Evidence Audit Log

| Case ID | Status | Phase | System ID | Resource ID | Evidence ID | Evidence Support Verified | Audit Cutoff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| case_33 | INCOMPLETE | VERIFICATION | account_service | account_018 | None | N/A (Proposed action) | 2026-07-19T13:00:00Z |
| case_34 | INCOMPLETE | VERIFICATION | account_service | account_5762 | None | N/A (Proposed action) | 2026-09-27T13:00:00Z |
| case_34 | INCOMPLETE | VERIFICATION | security_service | audit_record_3753 | None | N/A (Proposed action) | 2026-09-27T13:00:00Z |
| case_35 | INCOMPLETE | VERIFICATION | account_service | account_013 | None | N/A (Proposed action) | 2026-09-02T08:00:00Z |
| case_36 | INCOMPLETE | FINDING | export_service | export_7689 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | FINDING | search_service | search_5575 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | REMEDIATION | export_service | export_7689 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | REMEDIATION | search_service | search_5575 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | VERIFICATION | account_service | account_5823 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | VERIFICATION | export_service | export_7689 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | VERIFICATION | search_service | search_5575 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_36 | INCOMPLETE | VERIFICATION | security_service | audit_record_2966 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | FINDING | search_service | search_1934 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | FINDING | integration_service | data_flow_2528 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2528 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | REMEDIATION | search_service | search_1934 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | VERIFICATION | account_service | account_5193 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | VERIFICATION | search_service | search_1934 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | VERIFICATION | security_service | audit_record_2019 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_37 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2528 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_38 | INCOMPLETE | FINDING | integration_service | data_flow_7495 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_38 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7495 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_38 | INCOMPLETE | VERIFICATION | account_service | account_2381 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_38 | INCOMPLETE | VERIFICATION | security_service | audit_record_633 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_38 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7495 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_39 | INCOMPLETE | VERIFICATION | account_service | account_014 | None | N/A (Proposed action) | 2026-08-08T10:00:00Z |
| case_40 | INCOMPLETE | FINDING | search_service | search_3200 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | FINDING | support_platform | support_4887 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | REMEDIATION | search_service | search_3200 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | REMEDIATION | support_platform | support_4887 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | VERIFICATION | account_service | account_1810 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | VERIFICATION | search_service | search_3200 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | VERIFICATION | security_service | audit_record_8349 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_40 | INCOMPLETE | VERIFICATION | support_platform | support_4887 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_41 | COMPLETE | VERIFICATION | account_service | account_4051 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_41 | COMPLETE | VERIFICATION | security_service | audit_record_7814 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_41 | COMPLETE | VERIFICATION | support_platform | support_2667 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_41 | COMPLETE | VERIFICATION | integration_service | data_flow_2901 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_41 | COMPLETE | VERIFICATION | backup_service | backup_706 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | FINDING | search_service | search_7078 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | FINDING | support_platform | support_7769 | evidence_03 | Verified | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | REMEDIATION | search_service | search_7078 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | REMEDIATION | support_platform | support_7769 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | VERIFICATION | account_service | account_4337 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | VERIFICATION | search_service | search_7078 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | VERIFICATION | security_service | audit_record_6760 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_42 | INCOMPLETE | VERIFICATION | support_platform | support_7769 | None | N/A (Proposed action) | 2026-10-01T12:00:00Z |
| case_43 | INCOMPLETE | FINDING | account_service | account_8681 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_43 | INCOMPLETE | REMEDIATION | account_service | account_8681 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_43 | INCOMPLETE | VERIFICATION | account_service | account_8681 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | FINDING | account_service | account_2064 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | FINDING | support_platform | support_1066 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | FINDING | integration_service | data_flow_223 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | FINDING | backup_service | backup_6266 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | REMEDIATION | integration_service | data_flow_223 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | REMEDIATION | backup_service | backup_6266 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | REMEDIATION | account_service | account_2064 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | REMEDIATION | support_platform | support_1066 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | VERIFICATION | account_service | account_2064 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | VERIFICATION | security_service | audit_record_1105 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | VERIFICATION | support_platform | support_1066 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | VERIFICATION | integration_service | data_flow_223 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_44 | INCOMPLETE | VERIFICATION | backup_service | backup_6266 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_45 | INCOMPLETE | VERIFICATION | account_service | account_003 | None | N/A (Proposed action) | 2026-09-06T09:00:00Z |
| case_46 | INCOMPLETE | FINDING | account_service | account_6523 | evidence_67 | Verified | 2026-03-11T08:00:00Z |
| case_46 | INCOMPLETE | REMEDIATION | account_service | account_6523 | None | N/A (Proposed action) | 2026-03-11T08:00:00Z |
| case_46 | INCOMPLETE | VERIFICATION | account_service | account_6523 | None | N/A (Proposed action) | 2026-03-11T08:00:00Z |
| case_47 | INCOMPLETE | FINDING | search_service | search_4324 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | FINDING | support_platform | support_5742 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | REMEDIATION | search_service | search_4324 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | REMEDIATION | support_platform | support_5742 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | VERIFICATION | account_service | account_045 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | VERIFICATION | search_service | search_4324 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_47 | INCOMPLETE | VERIFICATION | support_platform | support_5742 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | FINDING | search_service | search_2127 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | FINDING | integration_service | data_flow_7759 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7759 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | REMEDIATION | search_service | search_2127 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | VERIFICATION | account_service | account_046 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | VERIFICATION | search_service | search_2127 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_48 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7759 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | FINDING | search_service | search_459 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | FINDING | integration_service | data_flow_1043 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1043 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | REMEDIATION | search_service | search_459 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | VERIFICATION | account_service | account_047 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | VERIFICATION | search_service | search_459 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_49 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1043 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_50 | INCOMPLETE | VERIFICATION | account_service | account_020 | None | N/A (Proposed action) | 2026-07-14T12:00:00Z |
| case_51 | INCOMPLETE | FINDING | account_service | account_3610 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | FINDING | support_platform | support_1097 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | FINDING | integration_service | data_flow_4713 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | FINDING | backup_service | backup_7809 | evidence_94 | Verified | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4713 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | REMEDIATION | backup_service | backup_7809 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | REMEDIATION | account_service | account_3610 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | REMEDIATION | support_platform | support_1097 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | VERIFICATION | account_service | account_3610 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | VERIFICATION | security_service | audit_record_3308 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | VERIFICATION | support_platform | support_1097 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4713 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_51 | INCOMPLETE | VERIFICATION | backup_service | backup_7809 | None | N/A (Proposed action) | 2026-09-26T11:00:00Z |
| case_52 | INCOMPLETE | VERIFICATION | account_service | account_018 | None | N/A (Proposed action) | 2026-06-19T14:00:00Z |
| case_53 | INCOMPLETE | VERIFICATION | account_service | account_022 | None | N/A (Proposed action) | 2026-05-25T09:00:00Z |
| case_54 | INCOMPLETE | FINDING | search_service | search_3995 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | FINDING | analytics_platform | analytics_1738 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | FINDING | support_platform | support_835 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | FINDING | integration_service | data_flow_5080 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5080 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | REMEDIATION | search_service | search_3995 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | REMEDIATION | support_platform | support_835 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1738 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | account_service | account_052 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | search_service | search_3995 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | security_service | audit_record_6325 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | support_platform | support_835 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1738 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_54 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5080 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_55 | INCOMPLETE | VERIFICATION | account_service | account_016 | None | N/A (Proposed action) | 2026-04-30T11:00:00Z |
| case_56 | INCOMPLETE | FINDING | integration_service | data_flow_373 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_56 | INCOMPLETE | REMEDIATION | integration_service | data_flow_373 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_56 | INCOMPLETE | VERIFICATION | account_service | account_054 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_56 | INCOMPLETE | VERIFICATION | security_service | audit_record_4078 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_56 | INCOMPLETE | VERIFICATION | integration_service | data_flow_373 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | FINDING | integration_service | data_flow_1368 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | FINDING | backup_service | backup_7711 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1368 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | REMEDIATION | backup_service | backup_7711 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | VERIFICATION | account_service | account_055 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | VERIFICATION | security_service | audit_record_7219 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | VERIFICATION | support_platform | support_7479 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1368 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_57 | INCOMPLETE | VERIFICATION | backup_service | backup_7711 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_58 | INCOMPLETE | VERIFICATION | account_service | account_056 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_58 | INCOMPLETE | VERIFICATION | security_service | audit_record_8465 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_59 | INCOMPLETE | VERIFICATION | account_service | account_057 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_59 | INCOMPLETE | VERIFICATION | security_service | audit_record_962 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_60 | INCOMPLETE | VERIFICATION | account_service | account_058 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_60 | INCOMPLETE | VERIFICATION | security_service | audit_record_629 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_61 | INCOMPLETE | VERIFICATION | account_service | account_007 | None | N/A (Proposed action) | 2026-02-14T10:00:00Z |
| case_62 | INCOMPLETE | FINDING | search_service | search_5960 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | FINDING | analytics_platform | analytics_5715 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | FINDING | support_platform | support_8765 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | FINDING | integration_service | data_flow_108 | evidence_05 | Verified | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | REMEDIATION | integration_service | data_flow_108 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | REMEDIATION | search_service | search_5960 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | REMEDIATION | support_platform | support_8765 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5715 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | account_service | account_060 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | search_service | search_5960 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | security_service | audit_record_4889 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | support_platform | support_8765 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5715 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_62 | INCOMPLETE | VERIFICATION | integration_service | data_flow_108 | None | N/A (Proposed action) | 2026-09-21T10:00:00Z |
| case_63 | INCOMPLETE | VERIFICATION | account_service | account_009 | None | N/A (Proposed action) | 2026-09-17T09:20:00Z |
| case_64 | INCOMPLETE | FINDING | support_platform | support_6334 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | FINDING | integration_service | data_flow_6846 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | FINDING | backup_service | backup_3933 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6846 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | REMEDIATION | backup_service | backup_3933 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | REMEDIATION | support_platform | support_6334 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | VERIFICATION | account_service | account_062 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | VERIFICATION | security_service | audit_record_1892 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | VERIFICATION | support_platform | support_6334 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6846 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_64 | INCOMPLETE | VERIFICATION | backup_service | backup_3933 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | FINDING | search_service | search_689 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | FINDING | analytics_platform | analytics_9246 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | REMEDIATION | search_service | search_689 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_9246 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | VERIFICATION | account_service | account_063 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | VERIFICATION | search_service | search_689 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_65 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_9246 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_66 | INCOMPLETE | FINDING | support_platform | support_4249 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_66 | INCOMPLETE | REMEDIATION | support_platform | support_4249 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_66 | INCOMPLETE | VERIFICATION | account_service | account_064 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_66 | INCOMPLETE | VERIFICATION | support_platform | support_4249 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_67 | INCOMPLETE | FINDING | account_service | account_9079 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_67 | INCOMPLETE | REMEDIATION | account_service | account_9079 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_67 | INCOMPLETE | VERIFICATION | account_service | account_9079 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | FINDING | search_service | search_2568 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | FINDING | integration_service | data_flow_2406 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2406 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | REMEDIATION | search_service | search_2568 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | VERIFICATION | account_service | account_066 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | VERIFICATION | search_service | search_2568 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_68 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2406 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_69 | INCOMPLETE | VERIFICATION | account_service | account_067 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_69 | INCOMPLETE | VERIFICATION | security_service | audit_record_9011 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_70 | INCOMPLETE | VERIFICATION | account_service | account_068 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_70 | INCOMPLETE | VERIFICATION | security_service | audit_record_1738 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | FINDING | search_service | search_684 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | FINDING | support_platform | support_1370 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | REMEDIATION | search_service | search_684 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | REMEDIATION | support_platform | support_1370 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | VERIFICATION | account_service | account_069 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | VERIFICATION | search_service | search_684 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_71 | INCOMPLETE | VERIFICATION | support_platform | support_1370 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_72 | INCOMPLETE | FINDING | export_service | export_4091 | evidence_93 | Verified | 2026-09-16T09:00:00Z |
| case_72 | INCOMPLETE | REMEDIATION | export_service | export_4091 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_72 | INCOMPLETE | VERIFICATION | account_service | account_070 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_72 | INCOMPLETE | VERIFICATION | export_service | export_4091 | None | N/A (Proposed action) | 2026-09-16T09:00:00Z |
| case_73 | INCOMPLETE | FINDING | account_service | account_6070 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_73 | INCOMPLETE | REMEDIATION | account_service | account_6070 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_73 | INCOMPLETE | VERIFICATION | account_service | account_6070 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_73 | INCOMPLETE | VERIFICATION | security_service | audit_record_5710 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_74 | INCOMPLETE | FINDING | integration_service | data_flow_4595 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_74 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4595 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_74 | INCOMPLETE | VERIFICATION | account_service | account_072 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_74 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4595 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_75 | INCOMPLETE | FINDING | backup_service | backup_8673 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_75 | INCOMPLETE | REMEDIATION | backup_service | backup_8673 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_75 | INCOMPLETE | VERIFICATION | account_service | account_073 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_75 | INCOMPLETE | VERIFICATION | backup_service | backup_8673 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_76 | INCOMPLETE | FINDING | support_platform | support_9746 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_76 | INCOMPLETE | REMEDIATION | support_platform | support_9746 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_76 | INCOMPLETE | VERIFICATION | account_service | account_074 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_76 | INCOMPLETE | VERIFICATION | support_platform | support_9746 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | FINDING | account_service | account_9334 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | FINDING | support_platform | support_008 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | FINDING | integration_service | data_flow_7773 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | FINDING | backup_service | backup_7303 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7773 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | REMEDIATION | backup_service | backup_7303 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | REMEDIATION | account_service | account_9334 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | REMEDIATION | support_platform | support_008 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | VERIFICATION | account_service | account_9334 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | VERIFICATION | security_service | audit_record_5425 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | VERIFICATION | support_platform | support_008 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7773 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_77 | INCOMPLETE | VERIFICATION | backup_service | backup_7303 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | FINDING | search_service | search_8295 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | FINDING | support_platform | support_9652 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | REMEDIATION | search_service | search_8295 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | REMEDIATION | support_platform | support_9652 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | VERIFICATION | account_service | account_076 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | VERIFICATION | search_service | search_8295 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_78 | INCOMPLETE | VERIFICATION | support_platform | support_9652 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_79 | INCOMPLETE | FINDING | account_service | account_5186 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_79 | INCOMPLETE | REMEDIATION | account_service | account_5186 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_79 | INCOMPLETE | VERIFICATION | account_service | account_5186 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_79 | INCOMPLETE | VERIFICATION | security_service | audit_record_1734 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_80 | INCOMPLETE | FINDING | account_service | account_4006 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_80 | INCOMPLETE | REMEDIATION | account_service | account_4006 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_80 | INCOMPLETE | VERIFICATION | account_service | account_4006 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_80 | INCOMPLETE | VERIFICATION | security_service | audit_record_5681 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | FINDING | account_service | account_9832 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | FINDING | support_platform | support_5953 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | FINDING | integration_service | data_flow_3255 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | FINDING | backup_service | backup_3332 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3255 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | REMEDIATION | backup_service | backup_3332 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | REMEDIATION | account_service | account_9832 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | REMEDIATION | support_platform | support_5953 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | VERIFICATION | account_service | account_9832 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | VERIFICATION | security_service | audit_record_9645 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | VERIFICATION | support_platform | support_5953 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3255 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_81 | INCOMPLETE | VERIFICATION | backup_service | backup_3332 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | FINDING | account_service | account_4156 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | FINDING | support_platform | support_9166 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | FINDING | integration_service | data_flow_9666 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | FINDING | backup_service | backup_317 | evidence_91 | Verified | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9666 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | REMEDIATION | backup_service | backup_317 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | REMEDIATION | account_service | account_4156 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | REMEDIATION | support_platform | support_9166 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | VERIFICATION | account_service | account_4156 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | VERIFICATION | security_service | audit_record_3747 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | VERIFICATION | support_platform | support_9166 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9666 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_82 | INCOMPLETE | VERIFICATION | backup_service | backup_317 | None | N/A (Proposed action) | 2026-09-11T08:00:00Z |
| case_83 | COMPLETE | VERIFICATION | account_service | account_2449 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_83 | COMPLETE | VERIFICATION | security_service | audit_record_2636 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_84 | COMPLETE | VERIFICATION | account_service | account_2387 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_84 | COMPLETE | VERIFICATION | security_service | audit_record_3787 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | FINDING | search_service | search_6302 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | FINDING | integration_service | data_flow_9927 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9927 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | REMEDIATION | search_service | search_6302 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | VERIFICATION | account_service | account_4911 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | VERIFICATION | search_service | search_6302 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | VERIFICATION | security_service | audit_record_8094 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_85 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9927 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_86 | INCOMPLETE | FINDING | account_service | account_8473 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_86 | INCOMPLETE | REMEDIATION | account_service | account_8473 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_86 | INCOMPLETE | VERIFICATION | account_service | account_8473 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_86 | INCOMPLETE | VERIFICATION | security_service | audit_record_5580 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_87 | INCOMPLETE | FINDING | backup_service | backup_4689 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_87 | INCOMPLETE | REMEDIATION | backup_service | backup_4689 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_87 | INCOMPLETE | VERIFICATION | account_service | account_8166 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_87 | INCOMPLETE | VERIFICATION | security_service | audit_record_4474 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_87 | INCOMPLETE | VERIFICATION | backup_service | backup_4689 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_88 | INCOMPLETE | FINDING | support_platform | support_2967 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_88 | INCOMPLETE | REMEDIATION | support_platform | support_2967 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_88 | INCOMPLETE | VERIFICATION | account_service | account_868 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_88 | INCOMPLETE | VERIFICATION | security_service | audit_record_3825 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_88 | INCOMPLETE | VERIFICATION | support_platform | support_2967 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | FINDING | search_service | search_1839 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | FINDING | analytics_platform | analytics_6499 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | REMEDIATION | search_service | search_1839 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6499 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | VERIFICATION | account_service | account_8764 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | VERIFICATION | search_service | search_1839 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | VERIFICATION | security_service | audit_record_2539 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_89 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6499 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | FINDING | search_service | search_5561 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | FINDING | analytics_platform | analytics_3181 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | FINDING | support_platform | support_7460 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | FINDING | integration_service | data_flow_2085 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2085 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | REMEDIATION | search_service | search_5561 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | REMEDIATION | support_platform | support_7460 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_3181 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | account_service | account_9673 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | search_service | search_5561 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | security_service | audit_record_9355 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | support_platform | support_7460 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_3181 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_90 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2085 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | FINDING | account_service | account_6075 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | FINDING | search_service | search_9156 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | FINDING | analytics_platform | analytics_8539 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | FINDING | support_platform | support_266 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | REMEDIATION | account_service | account_6075 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | REMEDIATION | search_service | search_9156 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | REMEDIATION | support_platform | support_266 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8539 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | VERIFICATION | account_service | account_6075 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | VERIFICATION | search_service | search_9156 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | VERIFICATION | security_service | audit_record_8304 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | VERIFICATION | support_platform | support_266 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_91 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8539 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_92 | INCOMPLETE | FINDING | integration_service | data_flow_7535 | evidence_08 | Verified | 2026-09-06T07:00:00Z |
| case_92 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7535 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_92 | INCOMPLETE | VERIFICATION | account_service | account_3609 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_92 | INCOMPLETE | VERIFICATION | security_service | audit_record_5625 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_92 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7535 | None | N/A (Proposed action) | 2026-09-06T07:00:00Z |
| case_93 | INCOMPLETE | FINDING | account_service | account_4421 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | FINDING | search_service | search_1310 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | FINDING | support_platform | support_1824 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | FINDING | integration_service | data_flow_047 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | REMEDIATION | integration_service | data_flow_047 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | REMEDIATION | account_service | account_4421 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | REMEDIATION | search_service | search_1310 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | REMEDIATION | support_platform | support_1824 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | VERIFICATION | account_service | account_4421 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | VERIFICATION | search_service | search_1310 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | VERIFICATION | support_platform | support_1824 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_93 | INCOMPLETE | VERIFICATION | integration_service | data_flow_047 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | FINDING | search_service | search_7631 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | FINDING | support_platform | support_7691 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | REMEDIATION | search_service | search_7631 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | REMEDIATION | support_platform | support_7691 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | VERIFICATION | account_service | account_092 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | VERIFICATION | search_service | search_7631 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_94 | INCOMPLETE | VERIFICATION | support_platform | support_7691 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | FINDING | search_service | search_7807 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | FINDING | analytics_platform | analytics_1316 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | FINDING | support_platform | support_5750 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | FINDING | support_platform | support_7311 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | REMEDIATION | search_service | search_7807 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | REMEDIATION | support_platform | support_5750 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | REMEDIATION | support_platform | support_7311 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1316 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | VERIFICATION | account_service | account_093 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | VERIFICATION | search_service | search_7807 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | VERIFICATION | support_platform | support_5750 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | VERIFICATION | support_platform | support_7311 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_95 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1316 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | FINDING | export_service | export_8827 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | FINDING | search_service | search_5672 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | REMEDIATION | export_service | export_8827 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | REMEDIATION | search_service | search_5672 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | VERIFICATION | account_service | account_094 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | VERIFICATION | export_service | export_8827 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_96 | INCOMPLETE | VERIFICATION | search_service | search_5672 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_97 | INCOMPLETE | VERIFICATION | account_service | account_095 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_97 | INCOMPLETE | VERIFICATION | security_service | audit_record_8778 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_98 | INCOMPLETE | FINDING | integration_service | data_flow_3165 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_98 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3165 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_98 | INCOMPLETE | VERIFICATION | account_service | account_096 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_98 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3165 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_99 | INCOMPLETE | FINDING | backup_service | backup_7804 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_99 | INCOMPLETE | REMEDIATION | backup_service | backup_7804 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_99 | INCOMPLETE | VERIFICATION | account_service | account_097 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_99 | INCOMPLETE | VERIFICATION | backup_service | backup_7804 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | FINDING | search_service | search_018 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | FINDING | support_platform | support_1630 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | REMEDIATION | search_service | search_018 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | REMEDIATION | support_platform | support_1630 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | VERIFICATION | account_service | account_098 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | VERIFICATION | search_service | search_018 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_100 | INCOMPLETE | VERIFICATION | support_platform | support_1630 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | FINDING | search_service | search_8561 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | FINDING | analytics_platform | analytics_6105 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | REMEDIATION | search_service | search_8561 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6105 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | VERIFICATION | account_service | account_099 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | VERIFICATION | search_service | search_8561 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_101 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6105 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | FINDING | search_service | search_4586 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | FINDING | support_platform | support_345 | evidence_89 | Verified | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | REMEDIATION | search_service | search_4586 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | REMEDIATION | support_platform | support_345 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | VERIFICATION | account_service | account_100 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | VERIFICATION | search_service | search_4586 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_102 | INCOMPLETE | VERIFICATION | support_platform | support_345 | None | N/A (Proposed action) | 2026-09-01T06:00:00Z |
| case_103 | INCOMPLETE | VERIFICATION | account_service | account_101 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_103 | INCOMPLETE | VERIFICATION | security_service | audit_record_9522 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | FINDING | search_service | search_8379 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | FINDING | analytics_platform | analytics_4882 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | FINDING | support_platform | support_4267 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | FINDING | integration_service | data_flow_5127 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5127 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | REMEDIATION | search_service | search_8379 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | REMEDIATION | support_platform | support_4267 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_4882 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | account_service | account_102 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | search_service | search_8379 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | security_service | audit_record_6230 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | support_platform | support_4267 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_4882 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_104 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5127 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | FINDING | account_service | account_6345 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | FINDING | search_service | search_4618 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | REMEDIATION | account_service | account_6345 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | REMEDIATION | search_service | search_4618 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | VERIFICATION | account_service | account_6345 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | VERIFICATION | search_service | search_4618 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_105 | INCOMPLETE | VERIFICATION | security_service | audit_record_4520 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_106 | INCOMPLETE | FINDING | search_service | search_7223 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_106 | INCOMPLETE | REMEDIATION | search_service | search_7223 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_106 | INCOMPLETE | VERIFICATION | account_service | account_104 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_106 | INCOMPLETE | VERIFICATION | search_service | search_7223 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_106 | INCOMPLETE | VERIFICATION | security_service | audit_record_8723 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_107 | INCOMPLETE | VERIFICATION | account_service | account_105 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_107 | INCOMPLETE | VERIFICATION | security_service | audit_record_7572 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_108 | INCOMPLETE | VERIFICATION | account_service | account_106 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_108 | INCOMPLETE | VERIFICATION | security_service | audit_record_1469 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | FINDING | search_service | search_2016 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | FINDING | integration_service | data_flow_9949 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9949 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | REMEDIATION | search_service | search_2016 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | VERIFICATION | account_service | account_107 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | VERIFICATION | search_service | search_2016 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | VERIFICATION | security_service | audit_record_2718 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_109 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9949 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | FINDING | search_service | search_3993 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | FINDING | integration_service | data_flow_8857 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8857 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | REMEDIATION | search_service | search_3993 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | VERIFICATION | account_service | account_108 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | VERIFICATION | search_service | search_3993 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | VERIFICATION | security_service | audit_record_9268 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_110 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8857 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_111 | INCOMPLETE | VERIFICATION | account_service | account_109 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_111 | INCOMPLETE | VERIFICATION | security_service | audit_record_8933 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | FINDING | integration_service | data_flow_3444 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | FINDING | backup_service | backup_4863 | evidence_10 | Verified | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3444 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | REMEDIATION | backup_service | backup_4863 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | VERIFICATION | account_service | account_110 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | VERIFICATION | security_service | audit_record_4082 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | VERIFICATION | support_platform | support_2859 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3444 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_112 | INCOMPLETE | VERIFICATION | backup_service | backup_4863 | None | N/A (Proposed action) | 2026-08-27T12:00:00Z |
| case_113 | INCOMPLETE | FINDING | account_service | account_6697 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_113 | INCOMPLETE | REMEDIATION | account_service | account_6697 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_113 | INCOMPLETE | VERIFICATION | account_service | account_6697 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_113 | INCOMPLETE | VERIFICATION | security_service | audit_record_1127 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | FINDING | search_service | search_5696 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | FINDING | support_platform | support_3786 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | REMEDIATION | search_service | search_5696 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | REMEDIATION | support_platform | support_3786 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | VERIFICATION | account_service | account_112 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | VERIFICATION | search_service | search_5696 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_114 | INCOMPLETE | VERIFICATION | support_platform | support_3786 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | FINDING | account_service | account_1785 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | FINDING | search_service | search_4417 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | REMEDIATION | account_service | account_1785 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | REMEDIATION | search_service | search_4417 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | VERIFICATION | account_service | account_1785 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_115 | INCOMPLETE | VERIFICATION | search_service | search_4417 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | FINDING | search_service | search_696 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | FINDING | integration_service | data_flow_6699 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6699 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | REMEDIATION | search_service | search_696 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | VERIFICATION | account_service | account_114 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | VERIFICATION | search_service | search_696 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_116 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6699 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_117 | INCOMPLETE | FINDING | account_service | account_1220 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_117 | INCOMPLETE | REMEDIATION | account_service | account_1220 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_117 | INCOMPLETE | VERIFICATION | account_service | account_1220 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_117 | INCOMPLETE | VERIFICATION | security_service | audit_record_1598 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | FINDING | search_service | search_9556 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | FINDING | support_platform | support_036 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | REMEDIATION | search_service | search_9556 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | REMEDIATION | support_platform | support_036 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | VERIFICATION | account_service | account_116 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | VERIFICATION | search_service | search_9556 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_118 | INCOMPLETE | VERIFICATION | support_platform | support_036 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | FINDING | search_service | search_5259 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | FINDING | support_platform | support_9309 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | REMEDIATION | search_service | search_5259 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | REMEDIATION | support_platform | support_9309 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | VERIFICATION | account_service | account_117 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | VERIFICATION | search_service | search_5259 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_119 | INCOMPLETE | VERIFICATION | support_platform | support_9309 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | FINDING | export_service | export_4289 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | FINDING | search_service | search_943 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | REMEDIATION | export_service | export_4289 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | REMEDIATION | search_service | search_943 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | VERIFICATION | account_service | account_118 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | VERIFICATION | export_service | export_4289 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_120 | INCOMPLETE | VERIFICATION | search_service | search_943 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_121 | INCOMPLETE | FINDING | account_service | account_081 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_121 | INCOMPLETE | REMEDIATION | account_service | account_081 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_121 | INCOMPLETE | VERIFICATION | account_service | account_081 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_121 | INCOMPLETE | VERIFICATION | security_service | audit_record_2103 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | FINDING | search_service | search_1752 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | FINDING | integration_service | data_flow_3199 | evidence_88 | Verified | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3199 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | REMEDIATION | search_service | search_1752 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | VERIFICATION | account_service | account_120 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | VERIFICATION | search_service | search_1752 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_122 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3199 | None | N/A (Proposed action) | 2026-08-22T11:00:00Z |
| case_123 | INCOMPLETE | FINDING | backup_service | backup_8742 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_123 | INCOMPLETE | REMEDIATION | backup_service | backup_8742 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_123 | INCOMPLETE | VERIFICATION | account_service | account_121 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_123 | INCOMPLETE | VERIFICATION | backup_service | backup_8742 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_124 | INCOMPLETE | FINDING | support_platform | support_9126 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_124 | INCOMPLETE | REMEDIATION | support_platform | support_9126 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_124 | INCOMPLETE | VERIFICATION | account_service | account_122 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_124 | INCOMPLETE | VERIFICATION | support_platform | support_9126 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | FINDING | search_service | search_9752 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | FINDING | analytics_platform | analytics_1103 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | REMEDIATION | search_service | search_9752 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1103 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | VERIFICATION | account_service | account_123 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | VERIFICATION | search_service | search_9752 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_125 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1103 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_126 | INCOMPLETE | VERIFICATION | account_service | account_124 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_126 | INCOMPLETE | VERIFICATION | security_service | audit_record_6884 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_127 | INCOMPLETE | VERIFICATION | account_service | account_125 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_127 | INCOMPLETE | VERIFICATION | security_service | audit_record_9649 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_128 | INCOMPLETE | FINDING | integration_service | data_flow_5550 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_128 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5550 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_128 | INCOMPLETE | VERIFICATION | account_service | account_126 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_128 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5550 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | FINDING | account_service | account_6673 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | FINDING | search_service | search_5148 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | REMEDIATION | account_service | account_6673 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | REMEDIATION | search_service | search_5148 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | VERIFICATION | account_service | account_6673 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_129 | INCOMPLETE | VERIFICATION | search_service | search_5148 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | FINDING | search_service | search_2364 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | FINDING | support_platform | support_187 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | REMEDIATION | search_service | search_2364 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | REMEDIATION | support_platform | support_187 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | VERIFICATION | account_service | account_128 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | VERIFICATION | search_service | search_2364 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_130 | INCOMPLETE | VERIFICATION | support_platform | support_187 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | FINDING | search_service | search_538 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | FINDING | analytics_platform | analytics_514 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | FINDING | support_platform | support_2315 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | FINDING | support_platform | support_7208 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | REMEDIATION | search_service | search_538 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | REMEDIATION | support_platform | support_2315 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | REMEDIATION | support_platform | support_7208 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_514 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | VERIFICATION | account_service | account_129 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | VERIFICATION | search_service | search_538 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | VERIFICATION | support_platform | support_2315 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | VERIFICATION | support_platform | support_7208 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_131 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_514 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | FINDING | export_service | export_9157 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | FINDING | search_service | search_3112 | evidence_87 | Verified | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | REMEDIATION | export_service | export_9157 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | REMEDIATION | search_service | search_3112 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | VERIFICATION | account_service | account_130 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | VERIFICATION | export_service | export_9157 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_132 | INCOMPLETE | VERIFICATION | search_service | search_3112 | None | N/A (Proposed action) | 2026-08-17T10:00:00Z |
| case_133 | INCOMPLETE | VERIFICATION | account_service | account_131 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_134 | INCOMPLETE | VERIFICATION | account_service | account_132 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_135 | INCOMPLETE | VERIFICATION | account_service | account_133 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_136 | INCOMPLETE | VERIFICATION | account_service | account_134 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_137 | INCOMPLETE | VERIFICATION | account_service | account_135 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_138 | INCOMPLETE | VERIFICATION | account_service | account_136 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_139 | INCOMPLETE | VERIFICATION | account_service | account_137 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_140 | INCOMPLETE | VERIFICATION | account_service | account_138 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_141 | INCOMPLETE | VERIFICATION | account_service | account_139 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_142 | INCOMPLETE | VERIFICATION | account_service | account_140 | None | N/A (Proposed action) | 2026-08-12T09:00:00Z |
| case_143 | INCOMPLETE | FINDING | search_service | search_6137 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | FINDING | support_platform | support_6560 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | REMEDIATION | search_service | search_6137 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | REMEDIATION | support_platform | support_6560 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | VERIFICATION | account_service | account_141 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | VERIFICATION | search_service | search_6137 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_143 | INCOMPLETE | VERIFICATION | support_platform | support_6560 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_144 | INCOMPLETE | FINDING | export_service | export_7992 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_144 | INCOMPLETE | REMEDIATION | export_service | export_7992 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_144 | INCOMPLETE | VERIFICATION | account_service | account_142 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_144 | INCOMPLETE | VERIFICATION | export_service | export_7992 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | FINDING | search_service | search_1725 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | FINDING | integration_service | data_flow_7253 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7253 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | REMEDIATION | search_service | search_1725 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | VERIFICATION | account_service | account_143 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | VERIFICATION | search_service | search_1725 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_145 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7253 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | FINDING | search_service | search_2262 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | FINDING | integration_service | data_flow_4889 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4889 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | REMEDIATION | search_service | search_2262 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | VERIFICATION | account_service | account_144 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | VERIFICATION | search_service | search_2262 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_146 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4889 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_147 | INCOMPLETE | FINDING | backup_service | backup_4244 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_147 | INCOMPLETE | REMEDIATION | backup_service | backup_4244 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_147 | INCOMPLETE | VERIFICATION | account_service | account_145 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_147 | INCOMPLETE | VERIFICATION | backup_service | backup_4244 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | FINDING | search_service | search_7239 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | FINDING | support_platform | support_5716 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | REMEDIATION | search_service | search_7239 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | REMEDIATION | support_platform | support_5716 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | VERIFICATION | account_service | account_146 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | VERIFICATION | search_service | search_7239 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_148 | INCOMPLETE | VERIFICATION | support_platform | support_5716 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | FINDING | search_service | search_7672 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | FINDING | analytics_platform | analytics_5886 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | REMEDIATION | search_service | search_7672 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5886 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | VERIFICATION | account_service | account_147 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | VERIFICATION | search_service | search_7672 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_149 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5886 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_150 | INCOMPLETE | VERIFICATION | account_service | account_148 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_150 | INCOMPLETE | VERIFICATION | security_service | audit_record_1584 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | FINDING | support_platform | support_5400 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | FINDING | integration_service | data_flow_2437 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | FINDING | backup_service | backup_9557 | evidence_86 | Verified | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2437 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | REMEDIATION | backup_service | backup_9557 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | REMEDIATION | support_platform | support_5400 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | VERIFICATION | account_service | account_149 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | VERIFICATION | security_service | audit_record_8905 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | VERIFICATION | support_platform | support_5400 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2437 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_151 | INCOMPLETE | VERIFICATION | backup_service | backup_9557 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_152 | INCOMPLETE | VERIFICATION | account_service | account_150 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_152 | INCOMPLETE | VERIFICATION | security_service | audit_record_3579 | None | N/A (Proposed action) | 2026-08-07T08:00:00Z |
| case_153 | INCOMPLETE | FINDING | account_service | account_8023 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | FINDING | search_service | search_9831 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | REMEDIATION | account_service | account_8023 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | REMEDIATION | search_service | search_9831 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | VERIFICATION | account_service | account_8023 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | VERIFICATION | search_service | search_9831 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_153 | INCOMPLETE | VERIFICATION | security_service | audit_record_5652 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_154 | INCOMPLETE | FINDING | search_service | search_1446 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_154 | INCOMPLETE | REMEDIATION | search_service | search_1446 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_154 | INCOMPLETE | VERIFICATION | account_service | account_152 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_154 | INCOMPLETE | VERIFICATION | search_service | search_1446 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_154 | INCOMPLETE | VERIFICATION | security_service | audit_record_2580 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | FINDING | integration_service | data_flow_4305 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | FINDING | backup_service | backup_161 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4305 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | REMEDIATION | backup_service | backup_161 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | VERIFICATION | account_service | account_153 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | VERIFICATION | security_service | audit_record_4199 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | VERIFICATION | support_platform | support_7867 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4305 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_155 | INCOMPLETE | VERIFICATION | backup_service | backup_161 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | FINDING | export_service | export_5897 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | FINDING | search_service | search_4870 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | REMEDIATION | export_service | export_5897 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | REMEDIATION | search_service | search_4870 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | VERIFICATION | account_service | account_154 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | VERIFICATION | export_service | export_5897 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | VERIFICATION | search_service | search_4870 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_156 | INCOMPLETE | VERIFICATION | security_service | audit_record_5890 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_157 | INCOMPLETE | VERIFICATION | account_service | account_155 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_157 | INCOMPLETE | VERIFICATION | security_service | audit_record_8821 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | FINDING | search_service | search_9834 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | FINDING | integration_service | data_flow_7704 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7704 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | REMEDIATION | search_service | search_9834 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | VERIFICATION | account_service | account_156 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | VERIFICATION | search_service | search_9834 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | VERIFICATION | security_service | audit_record_9665 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_158 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7704 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_159 | INCOMPLETE | FINDING | backup_service | backup_1214 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_159 | INCOMPLETE | REMEDIATION | backup_service | backup_1214 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_159 | INCOMPLETE | VERIFICATION | account_service | account_157 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_159 | INCOMPLETE | VERIFICATION | security_service | audit_record_8742 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_159 | INCOMPLETE | VERIFICATION | backup_service | backup_1214 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_160 | INCOMPLETE | FINDING | support_platform | support_4148 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_160 | INCOMPLETE | REMEDIATION | support_platform | support_4148 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_160 | INCOMPLETE | VERIFICATION | account_service | account_158 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_160 | INCOMPLETE | VERIFICATION | security_service | audit_record_9882 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_160 | INCOMPLETE | VERIFICATION | support_platform | support_4148 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_161 | INCOMPLETE | FINDING | analytics_platform | analytics_2008 | evidence_15 | Verified | 2026-08-02T07:00:00Z |
| case_161 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_2008 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_161 | INCOMPLETE | VERIFICATION | account_service | account_159 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_161 | INCOMPLETE | VERIFICATION | security_service | audit_record_8002 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_161 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_2008 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_162 | INCOMPLETE | VERIFICATION | account_service | account_160 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_162 | INCOMPLETE | VERIFICATION | security_service | audit_record_6362 | None | N/A (Proposed action) | 2026-08-02T07:00:00Z |
| case_163 | INCOMPLETE | FINDING | account_service | account_4289 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_163 | INCOMPLETE | FINDING | search_service | search_4509 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_163 | INCOMPLETE | REMEDIATION | account_service | account_4289 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_163 | INCOMPLETE | REMEDIATION | search_service | search_4509 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_163 | INCOMPLETE | VERIFICATION | account_service | account_4289 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_163 | INCOMPLETE | VERIFICATION | search_service | search_4509 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_164 | INCOMPLETE | FINDING | account_service | account_9549 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_164 | INCOMPLETE | REMEDIATION | account_service | account_9549 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_164 | INCOMPLETE | VERIFICATION | account_service | account_9549 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_164 | INCOMPLETE | VERIFICATION | security_service | audit_record_6780 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | FINDING | account_service | account_3064 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | FINDING | search_service | search_8678 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | FINDING | analytics_platform | analytics_2713 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | FINDING | support_platform | support_3586 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | REMEDIATION | account_service | account_3064 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | REMEDIATION | search_service | search_8678 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | REMEDIATION | support_platform | support_3586 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_2713 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | VERIFICATION | account_service | account_3064 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | VERIFICATION | search_service | search_8678 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | VERIFICATION | support_platform | support_3586 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_165 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_2713 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | FINDING | search_service | search_5261 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | FINDING | support_platform | support_3155 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | REMEDIATION | search_service | search_5261 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | REMEDIATION | support_platform | support_3155 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | VERIFICATION | account_service | account_164 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | VERIFICATION | search_service | search_5261 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_166 | INCOMPLETE | VERIFICATION | support_platform | support_3155 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_167 | INCOMPLETE | FINDING | account_service | account_5284 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_167 | INCOMPLETE | REMEDIATION | account_service | account_5284 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_167 | INCOMPLETE | VERIFICATION | account_service | account_5284 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_167 | INCOMPLETE | VERIFICATION | security_service | audit_record_3088 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_168 | INCOMPLETE | FINDING | export_service | export_4102 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_168 | INCOMPLETE | REMEDIATION | export_service | export_4102 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_168 | INCOMPLETE | VERIFICATION | account_service | account_166 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_168 | INCOMPLETE | VERIFICATION | export_service | export_4102 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | FINDING | search_service | search_2126 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | FINDING | integration_service | data_flow_7004 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7004 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | REMEDIATION | search_service | search_2126 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | VERIFICATION | account_service | account_167 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | VERIFICATION | search_service | search_2126 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_169 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7004 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_170 | INCOMPLETE | FINDING | account_service | account_665 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_170 | INCOMPLETE | REMEDIATION | account_service | account_665 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_170 | INCOMPLETE | VERIFICATION | account_service | account_665 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_170 | INCOMPLETE | VERIFICATION | security_service | audit_record_4443 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_171 | INCOMPLETE | FINDING | backup_service | backup_5520 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_171 | INCOMPLETE | REMEDIATION | backup_service | backup_5520 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_171 | INCOMPLETE | VERIFICATION | account_service | account_169 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_171 | INCOMPLETE | VERIFICATION | backup_service | backup_5520 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | FINDING | search_service | search_7102 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | FINDING | support_platform | support_2322 | evidence_85 | Verified | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | REMEDIATION | search_service | search_7102 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | REMEDIATION | support_platform | support_2322 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | VERIFICATION | account_service | account_170 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | VERIFICATION | search_service | search_7102 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_172 | INCOMPLETE | VERIFICATION | support_platform | support_2322 | None | N/A (Proposed action) | 2026-07-28T06:00:00Z |
| case_173 | INCOMPLETE | FINDING | search_service | search_9523 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | FINDING | analytics_platform | analytics_6000 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | REMEDIATION | search_service | search_9523 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6000 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | VERIFICATION | account_service | account_171 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | VERIFICATION | search_service | search_9523 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_173 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6000 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | FINDING | search_service | search_2138 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | FINDING | support_platform | support_1887 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | REMEDIATION | search_service | search_2138 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | REMEDIATION | support_platform | support_1887 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | VERIFICATION | account_service | account_172 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | VERIFICATION | search_service | search_2138 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_174 | INCOMPLETE | VERIFICATION | support_platform | support_1887 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | FINDING | support_platform | support_8164 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | FINDING | integration_service | data_flow_4319 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | FINDING | backup_service | backup_549 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4319 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | REMEDIATION | backup_service | backup_549 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | REMEDIATION | support_platform | support_8164 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | VERIFICATION | account_service | account_173 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | VERIFICATION | security_service | audit_record_7166 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | VERIFICATION | support_platform | support_8164 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4319 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_175 | INCOMPLETE | VERIFICATION | backup_service | backup_549 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | FINDING | search_service | search_8860 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | FINDING | integration_service | data_flow_296 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | REMEDIATION | integration_service | data_flow_296 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | REMEDIATION | search_service | search_8860 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | VERIFICATION | account_service | account_174 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | VERIFICATION | search_service | search_8860 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_176 | INCOMPLETE | VERIFICATION | integration_service | data_flow_296 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | FINDING | account_service | account_8423 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | FINDING | search_service | search_3038 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | REMEDIATION | account_service | account_8423 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | REMEDIATION | search_service | search_3038 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | VERIFICATION | account_service | account_8423 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_177 | INCOMPLETE | VERIFICATION | search_service | search_3038 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_178 | INCOMPLETE | VERIFICATION | account_service | account_176 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_178 | INCOMPLETE | VERIFICATION | security_service | audit_record_8521 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_179 | INCOMPLETE | FINDING | support_platform | support_2283 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_179 | INCOMPLETE | REMEDIATION | support_platform | support_2283 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_179 | INCOMPLETE | VERIFICATION | account_service | account_177 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_179 | INCOMPLETE | VERIFICATION | support_platform | support_2283 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | FINDING | export_service | export_7156 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | FINDING | search_service | search_5570 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | FINDING | analytics_platform | analytics_1391 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | FINDING | support_platform | support_2609 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | REMEDIATION | export_service | export_7156 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | REMEDIATION | search_service | search_5570 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | REMEDIATION | support_platform | support_2609 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1391 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | VERIFICATION | account_service | account_178 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | VERIFICATION | export_service | export_7156 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | VERIFICATION | search_service | search_5570 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | VERIFICATION | support_platform | support_2609 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_180 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1391 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | FINDING | search_service | search_4894 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | FINDING | integration_service | data_flow_8346 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8346 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | REMEDIATION | search_service | search_4894 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | VERIFICATION | account_service | account_179 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | VERIFICATION | search_service | search_4894 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_181 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8346 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | FINDING | search_service | search_2073 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | FINDING | analytics_platform | analytics_1522 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | FINDING | support_platform | support_4806 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | FINDING | integration_service | data_flow_7450 | evidence_84 | Verified | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7450 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | REMEDIATION | search_service | search_2073 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | REMEDIATION | support_platform | support_4806 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1522 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | VERIFICATION | account_service | account_180 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | VERIFICATION | search_service | search_2073 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | VERIFICATION | support_platform | support_4806 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1522 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_182 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7450 | None | N/A (Proposed action) | 2026-07-23T12:00:00Z |
| case_183 | INCOMPLETE | VERIFICATION | account_service | account_181 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_183 | INCOMPLETE | VERIFICATION | security_service | audit_record_3262 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | FINDING | search_service | search_8680 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | FINDING | support_platform | support_1892 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | REMEDIATION | search_service | search_8680 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | REMEDIATION | support_platform | support_1892 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | VERIFICATION | account_service | account_182 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | VERIFICATION | search_service | search_8680 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_184 | INCOMPLETE | VERIFICATION | support_platform | support_1892 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | FINDING | search_service | search_8463 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | FINDING | analytics_platform | analytics_1950 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | REMEDIATION | search_service | search_8463 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1950 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | VERIFICATION | account_service | account_183 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | VERIFICATION | search_service | search_8463 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_185 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1950 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | FINDING | search_service | search_4062 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | FINDING | integration_service | data_flow_7428 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7428 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | REMEDIATION | search_service | search_4062 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | VERIFICATION | account_service | account_184 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | VERIFICATION | search_service | search_4062 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_186 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7428 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | FINDING | account_service | account_5375 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | FINDING | search_service | search_9921 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | REMEDIATION | account_service | account_5375 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | REMEDIATION | search_service | search_9921 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | VERIFICATION | account_service | account_5375 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_187 | INCOMPLETE | VERIFICATION | search_service | search_9921 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | FINDING | search_service | search_3223 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | FINDING | integration_service | data_flow_707 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | REMEDIATION | integration_service | data_flow_707 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | REMEDIATION | search_service | search_3223 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | VERIFICATION | account_service | account_186 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | VERIFICATION | search_service | search_3223 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_188 | INCOMPLETE | VERIFICATION | integration_service | data_flow_707 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | FINDING | account_service | account_5848 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | FINDING | search_service | search_4334 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | FINDING | analytics_platform | analytics_1120 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | FINDING | support_platform | support_8447 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | REMEDIATION | account_service | account_5848 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | REMEDIATION | search_service | search_4334 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | REMEDIATION | support_platform | support_8447 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1120 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | VERIFICATION | account_service | account_5848 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | VERIFICATION | search_service | search_4334 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | VERIFICATION | support_platform | support_8447 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_189 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1120 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_190 | INCOMPLETE | VERIFICATION | account_service | account_188 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_190 | INCOMPLETE | VERIFICATION | security_service | audit_record_4417 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | FINDING | support_platform | support_5049 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | FINDING | integration_service | data_flow_1611 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | FINDING | backup_service | backup_3010 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1611 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | REMEDIATION | backup_service | backup_3010 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | REMEDIATION | support_platform | support_5049 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | VERIFICATION | account_service | account_189 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | VERIFICATION | security_service | audit_record_7493 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | VERIFICATION | support_platform | support_5049 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1611 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_191 | INCOMPLETE | VERIFICATION | backup_service | backup_3010 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | FINDING | export_service | export_2705 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | FINDING | search_service | search_6680 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | FINDING | analytics_platform | analytics_4472 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | FINDING | support_platform | support_5493 | evidence_83 | Verified | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | REMEDIATION | export_service | export_2705 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | REMEDIATION | search_service | search_6680 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | REMEDIATION | support_platform | support_5493 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_4472 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | VERIFICATION | account_service | account_190 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | VERIFICATION | export_service | export_2705 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | VERIFICATION | search_service | search_6680 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | VERIFICATION | support_platform | support_5493 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_192 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_4472 | None | N/A (Proposed action) | 2026-07-18T11:00:00Z |
| case_193 | INCOMPLETE | FINDING | account_service | account_1065 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_193 | INCOMPLETE | REMEDIATION | account_service | account_1065 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_193 | INCOMPLETE | VERIFICATION | account_service | account_1065 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_193 | INCOMPLETE | VERIFICATION | security_service | audit_record_1839 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | FINDING | search_service | search_8302 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | FINDING | integration_service | data_flow_3195 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3195 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | REMEDIATION | search_service | search_8302 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | VERIFICATION | account_service | account_192 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | VERIFICATION | search_service | search_8302 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_194 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3195 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_195 | INCOMPLETE | FINDING | account_service | account_4320 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_195 | INCOMPLETE | REMEDIATION | account_service | account_4320 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_195 | INCOMPLETE | VERIFICATION | account_service | account_4320 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_195 | INCOMPLETE | VERIFICATION | security_service | audit_record_1524 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_196 | INCOMPLETE | FINDING | account_service | account_5599 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_196 | INCOMPLETE | REMEDIATION | account_service | account_5599 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_196 | INCOMPLETE | VERIFICATION | account_service | account_5599 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_196 | INCOMPLETE | VERIFICATION | security_service | audit_record_6389 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | FINDING | search_service | search_6762 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | FINDING | analytics_platform | analytics_6093 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | REMEDIATION | search_service | search_6762 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6093 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | VERIFICATION | account_service | account_195 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | VERIFICATION | search_service | search_6762 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_197 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6093 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | FINDING | search_service | search_1414 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | FINDING | support_platform | support_6131 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | REMEDIATION | search_service | search_1414 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | REMEDIATION | support_platform | support_6131 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | VERIFICATION | account_service | account_196 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | VERIFICATION | search_service | search_1414 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_198 | INCOMPLETE | VERIFICATION | support_platform | support_6131 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | FINDING | account_service | account_9917 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | FINDING | search_service | search_9161 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | REMEDIATION | account_service | account_9917 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | REMEDIATION | search_service | search_9161 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | VERIFICATION | account_service | account_9917 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_199 | INCOMPLETE | VERIFICATION | search_service | search_9161 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | FINDING | search_service | search_7472 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | FINDING | integration_service | data_flow_2310 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2310 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | REMEDIATION | search_service | search_7472 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | VERIFICATION | account_service | account_198 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | VERIFICATION | search_service | search_7472 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_200 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2310 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | FINDING | account_service | account_2933 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | FINDING | search_service | search_5135 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | FINDING | support_platform | support_2863 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | FINDING | integration_service | data_flow_5688 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5688 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | REMEDIATION | account_service | account_2933 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | REMEDIATION | search_service | search_5135 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | REMEDIATION | support_platform | support_2863 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | VERIFICATION | account_service | account_2933 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | VERIFICATION | search_service | search_5135 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | VERIFICATION | support_platform | support_2863 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_201 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5688 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_202 | INCOMPLETE | FINDING | account_service | account_5547 | evidence_82 | Verified | 2026-07-13T10:00:00Z |
| case_202 | INCOMPLETE | REMEDIATION | account_service | account_5547 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_202 | INCOMPLETE | VERIFICATION | account_service | account_5547 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_202 | INCOMPLETE | VERIFICATION | security_service | audit_record_5401 | None | N/A (Proposed action) | 2026-07-13T10:00:00Z |
| case_203 | INCOMPLETE | FINDING | search_service | search_7542 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | FINDING | support_platform | support_8903 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | REMEDIATION | search_service | search_7542 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | REMEDIATION | support_platform | support_8903 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | VERIFICATION | account_service | account_201 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | VERIFICATION | search_service | search_7542 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | VERIFICATION | security_service | audit_record_1159 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_203 | INCOMPLETE | VERIFICATION | support_platform | support_8903 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | FINDING | integration_service | data_flow_5877 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | FINDING | backup_service | backup_9519 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5877 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | REMEDIATION | backup_service | backup_9519 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | VERIFICATION | account_service | account_202 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | VERIFICATION | security_service | audit_record_2736 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | VERIFICATION | support_platform | support_9505 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5877 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_204 | INCOMPLETE | VERIFICATION | backup_service | backup_9519 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | FINDING | search_service | search_540 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | FINDING | integration_service | data_flow_3530 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3530 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | REMEDIATION | search_service | search_540 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | VERIFICATION | account_service | account_203 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | VERIFICATION | search_service | search_540 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | VERIFICATION | security_service | audit_record_5023 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_205 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3530 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_206 | INCOMPLETE | VERIFICATION | account_service | account_204 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_206 | INCOMPLETE | VERIFICATION | security_service | audit_record_9878 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_207 | INCOMPLETE | FINDING | backup_service | backup_6407 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_207 | INCOMPLETE | REMEDIATION | backup_service | backup_6407 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_207 | INCOMPLETE | VERIFICATION | account_service | account_205 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_207 | INCOMPLETE | VERIFICATION | security_service | audit_record_3578 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_207 | INCOMPLETE | VERIFICATION | backup_service | backup_6407 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | FINDING | search_service | search_1118 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | FINDING | support_platform | support_2134 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | REMEDIATION | search_service | search_1118 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | REMEDIATION | support_platform | support_2134 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | VERIFICATION | account_service | account_206 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | VERIFICATION | search_service | search_1118 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | VERIFICATION | security_service | audit_record_2697 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_208 | INCOMPLETE | VERIFICATION | support_platform | support_2134 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | FINDING | search_service | search_7288 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | FINDING | analytics_platform | analytics_3156 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | FINDING | support_platform | support_8999 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | FINDING | integration_service | data_flow_5196 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5196 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | REMEDIATION | search_service | search_7288 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | REMEDIATION | support_platform | support_8999 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_3156 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | account_service | account_207 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | search_service | search_7288 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | security_service | audit_record_8189 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | support_platform | support_8999 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_3156 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_209 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5196 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | FINDING | search_service | search_045 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | FINDING | support_platform | support_4491 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | REMEDIATION | search_service | search_045 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | REMEDIATION | support_platform | support_4491 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | VERIFICATION | account_service | account_208 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | VERIFICATION | search_service | search_045 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | VERIFICATION | security_service | audit_record_6796 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_210 | INCOMPLETE | VERIFICATION | support_platform | support_4491 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | FINDING | account_service | account_4348 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | FINDING | search_service | search_9955 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | REMEDIATION | account_service | account_4348 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | REMEDIATION | search_service | search_9955 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | VERIFICATION | account_service | account_4348 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | VERIFICATION | search_service | search_9955 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_211 | INCOMPLETE | VERIFICATION | security_service | audit_record_7804 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | FINDING | search_service | search_2274 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | FINDING | integration_service | data_flow_8676 | evidence_20 | Verified | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8676 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | REMEDIATION | search_service | search_2274 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | VERIFICATION | account_service | account_210 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | VERIFICATION | search_service | search_2274 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | VERIFICATION | security_service | audit_record_3261 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_212 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8676 | None | N/A (Proposed action) | 2026-07-08T09:00:00Z |
| case_213 | INCOMPLETE | FINDING | support_platform | support_1360 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | FINDING | integration_service | data_flow_5279 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | FINDING | backup_service | backup_5626 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5279 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | REMEDIATION | backup_service | backup_5626 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | REMEDIATION | support_platform | support_1360 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | VERIFICATION | account_service | account_211 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | VERIFICATION | security_service | audit_record_4413 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | VERIFICATION | support_platform | support_1360 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5279 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_213 | INCOMPLETE | VERIFICATION | backup_service | backup_5626 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | FINDING | search_service | search_7351 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | FINDING | support_platform | support_1146 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | REMEDIATION | search_service | search_7351 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | REMEDIATION | support_platform | support_1146 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | VERIFICATION | account_service | account_212 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | VERIFICATION | search_service | search_7351 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_214 | INCOMPLETE | VERIFICATION | support_platform | support_1146 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_215 | INCOMPLETE | VERIFICATION | account_service | account_213 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_215 | INCOMPLETE | VERIFICATION | security_service | audit_record_1718 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | FINDING | export_service | export_5351 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | FINDING | search_service | search_5216 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | FINDING | analytics_platform | analytics_4527 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | FINDING | support_platform | support_8453 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | REMEDIATION | export_service | export_5351 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | REMEDIATION | search_service | search_5216 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | REMEDIATION | support_platform | support_8453 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_4527 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | VERIFICATION | account_service | account_214 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | VERIFICATION | export_service | export_5351 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | VERIFICATION | search_service | search_5216 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | VERIFICATION | support_platform | support_8453 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_216 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_4527 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | FINDING | search_service | search_3120 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | FINDING | integration_service | data_flow_1791 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1791 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | REMEDIATION | search_service | search_3120 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | VERIFICATION | account_service | account_215 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | VERIFICATION | search_service | search_3120 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_217 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1791 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_218 | INCOMPLETE | VERIFICATION | account_service | account_216 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_218 | INCOMPLETE | VERIFICATION | security_service | audit_record_8792 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_219 | INCOMPLETE | VERIFICATION | account_service | account_217 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_219 | INCOMPLETE | VERIFICATION | security_service | audit_record_3382 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | FINDING | search_service | search_941 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | FINDING | support_platform | support_4529 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | REMEDIATION | search_service | search_941 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | REMEDIATION | support_platform | support_4529 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | VERIFICATION | account_service | account_218 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | VERIFICATION | search_service | search_941 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_220 | INCOMPLETE | VERIFICATION | support_platform | support_4529 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_221 | INCOMPLETE | VERIFICATION | account_service | account_219 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_221 | INCOMPLETE | VERIFICATION | security_service | audit_record_3880 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | FINDING | search_service | search_6405 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | FINDING | support_platform | support_111 | evidence_81 | Verified | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | REMEDIATION | search_service | search_6405 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | REMEDIATION | support_platform | support_111 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | VERIFICATION | account_service | account_220 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | VERIFICATION | search_service | search_6405 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_222 | INCOMPLETE | VERIFICATION | support_platform | support_111 | None | N/A (Proposed action) | 2026-07-03T08:00:00Z |
| case_223 | INCOMPLETE | FINDING | account_service | account_5479 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_223 | INCOMPLETE | FINDING | search_service | search_8764 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_223 | INCOMPLETE | REMEDIATION | account_service | account_5479 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_223 | INCOMPLETE | REMEDIATION | search_service | search_8764 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_223 | INCOMPLETE | VERIFICATION | account_service | account_5479 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_223 | INCOMPLETE | VERIFICATION | search_service | search_8764 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_224 | INCOMPLETE | FINDING | integration_service | data_flow_1140 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_224 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1140 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_224 | INCOMPLETE | VERIFICATION | account_service | account_222 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_224 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1140 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_225 | INCOMPLETE | VERIFICATION | account_service | account_223 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_225 | INCOMPLETE | VERIFICATION | security_service | audit_record_9389 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_226 | INCOMPLETE | VERIFICATION | account_service | account_224 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_226 | INCOMPLETE | VERIFICATION | security_service | audit_record_9964 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | FINDING | search_service | search_8181 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | FINDING | support_platform | support_5830 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | REMEDIATION | search_service | search_8181 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | REMEDIATION | support_platform | support_5830 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | VERIFICATION | account_service | account_225 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | VERIFICATION | search_service | search_8181 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_227 | INCOMPLETE | VERIFICATION | support_platform | support_5830 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | FINDING | export_service | export_3210 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | FINDING | search_service | search_7054 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | REMEDIATION | export_service | export_3210 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | REMEDIATION | search_service | search_7054 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | VERIFICATION | account_service | account_226 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | VERIFICATION | export_service | export_3210 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_228 | INCOMPLETE | VERIFICATION | search_service | search_7054 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | FINDING | search_service | search_3627 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | FINDING | integration_service | data_flow_5831 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5831 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | REMEDIATION | search_service | search_3627 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | VERIFICATION | account_service | account_227 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | VERIFICATION | search_service | search_3627 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_229 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5831 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | FINDING | search_service | search_5612 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | FINDING | integration_service | data_flow_2516 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2516 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | REMEDIATION | search_service | search_5612 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | VERIFICATION | account_service | account_228 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | VERIFICATION | search_service | search_5612 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_230 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2516 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | FINDING | support_platform | support_3964 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | FINDING | integration_service | data_flow_2576 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | FINDING | backup_service | backup_6564 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2576 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | REMEDIATION | backup_service | backup_6564 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | REMEDIATION | support_platform | support_3964 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | VERIFICATION | account_service | account_229 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | VERIFICATION | security_service | audit_record_4425 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | VERIFICATION | support_platform | support_3964 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2576 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_231 | INCOMPLETE | VERIFICATION | backup_service | backup_6564 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_232 | INCOMPLETE | FINDING | support_platform | support_9862 | evidence_80 | Verified | 2026-06-28T07:00:00Z |
| case_232 | INCOMPLETE | REMEDIATION | support_platform | support_9862 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_232 | INCOMPLETE | VERIFICATION | account_service | account_230 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_232 | INCOMPLETE | VERIFICATION | support_platform | support_9862 | None | N/A (Proposed action) | 2026-06-28T07:00:00Z |
| case_233 | INCOMPLETE | FINDING | account_service | account_5264 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | FINDING | support_platform | support_9670 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | FINDING | integration_service | data_flow_6754 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | FINDING | backup_service | backup_8162 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6754 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | REMEDIATION | backup_service | backup_8162 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | REMEDIATION | account_service | account_5264 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | REMEDIATION | support_platform | support_9670 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | VERIFICATION | account_service | account_5264 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | VERIFICATION | security_service | audit_record_8350 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | VERIFICATION | support_platform | support_9670 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6754 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_233 | INCOMPLETE | VERIFICATION | backup_service | backup_8162 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | FINDING | search_service | search_2615 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | FINDING | support_platform | support_1254 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | REMEDIATION | search_service | search_2615 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | REMEDIATION | support_platform | support_1254 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | VERIFICATION | account_service | account_232 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | VERIFICATION | search_service | search_2615 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_234 | INCOMPLETE | VERIFICATION | support_platform | support_1254 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | FINDING | account_service | account_886 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | FINDING | support_platform | support_9391 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | FINDING | integration_service | data_flow_593 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | FINDING | backup_service | backup_2775 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | REMEDIATION | integration_service | data_flow_593 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | REMEDIATION | backup_service | backup_2775 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | REMEDIATION | account_service | account_886 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | REMEDIATION | support_platform | support_9391 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | VERIFICATION | account_service | account_886 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | VERIFICATION | security_service | audit_record_7103 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | VERIFICATION | support_platform | support_9391 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | VERIFICATION | integration_service | data_flow_593 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_235 | INCOMPLETE | VERIFICATION | backup_service | backup_2775 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | FINDING | search_service | search_5385 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | FINDING | integration_service | data_flow_7352 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7352 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | REMEDIATION | search_service | search_5385 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | VERIFICATION | account_service | account_234 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | VERIFICATION | search_service | search_5385 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_236 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7352 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | FINDING | account_service | account_2788 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | FINDING | search_service | search_2433 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | REMEDIATION | account_service | account_2788 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | REMEDIATION | search_service | search_2433 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | VERIFICATION | account_service | account_2788 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_237 | INCOMPLETE | VERIFICATION | search_service | search_2433 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_238 | INCOMPLETE | FINDING | account_service | account_945 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_238 | INCOMPLETE | REMEDIATION | account_service | account_945 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_238 | INCOMPLETE | VERIFICATION | account_service | account_945 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_238 | INCOMPLETE | VERIFICATION | security_service | audit_record_6797 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_239 | INCOMPLETE | FINDING | account_service | account_2838 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_239 | INCOMPLETE | REMEDIATION | account_service | account_2838 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_239 | INCOMPLETE | VERIFICATION | account_service | account_2838 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_239 | INCOMPLETE | VERIFICATION | security_service | audit_record_4940 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | FINDING | export_service | export_5242 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | FINDING | search_service | search_9335 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | REMEDIATION | export_service | export_5242 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | REMEDIATION | search_service | search_9335 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | VERIFICATION | account_service | account_238 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | VERIFICATION | export_service | export_5242 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_240 | INCOMPLETE | VERIFICATION | search_service | search_9335 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | FINDING | search_service | search_5659 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | FINDING | integration_service | data_flow_4568 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4568 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | REMEDIATION | search_service | search_5659 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | VERIFICATION | account_service | account_239 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | VERIFICATION | search_service | search_5659 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_241 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4568 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | FINDING | search_service | search_2904 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | FINDING | integration_service | data_flow_4475 | evidence_79 | Verified | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4475 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | REMEDIATION | search_service | search_2904 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | VERIFICATION | account_service | account_240 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | VERIFICATION | search_service | search_2904 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_242 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4475 | None | N/A (Proposed action) | 2026-06-23T06:00:00Z |
| case_243 | INCOMPLETE | VERIFICATION | account_service | account_241 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_243 | INCOMPLETE | VERIFICATION | security_service | audit_record_7202 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_244 | INCOMPLETE | VERIFICATION | account_service | account_242 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_244 | INCOMPLETE | VERIFICATION | security_service | audit_record_9314 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_245 | INCOMPLETE | FINDING | analytics_platform | analytics_4010 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_245 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_4010 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_245 | INCOMPLETE | VERIFICATION | account_service | account_243 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_245 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_4010 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | FINDING | search_service | search_2725 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | FINDING | support_platform | support_579 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | REMEDIATION | search_service | search_2725 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | REMEDIATION | support_platform | support_579 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | VERIFICATION | account_service | account_244 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | VERIFICATION | search_service | search_2725 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_246 | INCOMPLETE | VERIFICATION | support_platform | support_579 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | FINDING | account_service | account_2981 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | FINDING | search_service | search_9473 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | REMEDIATION | account_service | account_2981 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | REMEDIATION | search_service | search_9473 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | VERIFICATION | account_service | account_2981 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_247 | INCOMPLETE | VERIFICATION | search_service | search_9473 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_248 | INCOMPLETE | FINDING | integration_service | data_flow_677 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_248 | INCOMPLETE | REMEDIATION | integration_service | data_flow_677 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_248 | INCOMPLETE | VERIFICATION | account_service | account_246 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_248 | INCOMPLETE | VERIFICATION | integration_service | data_flow_677 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | FINDING | account_service | account_4181 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | FINDING | search_service | search_8190 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | FINDING | analytics_platform | analytics_8527 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | FINDING | support_platform | support_1364 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | REMEDIATION | account_service | account_4181 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | REMEDIATION | search_service | search_8190 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | REMEDIATION | support_platform | support_1364 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8527 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | VERIFICATION | account_service | account_4181 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | VERIFICATION | search_service | search_8190 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | VERIFICATION | support_platform | support_1364 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_249 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8527 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_250 | INCOMPLETE | FINDING | search_service | search_3760 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_250 | INCOMPLETE | REMEDIATION | search_service | search_3760 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_250 | INCOMPLETE | VERIFICATION | account_service | account_248 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_250 | INCOMPLETE | VERIFICATION | search_service | search_3760 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | FINDING | search_service | search_730 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | FINDING | support_platform | support_4541 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | REMEDIATION | search_service | search_730 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | REMEDIATION | support_platform | support_4541 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | VERIFICATION | account_service | account_249 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | VERIFICATION | search_service | search_730 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_251 | INCOMPLETE | VERIFICATION | support_platform | support_4541 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | FINDING | export_service | export_8598 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | FINDING | search_service | search_2936 | evidence_78 | Verified | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | REMEDIATION | export_service | export_8598 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | REMEDIATION | search_service | search_2936 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | VERIFICATION | account_service | account_250 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | VERIFICATION | export_service | export_8598 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_252 | INCOMPLETE | VERIFICATION | search_service | search_2936 | None | N/A (Proposed action) | 2026-06-18T12:00:00Z |
| case_253 | INCOMPLETE | VERIFICATION | account_service | account_251 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_253 | INCOMPLETE | VERIFICATION | security_service | audit_record_2927 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | FINDING | search_service | search_3011 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | FINDING | integration_service | data_flow_6233 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6233 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | REMEDIATION | search_service | search_3011 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | VERIFICATION | account_service | account_252 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | VERIFICATION | search_service | search_3011 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | VERIFICATION | security_service | audit_record_9256 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_254 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6233 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_255 | INCOMPLETE | FINDING | backup_service | backup_2427 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_255 | INCOMPLETE | REMEDIATION | backup_service | backup_2427 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_255 | INCOMPLETE | VERIFICATION | account_service | account_253 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_255 | INCOMPLETE | VERIFICATION | security_service | audit_record_2513 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_255 | INCOMPLETE | VERIFICATION | backup_service | backup_2427 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | FINDING | search_service | search_4027 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | FINDING | support_platform | support_3772 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | REMEDIATION | search_service | search_4027 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | REMEDIATION | support_platform | support_3772 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | VERIFICATION | account_service | account_254 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | VERIFICATION | search_service | search_4027 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | VERIFICATION | security_service | audit_record_2453 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_256 | INCOMPLETE | VERIFICATION | support_platform | support_3772 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_257 | INCOMPLETE | VERIFICATION | account_service | account_255 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_257 | INCOMPLETE | VERIFICATION | security_service | audit_record_7193 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | FINDING | search_service | search_5296 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | FINDING | support_platform | support_3834 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | REMEDIATION | search_service | search_5296 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | REMEDIATION | support_platform | support_3834 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | VERIFICATION | account_service | account_256 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | VERIFICATION | search_service | search_5296 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | VERIFICATION | security_service | audit_record_9890 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_258 | INCOMPLETE | VERIFICATION | support_platform | support_3834 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | FINDING | account_service | account_9608 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | FINDING | search_service | search_6990 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | REMEDIATION | account_service | account_9608 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | REMEDIATION | search_service | search_6990 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | VERIFICATION | account_service | account_9608 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | VERIFICATION | search_service | search_6990 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_259 | INCOMPLETE | VERIFICATION | security_service | audit_record_1421 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_260 | INCOMPLETE | VERIFICATION | account_service | account_258 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_260 | INCOMPLETE | VERIFICATION | security_service | audit_record_1876 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | FINDING | account_service | account_3150 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | FINDING | search_service | search_6781 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | REMEDIATION | account_service | account_3150 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | REMEDIATION | search_service | search_6781 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | VERIFICATION | account_service | account_3150 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | VERIFICATION | search_service | search_6781 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_261 | INCOMPLETE | VERIFICATION | security_service | audit_record_3335 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_262 | INCOMPLETE | FINDING | search_service | search_2228 | evidence_24 | Verified | 2026-06-13T11:00:00Z |
| case_262 | INCOMPLETE | REMEDIATION | search_service | search_2228 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_262 | INCOMPLETE | VERIFICATION | account_service | account_260 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_262 | INCOMPLETE | VERIFICATION | search_service | search_2228 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_262 | INCOMPLETE | VERIFICATION | security_service | audit_record_4812 | None | N/A (Proposed action) | 2026-06-13T11:00:00Z |
| case_263 | INCOMPLETE | FINDING | search_service | search_5331 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | FINDING | analytics_platform | analytics_515 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | FINDING | support_platform | support_2498 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | FINDING | support_platform | support_5234 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | REMEDIATION | search_service | search_5331 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | REMEDIATION | support_platform | support_2498 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | REMEDIATION | support_platform | support_5234 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_515 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | account_service | account_261 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | search_service | search_5331 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | security_service | audit_record_6863 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | support_platform | support_2498 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | support_platform | support_5234 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_263 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_515 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_264 | INCOMPLETE | VERIFICATION | account_service | account_262 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_264 | INCOMPLETE | VERIFICATION | support_platform | support_9996 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_265 | INCOMPLETE | VERIFICATION | account_service | account_263 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_266 | INCOMPLETE | FINDING | integration_service | data_flow_8277 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_266 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8277 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_266 | INCOMPLETE | VERIFICATION | account_service | account_264 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_266 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8277 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_267 | INCOMPLETE | VERIFICATION | account_service | account_265 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_268 | INCOMPLETE | FINDING | support_platform | support_8215 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_268 | INCOMPLETE | REMEDIATION | support_platform | support_8215 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_268 | INCOMPLETE | VERIFICATION | account_service | account_266 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_268 | INCOMPLETE | VERIFICATION | security_service | audit_record_4636 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_268 | INCOMPLETE | VERIFICATION | support_platform | support_8215 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | FINDING | search_service | search_1730 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | FINDING | analytics_platform | analytics_6766 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | FINDING | support_platform | support_8301 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | REMEDIATION | search_service | search_1730 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | REMEDIATION | support_platform | support_8301 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6766 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | VERIFICATION | account_service | account_267 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | VERIFICATION | search_service | search_1730 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | VERIFICATION | support_platform | support_8301 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_269 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6766 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_270 | INCOMPLETE | FINDING | support_platform | support_7707 | evidence_25 | Verified | 2026-06-08T10:00:00Z |
| case_270 | INCOMPLETE | REMEDIATION | support_platform | support_7707 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_270 | INCOMPLETE | VERIFICATION | account_service | account_268 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_270 | INCOMPLETE | VERIFICATION | security_service | audit_record_5206 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_270 | INCOMPLETE | VERIFICATION | support_platform | support_7707 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_271 | INCOMPLETE | VERIFICATION | account_service | account_269 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_272 | INCOMPLETE | VERIFICATION | account_service | account_270 | None | N/A (Proposed action) | 2026-06-08T10:00:00Z |
| case_273 | INCOMPLETE | FINDING | account_service | account_8689 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_273 | INCOMPLETE | FINDING | search_service | search_5454 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_273 | INCOMPLETE | REMEDIATION | account_service | account_8689 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_273 | INCOMPLETE | REMEDIATION | search_service | search_5454 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_273 | INCOMPLETE | VERIFICATION | account_service | account_8689 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_273 | INCOMPLETE | VERIFICATION | search_service | search_5454 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_274 | INCOMPLETE | VERIFICATION | account_service | account_272 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_274 | INCOMPLETE | VERIFICATION | security_service | audit_record_6398 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | FINDING | search_service | search_5264 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | FINDING | support_platform | support_3684 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | REMEDIATION | search_service | search_5264 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | REMEDIATION | support_platform | support_3684 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | VERIFICATION | account_service | account_273 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | VERIFICATION | search_service | search_5264 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_275 | INCOMPLETE | VERIFICATION | support_platform | support_3684 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_276 | INCOMPLETE | VERIFICATION | account_service | account_274 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_276 | INCOMPLETE | VERIFICATION | security_service | audit_record_8323 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | FINDING | support_platform | support_2036 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | FINDING | integration_service | data_flow_2439 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | FINDING | backup_service | backup_9728 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2439 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | REMEDIATION | backup_service | backup_9728 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | REMEDIATION | support_platform | support_2036 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | VERIFICATION | account_service | account_275 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | VERIFICATION | security_service | audit_record_8228 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | VERIFICATION | support_platform | support_2036 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2439 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_277 | INCOMPLETE | VERIFICATION | backup_service | backup_9728 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | FINDING | search_service | search_8082 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | FINDING | analytics_platform | analytics_5959 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | FINDING | support_platform | support_6333 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | FINDING | integration_service | data_flow_4629 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4629 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | REMEDIATION | search_service | search_8082 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | REMEDIATION | support_platform | support_6333 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5959 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | VERIFICATION | account_service | account_276 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | VERIFICATION | search_service | search_8082 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | VERIFICATION | support_platform | support_6333 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5959 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_278 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4629 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_279 | INCOMPLETE | FINDING | backup_service | backup_8588 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_279 | INCOMPLETE | REMEDIATION | backup_service | backup_8588 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_279 | INCOMPLETE | VERIFICATION | account_service | account_277 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_279 | INCOMPLETE | VERIFICATION | backup_service | backup_8588 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_280 | INCOMPLETE | FINDING | support_platform | support_7073 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_280 | INCOMPLETE | REMEDIATION | support_platform | support_7073 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_280 | INCOMPLETE | VERIFICATION | account_service | account_278 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_280 | INCOMPLETE | VERIFICATION | support_platform | support_7073 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | FINDING | search_service | search_3364 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | FINDING | analytics_platform | analytics_6265 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | FINDING | support_platform | support_2757 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | FINDING | integration_service | data_flow_9008 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9008 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | REMEDIATION | search_service | search_3364 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | REMEDIATION | support_platform | support_2757 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6265 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | VERIFICATION | account_service | account_279 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | VERIFICATION | search_service | search_3364 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | VERIFICATION | support_platform | support_2757 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6265 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_281 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9008 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_282 | INCOMPLETE | FINDING | support_platform | support_8370 | evidence_77 | Verified | 2026-06-03T09:00:00Z |
| case_282 | INCOMPLETE | REMEDIATION | support_platform | support_8370 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_282 | INCOMPLETE | VERIFICATION | account_service | account_280 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_282 | INCOMPLETE | VERIFICATION | support_platform | support_8370 | None | N/A (Proposed action) | 2026-06-03T09:00:00Z |
| case_283 | INCOMPLETE | FINDING | account_service | account_947 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_283 | INCOMPLETE | REMEDIATION | account_service | account_947 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_283 | INCOMPLETE | VERIFICATION | account_service | account_947 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_283 | INCOMPLETE | VERIFICATION | security_service | audit_record_5680 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_284 | INCOMPLETE | FINDING | integration_service | data_flow_6953 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_284 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6953 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_284 | INCOMPLETE | VERIFICATION | account_service | account_282 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_284 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6953 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | FINDING | account_service | account_285 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | FINDING | search_service | search_036 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | REMEDIATION | account_service | account_285 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | REMEDIATION | search_service | search_036 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | VERIFICATION | account_service | account_285 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_285 | INCOMPLETE | VERIFICATION | search_service | search_036 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_286 | INCOMPLETE | FINDING | account_service | account_2016 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_286 | INCOMPLETE | REMEDIATION | account_service | account_2016 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_286 | INCOMPLETE | VERIFICATION | account_service | account_2016 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_286 | INCOMPLETE | VERIFICATION | security_service | audit_record_1714 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | FINDING | search_service | search_5705 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | FINDING | support_platform | support_7432 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | REMEDIATION | search_service | search_5705 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | REMEDIATION | support_platform | support_7432 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | VERIFICATION | account_service | account_285 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | VERIFICATION | search_service | search_5705 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_287 | INCOMPLETE | VERIFICATION | support_platform | support_7432 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_288 | INCOMPLETE | FINDING | export_service | export_7906 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_288 | INCOMPLETE | REMEDIATION | export_service | export_7906 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_288 | INCOMPLETE | VERIFICATION | account_service | account_286 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_288 | INCOMPLETE | VERIFICATION | export_service | export_7906 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | FINDING | search_service | search_6432 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | FINDING | integration_service | data_flow_743 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | REMEDIATION | integration_service | data_flow_743 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | REMEDIATION | search_service | search_6432 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | VERIFICATION | account_service | account_287 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | VERIFICATION | search_service | search_6432 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_289 | INCOMPLETE | VERIFICATION | integration_service | data_flow_743 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | FINDING | search_service | search_3144 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | FINDING | integration_service | data_flow_179 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | REMEDIATION | integration_service | data_flow_179 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | REMEDIATION | search_service | search_3144 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | VERIFICATION | account_service | account_288 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | VERIFICATION | search_service | search_3144 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_290 | INCOMPLETE | VERIFICATION | integration_service | data_flow_179 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_291 | INCOMPLETE | FINDING | backup_service | backup_7079 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_291 | INCOMPLETE | REMEDIATION | backup_service | backup_7079 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_291 | INCOMPLETE | VERIFICATION | account_service | account_289 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_291 | INCOMPLETE | VERIFICATION | backup_service | backup_7079 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | FINDING | account_service | account_1125 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | FINDING | support_platform | support_1526 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | FINDING | integration_service | data_flow_5598 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | FINDING | backup_service | backup_1825 | evidence_76 | Verified | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5598 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | REMEDIATION | backup_service | backup_1825 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | REMEDIATION | account_service | account_1125 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | REMEDIATION | support_platform | support_1526 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | VERIFICATION | account_service | account_1125 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | VERIFICATION | security_service | audit_record_3432 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | VERIFICATION | support_platform | support_1526 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5598 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_292 | INCOMPLETE | VERIFICATION | backup_service | backup_1825 | None | N/A (Proposed action) | 2026-05-29T08:00:00Z |
| case_293 | INCOMPLETE | FINDING | analytics_platform | analytics_5854 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_293 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5854 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_293 | INCOMPLETE | VERIFICATION | account_service | account_291 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_293 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5854 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_294 | INCOMPLETE | VERIFICATION | account_service | account_292 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_294 | INCOMPLETE | VERIFICATION | security_service | audit_record_4387 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_295 | INCOMPLETE | VERIFICATION | account_service | account_293 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_295 | INCOMPLETE | VERIFICATION | security_service | audit_record_1269 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | FINDING | search_service | search_9631 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | FINDING | integration_service | data_flow_085 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | REMEDIATION | integration_service | data_flow_085 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | REMEDIATION | search_service | search_9631 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | VERIFICATION | account_service | account_294 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | VERIFICATION | search_service | search_9631 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_296 | INCOMPLETE | VERIFICATION | integration_service | data_flow_085 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | FINDING | support_platform | support_1983 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | FINDING | integration_service | data_flow_3391 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | FINDING | backup_service | backup_7308 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3391 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | REMEDIATION | backup_service | backup_7308 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | REMEDIATION | support_platform | support_1983 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | VERIFICATION | account_service | account_295 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | VERIFICATION | security_service | audit_record_7878 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | VERIFICATION | support_platform | support_1983 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3391 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_297 | INCOMPLETE | VERIFICATION | backup_service | backup_7308 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | FINDING | search_service | search_6282 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | FINDING | support_platform | support_643 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | REMEDIATION | search_service | search_6282 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | REMEDIATION | support_platform | support_643 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | VERIFICATION | account_service | account_296 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | VERIFICATION | search_service | search_6282 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_298 | INCOMPLETE | VERIFICATION | support_platform | support_643 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_299 | INCOMPLETE | VERIFICATION | account_service | account_297 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_299 | INCOMPLETE | VERIFICATION | security_service | audit_record_5194 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | FINDING | export_service | export_6623 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | FINDING | search_service | search_4299 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | REMEDIATION | export_service | export_6623 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | REMEDIATION | search_service | search_4299 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | VERIFICATION | account_service | account_298 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | VERIFICATION | export_service | export_6623 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_300 | INCOMPLETE | VERIFICATION | search_service | search_4299 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | FINDING | search_service | search_5268 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | FINDING | integration_service | data_flow_4521 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4521 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | REMEDIATION | search_service | search_5268 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | VERIFICATION | account_service | account_299 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | VERIFICATION | search_service | search_5268 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_301 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4521 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | FINDING | search_service | search_1033 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | FINDING | analytics_platform | analytics_1133 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | FINDING | support_platform | support_2983 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | FINDING | integration_service | data_flow_7594 | evidence_75 | Verified | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7594 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | REMEDIATION | search_service | search_1033 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | REMEDIATION | support_platform | support_2983 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1133 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | VERIFICATION | account_service | account_300 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | VERIFICATION | search_service | search_1033 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | VERIFICATION | support_platform | support_2983 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1133 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_302 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7594 | None | N/A (Proposed action) | 2026-05-24T07:00:00Z |
| case_303 | INCOMPLETE | FINDING | backup_service | backup_4935 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_303 | INCOMPLETE | REMEDIATION | backup_service | backup_4935 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_303 | INCOMPLETE | VERIFICATION | account_service | account_301 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_303 | INCOMPLETE | VERIFICATION | security_service | audit_record_7923 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_303 | INCOMPLETE | VERIFICATION | backup_service | backup_4935 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_304 | INCOMPLETE | VERIFICATION | account_service | account_302 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_304 | INCOMPLETE | VERIFICATION | security_service | audit_record_4759 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | FINDING | search_service | search_4321 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | FINDING | analytics_platform | analytics_9285 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | REMEDIATION | search_service | search_4321 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_9285 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | VERIFICATION | account_service | account_303 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | VERIFICATION | search_service | search_4321 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | VERIFICATION | security_service | audit_record_507 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_305 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_9285 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | FINDING | search_service | search_8250 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | FINDING | support_platform | support_450 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | REMEDIATION | search_service | search_8250 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | REMEDIATION | support_platform | support_450 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | VERIFICATION | account_service | account_304 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | VERIFICATION | search_service | search_8250 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | VERIFICATION | security_service | audit_record_9051 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_306 | INCOMPLETE | VERIFICATION | support_platform | support_450 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | FINDING | account_service | account_585 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | FINDING | search_service | search_7660 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | REMEDIATION | account_service | account_585 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | REMEDIATION | search_service | search_7660 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | VERIFICATION | account_service | account_585 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | VERIFICATION | search_service | search_7660 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_307 | INCOMPLETE | VERIFICATION | security_service | audit_record_5129 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | FINDING | integration_service | data_flow_8933 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | FINDING | backup_service | backup_4917 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8933 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | REMEDIATION | backup_service | backup_4917 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | VERIFICATION | account_service | account_306 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | VERIFICATION | security_service | audit_record_3221 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | VERIFICATION | support_platform | support_6046 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8933 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_308 | INCOMPLETE | VERIFICATION | backup_service | backup_4917 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_309 | INCOMPLETE | VERIFICATION | account_service | account_307 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_309 | INCOMPLETE | VERIFICATION | security_service | audit_record_1945 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | FINDING | search_service | search_6265 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | FINDING | support_platform | support_4263 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | REMEDIATION | search_service | search_6265 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | REMEDIATION | support_platform | support_4263 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | VERIFICATION | account_service | account_308 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | VERIFICATION | search_service | search_6265 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | VERIFICATION | security_service | audit_record_5640 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_310 | INCOMPLETE | VERIFICATION | support_platform | support_4263 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | FINDING | search_service | search_3004 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | FINDING | support_platform | support_4952 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | REMEDIATION | search_service | search_3004 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | REMEDIATION | support_platform | support_4952 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | VERIFICATION | account_service | account_309 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | VERIFICATION | search_service | search_3004 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | VERIFICATION | security_service | audit_record_6245 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_311 | INCOMPLETE | VERIFICATION | support_platform | support_4952 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | FINDING | export_service | export_9860 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | FINDING | search_service | search_6805 | evidence_29 | Verified | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | REMEDIATION | export_service | export_9860 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | REMEDIATION | search_service | search_6805 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | VERIFICATION | account_service | account_310 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | VERIFICATION | export_service | export_9860 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | VERIFICATION | search_service | search_6805 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_312 | INCOMPLETE | VERIFICATION | security_service | audit_record_6559 | None | N/A (Proposed action) | 2026-05-19T06:00:00Z |
| case_313 | INCOMPLETE | VERIFICATION | account_service | account_311 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_313 | INCOMPLETE | VERIFICATION | security_service | audit_record_7020 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_314 | INCOMPLETE | VERIFICATION | account_service | account_312 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_314 | INCOMPLETE | VERIFICATION | security_service | audit_record_7893 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_315 | INCOMPLETE | FINDING | backup_service | backup_7421 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_315 | INCOMPLETE | REMEDIATION | backup_service | backup_7421 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_315 | INCOMPLETE | VERIFICATION | account_service | account_313 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_315 | INCOMPLETE | VERIFICATION | backup_service | backup_7421 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | FINDING | search_service | search_8583 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | FINDING | support_platform | support_1176 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | REMEDIATION | search_service | search_8583 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | REMEDIATION | support_platform | support_1176 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | VERIFICATION | account_service | account_314 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | VERIFICATION | search_service | search_8583 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_316 | INCOMPLETE | VERIFICATION | support_platform | support_1176 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | FINDING | search_service | search_8665 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | FINDING | analytics_platform | analytics_1488 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | FINDING | support_platform | support_4439 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | FINDING | integration_service | data_flow_3064 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3064 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | REMEDIATION | search_service | search_8665 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | REMEDIATION | support_platform | support_4439 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1488 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | VERIFICATION | account_service | account_315 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | VERIFICATION | search_service | search_8665 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | VERIFICATION | support_platform | support_4439 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1488 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_317 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3064 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | FINDING | search_service | search_5472 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | FINDING | support_platform | support_7995 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | REMEDIATION | search_service | search_5472 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | REMEDIATION | support_platform | support_7995 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | VERIFICATION | account_service | account_316 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | VERIFICATION | search_service | search_5472 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_318 | INCOMPLETE | VERIFICATION | support_platform | support_7995 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_319 | INCOMPLETE | VERIFICATION | account_service | account_317 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_319 | INCOMPLETE | VERIFICATION | security_service | audit_record_7337 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | FINDING | search_service | search_2256 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | FINDING | integration_service | data_flow_8828 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8828 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | REMEDIATION | search_service | search_2256 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | VERIFICATION | account_service | account_318 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | VERIFICATION | search_service | search_2256 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_320 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8828 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | FINDING | search_service | search_3667 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | FINDING | integration_service | data_flow_4964 | evidence_74 | Verified | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4964 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | REMEDIATION | search_service | search_3667 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | VERIFICATION | account_service | account_319 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | VERIFICATION | search_service | search_3667 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_321 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4964 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_322 | INCOMPLETE | VERIFICATION | account_service | account_320 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_322 | INCOMPLETE | VERIFICATION | security_service | audit_record_3201 | None | N/A (Proposed action) | 2026-05-14T12:00:00Z |
| case_323 | INCOMPLETE | FINDING | account_service | account_2917 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_323 | INCOMPLETE | REMEDIATION | account_service | account_2917 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_323 | INCOMPLETE | VERIFICATION | account_service | account_2917 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_323 | INCOMPLETE | VERIFICATION | security_service | audit_record_3338 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | FINDING | account_service | account_1242 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | FINDING | support_platform | support_7249 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | FINDING | integration_service | data_flow_4769 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | FINDING | backup_service | backup_6458 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4769 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | REMEDIATION | backup_service | backup_6458 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | REMEDIATION | account_service | account_1242 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | REMEDIATION | support_platform | support_7249 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | VERIFICATION | account_service | account_1242 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | VERIFICATION | security_service | audit_record_4466 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | VERIFICATION | support_platform | support_7249 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4769 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_324 | INCOMPLETE | VERIFICATION | backup_service | backup_6458 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | FINDING | search_service | search_4054 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | FINDING | integration_service | data_flow_9962 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9962 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | REMEDIATION | search_service | search_4054 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | VERIFICATION | account_service | account_323 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | VERIFICATION | search_service | search_4054 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_325 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9962 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | FINDING | account_service | account_3785 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | FINDING | support_platform | support_305 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | FINDING | integration_service | data_flow_2468 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | FINDING | backup_service | backup_2894 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2468 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | REMEDIATION | backup_service | backup_2894 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | REMEDIATION | account_service | account_3785 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | REMEDIATION | support_platform | support_305 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | VERIFICATION | account_service | account_3785 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | VERIFICATION | security_service | audit_record_1219 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | VERIFICATION | support_platform | support_305 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2468 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_326 | INCOMPLETE | VERIFICATION | backup_service | backup_2894 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_327 | INCOMPLETE | FINDING | account_service | account_4606 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_327 | INCOMPLETE | REMEDIATION | account_service | account_4606 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_327 | INCOMPLETE | VERIFICATION | account_service | account_4606 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_327 | INCOMPLETE | VERIFICATION | security_service | audit_record_461 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | FINDING | search_service | search_9107 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | FINDING | support_platform | support_7926 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | REMEDIATION | search_service | search_9107 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | REMEDIATION | support_platform | support_7926 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | VERIFICATION | account_service | account_326 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | VERIFICATION | search_service | search_9107 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_328 | INCOMPLETE | VERIFICATION | support_platform | support_7926 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | FINDING | search_service | search_5226 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | FINDING | analytics_platform | analytics_671 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | REMEDIATION | search_service | search_5226 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_671 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | VERIFICATION | account_service | account_327 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | VERIFICATION | search_service | search_5226 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_329 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_671 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | FINDING | search_service | search_4560 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | FINDING | support_platform | support_4851 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | REMEDIATION | search_service | search_4560 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | REMEDIATION | support_platform | support_4851 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | VERIFICATION | account_service | account_328 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | VERIFICATION | search_service | search_4560 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_330 | INCOMPLETE | VERIFICATION | support_platform | support_4851 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | FINDING | account_service | account_6814 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | FINDING | support_platform | support_1403 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | FINDING | integration_service | data_flow_8534 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | FINDING | backup_service | backup_9376 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8534 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | REMEDIATION | backup_service | backup_9376 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | REMEDIATION | account_service | account_6814 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | REMEDIATION | support_platform | support_1403 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | VERIFICATION | account_service | account_6814 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | VERIFICATION | security_service | audit_record_6731 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | VERIFICATION | support_platform | support_1403 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8534 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_331 | INCOMPLETE | VERIFICATION | backup_service | backup_9376 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | FINDING | search_service | search_049 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | FINDING | integration_service | data_flow_4392 | evidence_73 | Verified | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4392 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | REMEDIATION | search_service | search_049 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | VERIFICATION | account_service | account_330 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | VERIFICATION | search_service | search_049 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_332 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4392 | None | N/A (Proposed action) | 2026-05-09T11:00:00Z |
| case_333 | INCOMPLETE | FINDING | account_service | account_2475 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_333 | INCOMPLETE | FINDING | search_service | search_5970 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_333 | INCOMPLETE | REMEDIATION | account_service | account_2475 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_333 | INCOMPLETE | REMEDIATION | search_service | search_5970 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_333 | INCOMPLETE | VERIFICATION | account_service | account_2475 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_333 | INCOMPLETE | VERIFICATION | search_service | search_5970 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | FINDING | search_service | search_7348 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | FINDING | support_platform | support_214 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | REMEDIATION | search_service | search_7348 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | REMEDIATION | support_platform | support_214 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | VERIFICATION | account_service | account_332 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | VERIFICATION | search_service | search_7348 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_334 | INCOMPLETE | VERIFICATION | support_platform | support_214 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | FINDING | support_platform | support_4712 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | FINDING | integration_service | data_flow_7452 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | FINDING | backup_service | backup_3136 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7452 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | REMEDIATION | backup_service | backup_3136 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | REMEDIATION | support_platform | support_4712 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | VERIFICATION | account_service | account_333 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | VERIFICATION | security_service | audit_record_711 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | VERIFICATION | support_platform | support_4712 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7452 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_335 | INCOMPLETE | VERIFICATION | backup_service | backup_3136 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_336 | INCOMPLETE | VERIFICATION | account_service | account_334 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_336 | INCOMPLETE | VERIFICATION | security_service | audit_record_5022 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | FINDING | search_service | search_3773 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | FINDING | integration_service | data_flow_5200 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5200 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | REMEDIATION | search_service | search_3773 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | VERIFICATION | account_service | account_335 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | VERIFICATION | search_service | search_3773 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_337 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5200 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | FINDING | search_service | search_1392 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | FINDING | integration_service | data_flow_9392 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9392 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | REMEDIATION | search_service | search_1392 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | VERIFICATION | account_service | account_336 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | VERIFICATION | search_service | search_1392 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_338 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9392 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_339 | INCOMPLETE | VERIFICATION | account_service | account_337 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_339 | INCOMPLETE | VERIFICATION | security_service | audit_record_2922 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | FINDING | search_service | search_5411 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | FINDING | integration_service | data_flow_5916 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5916 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | REMEDIATION | search_service | search_5411 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | VERIFICATION | account_service | account_338 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | VERIFICATION | search_service | search_5411 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_340 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5916 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | FINDING | search_service | search_7367 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | FINDING | analytics_platform | analytics_183 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | REMEDIATION | search_service | search_7367 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_183 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | VERIFICATION | account_service | account_339 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | VERIFICATION | search_service | search_7367 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_341 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_183 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_342 | INCOMPLETE | FINDING | support_platform | support_3399 | evidence_72 | Verified | 2026-05-04T10:00:00Z |
| case_342 | INCOMPLETE | REMEDIATION | support_platform | support_3399 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_342 | INCOMPLETE | VERIFICATION | account_service | account_340 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_342 | INCOMPLETE | VERIFICATION | support_platform | support_3399 | None | N/A (Proposed action) | 2026-05-04T10:00:00Z |
| case_343 | INCOMPLETE | VERIFICATION | account_service | account_341 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_343 | INCOMPLETE | VERIFICATION | security_service | audit_record_9233 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | FINDING | search_service | search_5267 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | FINDING | integration_service | data_flow_5544 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5544 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | REMEDIATION | search_service | search_5267 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | VERIFICATION | account_service | account_342 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | VERIFICATION | search_service | search_5267 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_344 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5544 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_345 | INCOMPLETE | VERIFICATION | account_service | account_343 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_345 | INCOMPLETE | VERIFICATION | security_service | audit_record_454 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_346 | INCOMPLETE | VERIFICATION | account_service | account_344 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_346 | INCOMPLETE | VERIFICATION | security_service | audit_record_1700 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | FINDING | search_service | search_8185 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | FINDING | support_platform | support_9474 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | REMEDIATION | search_service | search_8185 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | REMEDIATION | support_platform | support_9474 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | VERIFICATION | account_service | account_345 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | VERIFICATION | search_service | search_8185 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_347 | INCOMPLETE | VERIFICATION | support_platform | support_9474 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | FINDING | export_service | export_4871 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | FINDING | search_service | search_6170 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | FINDING | analytics_platform | analytics_9196 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | FINDING | support_platform | support_2897 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | REMEDIATION | export_service | export_4871 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | REMEDIATION | search_service | search_6170 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | REMEDIATION | support_platform | support_2897 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_9196 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | VERIFICATION | account_service | account_346 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | VERIFICATION | export_service | export_4871 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | VERIFICATION | search_service | search_6170 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | VERIFICATION | support_platform | support_2897 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_348 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_9196 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | FINDING | search_service | search_3944 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | FINDING | integration_service | data_flow_3178 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3178 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | REMEDIATION | search_service | search_3944 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | VERIFICATION | account_service | account_347 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | VERIFICATION | search_service | search_3944 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_349 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3178 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_350 | INCOMPLETE | FINDING | integration_service | data_flow_9775 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_350 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9775 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_350 | INCOMPLETE | VERIFICATION | account_service | account_348 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_350 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9775 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | FINDING | support_platform | support_7137 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | FINDING | integration_service | data_flow_4323 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | FINDING | backup_service | backup_024 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4323 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | REMEDIATION | backup_service | backup_024 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | REMEDIATION | support_platform | support_7137 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | VERIFICATION | account_service | account_349 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | VERIFICATION | security_service | audit_record_8787 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | VERIFICATION | support_platform | support_7137 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4323 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_351 | INCOMPLETE | VERIFICATION | backup_service | backup_024 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | FINDING | search_service | search_5685 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | FINDING | support_platform | support_3980 | evidence_71 | Verified | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | REMEDIATION | search_service | search_5685 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | REMEDIATION | support_platform | support_3980 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | VERIFICATION | account_service | account_350 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | VERIFICATION | search_service | search_5685 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_352 | INCOMPLETE | VERIFICATION | support_platform | support_3980 | None | N/A (Proposed action) | 2026-04-29T09:00:00Z |
| case_353 | INCOMPLETE | FINDING | search_service | search_495 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | FINDING | analytics_platform | analytics_8011 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | FINDING | support_platform | support_2406 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | FINDING | integration_service | data_flow_3180 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3180 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | REMEDIATION | search_service | search_495 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | REMEDIATION | support_platform | support_2406 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8011 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | account_service | account_351 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | search_service | search_495 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | security_service | audit_record_5773 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | support_platform | support_2406 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8011 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_353 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3180 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_354 | INCOMPLETE | VERIFICATION | account_service | account_352 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_354 | INCOMPLETE | VERIFICATION | security_service | audit_record_9286 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_355 | INCOMPLETE | FINDING | account_service | account_6539 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_355 | INCOMPLETE | REMEDIATION | account_service | account_6539 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_355 | INCOMPLETE | VERIFICATION | account_service | account_6539 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_355 | INCOMPLETE | VERIFICATION | security_service | audit_record_1151 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | FINDING | search_service | search_5025 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | FINDING | analytics_platform | analytics_5413 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | FINDING | support_platform | support_6224 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | FINDING | integration_service | data_flow_4472 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4472 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | REMEDIATION | search_service | search_5025 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | REMEDIATION | support_platform | support_6224 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5413 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | account_service | account_354 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | search_service | search_5025 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | security_service | audit_record_771 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | support_platform | support_6224 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5413 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_356 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4472 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | FINDING | account_service | account_8105 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | FINDING | search_service | search_6828 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | REMEDIATION | account_service | account_8105 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | REMEDIATION | search_service | search_6828 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | VERIFICATION | account_service | account_8105 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | VERIFICATION | search_service | search_6828 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_357 | INCOMPLETE | VERIFICATION | security_service | audit_record_350 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | FINDING | search_service | search_4067 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | FINDING | support_platform | support_1846 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | REMEDIATION | search_service | search_4067 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | REMEDIATION | support_platform | support_1846 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | VERIFICATION | account_service | account_356 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | VERIFICATION | search_service | search_4067 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | VERIFICATION | security_service | audit_record_1395 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_358 | INCOMPLETE | VERIFICATION | support_platform | support_1846 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | FINDING | search_service | search_2492 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | FINDING | support_platform | support_2537 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | REMEDIATION | search_service | search_2492 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | REMEDIATION | support_platform | support_2537 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | VERIFICATION | account_service | account_357 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | VERIFICATION | search_service | search_2492 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | VERIFICATION | security_service | audit_record_2641 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_359 | INCOMPLETE | VERIFICATION | support_platform | support_2537 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | FINDING | export_service | export_350 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | FINDING | search_service | search_957 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | REMEDIATION | export_service | export_350 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | REMEDIATION | search_service | search_957 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | VERIFICATION | account_service | account_358 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | VERIFICATION | export_service | export_350 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | VERIFICATION | search_service | search_957 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_360 | INCOMPLETE | VERIFICATION | security_service | audit_record_2605 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | FINDING | search_service | search_496 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | FINDING | integration_service | data_flow_3052 | evidence_33 | Verified | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3052 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | REMEDIATION | search_service | search_496 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | VERIFICATION | account_service | account_359 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | VERIFICATION | search_service | search_496 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | VERIFICATION | security_service | audit_record_7587 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_361 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3052 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_362 | INCOMPLETE | VERIFICATION | account_service | account_360 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_362 | INCOMPLETE | VERIFICATION | security_service | audit_record_8638 | None | N/A (Proposed action) | 2026-04-24T08:00:00Z |
| case_363 | INCOMPLETE | VERIFICATION | account_service | account_361 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | FINDING | search_service | search_8198 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | FINDING | support_platform | support_9699 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | REMEDIATION | search_service | search_8198 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | REMEDIATION | support_platform | support_9699 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | VERIFICATION | account_service | account_362 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | VERIFICATION | search_service | search_8198 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_364 | INCOMPLETE | VERIFICATION | support_platform | support_9699 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | FINDING | analytics_platform | analytics_547 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | FINDING | support_platform | support_3294 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | REMEDIATION | support_platform | support_3294 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_547 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | VERIFICATION | account_service | account_363 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | VERIFICATION | support_platform | support_3294 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_365 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_547 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | FINDING | analytics_platform | analytics_8593 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | FINDING | support_platform | support_5609 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | FINDING | integration_service | data_flow_8256 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8256 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | REMEDIATION | support_platform | support_5609 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8593 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | VERIFICATION | account_service | account_364 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | VERIFICATION | security_service | audit_record_4655 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | VERIFICATION | support_platform | support_5609 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8593 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_366 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8256 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | FINDING | analytics_platform | analytics_946 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | FINDING | support_platform | support_4691 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | REMEDIATION | support_platform | support_4691 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_946 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | VERIFICATION | account_service | account_365 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | VERIFICATION | support_platform | support_4691 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_367 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_946 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_368 | INCOMPLETE | FINDING | integration_service | data_flow_8293 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_368 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8293 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_368 | INCOMPLETE | VERIFICATION | account_service | account_9570 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_368 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8293 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_369 | INCOMPLETE | VERIFICATION | account_service | account_367 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | FINDING | analytics_platform | analytics_7215 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | FINDING | support_platform | support_6949 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | FINDING | integration_service | data_flow_5608 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5608 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | REMEDIATION | support_platform | support_6949 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_7215 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | VERIFICATION | account_service | account_368 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | VERIFICATION | support_platform | support_6949 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_7215 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_370 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5608 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_371 | INCOMPLETE | FINDING | support_platform | support_3110 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_371 | INCOMPLETE | REMEDIATION | support_platform | support_3110 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_371 | INCOMPLETE | VERIFICATION | account_service | account_369 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_371 | INCOMPLETE | VERIFICATION | support_platform | support_3110 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_372 | INCOMPLETE | FINDING | export_service | export_5081 | evidence_34 | Verified | 2026-04-19T07:00:00Z |
| case_372 | INCOMPLETE | REMEDIATION | export_service | export_5081 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_372 | INCOMPLETE | VERIFICATION | account_service | account_370 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_372 | INCOMPLETE | VERIFICATION | export_service | export_5081 | None | N/A (Proposed action) | 2026-04-19T07:00:00Z |
| case_373 | INCOMPLETE | FINDING | search_service | search_7859 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | FINDING | integration_service | data_flow_2984 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2984 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | REMEDIATION | search_service | search_7859 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | VERIFICATION | account_service | account_371 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | VERIFICATION | search_service | search_7859 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_373 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2984 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_374 | INCOMPLETE | FINDING | account_service | account_8598 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_374 | INCOMPLETE | REMEDIATION | account_service | account_8598 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_374 | INCOMPLETE | VERIFICATION | account_service | account_8598 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_374 | INCOMPLETE | VERIFICATION | security_service | audit_record_5137 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_375 | INCOMPLETE | FINDING | account_service | account_2854 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_375 | INCOMPLETE | REMEDIATION | account_service | account_2854 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_375 | INCOMPLETE | VERIFICATION | account_service | account_2854 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_375 | INCOMPLETE | VERIFICATION | security_service | audit_record_6359 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | FINDING | search_service | search_3126 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | FINDING | support_platform | support_475 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | REMEDIATION | search_service | search_3126 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | REMEDIATION | support_platform | support_475 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | VERIFICATION | account_service | account_374 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | VERIFICATION | search_service | search_3126 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_376 | INCOMPLETE | VERIFICATION | support_platform | support_475 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_377 | INCOMPLETE | FINDING | analytics_platform | analytics_3651 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_377 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_3651 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_377 | INCOMPLETE | VERIFICATION | account_service | account_375 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_377 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_3651 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_378 | INCOMPLETE | FINDING | account_service | account_976 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_378 | INCOMPLETE | REMEDIATION | account_service | account_976 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_378 | INCOMPLETE | VERIFICATION | account_service | account_976 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_378 | INCOMPLETE | VERIFICATION | security_service | audit_record_7312 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | FINDING | account_service | account_6246 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | FINDING | search_service | search_9124 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | REMEDIATION | account_service | account_6246 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | REMEDIATION | search_service | search_9124 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | VERIFICATION | account_service | account_6246 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_379 | INCOMPLETE | VERIFICATION | search_service | search_9124 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_380 | INCOMPLETE | FINDING | account_service | account_4001 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_380 | INCOMPLETE | REMEDIATION | account_service | account_4001 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_380 | INCOMPLETE | VERIFICATION | account_service | account_4001 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_380 | INCOMPLETE | VERIFICATION | security_service | audit_record_4489 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_381 | INCOMPLETE | FINDING | account_service | account_6784 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_381 | INCOMPLETE | REMEDIATION | account_service | account_6784 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_381 | INCOMPLETE | VERIFICATION | account_service | account_6784 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | FINDING | search_service | search_8171 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | FINDING | analytics_platform | analytics_9918 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | FINDING | support_platform | support_5071 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | FINDING | integration_service | data_flow_6090 | evidence_70 | Verified | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6090 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | REMEDIATION | search_service | search_8171 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | REMEDIATION | support_platform | support_5071 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_9918 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | VERIFICATION | account_service | account_380 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | VERIFICATION | search_service | search_8171 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | VERIFICATION | support_platform | support_5071 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_9918 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_382 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6090 | None | N/A (Proposed action) | 2026-04-14T06:00:00Z |
| case_383 | INCOMPLETE | VERIFICATION | account_service | account_381 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_384 | INCOMPLETE | VERIFICATION | account_service | account_382 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_385 | INCOMPLETE | VERIFICATION | account_service | account_383 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_386 | INCOMPLETE | VERIFICATION | account_service | account_384 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_387 | INCOMPLETE | VERIFICATION | account_service | account_385 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_388 | INCOMPLETE | VERIFICATION | account_service | account_386 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_389 | INCOMPLETE | VERIFICATION | account_service | account_387 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_390 | INCOMPLETE | VERIFICATION | account_service | account_388 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_391 | INCOMPLETE | VERIFICATION | account_service | account_389 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_392 | INCOMPLETE | VERIFICATION | account_service | account_390 | None | N/A (Proposed action) | 2026-04-09T12:00:00Z |
| case_393 | INCOMPLETE | VERIFICATION | account_service | account_391 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_393 | INCOMPLETE | VERIFICATION | security_service | audit_record_7330 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_394 | INCOMPLETE | FINDING | search_service | search_195 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_394 | INCOMPLETE | REMEDIATION | search_service | search_195 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_394 | INCOMPLETE | VERIFICATION | account_service | account_392 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_394 | INCOMPLETE | VERIFICATION | search_service | search_195 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_395 | INCOMPLETE | VERIFICATION | account_service | account_393 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_395 | INCOMPLETE | VERIFICATION | security_service | audit_record_2839 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | FINDING | export_service | export_4664 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | FINDING | search_service | search_7293 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | REMEDIATION | export_service | export_4664 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | REMEDIATION | search_service | search_7293 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | VERIFICATION | account_service | account_394 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | VERIFICATION | export_service | export_4664 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_396 | INCOMPLETE | VERIFICATION | search_service | search_7293 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | FINDING | search_service | search_3232 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | FINDING | integration_service | data_flow_626 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | REMEDIATION | integration_service | data_flow_626 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | REMEDIATION | search_service | search_3232 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | VERIFICATION | account_service | account_395 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | VERIFICATION | search_service | search_3232 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_397 | INCOMPLETE | VERIFICATION | integration_service | data_flow_626 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_398 | INCOMPLETE | VERIFICATION | account_service | account_396 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_398 | INCOMPLETE | VERIFICATION | security_service | audit_record_7361 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_399 | INCOMPLETE | FINDING | backup_service | backup_2642 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_399 | INCOMPLETE | REMEDIATION | backup_service | backup_2642 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_399 | INCOMPLETE | VERIFICATION | account_service | account_397 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_399 | INCOMPLETE | VERIFICATION | backup_service | backup_2642 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | FINDING | search_service | search_4649 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | FINDING | support_platform | support_4521 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | REMEDIATION | search_service | search_4649 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | REMEDIATION | support_platform | support_4521 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | VERIFICATION | account_service | account_398 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | VERIFICATION | search_service | search_4649 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_400 | INCOMPLETE | VERIFICATION | support_platform | support_4521 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_401 | INCOMPLETE | FINDING | analytics_platform | analytics_6872 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_401 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6872 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_401 | INCOMPLETE | VERIFICATION | account_service | account_399 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_401 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6872 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | FINDING | search_service | search_1338 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | FINDING | analytics_platform | analytics_5811 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | FINDING | support_platform | support_4290 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | FINDING | integration_service | data_flow_9411 | evidence_69 | Verified | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9411 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | REMEDIATION | search_service | search_1338 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | REMEDIATION | support_platform | support_4290 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_5811 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | VERIFICATION | account_service | account_400 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | VERIFICATION | search_service | search_1338 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | VERIFICATION | support_platform | support_4290 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_5811 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_402 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9411 | None | N/A (Proposed action) | 2026-04-04T11:00:00Z |
| case_403 | INCOMPLETE | VERIFICATION | account_service | account_401 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_403 | INCOMPLETE | VERIFICATION | security_service | audit_record_4733 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | FINDING | search_service | search_7022 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | FINDING | analytics_platform | analytics_1792 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | FINDING | support_platform | support_880 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | FINDING | integration_service | data_flow_8093 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8093 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | REMEDIATION | search_service | search_7022 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | REMEDIATION | support_platform | support_880 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1792 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | account_service | account_402 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | search_service | search_7022 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | security_service | audit_record_6099 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | support_platform | support_880 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1792 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_404 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8093 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | FINDING | account_service | account_5389 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | FINDING | search_service | search_1606 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | REMEDIATION | account_service | account_5389 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | REMEDIATION | search_service | search_1606 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | VERIFICATION | account_service | account_5389 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | VERIFICATION | search_service | search_1606 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_405 | INCOMPLETE | VERIFICATION | security_service | audit_record_4522 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | FINDING | search_service | search_2804 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | FINDING | support_platform | support_6047 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | REMEDIATION | search_service | search_2804 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | REMEDIATION | support_platform | support_6047 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | VERIFICATION | account_service | account_404 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | VERIFICATION | search_service | search_2804 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | VERIFICATION | security_service | audit_record_5455 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_406 | INCOMPLETE | VERIFICATION | support_platform | support_6047 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | FINDING | search_service | search_5146 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | FINDING | analytics_platform | analytics_1922 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | FINDING | support_platform | support_3802 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | FINDING | support_platform | support_6569 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | REMEDIATION | search_service | search_5146 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | REMEDIATION | support_platform | support_3802 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | REMEDIATION | support_platform | support_6569 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1922 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | account_service | account_405 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | search_service | search_5146 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | security_service | audit_record_6152 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | support_platform | support_3802 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | support_platform | support_6569 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_407 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1922 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_408 | INCOMPLETE | VERIFICATION | account_service | account_406 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_408 | INCOMPLETE | VERIFICATION | security_service | audit_record_4216 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_409 | INCOMPLETE | VERIFICATION | account_service | account_407 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_409 | INCOMPLETE | VERIFICATION | security_service | audit_record_2559 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | FINDING | search_service | search_9987 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | FINDING | integration_service | data_flow_8300 | evidence_38 | Verified | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8300 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | REMEDIATION | search_service | search_9987 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | VERIFICATION | account_service | account_408 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | VERIFICATION | search_service | search_9987 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | VERIFICATION | security_service | audit_record_896 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_410 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8300 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_411 | INCOMPLETE | VERIFICATION | account_service | account_409 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_411 | INCOMPLETE | VERIFICATION | security_service | audit_record_4330 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_412 | INCOMPLETE | VERIFICATION | account_service | account_410 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_412 | INCOMPLETE | VERIFICATION | security_service | audit_record_5637 | None | N/A (Proposed action) | 2026-03-30T10:00:00Z |
| case_413 | INCOMPLETE | FINDING | analytics_platform | analytics_4523 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_413 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_4523 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_413 | INCOMPLETE | VERIFICATION | account_service | account_411 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_413 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_4523 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_414 | INCOMPLETE | FINDING | support_platform | support_3768 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_414 | INCOMPLETE | REMEDIATION | support_platform | support_3768 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_414 | INCOMPLETE | VERIFICATION | account_service | account_5260 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_414 | INCOMPLETE | VERIFICATION | support_platform | support_3768 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | FINDING | search_service | search_3864 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | FINDING | analytics_platform | analytics_2102 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | FINDING | support_platform | support_1993 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | REMEDIATION | search_service | search_3864 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | REMEDIATION | support_platform | support_1993 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_2102 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | VERIFICATION | account_service | account_413 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | VERIFICATION | search_service | search_3864 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | VERIFICATION | support_platform | support_1993 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_415 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_2102 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_416 | INCOMPLETE | VERIFICATION | account_service | account_414 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_417 | INCOMPLETE | VERIFICATION | account_service | account_415 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_418 | INCOMPLETE | FINDING | support_platform | support_9464 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_418 | INCOMPLETE | REMEDIATION | support_platform | support_9464 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_418 | INCOMPLETE | VERIFICATION | account_service | account_416 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_418 | INCOMPLETE | VERIFICATION | security_service | audit_record_5493 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_418 | INCOMPLETE | VERIFICATION | support_platform | support_9464 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | FINDING | search_service | search_5797 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | FINDING | support_platform | support_2944 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | REMEDIATION | search_service | search_5797 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | REMEDIATION | support_platform | support_2944 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | VERIFICATION | account_service | account_417 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | VERIFICATION | search_service | search_5797 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_419 | INCOMPLETE | VERIFICATION | support_platform | support_2944 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_420 | INCOMPLETE | FINDING | export_service | export_389 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_420 | INCOMPLETE | REMEDIATION | export_service | export_389 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_420 | INCOMPLETE | VERIFICATION | account_service | account_7606 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_420 | INCOMPLETE | VERIFICATION | export_service | export_389 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_421 | INCOMPLETE | FINDING | integration_service | data_flow_4750 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_421 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4750 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_421 | INCOMPLETE | VERIFICATION | account_service | account_8482 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_421 | INCOMPLETE | VERIFICATION | security_service | audit_record_1256 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_421 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4750 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_422 | INCOMPLETE | FINDING | integration_service | data_flow_8871 | evidence_39 | Verified | 2026-03-25T09:00:00Z |
| case_422 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8871 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_422 | INCOMPLETE | VERIFICATION | account_service | account_420 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_422 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8871 | None | N/A (Proposed action) | 2026-03-25T09:00:00Z |
| case_423 | INCOMPLETE | VERIFICATION | account_service | account_421 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_423 | INCOMPLETE | VERIFICATION | security_service | audit_record_8082 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_424 | INCOMPLETE | VERIFICATION | account_service | account_422 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_424 | INCOMPLETE | VERIFICATION | security_service | audit_record_1474 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | FINDING | search_service | search_9072 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | FINDING | analytics_platform | analytics_891 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | FINDING | support_platform | support_1662 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | FINDING | integration_service | data_flow_7718 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7718 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | REMEDIATION | search_service | search_9072 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | REMEDIATION | support_platform | support_1662 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_891 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | VERIFICATION | account_service | account_423 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | VERIFICATION | search_service | search_9072 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | VERIFICATION | support_platform | support_1662 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_891 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_425 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7718 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | FINDING | search_service | search_2635 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | FINDING | support_platform | support_9212 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | REMEDIATION | search_service | search_2635 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | REMEDIATION | support_platform | support_9212 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | VERIFICATION | account_service | account_424 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | VERIFICATION | search_service | search_2635 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_426 | INCOMPLETE | VERIFICATION | support_platform | support_9212 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_427 | INCOMPLETE | VERIFICATION | account_service | account_425 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_427 | INCOMPLETE | VERIFICATION | security_service | audit_record_999 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | FINDING | search_service | search_2625 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | FINDING | integration_service | data_flow_2107 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2107 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | REMEDIATION | search_service | search_2625 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | VERIFICATION | account_service | account_426 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | VERIFICATION | search_service | search_2625 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_428 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2107 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | FINDING | account_service | account_4204 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | FINDING | search_service | search_1449 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | REMEDIATION | account_service | account_4204 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | REMEDIATION | search_service | search_1449 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | VERIFICATION | account_service | account_4204 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_429 | INCOMPLETE | VERIFICATION | search_service | search_1449 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_430 | INCOMPLETE | VERIFICATION | account_service | account_428 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_430 | INCOMPLETE | VERIFICATION | security_service | audit_record_5292 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | FINDING | search_service | search_7427 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | FINDING | support_platform | support_3615 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | REMEDIATION | search_service | search_7427 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | REMEDIATION | support_platform | support_3615 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | VERIFICATION | account_service | account_429 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | VERIFICATION | search_service | search_7427 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_431 | INCOMPLETE | VERIFICATION | support_platform | support_3615 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | FINDING | export_service | export_9343 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | FINDING | search_service | search_3844 | evidence_68 | Verified | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | REMEDIATION | export_service | export_9343 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | REMEDIATION | search_service | search_3844 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | VERIFICATION | account_service | account_430 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | VERIFICATION | export_service | export_9343 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_432 | INCOMPLETE | VERIFICATION | search_service | search_3844 | None | N/A (Proposed action) | 2026-03-20T08:00:00Z |
| case_433 | INCOMPLETE | FINDING | search_service | search_9100 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | FINDING | integration_service | data_flow_1283 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1283 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | REMEDIATION | search_service | search_9100 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | VERIFICATION | account_service | account_5817 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | VERIFICATION | search_service | search_9100 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | VERIFICATION | security_service | audit_record_6665 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_433 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1283 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | FINDING | search_service | search_5626 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | FINDING | analytics_platform | analytics_2354 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | FINDING | support_platform | support_3364 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | FINDING | integration_service | data_flow_9854 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9854 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | REMEDIATION | search_service | search_5626 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | REMEDIATION | support_platform | support_3364 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_2354 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | account_service | account_4813 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | search_service | search_5626 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | security_service | audit_record_4043 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | support_platform | support_3364 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_2354 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_434 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9854 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_435 | INCOMPLETE | FINDING | backup_service | backup_5237 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_435 | INCOMPLETE | REMEDIATION | backup_service | backup_5237 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_435 | INCOMPLETE | VERIFICATION | account_service | account_9194 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_435 | INCOMPLETE | VERIFICATION | security_service | audit_record_9695 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_435 | INCOMPLETE | VERIFICATION | backup_service | backup_5237 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | FINDING | search_service | search_6599 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | FINDING | support_platform | support_165 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | REMEDIATION | search_service | search_6599 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | REMEDIATION | support_platform | support_165 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | VERIFICATION | account_service | account_3078 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | VERIFICATION | search_service | search_6599 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | VERIFICATION | security_service | audit_record_2748 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_436 | INCOMPLETE | VERIFICATION | support_platform | support_165 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_437 | INCOMPLETE | FINDING | analytics_platform | analytics_6172 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_437 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6172 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_437 | INCOMPLETE | VERIFICATION | account_service | account_022 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_437 | INCOMPLETE | VERIFICATION | security_service | audit_record_6846 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_437 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6172 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | FINDING | search_service | search_2052 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | FINDING | analytics_platform | analytics_6528 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | FINDING | support_platform | support_6688 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | FINDING | integration_service | data_flow_3226 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3226 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | REMEDIATION | search_service | search_2052 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | REMEDIATION | support_platform | support_6688 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_6528 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | account_service | account_1680 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | search_service | search_2052 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | security_service | audit_record_1366 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | support_platform | support_6688 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_6528 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_438 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3226 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_439 | INCOMPLETE | FINDING | account_service | account_3002 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_439 | INCOMPLETE | REMEDIATION | account_service | account_3002 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_439 | INCOMPLETE | VERIFICATION | account_service | account_3002 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_439 | INCOMPLETE | VERIFICATION | security_service | audit_record_1149 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | FINDING | search_service | search_2922 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | FINDING | integration_service | data_flow_5967 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5967 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | REMEDIATION | search_service | search_2922 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | VERIFICATION | account_service | account_790 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | VERIFICATION | search_service | search_2922 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | VERIFICATION | security_service | audit_record_5488 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_440 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5967 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | FINDING | account_service | account_1538 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | FINDING | search_service | search_3058 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | REMEDIATION | account_service | account_1538 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | REMEDIATION | search_service | search_3058 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | VERIFICATION | account_service | account_1538 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | VERIFICATION | search_service | search_3058 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_441 | INCOMPLETE | VERIFICATION | security_service | audit_record_7313 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | FINDING | search_service | search_1194 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | FINDING | support_platform | support_4123 | evidence_41 | Verified | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | REMEDIATION | search_service | search_1194 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | REMEDIATION | support_platform | support_4123 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | VERIFICATION | account_service | account_1897 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | VERIFICATION | search_service | search_1194 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | VERIFICATION | security_service | audit_record_4839 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_442 | INCOMPLETE | VERIFICATION | support_platform | support_4123 | None | N/A (Proposed action) | 2026-03-15T07:00:00Z |
| case_443 | INCOMPLETE | FINDING | search_service | search_4925 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | FINDING | support_platform | support_8341 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | REMEDIATION | search_service | search_4925 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | REMEDIATION | support_platform | support_8341 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | VERIFICATION | account_service | account_441 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | VERIFICATION | search_service | search_4925 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_443 | INCOMPLETE | VERIFICATION | support_platform | support_8341 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | FINDING | export_service | export_4293 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | FINDING | search_service | search_3250 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | REMEDIATION | export_service | export_4293 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | REMEDIATION | search_service | search_3250 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | VERIFICATION | account_service | account_442 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | VERIFICATION | export_service | export_4293 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_444 | INCOMPLETE | VERIFICATION | search_service | search_3250 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | FINDING | search_service | search_2886 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | FINDING | integration_service | data_flow_7584 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7584 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | REMEDIATION | search_service | search_2886 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | VERIFICATION | account_service | account_443 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | VERIFICATION | search_service | search_2886 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_445 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7584 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | FINDING | search_service | search_3780 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | FINDING | analytics_platform | analytics_195 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | FINDING | support_platform | support_9938 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | FINDING | integration_service | data_flow_1068 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1068 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | REMEDIATION | search_service | search_3780 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | REMEDIATION | support_platform | support_9938 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_195 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | VERIFICATION | account_service | account_444 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | VERIFICATION | search_service | search_3780 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | VERIFICATION | support_platform | support_9938 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_195 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_446 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1068 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_447 | INCOMPLETE | FINDING | backup_service | backup_5192 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_447 | INCOMPLETE | REMEDIATION | backup_service | backup_5192 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_447 | INCOMPLETE | VERIFICATION | account_service | account_445 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_447 | INCOMPLETE | VERIFICATION | backup_service | backup_5192 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_448 | INCOMPLETE | VERIFICATION | account_service | account_446 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_448 | INCOMPLETE | VERIFICATION | security_service | audit_record_753 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | FINDING | search_service | search_1685 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | FINDING | analytics_platform | analytics_1138 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | REMEDIATION | search_service | search_1685 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1138 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | VERIFICATION | account_service | account_447 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | VERIFICATION | search_service | search_1685 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_449 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1138 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | FINDING | search_service | search_2365 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | FINDING | analytics_platform | analytics_8202 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | FINDING | support_platform | support_7245 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | FINDING | integration_service | data_flow_9755 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9755 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | REMEDIATION | search_service | search_2365 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | REMEDIATION | support_platform | support_7245 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8202 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | VERIFICATION | account_service | account_448 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | VERIFICATION | search_service | search_2365 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | VERIFICATION | support_platform | support_7245 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8202 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_450 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9755 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | FINDING | search_service | search_360 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | FINDING | integration_service | data_flow_7263 | evidence_66 | Verified | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | REMEDIATION | integration_service | data_flow_7263 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | REMEDIATION | search_service | search_360 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | VERIFICATION | account_service | account_449 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | VERIFICATION | search_service | search_360 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_451 | INCOMPLETE | VERIFICATION | integration_service | data_flow_7263 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_452 | INCOMPLETE | VERIFICATION | account_service | account_450 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_452 | INCOMPLETE | VERIFICATION | security_service | audit_record_8608 | None | N/A (Proposed action) | 2026-03-10T06:00:00Z |
| case_453 | INCOMPLETE | FINDING | account_service | account_3183 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | FINDING | search_service | search_1317 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | REMEDIATION | account_service | account_3183 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | REMEDIATION | search_service | search_1317 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | VERIFICATION | account_service | account_3183 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | VERIFICATION | search_service | search_1317 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_453 | INCOMPLETE | VERIFICATION | security_service | audit_record_3600 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_454 | INCOMPLETE | FINDING | search_service | search_892 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_454 | INCOMPLETE | REMEDIATION | search_service | search_892 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_454 | INCOMPLETE | VERIFICATION | account_service | account_452 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_454 | INCOMPLETE | VERIFICATION | search_service | search_892 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_454 | INCOMPLETE | VERIFICATION | security_service | audit_record_2775 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | FINDING | search_service | search_887 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | FINDING | support_platform | support_2055 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | REMEDIATION | search_service | search_887 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | REMEDIATION | support_platform | support_2055 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | VERIFICATION | account_service | account_453 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | VERIFICATION | search_service | search_887 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | VERIFICATION | security_service | audit_record_2788 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_455 | INCOMPLETE | VERIFICATION | support_platform | support_2055 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_456 | INCOMPLETE | VERIFICATION | account_service | account_454 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_456 | INCOMPLETE | VERIFICATION | security_service | audit_record_8176 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_457 | INCOMPLETE | VERIFICATION | account_service | account_455 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_457 | INCOMPLETE | VERIFICATION | security_service | audit_record_1171 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_458 | INCOMPLETE | VERIFICATION | account_service | account_456 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_458 | INCOMPLETE | VERIFICATION | security_service | audit_record_6750 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_459 | INCOMPLETE | FINDING | backup_service | backup_1140 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_459 | INCOMPLETE | REMEDIATION | backup_service | backup_1140 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_459 | INCOMPLETE | VERIFICATION | account_service | account_457 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_459 | INCOMPLETE | VERIFICATION | security_service | audit_record_6171 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_459 | INCOMPLETE | VERIFICATION | backup_service | backup_1140 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_460 | INCOMPLETE | FINDING | support_platform | support_4146 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_460 | INCOMPLETE | REMEDIATION | support_platform | support_4146 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_460 | INCOMPLETE | VERIFICATION | account_service | account_458 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_460 | INCOMPLETE | VERIFICATION | security_service | audit_record_1369 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_460 | INCOMPLETE | VERIFICATION | support_platform | support_4146 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | FINDING | search_service | search_9014 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | FINDING | analytics_platform | analytics_8403 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | FINDING | support_platform | support_3901 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | FINDING | integration_service | data_flow_4612 | evidence_43 | Verified | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | REMEDIATION | integration_service | data_flow_4612 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | REMEDIATION | search_service | search_9014 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | REMEDIATION | support_platform | support_3901 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8403 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | account_service | account_459 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | search_service | search_9014 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | security_service | audit_record_3883 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | support_platform | support_3901 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8403 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_461 | INCOMPLETE | VERIFICATION | integration_service | data_flow_4612 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_462 | INCOMPLETE | VERIFICATION | account_service | account_460 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_462 | INCOMPLETE | VERIFICATION | security_service | audit_record_641 | None | N/A (Proposed action) | 2026-03-05T12:00:00Z |
| case_463 | INCOMPLETE | FINDING | support_platform | support_2659 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | FINDING | integration_service | data_flow_8024 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | FINDING | backup_service | backup_2005 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8024 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | REMEDIATION | backup_service | backup_2005 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | REMEDIATION | support_platform | support_2659 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | VERIFICATION | account_service | account_461 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | VERIFICATION | security_service | audit_record_8444 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | VERIFICATION | support_platform | support_2659 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8024 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_463 | INCOMPLETE | VERIFICATION | backup_service | backup_2005 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | FINDING | support_platform | support_5586 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | FINDING | integration_service | data_flow_1344 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | FINDING | backup_service | backup_7400 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | REMEDIATION | integration_service | data_flow_1344 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | REMEDIATION | backup_service | backup_7400 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | REMEDIATION | support_platform | support_5586 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | VERIFICATION | account_service | account_462 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | VERIFICATION | security_service | audit_record_5183 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | VERIFICATION | support_platform | support_5586 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | VERIFICATION | integration_service | data_flow_1344 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_464 | INCOMPLETE | VERIFICATION | backup_service | backup_7400 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | FINDING | account_service | account_3653 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | FINDING | search_service | search_728 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | REMEDIATION | account_service | account_3653 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | REMEDIATION | search_service | search_728 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | VERIFICATION | account_service | account_3653 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_465 | INCOMPLETE | VERIFICATION | search_service | search_728 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_466 | INCOMPLETE | FINDING | search_service | search_8417 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_466 | INCOMPLETE | REMEDIATION | search_service | search_8417 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_466 | INCOMPLETE | VERIFICATION | account_service | account_464 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_466 | INCOMPLETE | VERIFICATION | search_service | search_8417 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_467 | INCOMPLETE | VERIFICATION | account_service | account_465 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_467 | INCOMPLETE | VERIFICATION | security_service | audit_record_8992 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | FINDING | export_service | export_9399 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | FINDING | search_service | search_9827 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | REMEDIATION | export_service | export_9399 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | REMEDIATION | search_service | search_9827 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | VERIFICATION | account_service | account_466 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | VERIFICATION | export_service | export_9399 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_468 | INCOMPLETE | VERIFICATION | search_service | search_9827 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | FINDING | search_service | search_8450 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | FINDING | integration_service | data_flow_8730 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8730 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | REMEDIATION | search_service | search_8450 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | VERIFICATION | account_service | account_467 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | VERIFICATION | search_service | search_8450 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_469 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8730 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_470 | INCOMPLETE | VERIFICATION | account_service | account_468 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_470 | INCOMPLETE | VERIFICATION | security_service | audit_record_2706 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_471 | INCOMPLETE | FINDING | backup_service | backup_7543 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_471 | INCOMPLETE | REMEDIATION | backup_service | backup_7543 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_471 | INCOMPLETE | VERIFICATION | account_service | account_469 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_471 | INCOMPLETE | VERIFICATION | backup_service | backup_7543 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | FINDING | search_service | search_9152 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | FINDING | support_platform | support_6987 | evidence_65 | Verified | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | REMEDIATION | search_service | search_9152 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | REMEDIATION | support_platform | support_6987 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | VERIFICATION | account_service | account_470 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | VERIFICATION | search_service | search_9152 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_472 | INCOMPLETE | VERIFICATION | support_platform | support_6987 | None | N/A (Proposed action) | 2026-02-28T11:00:00Z |
| case_473 | INCOMPLETE | FINDING | search_service | search_7375 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | FINDING | analytics_platform | analytics_8577 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | REMEDIATION | search_service | search_7375 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8577 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | VERIFICATION | account_service | account_471 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | VERIFICATION | search_service | search_7375 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | VERIFICATION | security_service | audit_record_519 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_473 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8577 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | FINDING | search_service | search_9925 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | FINDING | support_platform | support_4509 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | REMEDIATION | search_service | search_9925 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | REMEDIATION | support_platform | support_4509 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | VERIFICATION | account_service | account_472 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | VERIFICATION | search_service | search_9925 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | VERIFICATION | security_service | audit_record_712 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_474 | INCOMPLETE | VERIFICATION | support_platform | support_4509 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_475 | COMPLETE | VERIFICATION | account_service | account_3205 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_475 | COMPLETE | VERIFICATION | security_service | audit_record_5667 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | FINDING | search_service | search_3759 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | FINDING | integration_service | data_flow_8899 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8899 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | REMEDIATION | search_service | search_3759 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | VERIFICATION | account_service | account_474 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | VERIFICATION | search_service | search_3759 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | VERIFICATION | security_service | audit_record_4197 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_476 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8899 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_477 | INCOMPLETE | FINDING | search_service | search_5052 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_477 | INCOMPLETE | REMEDIATION | search_service | search_5052 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_477 | INCOMPLETE | VERIFICATION | account_service | account_3119 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_477 | INCOMPLETE | VERIFICATION | search_service | search_5052 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_477 | INCOMPLETE | VERIFICATION | security_service | audit_record_6405 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | FINDING | search_service | search_5412 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | FINDING | support_platform | support_3824 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | REMEDIATION | search_service | search_5412 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | REMEDIATION | support_platform | support_3824 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | VERIFICATION | account_service | account_476 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | VERIFICATION | search_service | search_5412 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | VERIFICATION | security_service | audit_record_8754 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_478 | INCOMPLETE | VERIFICATION | support_platform | support_3824 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_479 | INCOMPLETE | FINDING | support_platform | support_4665 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_479 | INCOMPLETE | REMEDIATION | support_platform | support_4665 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_479 | INCOMPLETE | VERIFICATION | account_service | account_477 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_479 | INCOMPLETE | VERIFICATION | support_platform | support_4665 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_479 | INCOMPLETE | VERIFICATION | security_service | audit_record_5745 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | FINDING | support_platform | support_5854 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | FINDING | integration_service | data_flow_2893 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | FINDING | backup_service | backup_7706 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2893 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | REMEDIATION | backup_service | backup_7706 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | REMEDIATION | support_platform | support_5854 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | VERIFICATION | account_service | account_478 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | VERIFICATION | security_service | audit_record_7742 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | VERIFICATION | support_platform | support_5854 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2893 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_480 | INCOMPLETE | VERIFICATION | backup_service | backup_7706 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | FINDING | search_service | search_8587 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | FINDING | integration_service | data_flow_173 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | REMEDIATION | integration_service | data_flow_173 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | REMEDIATION | search_service | search_8587 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | VERIFICATION | account_service | account_479 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | VERIFICATION | search_service | search_8587 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | VERIFICATION | security_service | audit_record_9025 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_481 | INCOMPLETE | VERIFICATION | integration_service | data_flow_173 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | FINDING | search_service | search_3728 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | FINDING | integration_service | data_flow_8519 | evidence_45 | Verified | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | REMEDIATION | integration_service | data_flow_8519 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | REMEDIATION | search_service | search_3728 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | VERIFICATION | account_service | account_480 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | VERIFICATION | search_service | search_3728 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | VERIFICATION | security_service | audit_record_2180 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_482 | INCOMPLETE | VERIFICATION | integration_service | data_flow_8519 | None | N/A (Proposed action) | 2026-02-23T10:00:00Z |
| case_483 | INCOMPLETE | FINDING | search_service | search_1613 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | FINDING | support_platform | support_4364 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | FINDING | integration_service | data_flow_3669 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | FINDING | backup_service | backup_4600 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3669 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | REMEDIATION | backup_service | backup_4600 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | REMEDIATION | search_service | search_1613 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | REMEDIATION | support_platform | support_4364 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | VERIFICATION | account_service | account_481 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | VERIFICATION | search_service | search_1613 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | VERIFICATION | support_platform | support_4364 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3669 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_483 | INCOMPLETE | VERIFICATION | backup_service | backup_4600 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_484 | INCOMPLETE | FINDING | support_platform | support_7973 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_484 | INCOMPLETE | REMEDIATION | support_platform | support_7973 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_484 | INCOMPLETE | VERIFICATION | account_service | account_482 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_484 | INCOMPLETE | VERIFICATION | support_platform | support_7973 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | FINDING | search_service | search_3582 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | FINDING | analytics_platform | analytics_1981 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | REMEDIATION | search_service | search_3582 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1981 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | VERIFICATION | account_service | account_483 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | VERIFICATION | search_service | search_3582 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_485 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1981 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_486 | INCOMPLETE | FINDING | account_service | account_9031 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_486 | INCOMPLETE | REMEDIATION | account_service | account_9031 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_486 | INCOMPLETE | VERIFICATION | account_service | account_9031 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_486 | INCOMPLETE | VERIFICATION | security_service | audit_record_5451 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | FINDING | account_service | account_5293 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | FINDING | search_service | search_901 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | FINDING | analytics_platform | analytics_7818 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | FINDING | support_platform | support_5361 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | REMEDIATION | account_service | account_5293 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | REMEDIATION | search_service | search_901 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | REMEDIATION | support_platform | support_5361 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_7818 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | VERIFICATION | account_service | account_5293 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | VERIFICATION | search_service | search_901 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | VERIFICATION | support_platform | support_5361 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_487 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_7818 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | FINDING | search_service | search_4216 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | FINDING | integration_service | data_flow_3755 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | REMEDIATION | integration_service | data_flow_3755 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | REMEDIATION | search_service | search_4216 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | VERIFICATION | account_service | account_486 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | VERIFICATION | search_service | search_4216 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_488 | INCOMPLETE | VERIFICATION | integration_service | data_flow_3755 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | FINDING | account_service | account_6654 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | FINDING | search_service | search_3426 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | REMEDIATION | account_service | account_6654 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | REMEDIATION | search_service | search_3426 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | VERIFICATION | account_service | account_6654 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_489 | INCOMPLETE | VERIFICATION | search_service | search_3426 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | FINDING | search_service | search_9931 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | FINDING | support_platform | support_4247 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | REMEDIATION | search_service | search_9931 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | REMEDIATION | support_platform | support_4247 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | VERIFICATION | account_service | account_488 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | VERIFICATION | search_service | search_9931 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_490 | INCOMPLETE | VERIFICATION | support_platform | support_4247 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_491 | INCOMPLETE | FINDING | account_service | account_7455 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_491 | INCOMPLETE | REMEDIATION | account_service | account_7455 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_491 | INCOMPLETE | VERIFICATION | account_service | account_7455 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_491 | INCOMPLETE | VERIFICATION | security_service | audit_record_7073 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | FINDING | export_service | export_6406 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | FINDING | search_service | search_9733 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | FINDING | analytics_platform | analytics_1575 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | FINDING | support_platform | support_6737 | evidence_64 | Verified | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | REMEDIATION | export_service | export_6406 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | REMEDIATION | search_service | search_9733 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | REMEDIATION | support_platform | support_6737 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_1575 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | VERIFICATION | account_service | account_490 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | VERIFICATION | export_service | export_6406 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | VERIFICATION | search_service | search_9733 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | VERIFICATION | support_platform | support_6737 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_492 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_1575 | None | N/A (Proposed action) | 2026-02-18T09:00:00Z |
| case_493 | INCOMPLETE | VERIFICATION | account_service | account_491 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_493 | INCOMPLETE | VERIFICATION | security_service | audit_record_730 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_494 | INCOMPLETE | VERIFICATION | account_service | account_492 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_494 | INCOMPLETE | VERIFICATION | security_service | audit_record_1112 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_495 | INCOMPLETE | FINDING | backup_service | backup_5061 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_495 | INCOMPLETE | REMEDIATION | backup_service | backup_5061 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_495 | INCOMPLETE | VERIFICATION | account_service | account_493 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_495 | INCOMPLETE | VERIFICATION | backup_service | backup_5061 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | FINDING | search_service | search_3169 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | FINDING | support_platform | support_6391 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | REMEDIATION | search_service | search_3169 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | REMEDIATION | support_platform | support_6391 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | VERIFICATION | account_service | account_494 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | VERIFICATION | search_service | search_3169 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_496 | INCOMPLETE | VERIFICATION | support_platform | support_6391 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_497 | INCOMPLETE | VERIFICATION | account_service | account_495 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_497 | INCOMPLETE | VERIFICATION | security_service | audit_record_9796 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | FINDING | search_service | search_6093 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | FINDING | support_platform | support_9075 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | REMEDIATION | search_service | search_6093 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | REMEDIATION | support_platform | support_9075 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | VERIFICATION | account_service | account_496 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | VERIFICATION | search_service | search_6093 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_498 | INCOMPLETE | VERIFICATION | support_platform | support_9075 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_499 | INCOMPLETE | FINDING | account_service | account_3626 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_499 | INCOMPLETE | REMEDIATION | account_service | account_3626 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_499 | INCOMPLETE | VERIFICATION | account_service | account_3626 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | FINDING | search_service | search_6092 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | FINDING | integration_service | data_flow_006 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | REMEDIATION | integration_service | data_flow_006 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | REMEDIATION | search_service | search_6092 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | VERIFICATION | account_service | account_498 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | VERIFICATION | search_service | search_6092 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_500 | INCOMPLETE | VERIFICATION | integration_service | data_flow_006 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | FINDING | account_service | account_634 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | FINDING | search_service | search_2799 | evidence_63 | Verified | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | REMEDIATION | account_service | account_634 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | REMEDIATION | search_service | search_2799 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | VERIFICATION | account_service | account_634 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_501 | INCOMPLETE | VERIFICATION | search_service | search_2799 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_502 | INCOMPLETE | VERIFICATION | account_service | account_500 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_502 | INCOMPLETE | VERIFICATION | security_service | audit_record_5238 | None | N/A (Proposed action) | 2026-02-13T08:00:00Z |
| case_503 | INCOMPLETE | FINDING | support_platform | support_2295 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_503 | INCOMPLETE | REMEDIATION | support_platform | support_2295 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_503 | INCOMPLETE | VERIFICATION | account_service | account_501 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_503 | INCOMPLETE | VERIFICATION | security_service | audit_record_5454 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_503 | INCOMPLETE | VERIFICATION | support_platform | support_2295 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_504 | INCOMPLETE | FINDING | export_service | export_3120 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_504 | INCOMPLETE | REMEDIATION | export_service | export_3120 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_504 | INCOMPLETE | VERIFICATION | account_service | account_502 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_504 | INCOMPLETE | VERIFICATION | export_service | export_3120 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_504 | INCOMPLETE | VERIFICATION | security_service | audit_record_3733 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | FINDING | search_service | search_2591 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | FINDING | integration_service | data_flow_5281 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | REMEDIATION | integration_service | data_flow_5281 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | REMEDIATION | search_service | search_2591 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | VERIFICATION | account_service | account_503 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | VERIFICATION | search_service | search_2591 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | VERIFICATION | security_service | audit_record_3441 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_505 | INCOMPLETE | VERIFICATION | integration_service | data_flow_5281 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_506 | INCOMPLETE | VERIFICATION | account_service | account_504 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_506 | INCOMPLETE | VERIFICATION | security_service | audit_record_1361 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_507 | INCOMPLETE | FINDING | backup_service | backup_369 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_507 | INCOMPLETE | REMEDIATION | backup_service | backup_369 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_507 | INCOMPLETE | VERIFICATION | account_service | account_505 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_507 | INCOMPLETE | VERIFICATION | security_service | audit_record_7627 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_507 | INCOMPLETE | VERIFICATION | backup_service | backup_369 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_508 | INCOMPLETE | FINDING | support_platform | support_2691 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_508 | INCOMPLETE | REMEDIATION | support_platform | support_2691 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_508 | INCOMPLETE | VERIFICATION | account_service | account_506 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_508 | INCOMPLETE | VERIFICATION | security_service | audit_record_8154 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_508 | INCOMPLETE | VERIFICATION | support_platform | support_2691 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | FINDING | search_service | search_6246 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | FINDING | analytics_platform | analytics_784 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | REMEDIATION | search_service | search_6246 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_784 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | VERIFICATION | account_service | account_507 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | VERIFICATION | search_service | search_6246 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | VERIFICATION | security_service | audit_record_2323 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_509 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_784 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | FINDING | search_service | search_6147 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | FINDING | support_platform | support_9648 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | REMEDIATION | search_service | search_6147 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | REMEDIATION | support_platform | support_9648 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | VERIFICATION | account_service | account_508 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | VERIFICATION | search_service | search_6147 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | VERIFICATION | security_service | audit_record_4266 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_510 | INCOMPLETE | VERIFICATION | support_platform | support_9648 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_511 | INCOMPLETE | FINDING | account_service | account_1035 | evidence_47 | Verified | 2026-02-08T07:00:00Z |
| case_511 | INCOMPLETE | REMEDIATION | account_service | account_1035 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_511 | INCOMPLETE | VERIFICATION | account_service | account_1035 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_511 | INCOMPLETE | VERIFICATION | security_service | audit_record_4883 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_512 | INCOMPLETE | VERIFICATION | account_service | account_510 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_512 | INCOMPLETE | VERIFICATION | security_service | audit_record_4219 | None | N/A (Proposed action) | 2026-02-08T07:00:00Z |
| case_513 | INCOMPLETE | FINDING | account_service | account_1334 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_513 | INCOMPLETE | REMEDIATION | account_service | account_1334 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_513 | INCOMPLETE | VERIFICATION | account_service | account_1334 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | FINDING | analytics_platform | analytics_9920 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | FINDING | support_platform | support_3982 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | FINDING | integration_service | data_flow_9556 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | REMEDIATION | integration_service | data_flow_9556 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | REMEDIATION | support_platform | support_3982 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_9920 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | VERIFICATION | account_service | account_512 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | VERIFICATION | support_platform | support_3982 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_9920 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_514 | INCOMPLETE | VERIFICATION | integration_service | data_flow_9556 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_515 | INCOMPLETE | FINDING | support_platform | support_4533 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_515 | INCOMPLETE | REMEDIATION | support_platform | support_4533 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_515 | INCOMPLETE | VERIFICATION | account_service | account_513 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_515 | INCOMPLETE | VERIFICATION | support_platform | support_4533 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_516 | COMPLETE | VERIFICATION | account_service | account_141 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_517 | INCOMPLETE | VERIFICATION | account_service | account_515 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_518 | INCOMPLETE | FINDING | search_service | search_6401 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_518 | INCOMPLETE | REMEDIATION | search_service | search_6401 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_518 | INCOMPLETE | VERIFICATION | account_service | account_516 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_518 | INCOMPLETE | VERIFICATION | search_service | search_6401 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_519 | INCOMPLETE | VERIFICATION | account_service | account_517 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_520 | INCOMPLETE | FINDING | support_platform | support_9251 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_520 | INCOMPLETE | REMEDIATION | support_platform | support_9251 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_520 | INCOMPLETE | VERIFICATION | account_service | account_518 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_520 | INCOMPLETE | VERIFICATION | support_platform | support_9251 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_521 | INCOMPLETE | VERIFICATION | account_service | account_519 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_522 | INCOMPLETE | FINDING | support_platform | support_8538 | evidence_48 | Verified | 2026-02-03T06:00:00Z |
| case_522 | INCOMPLETE | REMEDIATION | support_platform | support_8538 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_522 | INCOMPLETE | VERIFICATION | account_service | account_1096 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_522 | INCOMPLETE | VERIFICATION | support_platform | support_8538 | None | N/A (Proposed action) | 2026-02-03T06:00:00Z |
| case_523 | INCOMPLETE | FINDING | account_service | account_2424 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_523 | INCOMPLETE | FINDING | search_service | search_9075 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_523 | INCOMPLETE | REMEDIATION | account_service | account_2424 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_523 | INCOMPLETE | REMEDIATION | search_service | search_9075 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_523 | INCOMPLETE | VERIFICATION | account_service | account_2424 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_523 | INCOMPLETE | VERIFICATION | search_service | search_9075 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_524 | INCOMPLETE | VERIFICATION | account_service | account_522 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_524 | INCOMPLETE | VERIFICATION | security_service | audit_record_5429 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_525 | INCOMPLETE | FINDING | account_service | account_4974 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_525 | INCOMPLETE | REMEDIATION | account_service | account_4974 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_525 | INCOMPLETE | VERIFICATION | account_service | account_4974 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | FINDING | search_service | search_3879 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | FINDING | analytics_platform | analytics_131 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | FINDING | support_platform | support_1191 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | FINDING | integration_service | data_flow_2263 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | REMEDIATION | integration_service | data_flow_2263 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | REMEDIATION | search_service | search_3879 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | REMEDIATION | support_platform | support_1191 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_131 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | VERIFICATION | account_service | account_524 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | VERIFICATION | search_service | search_3879 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | VERIFICATION | support_platform | support_1191 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_131 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_526 | INCOMPLETE | VERIFICATION | integration_service | data_flow_2263 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | FINDING | search_service | search_1091 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | FINDING | analytics_platform | analytics_7468 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | FINDING | support_platform | support_3896 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | FINDING | support_platform | support_9832 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | REMEDIATION | search_service | search_1091 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | REMEDIATION | support_platform | support_3896 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | REMEDIATION | support_platform | support_9832 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_7468 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | VERIFICATION | account_service | account_525 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | VERIFICATION | search_service | search_1091 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | VERIFICATION | support_platform | support_3896 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | VERIFICATION | support_platform | support_9832 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_527 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_7468 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | FINDING | export_service | export_9388 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | FINDING | search_service | search_1429 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | FINDING | analytics_platform | analytics_8476 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | FINDING | support_platform | support_193 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | REMEDIATION | export_service | export_9388 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | REMEDIATION | search_service | search_1429 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | REMEDIATION | support_platform | support_193 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | REMEDIATION | analytics_platform | analytics_8476 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | VERIFICATION | account_service | account_526 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | VERIFICATION | export_service | export_9388 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | VERIFICATION | search_service | search_1429 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | VERIFICATION | support_platform | support_193 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_528 | INCOMPLETE | VERIFICATION | analytics_platform | analytics_8476 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | FINDING | search_service | search_3382 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | FINDING | integration_service | data_flow_6588 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6588 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | REMEDIATION | search_service | search_3382 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | VERIFICATION | account_service | account_527 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | VERIFICATION | search_service | search_3382 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_529 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6588 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_530 | INCOMPLETE | VERIFICATION | account_service | account_528 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_530 | INCOMPLETE | VERIFICATION | security_service | audit_record_2152 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_531 | INCOMPLETE | FINDING | backup_service | backup_3382 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_531 | INCOMPLETE | REMEDIATION | backup_service | backup_3382 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_531 | INCOMPLETE | VERIFICATION | account_service | account_529 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_531 | INCOMPLETE | VERIFICATION | backup_service | backup_3382 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | FINDING | support_platform | support_7724 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | FINDING | integration_service | data_flow_6987 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | FINDING | backup_service | backup_6344 | evidence_62 | Verified | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | REMEDIATION | integration_service | data_flow_6987 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | REMEDIATION | backup_service | backup_6344 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | REMEDIATION | support_platform | support_7724 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | VERIFICATION | account_service | account_530 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | VERIFICATION | security_service | audit_record_4828 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | VERIFICATION | support_platform | support_7724 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | VERIFICATION | integration_service | data_flow_6987 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_532 | INCOMPLETE | VERIFICATION | backup_service | backup_6344 | None | N/A (Proposed action) | 2026-01-29T12:00:00Z |
| case_533 | NOT_APPLICABLE | N/A | N/A | N/A | N/A | Verified (Non-deletion request) | 2026-10-01T12:00:00Z |
| case_534 | INCOMPLETE | VERIFICATION | account_service | account_532 | None | N/A (Proposed action) | 2026-09-30T12:00:00Z |
| case_535 | NOT_APPLICABLE | N/A | N/A | N/A | N/A | Verified (Non-deletion request) | 2026-09-29T12:00:00Z |
| case_536 | INCOMPLETE | VERIFICATION | account_service | account_534 | None | N/A (Proposed action) | 2026-09-28T12:00:00Z |
| case_537 | NOT_APPLICABLE | N/A | N/A | N/A | N/A | Verified (Non-deletion request) | 2026-09-27T12:00:00Z |
| case_538 | INCOMPLETE | VERIFICATION | account_service | account_536 | None | N/A (Proposed action) | 2026-09-26T12:00:00Z |
| case_539 | INCOMPLETE | VERIFICATION | account_service | account_537 | None | N/A (Proposed action) | 2026-09-25T12:00:00Z |
| case_540 | NOT_APPLICABLE | N/A | N/A | N/A | N/A | Verified (Non-deletion request) | 2026-09-24T12:00:00Z |
| case_541 | NOT_APPLICABLE | N/A | N/A | N/A | N/A | Verified (Non-deletion request) | 2026-09-23T12:00:00Z |
| case_542 | INCOMPLETE | VERIFICATION | account_service | account_540 | None | N/A (Proposed action) | 2026-09-22T12:00:00Z |
| case_543 | INCOMPLETE | VERIFICATION | account_service | account_543 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_543 | INCOMPLETE | VERIFICATION | security_service | audit_record_6244 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_543 | INCOMPLETE | VERIFICATION | identity_service | tombstone_205 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_544 | INCOMPLETE | FINDING | identity_service | tombstone_8648 | evidence_52 | Verified | 2026-09-20T12:00:00Z |
| case_544 | INCOMPLETE | REMEDIATION | identity_service | tombstone_8648 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_544 | INCOMPLETE | VERIFICATION | account_service | account_544 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_544 | INCOMPLETE | VERIFICATION | security_service | audit_record_1037 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_544 | INCOMPLETE | VERIFICATION | identity_service | tombstone_8648 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_545 | INCOMPLETE | VERIFICATION | account_service | account_545 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_545 | INCOMPLETE | VERIFICATION | security_service | audit_record_5041 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_545 | INCOMPLETE | VERIFICATION | identity_service | tombstone_946 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_546 | INCOMPLETE | VERIFICATION | account_service | account_546 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_546 | INCOMPLETE | VERIFICATION | security_service | audit_record_518 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_546 | INCOMPLETE | VERIFICATION | identity_service | tombstone_8095 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_547 | INCOMPLETE | VERIFICATION | account_service | account_547 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_547 | INCOMPLETE | VERIFICATION | security_service | audit_record_7352 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_547 | INCOMPLETE | VERIFICATION | identity_service | tombstone_8774 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_548 | INCOMPLETE | FINDING | identity_service | tombstone_3745 | evidence_52 | Verified | 2026-09-20T12:00:00Z |
| case_548 | INCOMPLETE | REMEDIATION | identity_service | tombstone_3745 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_548 | INCOMPLETE | VERIFICATION | account_service | account_548 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_548 | INCOMPLETE | VERIFICATION | security_service | audit_record_6970 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_548 | INCOMPLETE | VERIFICATION | identity_service | tombstone_3745 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_549 | INCOMPLETE | VERIFICATION | account_service | account_549 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_549 | INCOMPLETE | VERIFICATION | security_service | audit_record_1491 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_549 | INCOMPLETE | VERIFICATION | identity_service | tombstone_3963 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_550 | INCOMPLETE | FINDING | identity_service | tombstone_7389 | evidence_52 | Verified | 2026-09-20T12:00:00Z |
| case_550 | INCOMPLETE | REMEDIATION | identity_service | tombstone_7389 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_550 | INCOMPLETE | VERIFICATION | account_service | account_550 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_550 | INCOMPLETE | VERIFICATION | security_service | audit_record_3831 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
| case_550 | INCOMPLETE | VERIFICATION | identity_service | tombstone_7389 | None | N/A (Proposed action) | 2026-09-20T12:00:00Z |
