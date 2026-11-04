"""Policy engine: applies deletion_rules.csv to a reconstructed resource state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .dataset_loader import DatasetContext
from .state_reconstructor import ResourceState

ACTION_TO_FINAL = {"DELETE": "ABSENT", "REDACT": "REDACTED", "ANONYMIZE": "ANONYMIZED", "RETAIN": "PRESENT"}
VERIFY_OP = {"ABSENT": "VERIFY_RECORD_ABSENT", "PRESENT": "VERIFY_RECORD_PRESENT", "REDACTED": "VERIFY_RECORD_REDACTED",
             "ANONYMIZED": "VERIFY_RECORD_ANONYMIZED", "DISABLED": "VERIFY_DATA_FLOW_DISABLED", "BLOCKED": "VERIFY_RESTORE_BLOCKED"}


@dataclass
class Decision:
    resource_id: str
    system_id: str
    category: str
    rule_id: str
    required_action: str          # DELETE | REDACT | ANONYMIZE | RETAIN | DISABLE | BLOCK_RESTORE
    required_final_state: str     # ABSENT | REDACTED | ANONYMIZED | PRESENT | DISABLED | BLOCKED
    compliant: bool
    finding_op: str = ""          # REPORT_* when non-compliant
    remediation_op: str = ""
    verification_op: str = ""
    evidence_id: str = ""
    reason: str = ""


def evaluate(ctx: DatasetContext, rs: ResourceState, audit_at: str) -> Optional[Decision]:
    cat = rs.category
    base = dict(resource_id=rs.resource_id, system_id=rs.system_id, category=cat, evidence_id=rs.evidence_id)

    if cat == "DATA_FLOW":       # not in deletion_rules.csv: an active flow that can copy/recreate data must be disabled
        active = rs.state == "ACTIVE"
        return Decision(**base, rule_id="problem_statement", required_action="DISABLE", required_final_state="DISABLED",
                        compliant=not active, finding_op="REPORT_ACTIVE_DATA_FLOW" if active else "",
                        remediation_op="DISABLE_DATA_FLOW" if active else "", verification_op=VERIFY_OP["DISABLED"],
                        reason="active data flow can copy or recreate the subject's data" if active else "data flow not active")

    rule = ctx.rules.get(cat)
    if rule is None:
        return None
    action = rule["required_action"]

    if cat == "BACKUP_ARCHIVE":  # RETAIN, but restore access must be blockable/blocked
        risk = rs.state == "ACTIVE"
        return Decision(**base, rule_id=rule["rule_id"], required_action="BLOCK_RESTORE", required_final_state="BLOCKED",
                        compliant=not risk, finding_op="REPORT_RESTORE_RISK" if risk else "",
                        remediation_op="BLOCK_RESTORE" if risk else "", verification_op=VERIFY_OP["BLOCKED"],
                        reason="archive can still be restored" if risk else "restore access is blocked")

    final = ACTION_TO_FINAL[action]
    present = rs.state in ("PRESENT", "ACTIVE")
    if action == "DELETE":
        bad = present
        return Decision(**base, rule_id=rule["rule_id"], required_action=action, required_final_state=final, compliant=not bad,
                        finding_op="REPORT_REMAINING_RECORD" if bad else "", remediation_op="DELETE_RECORD" if bad else "",
                        verification_op=VERIFY_OP[final], reason="record must be deleted" if bad else "record absent")
    if action in ("REDACT", "ANONYMIZE"):
        bad = present and rs.exposed
        rem = "REDACT_RECORD" if action == "REDACT" else "ANONYMIZE_RECORD"
        return Decision(**base, rule_id=rule["rule_id"], required_action=action, required_final_state=final, compliant=not bad,
                        finding_op="REPORT_EXPOSED_PII" if bad else "", remediation_op=rem if bad else "",
                        verification_op=VERIFY_OP[final],
                        reason=f"still exposes {', '.join(rs.exposed_fields)}" if bad else "no prohibited identifiers")
    # RETAIN (security audit log, legal hold): must remain available; never delete
    return Decision(**base, rule_id=rule["rule_id"], required_action=action, required_final_state=final, compliant=True,
                    verification_op=VERIFY_OP[final], reason="policy requires retention")
