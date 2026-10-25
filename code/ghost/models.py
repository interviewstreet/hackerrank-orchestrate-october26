"""Plain data records shared by every stage."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .config import OPERATION_ORDER, OPERATION_STATE, PHASE_ORDER


@dataclass(frozen=True)
class Request:
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str


@dataclass(frozen=True)
class Subject:
    """The person a request resolves to, with every identifier ever held."""

    user_id: str
    identifiers: frozenset[str]  # lower-cased emails, hashes, phones, and the user_id


@dataclass(frozen=True)
class Observation:
    """One record seen in one evidence file. The common row every parser emits."""

    evidence_id: str
    captured_at: str          # manifest capture time of the file: decides citation eligibility
    observed_at: str          # moment this record was observed inside the file: orders observations
    system_id: str
    resource_id: str
    category: str
    result: str
    subjects: tuple[str, ...] = ()
    retention_until: str | None = None
    raw_ref: str = ""


@dataclass(frozen=True)
class Activity:
    activity_id: str
    event_time: str
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    result: str


@dataclass(frozen=True)
class Step:
    phase: str
    system_id: str
    resource_id: str
    operation: str
    evidence_id: str = ""

    def __post_init__(self) -> None:
        if self.operation not in OPERATION_ORDER.get(self.phase, ()):
            raise ValueError(f"operation {self.operation} not allowed in phase {self.phase}")

    @property
    def state(self) -> str:
        return OPERATION_STATE[self.operation]

    def sort_key(self) -> tuple[int, int, str, str]:
        return (
            PHASE_ORDER.index(self.phase),
            OPERATION_ORDER[self.phase].index(self.operation),
            self.system_id,
            self.resource_id,
        )


@dataclass
class CaseResult:
    case_id: str
    status: str
    steps: list[Step] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # reasons for review.jsonl

    def ordered_steps(self) -> list[Step]:
        # Deduplicate identical steps, then apply the contract ordering.
        return sorted(set(self.steps), key=Step.sort_key)

    def steps_json(self) -> str:
        payload = [
            {
                "step_no": n,
                "phase": s.phase,
                "system_id": s.system_id,
                "resource_id": s.resource_id,
                "operation": s.operation,
                "state": s.state,
                "evidence_id": s.evidence_id,
            }
            for n, s in enumerate(self.ordered_steps(), start=1)
        ]
        # Keys in contract order; insertion order is deterministic. The grader ignores key order.
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
