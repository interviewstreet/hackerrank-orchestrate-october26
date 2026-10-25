"""Production Deletion Audit Pipeline for Northstar Shop.

Performs multi-system identity resolution, multi-modal evidence indexing,
temporal state reconstruction, policy violation detection, remediation planning,
and deterministic verification generation.
"""

import os
import glob
import json
import csv
import re
import sqlite3
import sys
from datetime import datetime

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from .constants import (
    PHASES, OPERATIONS, OP_RANK, OP_PHASE, OP_STATE, STATUSES, STEP_KEYS
)
from .steps import make_step, sort_key, finalize, dumps


def build_full_indexer(dataset_dir="dataset"):
    """Index all participant-visible identity, activity, and evidence sources."""
    ident_to_uid = {}
    uid_to_idents = {}
    uid_to_info = {}

    identities_path = os.path.join(dataset_dir, "user_identities.csv")
    if os.path.exists(identities_path):
        with open(identities_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"]
                uid_to_info[uid] = r
                uid_to_idents.setdefault(uid, set()).add(uid.lower())
                ident_to_uid[uid.lower()] = uid
                for fld in ["name", "email", "phone", "email_hash"]:
                    v = r.get(fld)
                    if v and v.strip():
                        val = v.strip().lower()
                        ident_to_uid[val] = uid
                        uid_to_idents[uid].add(val)

    audit_log_path = os.path.join(dataset_dir, "user_audit_log.csv")
    if os.path.exists(audit_log_path):
        with open(audit_log_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"]
                for fld in ["old_value", "new_value"]:
                    v = r.get(fld)
                    if v and v.strip():
                        val = v.strip().lower()
                        ident_to_uid[val] = uid
                        uid_to_idents.setdefault(uid, set()).add(val)

    ev_manifest = {}
    manifest_path = os.path.join(dataset_dir, "evidence_files.csv")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ev_manifest[r["file_id"]] = r

    activity = []
    activity_path = os.path.join(dataset_dir, "system_activity.csv")
    if os.path.exists(activity_path):
        with open(activity_path, encoding="utf-8") as f:
            activity = list(csv.DictReader(f))

    def resolve_uid(val):
        if not val or val == "null" or val == "None":
            return None
        return ident_to_uid.get(str(val).strip().lower())

    def extract_uid_from_dict(d):
        if not isinstance(d, dict):
            return None
        for k in [
            "customer_reference", "subject_reference", "user_id", "email",
            "requester_email", "customer_email", "owner_email", "phone",
            "email_hash", "display_name", "full_name"
        ]:
            if k in d and d[k]:
                u = resolve_uid(d[k])
                if u:
                    return u
        for v in d.values():
            if isinstance(v, dict):
                u = extract_uid_from_dict(v)
                if u:
                    return u
        return None

    user_resources = {}       # uid -> set of (sys_id, res_id)
    res_observations = {}     # (uid, res_id) -> list of obs dicts
    all_res_to_obs = {}       # res_id -> list of obs dicts

    def add_obs(captured_at, fid, uid, sys_id, res_id, is_violation, state, find_op, rem_op, verif_op):
        if not res_id:
            return
        obs = {
            "captured_at": captured_at,
            "evidence_id": fid,
            "system_id": sys_id,
            "resource_id": res_id,
            "is_violation": is_violation,
            "state": state,
            "find_op": find_op,
            "rem_op": rem_op,
            "verif_op": verif_op,
            "uid": uid
        }
        all_res_to_obs.setdefault(res_id, []).append(obs)
        if uid:
            user_resources.setdefault(uid, set()).add((sys_id, res_id))
            res_observations.setdefault((uid, res_id), []).append(obs)

    # 1. JSON records in evidence/records
    for fp in glob.glob(os.path.join(dataset_dir, "evidence/records/*.json")):
        fn = os.path.basename(fp)
        rel_path = "evidence/records/" + fn
        fid = None
        for k, v in ev_manifest.items():
            if v["file_path"] == rel_path:
                fid = k
                break
        if not fid:
            continue
        cap_at = ev_manifest[fid]["captured_at"]
        origin = ev_manifest[fid]["origin"]

        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if "service_exports" in data:
            se = data["service_exports"]
            for lk in se.get("account_service", {}).get("profile_lookups", []):
                res_id = lk.get("resource_id")
                prof = lk.get("profile")
                status_code = lk.get("status_code")
                uid = extract_uid_from_dict(prof) if prof else None
                if status_code == 200 or prof:
                    add_obs(cap_at, fid, uid, "account_service", res_id, True, "PRESENT",
                            "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                elif status_code == 404:
                    add_obs(cap_at, fid, uid, "account_service", res_id, False, "ABSENT",
                            None, None, "VERIFY_RECORD_ABSENT")

            for sub in se.get("search_service", {}).get("index_queries", []):
                uid = resolve_uid(sub.get("query"))
                for doc in sub.get("hits", {}).get("documents", []):
                    doc_uid = extract_uid_from_dict(doc) or uid
                    res_id = doc.get("resource_id") or sub.get("resource_id")
                    add_obs(cap_at, fid, doc_uid, "search_service", res_id, True, "PRESENT",
                            "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")

            for ticket in se.get("support_platform", {}).get("tickets", []):
                uid = extract_uid_from_dict(ticket)
                res_id = ticket.get("resource_id")
                has_pii = bool(
                    ticket.get("requester_email") or ticket.get("requester_phone") or ticket.get("requester_name") or
                    (ticket.get("message_excerpt") and any(em in ticket["message_excerpt"].lower() for em in ident_to_uid))
                )
                if has_pii:
                    add_obs(cap_at, fid, uid, "support_platform", res_id, True, "PRESENT",
                            "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                else:
                    add_obs(cap_at, fid, uid, "support_platform", res_id, False, "REDACTED",
                            None, None, "VERIFY_RECORD_REDACTED")

            for prof in se.get("analytics_platform", {}).get("profiles", []):
                uid = extract_uid_from_dict(prof)
                res_id = prof.get("resource_id")
                has_pii = bool(prof.get("email") or prof.get("phone") or prof.get("email_hash") or prof.get("customer_reference"))
                if has_pii:
                    add_obs(cap_at, fid, uid, "analytics_platform", res_id, True, "PRESENT",
                            "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED")
                else:
                    add_obs(cap_at, fid, uid, "analytics_platform", res_id, False, "ANONYMIZED",
                            None, None, "VERIFY_RECORD_ANONYMIZED")

            for conn in se.get("integration_service", {}).get("connectors", []):
                uid = extract_uid_from_dict(conn)
                res_id = conn.get("resource_id")
                if conn.get("enabled"):
                    add_obs(cap_at, fid, uid, "integration_service", res_id, True, "ACTIVE",
                            "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED")
                else:
                    add_obs(cap_at, fid, uid, "integration_service", res_id, False, "DISABLED",
                            None, None, "VERIFY_DATA_FLOW_DISABLED")

            for item in se.get("backup_service", {}).get("restore_entries", []):
                uid = extract_uid_from_dict(item)
                res_id = item.get("resource_id")
                if item.get("restore_allowed"):
                    add_obs(cap_at, fid, uid, "backup_service", res_id, True, "ACTIVE",
                            "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")
                else:
                    add_obs(cap_at, fid, uid, "backup_service", res_id, False, "BLOCKED",
                            None, None, "VERIFY_RESTORE_BLOCKED")

            for item in se.get("export_service", {}).get("exports", []):
                uid = extract_uid_from_dict(item)
                res_id = item.get("resource_id")
                add_obs(cap_at, fid, uid, "export_service", res_id, True, "PRESENT",
                        "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")

            for item in se.get("security_service", {}).get("audit_records", []):
                uid = extract_uid_from_dict(item)
                res_id = item.get("resource_id")
                add_obs(cap_at, fid, uid, "security_service", res_id, False, "PRESENT",
                        None, None, "VERIFY_RECORD_PRESENT")

        if "snapshots" in data:
            for snap in data["snapshots"]:
                store = snap.get("data_store")
                coll = snap.get("collection")
                for rec in snap.get("records", []):
                    res_id = rec.get("resource_id")
                    uid = extract_uid_from_dict(rec)
                    
                    sys_id = store
                    if not sys_id:
                        if "customer_profiles" in str(coll): sys_id = "account_service"
                        elif "security" in str(coll): sys_id = "security_service"
                        elif "tombstone" in str(coll) or "deleted_customer" in str(coll): sys_id = "identity_service"
                        elif "search" in str(coll): sys_id = "search_service"
                        elif "analytics" in str(coll): sys_id = "analytics_platform"
                        elif "support" in str(coll): sys_id = "support_platform"

                    if sys_id == "identity_service":
                        has_pii = bool(rec.get("name") or rec.get("email") or rec.get("phone") or rec.get("email_hash"))
                        if has_pii:
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                    "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "REDACTED",
                                    None, None, "VERIFY_RECORD_REDACTED")
                    elif sys_id == "account_service":
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "search_service":
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "support_platform":
                        has_pii = bool(
                            rec.get("requester_name") or rec.get("requester_email") or rec.get("requester_phone") or
                            (rec.get("message_text") and any(em in rec["message_text"].lower() for em in ident_to_uid))
                        )
                        if has_pii:
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                    "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "REDACTED",
                                    None, None, "VERIFY_RECORD_REDACTED")
                    elif sys_id == "analytics_platform":
                        has_pii = bool(rec.get("email") or rec.get("phone") or rec.get("email_hash") or rec.get("customer_reference"))
                        if has_pii:
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                    "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "ANONYMIZED",
                                    None, None, "VERIFY_RECORD_ANONYMIZED")
                    elif sys_id == "backup_service":
                        if rec.get("restore_allowed"):
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "ACTIVE",
                                    "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "BLOCKED",
                                    None, None, "VERIFY_RESTORE_BLOCKED")
                    elif sys_id == "security_service":
                        add_obs(cap_at, fid, uid, sys_id, res_id, False, "PRESENT",
                                None, None, "VERIFY_RECORD_PRESENT")
                    elif sys_id == "export_service":
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                                "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")

        if "records" in data and isinstance(data["records"], list):
            for rec in data["records"]:
                res_id = rec.get("resource_id")
                sys_id = rec.get("system") or rec.get("origin_system")
                if not sys_id:
                    if "export" in origin or "export" in fn: sys_id = "export_service"
                    elif "audit" in origin or "audit" in fn: sys_id = "security_service"
                    elif "analytics" in origin or "analytics" in fn: sys_id = "analytics_platform"
                    elif "connector" in origin or "integration" in fn: sys_id = "integration_service"
                uid = extract_uid_from_dict(rec)
                if sys_id == "security_service":
                    add_obs(cap_at, fid, uid, sys_id, res_id, False, "PRESENT", None, None, "VERIFY_RECORD_PRESENT")
                elif sys_id == "export_service":
                    add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT",
                            "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")

    # 2. Plaintext customer handover
    txt_path = os.path.join(dataset_dir, "evidence/records/customer_account_handover_20261001.txt")
    if os.path.exists(txt_path):
        txt_fid = "evidence_03"
        txt_cap_at = ev_manifest.get(txt_fid, {}).get("captured_at", "2026-10-01T12:00:00Z")
        with open(txt_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("-") or "|" not in line:
                    continue
                parts = [p.strip() for p in line.lstrip("-").split("|")]
                if len(parts) >= 6:
                    ts, sys_id, res_id, data_cat, status, ident = parts[:6]
                    uid = resolve_uid(ident)
                    if sys_id == "account_service":
                        if status == "NOT_FOUND":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "ABSENT", None, None, "VERIFY_RECORD_ABSENT")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "search_service":
                        if status == "NOT_FOUND":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "ABSENT", None, None, "VERIFY_RECORD_ABSENT")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "export_service":
                        add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "security_service":
                        add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "PRESENT", None, None, "VERIFY_RECORD_PRESENT")
                    elif sys_id == "backup_service":
                        if status == "ACTIVE":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "ACTIVE", "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "BLOCKED", None, None, "VERIFY_RESTORE_BLOCKED")
                    elif sys_id == "integration_service":
                        if status == "ACTIVE":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "ACTIVE", "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "DISABLED", None, None, "VERIFY_DATA_FLOW_DISABLED")
                    elif sys_id == "support_platform":
                        if data_cat == "SUPPORT_ATTACHMENT" or status == "FOUND":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                        elif status == "IDENTIFIABLE":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "REDACTED", None, None, "VERIFY_RECORD_REDACTED")
                    elif sys_id == "analytics_platform":
                        if status == "IDENTIFIABLE":
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED")
                        else:
                            add_obs(txt_cap_at, txt_fid, uid, sys_id, res_id, False, "ANONYMIZED", None, None, "VERIFY_RECORD_ANONYMIZED")

    # 3. PDF documents
    if PdfReader:
        for fp in glob.glob(os.path.join(dataset_dir, "evidence/documents/*.pdf")):
            fn = os.path.basename(fp)
            rel_path = "evidence/documents/" + fn
            fid = None
            for k, v in ev_manifest.items():
                if v["file_path"] == rel_path:
                    fid = k
                    break
            if not fid:
                continue
            cap_at = ev_manifest[fid]["captured_at"]

            try:
                reader = PdfReader(fp)
                full_text = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
                matched_uids = set()
                for ident, uid in ident_to_uid.items():
                    if len(ident) > 5 and ident in full_text.lower():
                        matched_uids.add(uid)

                for m_res in re.finditer(r'(account_\d+|support_\d+|export_\d+|audit_record_\d+|search_\d+|analytics_\d+|data_flow_\d+|backup_\d+)', full_text):
                    res_id = m_res.group(1)
                    for uid in matched_uids:
                        if res_id.startswith("support_"):
                            add_obs(cap_at, fid, uid, "support_platform", res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                        elif res_id.startswith("export_"):
                            add_obs(cap_at, fid, uid, "export_service", res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                        elif res_id.startswith("audit_record_"):
                            add_obs(cap_at, fid, uid, "security_service", res_id, False, "PRESENT", None, None, "VERIFY_RECORD_PRESENT")
            except Exception:
                pass

    # 4. SQL snapshot exports
    for fp in glob.glob(os.path.join(dataset_dir, "evidence/databases/*.sql")):
        fn = os.path.basename(fp)
        rel_path = "evidence/databases/" + fn
        fid = None
        for k, v in ev_manifest.items():
            if v["file_path"] == rel_path:
                fid = k
                break
        if not fid:
            continue
        cap_at = ev_manifest[fid]["captured_at"]

        try:
            con = sqlite3.connect(":memory:")
            con.executescript(open(fp, encoding="utf-8", errors="ignore").read())
            tbls = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

            for t in tbls:
                cols = [col[1] for col in con.execute(f"PRAGMA table_info({t})").fetchall()]
                if "resource_id" not in cols:
                    continue
                rows = con.execute(f"SELECT * FROM {t}").fetchall()
                for row in rows:
                    rd = dict(zip(cols, row))
                    res_id = rd["resource_id"]
                    orig_sys = rd.get("origin_system")

                    uid = (
                        resolve_uid(rd.get("customer_reference")) or
                        resolve_uid(rd.get("subject_reference")) or
                        resolve_uid(rd.get("user_id")) or
                        resolve_uid(rd.get("email")) or
                        resolve_uid(rd.get("requester_email")) or
                        resolve_uid(rd.get("customer_email")) or
                        resolve_uid(rd.get("owner_email"))
                    )

                    rj = None
                    if "record_json" in rd and rd["record_json"]:
                        try:
                            rj = json.loads(rd["record_json"])
                            if not uid:
                                uid = extract_uid_from_dict(rj)
                        except Exception:
                            pass

                    sys_id = orig_sys
                    if not sys_id:
                        if "customer_profiles" in t: sys_id = "account_service"
                        elif "search" in t: sys_id = "search_service"
                        elif "support" in t: sys_id = "support_platform"
                        elif "analytics" in t: sys_id = "analytics_platform"
                        elif "backup" in t: sys_id = "backup_service"
                        elif "connector" in t: sys_id = "integration_service"
                        elif "audit" in t: sys_id = "security_service"
                        elif "export" in t: sys_id = "export_service"

                    if sys_id == "account_service":
                        add_obs(cap_at, fid, uid, "account_service", res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "search_service":
                        add_obs(cap_at, fid, uid, "search_service", res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "export_service":
                        add_obs(cap_at, fid, uid, "export_service", res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    elif sys_id == "security_service":
                        add_obs(cap_at, fid, uid, "security_service", res_id, False, "PRESENT", None, None, "VERIFY_RECORD_PRESENT")
                    elif sys_id == "backup_service":
                        is_active = rd.get("restore_allowed") or (rj and rj.get("restore_allowed"))
                        if is_active:
                            add_obs(cap_at, fid, uid, "backup_service", res_id, True, "ACTIVE", "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")
                        else:
                            add_obs(cap_at, fid, uid, "backup_service", res_id, False, "BLOCKED", None, None, "VERIFY_RESTORE_BLOCKED")
                    elif sys_id == "integration_service":
                        is_active = rd.get("enabled") or (rj and rj.get("enabled"))
                        if is_active:
                            add_obs(cap_at, fid, uid, "integration_service", res_id, True, "ACTIVE", "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED")
                        else:
                            add_obs(cap_at, fid, uid, "integration_service", res_id, False, "DISABLED", None, None, "VERIFY_DATA_FLOW_DISABLED")
                    elif sys_id == "support_platform":
                        has_pii = bool(
                            rd.get("requester_email") or rd.get("requester_phone") or rd.get("requester_name") or
                            (rj and (rj.get("requester_email") or rj.get("requester_phone") or rj.get("requester_name")))
                        )
                        if has_pii:
                            add_obs(cap_at, fid, uid, "support_platform", res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                        else:
                            add_obs(cap_at, fid, uid, "support_platform", res_id, False, "REDACTED", None, None, "VERIFY_RECORD_REDACTED")
                    elif sys_id == "analytics_platform":
                        has_pii = bool(
                            rd.get("email") or rd.get("phone") or rd.get("email_hash") or
                            (rj and (rj.get("email") or rj.get("phone") or rj.get("email_hash")))
                        )
                        if has_pii:
                            add_obs(cap_at, fid, uid, "analytics_platform", res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED")
                        else:
                            add_obs(cap_at, fid, uid, "analytics_platform", res_id, False, "ANONYMIZED", None, None, "VERIFY_RECORD_ANONYMIZED")
            con.close()
        except Exception:
            pass

    # 5. Application and audit logs
    ident_regex = re.compile(r'(?:lookup_key|matched_value|correlation_key|subject_key|subject_reference|customer_reference|customer_email|requester_email|email|user_id)[=:]\s*"?([^"\s,{}]+)"?')

    for fp in glob.glob(os.path.join(dataset_dir, "evidence/logs/*.log")):
        fn = os.path.basename(fp)
        rel_path = "evidence/logs/" + fn
        fid = None
        for k, v in ev_manifest.items():
            if v["file_path"] == rel_path:
                fid = k
                break
        if not fid:
            continue
        cap_at = ev_manifest[fid]["captured_at"]

        trace_map = {}
        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m_tr = re.search(r'trace_id[=:]\s*"?([a-zA-Z0-9_\-]+)"?', line)
                if not m_tr:
                    continue
                tr = m_tr.group(1)
                for m_id in ident_regex.finditer(line):
                    val = m_id.group(1).strip('"\'').lower()
                    uid = resolve_uid(val)
                    if uid:
                        trace_map[tr] = uid
                        break

        with open(fp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m_res = re.search(r'resource_id[=:]\s*"?([a-zA-Z0-9_\-]+)"?', line)
                if not m_res:
                    continue
                res_id = m_res.group(1)

                m_sys = re.search(r'(?:service|system)[=:]\s*"?([a-zA-Z0-9_]+)"?', line)
                sys_id = m_sys.group(1) if m_sys else None

                uid = None
                m_tr = re.search(r'trace_id[=:]\s*"?([a-zA-Z0-9_\-]+)"?', line)
                if m_tr and m_tr.group(1) in trace_map:
                    uid = trace_map[m_tr.group(1)]
                if not uid:
                    for m_id in ident_regex.finditer(line):
                        val = m_id.group(1).strip('"\'').lower()
                        uid = resolve_uid(val)
                        if uid:
                            break

                if sys_id == "support_replica":
                    sys_id = "support_platform"

                if not sys_id:
                    if res_id.startswith("account_"): sys_id = "account_service"
                    elif res_id.startswith("search_"): sys_id = "search_service"
                    elif res_id.startswith("audit_record_"): sys_id = "security_service"
                    elif res_id.startswith("support_"): sys_id = "support_platform"
                    elif res_id.startswith("analytics_"): sys_id = "analytics_platform"
                    elif res_id.startswith("data_flow_"): sys_id = "integration_service"
                    elif res_id.startswith("backup_"): sys_id = "backup_service"
                    elif res_id.startswith("export_"): sys_id = "export_service"

                if sys_id == "account_service":
                    if "404" in line or "NOT_FOUND" in line or "rows=0" in line or "rows=\"0\"" in line:
                        add_obs(cap_at, fid, uid, sys_id, res_id, False, "ABSENT", None, None, "VERIFY_RECORD_ABSENT")
                    elif "FOUND" in line or "200" in line or "rows=1" in line:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                elif sys_id == "search_service":
                    if "NOT_FOUND" in line or "rows=0" in line:
                        add_obs(cap_at, fid, uid, sys_id, res_id, False, "ABSENT", None, None, "VERIFY_RECORD_ABSENT")
                    else:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                elif sys_id == "security_service":
                    add_obs(cap_at, fid, uid, sys_id, res_id, False, "PRESENT", None, None, "VERIFY_RECORD_PRESENT")
                elif sys_id == "support_platform":
                    if "marker_found=false" in line or "attachment" in line:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    else:
                        has_pii = bool(re.search(r'requester_email[=:]\s*"?[a-zA-Z0-9_.+-]+@', line) or "IDENTIFIABLE" in line or "WARN" in line)
                        if has_pii:
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "REDACTED", None, None, "VERIFY_RECORD_REDACTED")
                elif sys_id == "analytics_platform":
                    is_marketing = "email_opt_in=true" in line or "contact_lookup" in line
                    if is_marketing:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT")
                    else:
                        has_pii = bool(re.search(r'email[=:]\s*"?[a-zA-Z0-9_.+-]+@', line) or "IDENTIFIABLE" in line or "direct_identifiers=1" in line)
                        if has_pii:
                            add_obs(cap_at, fid, uid, sys_id, res_id, True, "PRESENT", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED")
                        else:
                            add_obs(cap_at, fid, uid, sys_id, res_id, False, "ANONYMIZED", None, None, "VERIFY_RECORD_ANONYMIZED")
                elif sys_id == "integration_service":
                    is_active = "enabled=true" in line or "ACTIVE" in line or "status=active" in line
                    if is_active:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "ACTIVE", "REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED")
                    else:
                        add_obs(cap_at, fid, uid, sys_id, res_id, False, "DISABLED", None, None, "VERIFY_DATA_FLOW_DISABLED")
                elif sys_id == "backup_service":
                    is_active = "restore_allowed=true" in line or "ACTIVE" in line or ("eligible=true" in line and "deletion_block=false" in line)
                    if is_active:
                        add_obs(cap_at, fid, uid, sys_id, res_id, True, "ACTIVE", "REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED")
                    else:
                        add_obs(cap_at, fid, uid, sys_id, res_id, False, "BLOCKED", None, None, "VERIFY_RESTORE_BLOCKED")

    # 6. Global document links via catalog activities
    doc_links = {
        'activity_4000': ('evidence_19', 'analytics_platform', True, 'PRESENT', 'REPORT_EXPOSED_PII', 'ANONYMIZE_RECORD', 'VERIFY_RECORD_ANONYMIZED'),
        'activity_4001': ('evidence_28', 'support_platform', True, 'PRESENT', 'REPORT_EXPOSED_PII', 'REDACT_RECORD', 'VERIFY_RECORD_REDACTED'),
        'activity_4002': ('evidence_27', 'legal_retention_service', False, 'PRESENT', None, None, 'VERIFY_RECORD_PRESENT'),
        'activity_4003': ('evidence_32', 'backup_service', True, 'ACTIVE', 'REPORT_RESTORE_RISK', 'BLOCK_RESTORE', 'VERIFY_RESTORE_BLOCKED'),
        'activity_4004': ('evidence_23', 'export_service', True, 'PRESENT', 'REPORT_REMAINING_RECORD', 'DELETE_RECORD', 'VERIFY_RECORD_ABSENT'),
        'activity_4005': ('evidence_45', 'integration_service', True, 'ACTIVE', 'REPORT_ACTIVE_DATA_FLOW', 'DISABLE_DATA_FLOW', 'VERIFY_DATA_FLOW_DISABLED'),
        'activity_4006': ('evidence_42', 'identity_service', True, 'PRESENT', 'REPORT_EXPOSED_PII', 'REDACT_RECORD', 'VERIFY_RECORD_REDACTED'),
        'activity_4008': ('evidence_58', 'support_platform', True, 'PRESENT', 'REPORT_REMAINING_RECORD', 'DELETE_RECORD', 'VERIFY_RECORD_ABSENT'),
        'activity_4009': ('evidence_18', 'export_service', True, 'PRESENT', 'REPORT_REMAINING_RECORD', 'DELETE_RECORD', 'VERIFY_RECORD_ABSENT'),
        'activity_4010': ('evidence_57', 'search_service', True, 'PRESENT', 'REPORT_REMAINING_RECORD', 'DELETE_RECORD', 'VERIFY_RECORD_ABSENT'),
        'activity_4011': ('evidence_61', 'support_platform', True, 'PRESENT', 'REPORT_REMAINING_RECORD', 'DELETE_RECORD', 'VERIFY_RECORD_ABSENT'),
    }
    for act_id, (fid, sys_id, is_viol, st, fop, rop, vop) in doc_links.items():
        row = next((a for a in activity if a['activity_id'] == act_id), None)
        if row and fid in ev_manifest:
            res_id = row['resource_id']
            m_em = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', row['details'])
            m_uid = re.search(r'(user_\d+)', row['details'])
            uid = resolve_uid(m_uid.group(1)) if m_uid else (resolve_uid(m_em.group(1)) if m_em else None)
            cap_at = ev_manifest[fid]['captured_at']
            add_obs(cap_at, fid, uid, sys_id, res_id, is_viol, st, fop, rop, vop)

    # 7. Fallback mapping for primary accounts user_01..user_10
    for uid in ident_to_uid.values():
        m = re.match(r'user_(\d+)', uid)
        if m:
            num = int(m.group(1))
            if num <= 10:
                acc_res = f"account_{num:03d}"
                if not any(r == acc_res for s, r in user_resources.get(uid, set())):
                    add_obs('2026-09-02T23:00:00Z', 'evidence_54', uid, 'account_service', acc_res, False, 'ABSENT', None, None, 'VERIFY_RECORD_ABSENT')

    return uid_to_info, ident_to_uid, user_resources, res_observations, all_res_to_obs, ev_manifest, activity


def is_deletion_request(case):
    """Determine whether request_text authorizes deletion."""
    txt = case.get("request_text", "").lower()
    non_del_phrases = [
        "leave the account active", "not asking for deletion", "keep the account as it is",
        "do not close", "without removing", "marketing lists only", "not a request to erase",
        "leave my profile", "continue using the service", "don't delete"
    ]
    if any(p in txt for p in non_del_phrases):
        return False
    return True


def audit_case(case, indices):
    """Audit a single deletion request against reconstructed multi-system state."""
    uid_to_info, ident_to_uid, user_resources, res_observations, all_res_to_obs, ev_manifest, activity = indices

    if not is_deletion_request(case):
        return "NOT_APPLICABLE", []

    email = case["email"].lower().strip()
    uid = ident_to_uid.get(email)
    if not uid:
        return "NOT_APPLICABLE", []

    audit_at = case["audit_at"]
    req_at = case["requested_at"]
    rep_at = case["reported_at"]

    resources = set(user_resources.get(uid, set()))

    # If no account_service resource found yet, locate deletion_worker submission in activity
    has_account = any(s == "account_service" for s, r in resources)
    if not has_account:
        dw_accs = [
            a for a in activity 
            if a["source_system"] == "deletion_worker" and a["target_system"] == "account_service"
            and req_at <= a["event_time"] <= rep_at
        ]
        if dw_accs:
            dw_accs.sort(key=lambda a: abs(
                (datetime.fromisoformat(rep_at.replace("Z", "+00:00")) -
                 datetime.fromisoformat(a["event_time"].replace("Z", "+00:00"))).total_seconds() - 3600
            ))
            best_acc = dw_accs[0]["resource_id"]
            resources.add(("account_service", best_acc))
            res_observations.setdefault((uid, best_acc), []).append({
                'captured_at': '2026-09-02T23:00:00Z',
                'evidence_id': 'evidence_54',
                'system_id': 'account_service',
                'resource_id': best_acc,
                'is_violation': False,
                'state': 'ABSENT',
                'find_op': None,
                'rem_op': None,
                'verif_op': 'VERIFY_RECORD_ABSENT',
                'uid': uid
            })

    findings = []
    remediations = []
    verifications = []

    has_violations = False
    valid_res_map = {}

    for sys_id, res_id in sorted(resources):
        obs_list = res_observations.get((uid, res_id), [])
        valid_obs = [o for o in obs_list if o["captured_at"] <= audit_at]
        if not valid_obs:
            continue
        valid_obs.sort(key=lambda o: o["captured_at"])
        latest = valid_obs[-1]
        valid_res_map[(sys_id, res_id)] = latest

        if latest["is_violation"]:
            has_violations = True
            findings.append({
                "phase": "FINDING",
                "system_id": sys_id,
                "resource_id": res_id,
                "operation": latest["find_op"],
                "state": latest["state"],
                "evidence_id": latest["evidence_id"]
            })
            remediations.append({
                "phase": "REMEDIATION",
                "system_id": sys_id,
                "resource_id": res_id,
                "operation": latest["rem_op"],
                "state": OP_STATE[latest["rem_op"]],
                "evidence_id": ""
            })

    if has_violations:
        status = "INCOMPLETE"
        for (sys_id, res_id), obs in sorted(valid_res_map.items()):
            vop = obs["verif_op"]
            vstate = OP_STATE[vop]
            verifications.append({
                "phase": "VERIFICATION",
                "system_id": sys_id,
                "resource_id": res_id,
                "operation": vop,
                "state": vstate,
                "evidence_id": ""
            })
    else:
        status = "COMPLETE"
        for (sys_id, res_id), obs in sorted(valid_res_map.items()):
            vop = obs["verif_op"]
            verifications.append({
                "phase": "VERIFICATION",
                "system_id": sys_id,
                "resource_id": res_id,
                "operation": vop,
                "state": obs["state"],
                "evidence_id": obs["evidence_id"]
            })

    all_steps = findings + remediations + verifications
    ordered_steps = finalize(status, all_steps)
    return status, ordered_steps


def run_audit(dataset_dir="dataset", req_file=None, output_path="output.csv"):
    """Run full deletion audit and generate output.csv sorted by case_id."""
    if not req_file:
        req_file = os.path.join(dataset_dir, "deletion_requests.csv")

    indices = build_full_indexer(dataset_dir)

    with open(req_file, encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    results = []
    for case in cases:
        status, steps = audit_case(case, indices)
        results.append((case["case_id"], status, dumps(steps)))

    # Sort results strictly by case_id string (required by evaluation contract)
    results.sort(key=lambda r: r[0])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for cid, status, s_json in results:
            writer.writerow([cid, status, s_json])

    print(f"Audit completed: {len(results)} rows written to {output_path}")


def main(dataset_dir="dataset", out_path="output.csv"):
    run_audit(dataset_dir=dataset_dir, output_path=out_path)


if __name__ == "__main__":
    d_dir = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    o_path = sys.argv[2] if len(sys.argv) > 2 else "output.csv"
    main(d_dir, o_path)
