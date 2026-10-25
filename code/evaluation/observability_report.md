# Candidate Observability Report

This is an evaluation-only diagnostic. It may compare against public canonical
output, but none of its expected-resource data may enter prediction or training.

## Gate Result

- Pre-audit candidate recall: **103/111 (92.8%)**
- 100% observability gate: **FAIL**

## Classification Counts

| Classification | Case-resource pairs |
|---|---:|
| `ABSENT_GLOBALLY` | 3 |
| `POST_AUDIT_ONLY` | 5 |
| `PRE_AUDIT_LINKED_UNRETRIEVED` | 1 |
| `PRE_AUDIT_RETRIEVABLE` | 76 |
| `PRE_AUDIT_UNLINKED` | 26 |

## Blocked Canonical Resources

| Case | Resource | Audit cutoff | Classification | Later sources |
|---|---|---|---|---|
| `case_04` | `account_004` | `2026-09-07T10:20:00Z` | `ABSENT_GLOBALLY` | — |
| `case_09` | `audit_record_4902` | `2026-09-16T09:00:00Z` | `POST_AUDIT_ONLY` | evidence_06 |
| `case_18` | `audit_record_6645` | `2026-09-26T11:00:00Z` | `ABSENT_GLOBALLY` | — |
| `case_20` | `audit_record_5569` | `2026-09-26T11:00:00Z` | `ABSENT_GLOBALLY` | — |
| `case_23` | `audit_record_4128` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_24` | `audit_record_7095` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_29` | `audit_record_3954` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |
| `case_30` | `audit_record_1707` | `2026-09-15T12:00:00Z` | `POST_AUDIT_ONLY` | evidence_02 |

## All 111 Canonical Case-resource Pairs

`Earliest at` is the earliest manifest capture time or activity event time in
participant data. `Linked` means the production retriever found the resource or
the same local pre-audit context contains a resolved subject identifier.

| Case | Resource | Earliest at | Earliest source | Linked | Classification |
|---|---|---|---|---|---|
| `case_01` | `account_001` | `2026-08-20T16:41:43Z` | `activity_3342` | no | `PRE_AUDIT_UNLINKED` |
| `case_02` | `account_002` | `2026-08-22T07:30:03Z` | `activity_3376` | no | `PRE_AUDIT_UNLINKED` |
| `case_03` | `account_7566` | `2026-09-15T10:07:35Z` | `activity_3851` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_03` | `audit_record_2016` | `2026-09-26T10:38:56Z` | `evidence_94` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_03` | `analytics_9406` | `2026-09-15T10:31:16Z` | `activity_3852` | no | `PRE_AUDIT_UNLINKED` |
| `case_04` | `account_004` | — | — | no | `ABSENT_GLOBALLY` |
| `case_04` | `analytics_901` | `2026-08-27T08:47:41Z` | `activity_3463` | no | `PRE_AUDIT_UNLINKED` |
| `case_05` | `account_005` | `2026-08-28T09:11:01Z` | `activity_3482` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_06` | `search_001` | `2026-08-30T17:21:43Z` | `activity_3546` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_06` | `account_006` | `2026-08-30T17:08:20Z` | `activity_3545` | yes | `PRE_AUDIT_LINKED_UNRETRIEVED` |
| `case_07` | `support_001` | `2026-09-12T07:30:00Z` | `evidence_58` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_07` | `account_007` | `2026-09-01T19:28:39Z` | `activity_3590` | no | `PRE_AUDIT_UNLINKED` |
| `case_08` | `export_001` | `2026-08-31T13:49:22Z` | `activity_3555` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_08` | `account_008` | `2026-08-31T13:48:58Z` | `activity_3554` | no | `PRE_AUDIT_UNLINKED` |
| `case_09` | `backup_4978` | `2026-09-07T09:51:10Z` | `activity_3709` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_09` | `account_3960` | `2026-09-07T07:55:18Z` | `activity_3703` | no | `PRE_AUDIT_UNLINKED` |
| `case_09` | `audit_record_4902` | `2026-09-18T11:55:24Z` | `evidence_06` | no | `POST_AUDIT_ONLY` |
| `case_10` | `support_002` | `2026-09-02T10:09:01Z` | `activity_3596` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_10` | `account_010` | `2026-09-02T10:08:37Z` | `activity_3595` | no | `PRE_AUDIT_UNLINKED` |
| `case_11` | `search_052` | `2026-09-12T12:55:35Z` | `activity_3814` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_11` | `analytics_2034` | `2026-09-12T13:33:34Z` | `activity_3816` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_11` | `support_864` | `2026-09-12T13:14:05Z` | `activity_3815` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_11` | `data_flow_9522` | `2026-09-12T13:52:04Z` | `activity_3817` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_11` | `account_4248` | `2026-09-12T11:04:43Z` | `activity_3801` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_11` | `audit_record_9394` | `2026-10-01T12:00:00Z` | `evidence_03` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_12` | `analytics_9914` | `2026-08-25T12:53:51Z` | `activity_3435` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_12` | `account_9797` | `2026-08-25T11:07:59Z` | `activity_3432` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_12` | `audit_record_2945` | `2026-09-15T11:59:39Z` | `evidence_01` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_13` | `search_1308` | `2026-09-09T12:58:49Z` | `activity_3756` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_13` | `support_4218` | `2026-09-09T12:39:20Z` | `activity_3752` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_13` | `account_9335` | `2026-09-09T10:53:28Z` | `activity_3739` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_13` | `audit_record_4816` | `2026-10-01T12:00:00Z` | `evidence_03` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_14` | `backup_3870` | `2026-09-06T12:44:53Z` | `activity_3690` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_14` | `account_3677` | `2026-09-06T11:11:02Z` | `activity_3686` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_14` | `audit_record_987` | `2026-10-01T12:00:00Z` | `evidence_03` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_15` | `data_flow_9846` | `2026-08-07T08:00:00Z` | `evidence_14` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_15` | `account_4745` | `2026-08-22T11:05:18Z` | `activity_3382` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_15` | `audit_record_1596` | `2026-09-15T11:59:39Z` | `evidence_01` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_16` | `account_994` | `2026-09-01T08:50:41Z` | `activity_3571` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_16` | `search_1007` | `2026-09-01T11:00:03Z` | `activity_3580` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_16` | `audit_record_9528` | `2026-09-21T10:00:00Z` | `evidence_05` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_17` | `backup_3245` | `2026-08-22T12:42:12Z` | `activity_3385` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_17` | `account_4092` | `2026-08-22T11:14:20Z` | `activity_3383` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_17` | `audit_record_1797` | `2026-09-15T11:59:39Z` | `evidence_01` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_18` | `search_4013` | `2026-09-09T12:02:47Z` | `activity_3747` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_18` | `analytics_037` | `2026-09-09T12:21:17Z` | `activity_3751` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_18` | `support_5569` | `2026-09-09T11:43:18Z` | `activity_3744` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_18` | `data_flow_4890` | `2026-09-09T12:40:46Z` | `activity_3753` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_18` | `account_5521` | `2026-09-09T09:52:26Z` | `activity_3732` | no | `PRE_AUDIT_UNLINKED` |
| `case_18` | `audit_record_6645` | — | — | no | `ABSENT_GLOBALLY` |
| `case_19` | `search_6083` | `2026-08-19T13:15:43Z` | `activity_3332` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_19` | `support_9553` | `2026-08-19T12:56:14Z` | `activity_3329` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_19` | `account_9102` | `2026-08-19T10:52:22Z` | `activity_3323` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_19` | `audit_record_6793` | `2026-09-15T11:59:39Z` | `evidence_01` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_20` | `search_4262` | `2026-09-09T12:11:17Z` | `activity_3750` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_20` | `data_flow_1770` | `2026-09-09T11:52:47Z` | `activity_3745` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_20` | `account_5037` | `2026-09-09T10:14:55Z` | `activity_3734` | no | `PRE_AUDIT_UNLINKED` |
| `case_20` | `audit_record_5569` | — | — | no | `ABSENT_GLOBALLY` |
| `case_21` | `account_6440` | `2026-09-05T11:01:53Z` | `activity_3661` | no | `PRE_AUDIT_UNLINKED` |
| `case_21` | `audit_record_3737` | `2026-09-15T11:44:55Z` | `evidence_92` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_21` | `analytics_5335` | `2026-09-05T11:31:34Z` | `activity_3665` | no | `PRE_AUDIT_UNLINKED` |
| `case_22` | `search_8911` | `2026-09-01T11:09:32Z` | `activity_3581` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_22` | `analytics_4440` | `2026-09-01T10:50:03Z` | `activity_3578` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_22` | `account_4990` | `2026-09-01T09:12:11Z` | `activity_3573` | no | `PRE_AUDIT_UNLINKED` |
| `case_22` | `audit_record_3482` | `2026-09-21T10:00:00Z` | `evidence_05` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_23` | `export_7364` | `2026-09-05T12:38:47Z` | `activity_3667` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_23` | `search_898` | `2026-09-05T12:57:17Z` | `activity_3671` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_23` | `account_410` | `2026-09-05T11:10:55Z` | `activity_3662` | no | `PRE_AUDIT_UNLINKED` |
| `case_23` | `audit_record_4128` | `2026-09-17T12:00:00Z` | `evidence_02` | no | `POST_AUDIT_ONLY` |
| `case_24` | `account_5334` | `2026-09-02T10:59:41Z` | `activity_3599` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_24` | `search_5577` | `2026-09-02T13:04:03Z` | `activity_3610` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_24` | `audit_record_7095` | `2026-09-17T12:00:00Z` | `evidence_02` | no | `POST_AUDIT_ONLY` |
| `case_25` | `account_3136` | `2026-09-02T10:48:27Z` | `activity_3597` | no | `PRE_AUDIT_UNLINKED` |
| `case_25` | `audit_record_451` | `2026-09-15T11:44:55Z` | `evidence_92` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_25` | `analytics_1895` | `2026-09-02T11:31:08Z` | `activity_3602` | no | `PRE_AUDIT_UNLINKED` |
| `case_26` | `account_5684` | `2026-09-02T11:08:43Z` | `activity_3600` | no | `PRE_AUDIT_UNLINKED` |
| `case_26` | `audit_record_5416` | `2026-09-15T11:44:55Z` | `evidence_92` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_26` | `support_4715` | `2026-09-02T11:38:53Z` | `activity_3605` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_26` | `analytics_4566` | `2026-09-02T11:31:24Z` | `activity_3603` | no | `PRE_AUDIT_UNLINKED` |
| `case_26` | `data_flow_6244` | `2026-09-02T11:45:23Z` | `activity_3606` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_26` | `backup_3120` | `2026-09-02T11:52:52Z` | `activity_3607` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_27` | `account_3866` | `2026-08-30T10:57:28Z` | `activity_3530` | no | `PRE_AUDIT_UNLINKED` |
| `case_27` | `audit_record_3830` | `2026-09-15T11:44:55Z` | `evidence_92` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_27` | `support_4707` | `2026-08-30T11:38:38Z` | `activity_3536` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_27` | `analytics_4574` | `2026-08-30T11:31:09Z` | `activity_3533` | no | `PRE_AUDIT_UNLINKED` |
| `case_27` | `data_flow_2295` | `2026-08-30T11:45:08Z` | `activity_3537` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_27` | `backup_5970` | `2026-08-30T11:52:37Z` | `activity_3540` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_28` | `account_5482` | `2026-08-30T10:46:13Z` | `activity_3529` | no | `PRE_AUDIT_UNLINKED` |
| `case_28` | `audit_record_9265` | `2026-09-15T11:44:55Z` | `evidence_92` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_28` | `support_2351` | `2026-08-30T11:38:23Z` | `activity_3535` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_28` | `analytics_6077` | `2026-08-30T11:31:53Z` | `activity_3534` | no | `PRE_AUDIT_UNLINKED` |
| `case_28` | `data_flow_2337` | `2026-08-30T11:45:52Z` | `activity_3538` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_28` | `backup_838` | `2026-08-30T11:52:22Z` | `activity_3539` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_29` | `search_1993` | `2026-08-30T13:16:19Z` | `activity_3542` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_29` | `analytics_5208` | `2026-08-30T13:54:18Z` | `activity_3544` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_29` | `support_5281` | `2026-08-30T13:35:48Z` | `activity_3543` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_29` | `data_flow_3827` | `2026-08-30T12:57:49Z` | `activity_3541` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_29` | `account_7012` | `2026-08-30T11:06:57Z` | `activity_3532` | no | `PRE_AUDIT_UNLINKED` |
| `case_29` | `audit_record_3954` | `2026-09-17T12:00:00Z` | `evidence_02` | no | `POST_AUDIT_ONLY` |
| `case_30` | `search_9359` | `2026-08-27T13:00:04Z` | `activity_3468` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_30` | `analytics_3697` | `2026-08-27T13:38:03Z` | `activity_3470` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_30` | `support_6477` | `2026-08-27T13:19:33Z` | `activity_3469` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_30` | `data_flow_8524` | `2026-08-27T12:41:34Z` | `activity_3467` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_30` | `account_4163` | `2026-08-27T10:55:42Z` | `activity_3465` | no | `PRE_AUDIT_UNLINKED` |
| `case_30` | `audit_record_1707` | `2026-09-17T12:00:00Z` | `evidence_02` | no | `POST_AUDIT_ONLY` |
| `case_31` | `account_4857` | `2026-09-06T10:45:58Z` | `activity_3682` | no | `PRE_AUDIT_UNLINKED` |
| `case_31` | `audit_record_6909` | `2026-09-15T12:00:00Z` | `evidence_51` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_31` | `tombstone_440` | `2026-09-06T11:31:39Z` | `activity_3687` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_32` | `tombstone_9178` | `2026-09-06T13:00:07Z` | `activity_3692` | yes | `PRE_AUDIT_RETRIEVABLE` |
| `case_32` | `account_8858` | `2026-09-06T11:05:15Z` | `activity_3685` | no | `PRE_AUDIT_UNLINKED` |
| `case_32` | `audit_record_7068` | `2026-09-15T12:00:00Z` | `evidence_51` | yes | `PRE_AUDIT_RETRIEVABLE` |

## Decision

Training is blocked from claiming a lawful 100% result while this gate fails.
Post-audit artifacts and absent resource IDs must not become runtime mappings.
The remedy is pre-audit lineage in participant data or an evaluator correction.
