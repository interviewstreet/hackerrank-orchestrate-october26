"""Hand-labelled end-to-end scenarios (SPEC §13.3). Each returns (dataset, {case_id: (status, steps)}).

Expected steps are derived by hand from the public contract (problem statement + deletion rules), not by
running the engine: phases FINDING -> REMEDIATION -> VERIFICATION, operations in contract-table order, then
system_id and resource_id; findings cite the evidence that shows the violation, future steps cite nothing,
and COMPLETE cases cite the latest evidence proving each compliant state.
"""
from __future__ import annotations

from .builder import MiniDataset, sha

REQ, REP, AUD = "2026-05-01T09:00:00Z", "2026-05-03T09:00:00Z", "2026-05-10T12:00:00Z"
EMAIL, OLD_EMAIL = "lena.novak@example.org", "l.novak@example.org"
ACC = "rows=0 http_status=404"


def base() -> MiniDataset:
    return MiniDataset().user("user_101", "Lena Novak", EMAIL, "+48 600 100 200")


def F(sys, rid, op, ev):
    state = {"REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
             "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE"}[op]
    return ("FINDING", sys, rid, op, state, ev)


def R(sys, rid, op):
    state = {"DELETE_RECORD": "ABSENT", "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED",
             "BLOCK_RESTORE": "BLOCKED", "DISABLE_DATA_FLOW": "DISABLED"}[op]
    return ("REMEDIATION", sys, rid, op, state, "")


def V(sys, rid, op, ev=""):
    state = {"VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT", "VERIFY_RECORD_REDACTED": "REDACTED",
             "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
             "VERIFY_RESTORE_BLOCKED": "BLOCKED"}[op]
    return ("VERIFICATION", sys, rid, op, state, ev)


def profile_lookup(rid, key, kv=ACC, ts="2026-05-10T08:00:00Z"):
    return (ts, "account_service", "profile_lookup", rid, key, kv)


def search_lookup(rid, key, hit=True, email=None, ts="2026-05-10T08:05:00Z"):
    kv = (f"result=hit total_hits=1 index=customer_directory_v3 email={email or key} customer_reference=null" if hit
          else "result=miss total_hits=0 index=customer_directory_v3")
    return (ts, "search_service", "index_query", rid, key, kv)


def profile_deletion(ds: MiniDataset, rid: str, at: str = "2026-05-03T08:00:00Z"):
    ds.act(at, "DELETE_RECORD", "deletion_worker", "account_service", rid, "SUCCESS",
           f"Deletion worker submitted primary profile {rid} to account_service.")


# 1 -----------------------------------------------------------------------------------------------------------
def historical_email_only():
    ds = base().change("user_101", "email", OLD_EMAIL, EMAIL, "2026-03-01T10:00:00Z")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL),
                                             search_lookup("search_7002", OLD_EMAIL)])
    ds.request("case_01", OLD_EMAIL, REQ, REP, AUD)
    return ds, {"case_01": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
    ])}


# 2 -----------------------------------------------------------------------------------------------------------
def near_miss_decoys():
    ds = base().user("user_102", "Lena Nowak", "lena.novak.jr@example.org", "+48 600 100 201") \
               .user("user_103", "Lena Novak", "lena.novak1@example.org", "+48 600 100 202")
    ds.readback_log("2026-05-10T10:00:00Z", [
        profile_lookup("account_7001", EMAIL),
        search_lookup("search_7100", "lena.novak.jr@example.org"),
        profile_lookup("account_7101", "lena.novak1@example.org", "rows=1 http_status=200 email=lena.novak1@example.org"),
    ])
    ds.request("case_02", EMAIL, REQ, REP, AUD)
    return ds, {"case_02": ("COMPLETE", [V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_01")])}


# 3 -----------------------------------------------------------------------------------------------------------
def evidence_after_audit_is_ignored():
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL)])
    ds.service_export_json("2026-05-20T10:00:00Z", {"search_service": {"index_queries": [{
        "observed_at": "2026-05-20T09:00:00Z", "query": EMAIL, "resource_id": "search_7002",
        "hits": {"total": 1, "documents": [{"resource_id": "search_7002", "email": EMAIL}]}}]}})
    ds.request("case_03", EMAIL, REQ, REP, AUD)
    return ds, {"case_03": ("COMPLETE", [V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_01")])}


# 4 -----------------------------------------------------------------------------------------------------------
def korean_non_deletion_request():
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL, f"rows=1 http_status=200 email={EMAIL}")])
    ds.request("case_04", EMAIL, REQ, REP, AUD, text="계정은 그대로 유지해 주세요. 마케팅 이메일 수신만 중단하고 데이터는 삭제하지 마세요.",
               status="NOT_STARTED")
    return ds, {"case_04": ("NOT_APPLICABLE", [])}


# 5 -----------------------------------------------------------------------------------------------------------
def success_claim_is_not_proof():
    ds = base()
    ds.act("2026-05-02T10:00:00Z", "DELETE_RECORD", "deletion_worker", "search_service", "search_7002", "SUCCESS",
           "Deletion worker received the final result for search_7002 from search_service.")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL), search_lookup("search_7002", EMAIL)])
    ds.request("case_05", EMAIL, REQ, REP, AUD)
    return ds, {"case_05": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
    ])}


# 6 -----------------------------------------------------------------------------------------------------------
def failover_replica_drift():
    ds = base().user("user_104", "Piotr Zielinski", "p.zielinski@example.org", "+48 600 100 300")
    ds.failover_sql("2026-05-10T09:00:00Z",
                    primary=[("account_7200", "user_104", "Piotr Zielinski", "p.zielinski@example.org", "+48 600 100 300", "ACTIVE", "2026-05-10T08:00:00Z")],
                    failover=[("account_7200", "user_104", "Piotr Zielinski", "p.zielinski@example.org", "+48 600 100 300", "ACTIVE", "2026-05-10T08:00:00Z"),
                              ("account_7001", "user_101", "Lena Novak", EMAIL, "+48 600 100 200", "ACTIVE", "2026-05-10T08:00:00Z")])
    ds.request("case_06", EMAIL, REQ, REP, AUD)
    return ds, {"case_06": ("INCOMPLETE", [
        F("account_service", "account_7001", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("account_service", "account_7001", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
    ])}


# 7 -----------------------------------------------------------------------------------------------------------
def connector_recreates_deleted_entry():
    ds = base()
    ds.readback_log("2026-05-05T10:00:00Z", [profile_lookup("account_7001", EMAIL, ts="2026-05-05T08:00:00Z"),
                                             search_lookup("search_7002", EMAIL, hit=False, ts="2026-05-05T08:05:00Z")])
    ds.act("2026-05-08T06:00:00Z", "SYNC_RECORD", "integration_service", "search_service", "data_flow_7003", "SUCCESS",
           "Active connector repopulated downstream resource search_7002.")
    ds.request("case_07", EMAIL, REQ, REP, AUD)
    return ds, {"case_07": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "activity_01"),
        F("integration_service", "data_flow_7003", "REPORT_ACTIVE_DATA_FLOW", "activity_01"),
        R("integration_service", "data_flow_7003", "DISABLE_DATA_FLOW"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
        V("integration_service", "data_flow_7003", "VERIFY_DATA_FLOW_DISABLED"),
    ])}


# 8 -----------------------------------------------------------------------------------------------------------
def restorable_backup():
    ds = base()
    profile_deletion(ds, "account_7001")
    ds.inventory_sql("2026-05-10T09:00:00Z", ["account_service", "backup_service"], [
        f"INSERT INTO backup_restore_entries VALUES ('backup_7004', NULL, '{EMAIL}', 'archive/customer-data/backup_7004.tar.zst', '1', '2026-05-10T08:00:00Z')",
    ])
    ds.request("case_08", EMAIL, REQ, REP, AUD)
    return ds, {"case_08": ("INCOMPLETE", [
        F("backup_service", "backup_7004", "REPORT_RESTORE_RISK", "evidence_01"),
        R("backup_service", "backup_7004", "BLOCK_RESTORE"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("backup_service", "backup_7004", "VERIFY_RESTORE_BLOCKED"),
    ])}


# 9 -----------------------------------------------------------------------------------------------------------
def tombstones_exposed_and_clean():
    ds = base().user("user_103", "Omar Haddad", "omar.h@example.org", "+971 50 100 2000")
    profile_deletion(ds, "account_7001", "2026-05-03T08:00:00Z")
    profile_deletion(ds, "account_7301", "2026-05-06T08:00:00Z")
    ds.bundle_json("2026-05-10T09:00:00Z", [
        ("account_service", "customer_profiles", []),
        ("identity_service", "deleted_customer_references", [
            {"resource_id": "tombstone_7005", "subject_reference": "user_101", "name": "Lena Novak", "email": EMAIL,
             "phone": "+48 600 100 200", "email_hash": sha(EMAIL), "account_status": "DELETED"},
            {"resource_id": "tombstone_7006", "subject_reference": "user_103", "name": None, "email": None,
             "phone": None, "email_hash": None, "account_status": "DELETED"}]),
    ])
    ds.request("case_09", EMAIL, REQ, REP, AUD)
    ds.request("case_10", "omar.h@example.org", "2026-05-04T09:00:00Z", "2026-05-06T09:00:00Z", AUD)
    return ds, {
        "case_09": ("INCOMPLETE", [
            F("identity_service", "tombstone_7005", "REPORT_EXPOSED_PII", "evidence_01"),
            R("identity_service", "tombstone_7005", "REDACT_RECORD"),
            V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
            V("identity_service", "tombstone_7005", "VERIFY_RECORD_REDACTED"),
        ]),
        "case_10": ("COMPLETE", [
            V("account_service", "account_7301", "VERIFY_RECORD_ABSENT", "evidence_01"),
            V("identity_service", "tombstone_7006", "VERIFY_RECORD_REDACTED", "evidence_01"),
        ]),
    }


# 10 ----------------------------------------------------------------------------------------------------------
def support_message_vs_attachment():
    ds = base()
    profile_deletion(ds, "account_7001")
    ds.inventory_sql("2026-05-09T09:00:00Z", ["account_service", "support_platform"], [
        f"INSERT INTO support_records VALUES ('support_7007', NULL, NULL, '{EMAIL}', NULL, 'Customer asked support to correct delivery details.', '2026-05-09T08:00:00Z')",
    ])
    ds.bundle_json("2026-05-10T09:00:00Z", [("support_platform", "ticket_attachments", [
        {"resource_id": "support_7008", "ticket_id": "CS-7008", "file_name": "delivery_note_7008.pdf",
         "uploaded_by": EMAIL, "storage_class": "ticket_attachment"}])])
    ds.request("case_11", EMAIL, REQ, REP, AUD)
    return ds, {"case_11": ("INCOMPLETE", [
        F("support_platform", "support_7008", "REPORT_REMAINING_RECORD", "evidence_02"),
        F("support_platform", "support_7007", "REPORT_EXPOSED_PII", "evidence_01"),
        R("support_platform", "support_7008", "DELETE_RECORD"),
        R("support_platform", "support_7007", "REDACT_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("support_platform", "support_7008", "VERIFY_RECORD_ABSENT"),
        V("support_platform", "support_7007", "VERIFY_RECORD_REDACTED"),
    ])}


# 11 ----------------------------------------------------------------------------------------------------------
def retained_audit_and_legal_hold():
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [
        profile_lookup("account_7001", EMAIL),
        ("2026-05-10T08:10:00Z", "security_service", "audit_record_read", "audit_record_7009", "user_101",
         "rows=1 subject_reference=user_101 event_code=ACCOUNT_DELETION_RECORDED retention_until=2031-12-31T23:59:59Z"),
    ])
    ds.bundle_json("2026-05-10T09:00:00Z", [("legal_service", "retained_order_records", [
        {"resource_id": "legal_hold_7010", "subject_reference": "user_101", "order_reference": "ORD-7010",
         "retention_reason": "payment_dispute_and_tax_record", "retained_until": "2033-12-31T23:59:59Z"}])])
    ds.request("case_12", EMAIL, REQ, REP, AUD)
    return ds, {"case_12": ("COMPLETE", [
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_01"),
        V("legal_service", "legal_hold_7010", "VERIFY_RECORD_PRESENT", "evidence_02"),
        V("security_service", "audit_record_7009", "VERIFY_RECORD_PRESENT", "evidence_01"),
    ])}


# 12 ----------------------------------------------------------------------------------------------------------
def analytics_profile_vs_marketing_contact():
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [
        profile_lookup("account_7001", EMAIL),
        ("2026-05-10T08:20:00Z", "analytics_platform", "analytics_profile_read", "analytics_7011", EMAIL,
         f"customer_reference=null email={EMAIL} phone=null email_hash=null audience_cohort=general_shopper"),
    ])
    ds.evidence("evidence/logs/service_events_20260510.log", "2026-05-10T11:00:00Z",
                "2026-05-10T10:58:26Z level=DEBUG service=analytics_platform instance=analytics-2 trace_id=tr-9137340 "
                f"resource_id=analytics_7012 event=contact_lookup_completed rows=1 email_opt_in=true correlation_key=\"{sha(EMAIL)}\"\n",
                "central_observability_export")
    ds.request("case_13", EMAIL, REQ, REP, AUD)
    return ds, {"case_13": ("INCOMPLETE", [
        F("analytics_platform", "analytics_7012", "REPORT_REMAINING_RECORD", "evidence_02"),
        F("analytics_platform", "analytics_7011", "REPORT_EXPOSED_PII", "evidence_01"),
        R("analytics_platform", "analytics_7012", "DELETE_RECORD"),
        R("analytics_platform", "analytics_7011", "ANONYMIZE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("analytics_platform", "analytics_7012", "VERIFY_RECORD_ABSENT"),
        V("analytics_platform", "analytics_7011", "VERIFY_RECORD_ANONYMIZED"),
    ])}


# 13 ----------------------------------------------------------------------------------------------------------
def complete_cites_latest_evidence():
    ds = base()
    ds.readback_log("2026-05-01T10:00:00Z", [
        profile_lookup("account_7001", EMAIL, f"rows=1 http_status=200 email={EMAIL}", ts="2026-05-01T08:00:00Z"),
        search_lookup("search_7002", EMAIL, ts="2026-05-01T08:05:00Z")])
    ds.readback_log("2026-05-08T10:00:00Z", [
        profile_lookup("account_7001", EMAIL, ts="2026-05-08T08:00:00Z"),
        search_lookup("search_7002", EMAIL, hit=False, ts="2026-05-08T08:05:00Z")])
    ds.inventory_sql("2026-05-09T09:00:00Z", ["integration_service"], [
        f"INSERT INTO connector_subscriptions VALUES ('data_flow_7003', NULL, '{EMAIL}', 'customer_events_connector', '0', 'stopped', '2026-05-09T08:00:00Z')"])
    ds.request("case_14", EMAIL, REQ, REP, AUD)
    return ds, {"case_14": ("COMPLETE", [
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_02"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT", "evidence_02"),
        V("integration_service", "data_flow_7003", "VERIFY_DATA_FLOW_DISABLED", "evidence_03"),
    ])}


# 14 ----------------------------------------------------------------------------------------------------------
def identifiers_joined_across_trace_lines():
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL)])
    ds.split_trace_log("2026-05-10T11:00:00Z", "2026-05-10T10:30:00Z", "search_service", EMAIL, "search_7002",
                       "result=hit index=customer_directory_v3")
    ds.request("case_15", EMAIL, REQ, REP, AUD)
    return ds, {"case_15": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "evidence_02"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
    ])}


# 15 ----------------------------------------------------------------------------------------------------------
def unknown_identity_uses_bare_email():
    """Defined behaviour: an email that matches no identity is audited with the email and its hash only."""
    ds = base()
    ghost = "ghost.customer@example.org"
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7013", ghost, f"rows=1 http_status=200 email={ghost}")])
    ds.request("case_16", ghost, REQ, REP, AUD)
    return ds, {"case_16": ("INCOMPLETE", [
        F("account_service", "account_7013", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("account_service", "account_7013", "DELETE_RECORD"),
        V("account_service", "account_7013", "VERIFY_RECORD_ABSENT"),
    ])}


# 16 ----------------------------------------------------------------------------------------------------------
def late_export(ds, exported: str, snapshot: str, rid: str) -> str:
    """A records bundle exported after the audit whose security snapshot was taken before it."""
    import json
    data = {"exported_at": exported, "source": "records_assurance_service", "snapshots": [{
        "captured_at": snapshot, "data_store": "security_service", "collection": "security_audit_events",
        "records": [{"resource_id": rid, "subject_reference": "user_101", "event_name": "account_deletion_reviewed",
                     "actor_type": "automated_privacy_workflow", "integrity_seal": "sha256:" + "0" * 60 + "1f2e"}]}]}
    return ds.evidence(f"evidence/records/customer_data_snapshot_bundle_{exported[:10].replace('-', '')}.json",
                       exported, json.dumps(data, indent=2), "records_assurance_snapshot_bundle")


def retained_record_from_late_export():
    """A retained record seen only in a file exported after the audit (snapshot taken before it) adds an
    uncited post-remediation check to an INCOMPLETE case; the late file is never cited."""
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL), search_lookup("search_7002", EMAIL)])
    late_export(ds, "2026-05-12T12:00:00Z", "2026-05-10T11:00:00Z", "audit_record_7020")
    ds.request("case_17", EMAIL, REQ, REP, AUD)
    return ds, {"case_17": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
        V("security_service", "audit_record_7020", "VERIFY_RECORD_PRESENT"),
    ])}


def late_export_never_supports_complete():
    """The same late file cannot be cited, so it adds nothing to a COMPLETE case, and a snapshot taken after the
    audit adds nothing to an INCOMPLETE one."""
    ds = base().user("user_104", "Ola Berg", "ola.berg@example.org", "+47 400 100 300")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL)])
    late_export(ds, "2026-05-12T12:00:00Z", "2026-05-10T11:00:00Z", "audit_record_7021")
    ds.request("case_18", EMAIL, REQ, REP, AUD)
    return ds, {"case_18": ("COMPLETE", [V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_01")])}


def unknown_email_gets_no_timing_link():
    """A deletion workflow in the request window is not attached to an email that matches nobody: timing alone
    proves nothing, so the case has no footprint (COMPLETE without steps) instead of a borrowed account."""
    ds = base()
    profile_deletion(ds, "account_7030", "2026-05-03T08:00:00Z")
    ds.request("case_19", "nobody@nowhere.invalid", REQ, REP, AUD)
    return ds, {"case_19": ("COMPLETE", [])}


def earlier_request_owns_its_leftovers():
    """A record last seen months ago, during the same person's earlier request, is reported by that request; the
    later request (made after the earlier audit) only answers for what was observed in its own lifecycle."""
    ds = base()
    ds.readback_log("2026-01-10T10:00:00Z", [profile_lookup("account_7040", EMAIL, ts="2026-01-10T08:00:00Z"),
                                             search_lookup("search_7041", EMAIL, ts="2026-01-10T08:05:00Z")])
    ds.request("case_20", EMAIL, "2026-01-01T09:00:00Z", "2026-01-03T09:00:00Z", "2026-01-10T12:00:00Z")
    profile_deletion(ds, "account_7040", "2026-01-03T08:00:00Z")
    profile_deletion(ds, "account_7001", "2026-05-03T08:00:00Z")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL)])
    ds.request("case_21", EMAIL, REQ, REP, AUD)
    return ds, {
        "case_20": ("INCOMPLETE", [
            F("search_service", "search_7041", "REPORT_REMAINING_RECORD", "evidence_01"),
            R("search_service", "search_7041", "DELETE_RECORD"),
            V("account_service", "account_7040", "VERIFY_RECORD_ABSENT"),
            V("search_service", "search_7041", "VERIFY_RECORD_ABSENT"),
        ]),
        "case_21": ("COMPLETE", [V("account_service", "account_7001", "VERIFY_RECORD_ABSENT", "evidence_02")]),
    }


def recent_leftover_of_earlier_request_is_reported():
    """Safety margin: a leftover seen a few weeks ago during the earlier request is still reported by the later
    one; only months-old records are left to the earlier lifecycle (a missed leftover is a false COMPLETE)."""
    ds = base()
    ds.readback_log("2026-04-10T10:00:00Z", [profile_lookup("account_7040", EMAIL, ts="2026-04-10T08:00:00Z"),
                                             search_lookup("search_7041", EMAIL, ts="2026-04-10T08:05:00Z")])
    ds.request("case_22", EMAIL, "2026-04-01T09:00:00Z", "2026-04-03T09:00:00Z", "2026-04-10T12:00:00Z")
    profile_deletion(ds, "account_7040", "2026-04-03T08:00:00Z")
    profile_deletion(ds, "account_7001", "2026-05-03T08:00:00Z")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL)])
    ds.request("case_23", EMAIL, REQ, REP, AUD)
    return ds, {"case_23": ("INCOMPLETE", [
        F("search_service", "search_7041", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("search_service", "search_7041", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7041", "VERIFY_RECORD_ABSENT"),
    ])}


# Shapes from an external QA fixture (rebuilt from its quoted evidence, not its answers): other id schemes,
# other wordings, other scripts. Same contract, different spelling.
def tombstone_status_on_profile_rows():
    """An `account_*` row whose account_status is TOMBSTONE is an ACCOUNT_TOMBSTONE (REDACT), not a profile to
    delete; it is linked through a user id that does not follow the `user_<n>` scheme."""
    ds = MiniDataset().user("u_2008", "Hana Kobayashi", "hana.k08@example.test", "+81 90 5555 0108") \
                      .user("u_2009", "Karim El-Masri", "karim.e09@example.test", "+971 50 555 0109")
    ds.inventory_sql("2026-05-10T09:00:00Z", ["account_service"], [
        "INSERT INTO customer_profiles VALUES ('account_2008', 'u_2008', NULL, NULL, NULL, NULL, 'TOMBSTONE', '2026-05-10T08:00:00Z')",
        f"INSERT INTO customer_profiles VALUES ('account_2009', 'u_2009', 'Karim El-Masri', 'karim.e09@example.test', "
        f"'+971 50 555 0109', '{sha('karim.e09@example.test')}', 'TOMBSTONE', '2026-05-10T08:00:00Z')",
    ])
    ds.request("case_24", "hana.k08@example.test", REQ, REP, AUD)
    ds.request("case_25", "karim.e09@example.test", REQ, REP, AUD)
    return ds, {
        "case_24": ("COMPLETE", [V("account_service", "account_2008", "VERIFY_RECORD_REDACTED", "evidence_01")]),
        "case_25": ("INCOMPLETE", [
            F("account_service", "account_2009", "REPORT_EXPOSED_PII", "evidence_01"),
            R("account_service", "account_2009", "REDACT_RECORD"),
            V("account_service", "account_2009", "VERIFY_RECORD_REDACTED"),
        ]),
    }


def unlisted_resource_prefixes():
    """Resource ids outside the known prefixes take their system from the evidence (origin_system column, the
    log line's service) and their category from the collection / event name."""
    ds = base()
    ds.json_table_sql("2026-05-09T09:00:00Z", [("cust_7040", "customer_data", "customer_profiles",
                                                {"resource_id": "cust_7040", "user_id": "user_101", "email": EMAIL})])
    ds.evidence("evidence/logs/notification_events_20260510.log", "2026-05-10T09:00:00Z",
                f'2026-05-10T07:12:02Z [WARN] [notification_service] email_delivery: resource_id="log_7041" '
                f'matched_value="{EMAIL}" detector="direct_identifier"\n')
    ds.request("case_26", EMAIL, REQ, REP, AUD)
    return ds, {"case_26": ("INCOMPLETE", [
        F("customer_data", "cust_7040", "REPORT_REMAINING_RECORD", "evidence_01"),
        F("notification_service", "log_7041", "REPORT_EXPOSED_PII", "evidence_02"),
        R("customer_data", "cust_7040", "DELETE_RECORD"),
        R("notification_service", "log_7041", "REDACT_RECORD"),
        V("customer_data", "cust_7040", "VERIFY_RECORD_ABSENT"),
        V("notification_service", "log_7041", "VERIFY_RECORD_REDACTED"),
    ])}


def cyrillic_deletion_request():
    """Without an LLM, a Russian erasure request is still recognised as authorizing deletion."""
    ds = base()
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL), search_lookup("search_7002", EMAIL)])
    ds.request("case_27", EMAIL, REQ, REP, AUD, text="Здравствуйте, прошу удалить мой аккаунт и все мои персональные данные.")
    return ds, {"case_27": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "evidence_01"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
    ])}


def other_recreation_and_check_wordings():
    """"Reindex job recreated ..." is a recreation like "repopulated downstream resource ..."; "check confirmed
    X can restore ..." reopens a backup that an earlier snapshot showed blocked."""
    ds = base()
    ds.readback_log("2026-05-05T10:00:00Z", [profile_lookup("account_7001", EMAIL, ts="2026-05-05T08:00:00Z"),
                                             search_lookup("search_7002", EMAIL, hit=False, ts="2026-05-05T08:05:00Z")])
    ds.inventory_sql("2026-05-06T09:00:00Z", ["backup_service"], [
        f"INSERT INTO backup_restore_entries VALUES ('backup_7004', NULL, '{EMAIL}', 'archive/backup_7004.tar.zst', '0', '2026-05-06T08:00:00Z')"])
    ds.act("2026-05-08T06:00:00Z", "INDEX_RECORD", "search_reindexer", "search_service", "data_flow_7003", "SUCCESS",
           "Reindex job recreated search document search_7002 after the account deletion.")
    ds.act("2026-05-09T06:00:00Z", "CHECK_RESTORE_ACCESS", "deletion_worker", "backup_service", "backup_7004", "SUCCESS",
           "Restore access check confirmed backup_7004 can restore the deleted account.")
    ds.request("case_28", EMAIL, REQ, REP, AUD)
    return ds, {"case_28": ("INCOMPLETE", [
        F("search_service", "search_7002", "REPORT_REMAINING_RECORD", "activity_01"),
        F("integration_service", "data_flow_7003", "REPORT_ACTIVE_DATA_FLOW", "activity_01"),
        F("backup_service", "backup_7004", "REPORT_RESTORE_RISK", "activity_02"),
        R("integration_service", "data_flow_7003", "DISABLE_DATA_FLOW"),
        R("backup_service", "backup_7004", "BLOCK_RESTORE"),
        R("search_service", "search_7002", "DELETE_RECORD"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("search_service", "search_7002", "VERIFY_RECORD_ABSENT"),
        V("integration_service", "data_flow_7003", "VERIFY_DATA_FLOW_DISABLED"),
        V("backup_service", "backup_7004", "VERIFY_RESTORE_BLOCKED"),
    ])}


def archive_without_visible_block_is_a_restore_risk():
    """A subject's archive that evidence shows to exist, with no restore state shown, is a restore path until a
    block is proven; another person's archive on the same screen is not the subject's risk."""
    ds = base().user("user_150", "Miller Logistics", "miller.logistics@example.com", "+1 555 0100 150")
    profile_deletion(ds, "account_7001")
    ds.bundle_json("2026-05-09T09:00:00Z", [("backup_service", "archive_catalog", [
        {"resource_id": "backup_7060", "account": EMAIL, "customer_email": EMAIL, "result": "FOUND",
         "retention_until": "2026-08-01T00:00:00Z"},
        {"resource_id": "backup_7061", "customer_email": "miller.logistics@example.com", "result": "FOUND"}])])
    ds.request("case_29", EMAIL, REQ, REP, AUD)
    return ds, {"case_29": ("INCOMPLETE", [
        F("backup_service", "backup_7060", "REPORT_RESTORE_RISK", "evidence_01"),
        R("backup_service", "backup_7060", "BLOCK_RESTORE"),
        V("account_service", "account_7001", "VERIFY_RECORD_ABSENT"),
        V("backup_service", "backup_7060", "VERIFY_RESTORE_BLOCKED"),
    ])}


SCENARIOS = [
    historical_email_only, near_miss_decoys, evidence_after_audit_is_ignored, korean_non_deletion_request,
    success_claim_is_not_proof, failover_replica_drift, connector_recreates_deleted_entry, restorable_backup,
    tombstones_exposed_and_clean, support_message_vs_attachment, retained_audit_and_legal_hold,
    analytics_profile_vs_marketing_contact, complete_cites_latest_evidence, identifiers_joined_across_trace_lines,
    unknown_identity_uses_bare_email, retained_record_from_late_export, late_export_never_supports_complete,
    unknown_email_gets_no_timing_link, earlier_request_owns_its_leftovers,
    recent_leftover_of_earlier_request_is_reported, tombstone_status_on_profile_rows, unlisted_resource_prefixes,
    cyrillic_deletion_request, other_recreation_and_check_wordings, archive_without_visible_block_is_a_restore_risk,
]
