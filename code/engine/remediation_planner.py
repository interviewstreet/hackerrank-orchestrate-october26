"""Remediation planner: ordered proposed actions (never claimed as executed, so evidence_id is always empty)."""
from __future__ import annotations

from typing import Dict, List

from .policy_engine import Decision


def plan_remediation(violations: List[Decision]) -> List[Dict[str, str]]:
    """One action per violating resource. Ordering is applied later by operation order, system_id, resource_id:
    DISABLE_DATA_FLOW and BLOCK_RESTORE come before any DELETE/REDACT/ANONYMIZE, so nothing can recreate a record
    that has just been cleaned."""
    return [{"system_id": d.system_id, "resource_id": d.resource_id, "operation": d.remediation_op, "evidence_id": ""}
            for d in violations if d.remediation_op]
