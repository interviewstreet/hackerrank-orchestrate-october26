"""Steps and status from per-target decisions (plan 9.8, decision 4).

* FINDING: one per proven violation, citing its evidence.
* REMEDIATION: one per violation with an action, evidence ``""``.
* VERIFICATION: one per target. COMPLETE cites the proof; INCOMPLETE uses ``""``.
* A stale target (links only before ``requested_at``) gets steps only as a proven violation.
* Canonical sort and step numbers come from ``schema.step_sort_key``.
* Every planned remediation passes ``policy.check_safety``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from citation import cite
from links import Target
from policy import COMPLIANT, MISSING_RETAINED, NOT_TARGET, VIOLATION, Decision, check_safety
from resolver import ResourceState, Statement
from schema import OP_PHASE, OP_STATE, Operation, Status, step_sort_key

STRONG_KINDS = ("identifier", "catalog_link")


@dataclass
class Item:
    """One target with its resolved state, policy decision and citation."""
    target: Target
    state: ResourceState
    decision: Decision
    evidence_id: str = ""
    support: list[Statement] = field(default_factory=list)

    @property
    def violation(self) -> bool:
        return self.decision.outcome == VIOLATION and bool(self.evidence_id)

    @property
    def proven_compliant(self) -> bool:
        return self.decision.outcome == COMPLIANT and bool(self.evidence_id)


def build_item(target: Target, state: ResourceState, decision: Decision) -> Item:
    item = Item(target, state, decision)
    if decision.outcome in (VIOLATION, COMPLIANT):
        item.evidence_id, item.support = cite(state, decision, violating=decision.outcome == VIOLATION)
    return item


def decide_status(items: list[Item]) -> str:
    """Decision 4, the only status rule.

    INCOMPLETE if at least one violation is proven by evidence (a missing retained record
    proven absent counts); else COMPLETE when at least one target is proven compliant;
    else INCOMPLETE (nothing can be proven).
    """
    if any(i.violation or (i.decision.outcome == MISSING_RETAINED and i.state.known) for i in items):
        return Status.INCOMPLETE.value
    if any(i.proven_compliant for i in items):
        return Status.COMPLETE.value
    return Status.INCOMPLETE.value


def _step(op: Operation, item: Item, evidence_id: str) -> dict:
    return {"step_no": 0, "phase": str(OP_PHASE[op]), "system_id": item.target.system_id,
            "resource_id": item.target.resource_id, "operation": op.value, "state": str(OP_STATE[op]),
            "evidence_id": evidence_id}


def _safety(item: Item) -> None:
    tgt = item.target
    foreign_only = bool(tgt.shared_with) and not any(e.kind in STRONG_KINDS for e in tgt.edges)
    assertions = [s.obs.assertion if s.obs is not None else "scoped_absence" for s in item.support]
    check_safety(item.decision, foreign_only=foreign_only, proof_assertions=assertions)


def plan(items: list[Item]) -> tuple[str, list[dict]]:
    items = [i for i in items if i.decision.outcome != NOT_TARGET and (i.violation or not i.target.stale)]
    status = decide_status(items)
    steps: list[dict] = []
    for item in items:
        _safety(item)
        d = item.decision
        if status == Status.COMPLETE.value:
            if item.proven_compliant:
                steps.append(_step(d.verification, item, item.evidence_id))
            continue
        if item.violation:
            if d.finding is not None:
                steps.append(_step(d.finding, item, item.evidence_id))
            if d.remediation is not None:
                steps.append(_step(d.remediation, item, ""))
        if d.verification is not None:
            steps.append(_step(d.verification, item, ""))
    steps.sort(key=step_sort_key)
    for n, step in enumerate(steps, start=1):
        step["step_no"] = n
    return status, steps
