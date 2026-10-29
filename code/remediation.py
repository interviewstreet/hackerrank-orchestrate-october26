# code/remediation.py
"""Remediation planning utilities for Stage 4.

Generates ordered FINDING → REMEDIATION → VERIFICATION steps for
incomplete deletion requests. The steps conform to the contract
defined in AGENTS.md / problem_statement.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Set

# Operation / state tables from the contract (enhanced mapping)
FINDING_OP_MAP = {
    "DELETE": "REPORT_REMAINING_RECORD",
    "REDACT": "REPORT_EXPOSED_PII",
    "ANONYMIZE": "REPORT_EXPOSED_PII",
    "RETAIN": "REPORT_REMAINING_RECORD",  # treat as presence check
    "LEGAL_HOLD": "REPORT_ACTIVE_DATA_FLOW",
    "BACKUP": "REPORT_RESTORE_RISK",
}
FINDING_STATE_MAP = {
    "DELETE": "PRESENT",
    "REDACT": "PRESENT",
    "ANONYMIZE": "PRESENT",
    "RETAIN": "PRESENT",
    "LEGAL_HOLD": "ACTIVE",
    "BACKUP": "ACTIVE",
}
# Remediation operation/state per action
REMediation_OP_MAP = {
    "DELETE": "DELETE_RECORD",
    "REDACT": "REDACT_RECORD",
    "ANONYMIZE": "ANONYMIZE_RECORD",
    "RETAIN": None,  # no remediation needed
    "LEGAL_HOLD": "BLOCK_RESTORE",
    "BACKUP": "DISABLE_DATA_FLOW",
}
REMediation_STATE_MAP = {
    "DELETE": "ABSENT",
    "REDACT": "REDACTED",
    "ANONYMIZE": "ANONYMIZED",
    "LEGAL_HOLD": "BLOCKED",
    "BACKUP": "DISABLED",
}
VERIFICATION_OP_MAP = {
    "DELETE": "VERIFY_RECORD_ABSENT",
    "REDACT": "VERIFY_RECORD_REDACTED",
    "ANONYMIZE": "VERIFY_RECORD_ANONYMIZED",
    "RETAIN": "VERIFY_RECORD_PRESENT",
    "LEGAL_HOLD": "VERIFY_RESTORE_BLOCKED",
    "BACKUP": "VERIFY_DATA_FLOW_DISABLED",
}
VERIFICATION_STATE_MAP = {
    "DELETE": "ABSENT",
    "REDACT": "REDACTED",
    "ANONYMIZE": "ANONYMIZED",
    "RETAIN": "PRESENT",
    "LEGAL_HOLD": "BLOCKED",
    "BACKUP": "DISABLED",
}

def _category_to_resource_id(category: str) -> str:
    """Derive a deterministic resource identifier from a data category.
    This is a simple placeholder used for demonstration purposes.
    """
    return f"{category}_resource"

def _extract_system_id_from_path(file_path: str) -> str:
    """Extract the system identifier from an evidence file path.
    Expected layout: dataset/evidence/<system_id>/... (any deeper folders).
    Returns 'unknown' if the pattern cannot be resolved.
    """
    try:
        parts = Path(file_path).parts
        # Find the index of "evidence" and return the next part
        idx = parts.index("evidence")
        return parts[idx + 1]
    except Exception:
        return "unknown"

def generate_steps(
    case_id: str,
    missing_categories: Set[str],
    evidence_info: Dict[str, Dict[str, str]],
) -> List[Dict]:
    """Generate a list of step dictionaries for an incomplete case.

    Args:
        case_id: Identifier of the request (used only for ordering).
        missing_categories: Set of data_category strings for which deletion
            evidence (DELETE_CONFIRMED) was not found.
        evidence_info: Mapping data_category → {"evidence_id": str, "system_id": str}.
            May be empty for categories without examined evidence.
    Returns:
        Ordered list of step dicts complying with the required schema.
    """
    steps: List[Dict] = []
    step_no = 1
    for cat in sorted(missing_categories):
        resource_id = _category_to_resource_id(cat)
        info = evidence_info.get(cat, {})
        system_id = info.get("system_id", "unknown")
        evidence_id = info.get("evidence_id", "")
        # FINDING step (evidence‑backed)
        steps.append({
            "step_no": step_no,
            "phase": "FINDING",
            "system_id": system_id,
            "resource_id": resource_id,
            "operation": FINDING_OP_MAP.get(cat.upper(), FINDING_OP_MAP["DELETE"]),
            "state": FINDING_STATE_MAP.get(cat.upper(), FINDING_STATE_MAP["DELETE"]),
            "evidence_id": evidence_id,
        })
        step_no += 1
        # REMEDIATION step (future action, no evidence)
        # For current implementation, all missing categories are DELETE actions
        rem_op = REMediation_OP_MAP.get('DELETE')
        rem_state = REMediation_STATE_MAP.get('DELETE')
        if rem_op:
            steps.append({
                "step_no": step_no,
                "phase": "REMEDIATION",
                "system_id": system_id,
                "resource_id": resource_id,
                "operation": rem_op,
                "state": rem_state,
                "evidence_id": "",
            })
            step_no += 1
        # VERIFICATION step (use DELETE verification)
        steps.append({
            "step_no": step_no,
            "phase": "VERIFICATION",
            "system_id": system_id,
            "resource_id": resource_id,
            "operation": VERIFICATION_OP_MAP.get('DELETE'),
            "state": VERIFICATION_STATE_MAP.get('DELETE'),
            "evidence_id": "",
        })
        step_no += 1
    return steps

# Helper used by main to compute missing categories and map evidence
def plan_remediation(
    request: Dict[str, str],
    identities: List[Dict[str, str]],
    audit_log: List[Dict[str, str]],
    system_activity: List[Dict[str, str]],
    deletion_rules: List[Dict[str, str]],
    evidence_files: List[Dict[str, str]],
) -> List[Dict]:
    """High‑level wrapper that determines missing DELETE categories and calls
    ``generate_steps``. Returns an empty list for COMPLETE or NOT_APPLICABLE.
    """
    from .decision import classify_requests
    # Re‑use decision logic to obtain status for a single request
    classification = classify_requests(
        [request], identities, audit_log, system_activity, deletion_rules, evidence_files
    )
    status = classification.get(request["case_id"], "INCOMPLETE")
    if status != "INCOMPLETE":
        return []

    audit_at = request["audit_at"]
    from .resolve import filter_evidence
    evid_cut = filter_evidence(evidence_files, audit_at)
    # Build maps: category -> evidence_id and category -> system_id (from first matching file)
    evidence_info: Dict[str, Dict[str, str]] = {}
    for ev in evid_cut:
        path = ev.get("file_path", "").lower()
        for rule in deletion_rules:
            if rule.get("required_action", "").strip().upper() != "DELETE":
                continue
            cat = rule.get("data_category", "").strip().lower()
            if not cat:
                continue
            if cat in path:
                # Read file content to check for marker
                try:
                    txt = Path(ev["file_path"]).read_text(encoding="utf-8")
                except Exception:
                    txt = ""
                if "DELETE_CONFIRMED" in txt:
                    # Evidence proves deletion – do not consider missing
                    continue
                # Record first evidence examined for this category
                if cat not in evidence_info:
                    evidence_info[cat] = {
                        "evidence_id": ev.get("file_id", ""),
                        "system_id": _extract_system_id_from_path(ev.get("file_path", "")),
                    }
    # Determine missing categories – those for which we have examined evidence but no DELETE_CONFIRMED marker.
    # These are exactly the categories recorded in evidence_info.
    missing: Set[str] = set(evidence_info.keys())
    return generate_steps(request["case_id"], missing, evidence_info)
