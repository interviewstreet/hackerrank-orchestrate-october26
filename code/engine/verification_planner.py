"""Verification planner: the final state every relevant resource must be in."""
from __future__ import annotations

from typing import Dict, List

from .policy_engine import Decision


def plan_verification(decisions: List[Decision], complete: bool) -> List[Dict[str, str]]:
    """COMPLETE case: cite the evidence that proves the compliant state at audit_at.
    INCOMPLETE case: these are future checks, so evidence_id is empty."""
    rows = []
    for d in decisions:
        if not d.verification_op:
            continue
        rows.append({"system_id": d.system_id, "resource_id": d.resource_id, "operation": d.verification_op,
                     "evidence_id": d.evidence_id if complete else ""})
    return rows
