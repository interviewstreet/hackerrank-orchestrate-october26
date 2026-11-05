"""Ghost detection: turn policy decisions into findings (only when the evidence supports them)."""
from __future__ import annotations

from typing import Dict, List

from .policy_engine import Decision


def detect_findings(decisions: List[Decision]) -> List[Dict[str, str]]:
    return [{"system_id": d.system_id, "resource_id": d.resource_id, "operation": d.finding_op,
             "evidence_id": d.evidence_id, "reason": d.reason}
            for d in decisions if d.finding_op]
