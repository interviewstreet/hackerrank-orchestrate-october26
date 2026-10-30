"""Turns per-resource decisions into FINDING / REMEDIATION / VERIFICATION steps (SPEC §5 steps 6-9)."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Kind, Step
from .policy import COMPLIANT, TREATMENTS, Decision
from .state import ResourceState


@dataclass
class ResourcePlan:
    system_id: str
    resource_id: str
    decision: Decision
    state: ResourceState
    link: str               # how ownership was established

    @property
    def compliant(self) -> bool:
        return self.state.kind in COMPLIANT[self.decision.treatment]

    @property
    def required_state(self) -> str:
        return TREATMENTS[self.decision.treatment][0]


def violation_finding(plan: ResourcePlan) -> str | None:
    """Finding operation for a non-compliant resource, refined by what is actually wrong."""
    _, finding, _, _ = TREATMENTS[plan.decision.treatment]
    if plan.decision.treatment in {"REDACT", "ANONYMIZE"} and plan.state.kind == Kind.PRESENT:
        return finding
    return finding


def build_steps(plans: list[ResourcePlan]) -> tuple[str, list[Step]]:
    incomplete = [p for p in plans if not p.compliant and TREATMENTS[p.decision.treatment][1]]
    steps: list[Step] = []
    if not incomplete:
        for p in plans:
            if not p.state.evidence_id:
                continue  # a COMPLETE case verifies only what evidence proves; an unproven state is not a check
            verify = TREATMENTS[p.decision.treatment][3]
            steps.append(Step("VERIFICATION", p.system_id, p.resource_id, verify,
                              _state(verify), p.state.evidence_id))
        return "COMPLETE", steps
    for p in incomplete:
        _, finding, remediation, _ = TREATMENTS[p.decision.treatment]
        steps.append(Step("FINDING", p.system_id, p.resource_id, finding, _finding_state(finding), p.state.evidence_id))
        steps.append(Step("REMEDIATION", p.system_id, p.resource_id, remediation, _state(remediation), ""))
    for p in plans:
        verify = TREATMENTS[p.decision.treatment][3]
        steps.append(Step("VERIFICATION", p.system_id, p.resource_id, verify, _state(verify), ""))
    return "INCOMPLETE", steps


def _state(op: str) -> str:
    from .policy import STATE_OF_OP
    return STATE_OF_OP[op]


def _finding_state(op: str) -> str:
    from .policy import FINDING_STATE
    return FINDING_STATE[op]
