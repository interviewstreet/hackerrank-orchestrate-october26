"""Policy and contract invariants every output row must satisfy (independent of any answer key)."""
from __future__ import annotations

import json
from typing import Dict, Iterable, List

# resource-id prefix -> operations that may legitimately be applied to it (from deletion_rules.csv)
ALLOWED_OPS: Dict[str, set] = {
    "account_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "search_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "cache_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "export_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "marketing_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "support_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "DELETE_RECORD", "VERIFY_RECORD_ABSENT",
                 "REDACT_RECORD", "VERIFY_RECORD_REDACTED"},
    "analytics_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED",
                   "DELETE_RECORD", "VERIFY_RECORD_ABSENT"},
    "tombstone_": {"REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"},
    "data_flow_": {"REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"},
    "backup_": {"REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"},
    "audit_record_": {"VERIFY_RECORD_PRESENT"},        # retained: never deleted, redacted or anonymized
    "legal_hold_": {"VERIFY_RECORD_PRESENT"},
}


def check_rows(rows: Iterable[Dict[str, str]], audit_at_by_case: Dict[str, str],
               captured_at: Dict[str, str]) -> List[str]:
    """rows: dicts with case_id, deletion_status, steps_json. Returns a list of violations (empty = clean)."""
    bad: List[str] = []
    for r in rows:
        cid, status = r["case_id"], r["deletion_status"]
        steps = json.loads(r["steps_json"])
        if status == "NOT_APPLICABLE" and steps:
            bad.append(f"{cid}: NOT_APPLICABLE with steps")
        if status == "COMPLETE" and any(s["phase"] == "REMEDIATION" for s in steps):
            bad.append(f"{cid}: COMPLETE but has remediation steps")
        if status == "INCOMPLETE" and steps and not any(s["phase"] != "VERIFICATION" for s in steps):
            bad.append(f"{cid}: INCOMPLETE with only verification steps")
        for s in steps:
            for prefix, ops in ALLOWED_OPS.items():
                if s["resource_id"].startswith(prefix) and s["operation"] not in ops:
                    bad.append(f"{cid}: {s['operation']} not allowed on {s['resource_id']}")
            e = s["evidence_id"]
            if status == "INCOMPLETE" and s["phase"] == "REMEDIATION" and e:
                bad.append(f"{cid}: remediation step cites evidence")
            if e and captured_at.get(e, "9") > audit_at_by_case[cid]:
                bad.append(f"{cid}: {e} captured after audit_at")
            if status == "COMPLETE" and s["phase"] in ("FINDING", "VERIFICATION") and not e:
                bad.append(f"{cid}: COMPLETE {s['phase']} step without evidence")
    return bad
