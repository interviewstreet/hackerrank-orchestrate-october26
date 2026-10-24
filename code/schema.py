"""Single source of truth for the output contract (decision D21).

Enums, the allowed phase/operation/state table, the canonical step order and the
Pydantic v2 models live here. The validator, the pipeline, the intent rules and
(later) prompts and LLM-output checks import from this module only.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

HEADER = ("case_id", "deletion_status", "steps_json")


class Status(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReportedStatus(StrEnum):
    """The workflow's claim in deletion_requests.csv. A claim, never proof."""
    COMPLETE = "COMPLETE"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    NOT_STARTED = "NOT_STARTED"


class Phase(StrEnum):
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class Operation(StrEnum):
    REPORT_REMAINING_RECORD = "REPORT_REMAINING_RECORD"
    REPORT_EXPOSED_PII = "REPORT_EXPOSED_PII"
    REPORT_ACTIVE_DATA_FLOW = "REPORT_ACTIVE_DATA_FLOW"
    REPORT_RESTORE_RISK = "REPORT_RESTORE_RISK"
    DISABLE_DATA_FLOW = "DISABLE_DATA_FLOW"
    BLOCK_RESTORE = "BLOCK_RESTORE"
    DELETE_RECORD = "DELETE_RECORD"
    REDACT_RECORD = "REDACT_RECORD"
    ANONYMIZE_RECORD = "ANONYMIZE_RECORD"
    VERIFY_RECORD_ABSENT = "VERIFY_RECORD_ABSENT"
    VERIFY_RECORD_PRESENT = "VERIFY_RECORD_PRESENT"
    VERIFY_RECORD_REDACTED = "VERIFY_RECORD_REDACTED"
    VERIFY_RECORD_ANONYMIZED = "VERIFY_RECORD_ANONYMIZED"
    VERIFY_DATA_FLOW_DISABLED = "VERIFY_DATA_FLOW_DISABLED"
    VERIFY_RESTORE_BLOCKED = "VERIFY_RESTORE_BLOCKED"


class StepState(StrEnum):
    PRESENT = "PRESENT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
    ABSENT = "ABSENT"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"


class IntentLabel(StrEnum):
    DELETE = "DELETE"
    VERIFY_DELETE = "VERIFY_DELETE"   # "check that my deletion happened" - counts as deletion
    NOT_DELETION = "NOT_DELETION"
    AMBIGUOUS = "AMBIGUOUS"           # rules cannot decide; Phase 4 sends these to the model


DELETION_INTENTS = (IntentLabel.DELETE, IntentLabel.VERIFY_DELETE)

# (phase, operation, state) in the mandated table order. Index = sort rank.
OPERATIONS: tuple[tuple[Phase, Operation, StepState], ...] = (
    (Phase.FINDING, Operation.REPORT_REMAINING_RECORD, StepState.PRESENT),
    (Phase.FINDING, Operation.REPORT_EXPOSED_PII, StepState.PRESENT),
    (Phase.FINDING, Operation.REPORT_ACTIVE_DATA_FLOW, StepState.ACTIVE),
    (Phase.FINDING, Operation.REPORT_RESTORE_RISK, StepState.ACTIVE),
    (Phase.REMEDIATION, Operation.DISABLE_DATA_FLOW, StepState.DISABLED),
    (Phase.REMEDIATION, Operation.BLOCK_RESTORE, StepState.BLOCKED),
    (Phase.REMEDIATION, Operation.DELETE_RECORD, StepState.ABSENT),
    (Phase.REMEDIATION, Operation.REDACT_RECORD, StepState.REDACTED),
    (Phase.REMEDIATION, Operation.ANONYMIZE_RECORD, StepState.ANONYMIZED),
    (Phase.VERIFICATION, Operation.VERIFY_RECORD_ABSENT, StepState.ABSENT),
    (Phase.VERIFICATION, Operation.VERIFY_RECORD_PRESENT, StepState.PRESENT),
    (Phase.VERIFICATION, Operation.VERIFY_RECORD_REDACTED, StepState.REDACTED),
    (Phase.VERIFICATION, Operation.VERIFY_RECORD_ANONYMIZED, StepState.ANONYMIZED),
    (Phase.VERIFICATION, Operation.VERIFY_DATA_FLOW_DISABLED, StepState.DISABLED),
    (Phase.VERIFICATION, Operation.VERIFY_RESTORE_BLOCKED, StepState.BLOCKED),
)
PHASE_ORDER: tuple[Phase, ...] = tuple(Phase)
OP_RANK: dict[str, int] = {op.value: i for i, (_, op, _) in enumerate(OPERATIONS)}
OP_PHASE: dict[str, Phase] = {op.value: phase for phase, op, _ in OPERATIONS}
OP_STATE: dict[str, StepState] = {op.value: state for _, op, state in OPERATIONS}
STEP_KEYS = frozenset({"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"})


def step_sort_key(step: dict) -> tuple:
    """Mandated order: phase, operation table order, system_id, resource_id."""
    return (PHASE_ORDER.index(step["phase"]), OP_RANK[step["operation"]], step["system_id"], step["resource_id"])


# ------------------------------------------------------------------ models

class Step(BaseModel):
    """One step object. Field names and types match the contract exactly."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_no: StrictInt = Field(ge=1)
    phase: Phase
    system_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    operation: Operation
    state: StepState
    evidence_id: str

    @model_validator(mode="after")
    def _allowed_pair(self) -> "Step":
        if OP_PHASE[self.operation] != self.phase:
            raise ValueError(f"operation {self.operation} is not allowed in phase {self.phase}")
        if OP_STATE[self.operation] != self.state:
            raise ValueError(f"operation {self.operation} needs state {OP_STATE[self.operation]}")
        return self

    def as_dict(self) -> dict:
        return {k: (v.value if isinstance(v, StrEnum) else v) for k, v in self.model_dump().items()}


class OutputRow(BaseModel):
    """One output row. Checks every row-level rule except "deletion rows need steps",
    which ``validate.py`` enforces (it has the Phase 1 placeholder switch)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^case_\d+$")
    deletion_status: Status
    steps: tuple[Step, ...] = ()

    @model_validator(mode="after")
    def _row_rules(self) -> "OutputRow":
        steps = self.steps
        if self.deletion_status == Status.NOT_APPLICABLE and steps:
            raise ValueError("NOT_APPLICABLE must have no steps")
        if [s.step_no for s in steps] != list(range(1, len(steps) + 1)):
            raise ValueError("step_no must be 1..n consecutive")
        keys = [step_sort_key(s.as_dict()) for s in steps]
        if keys != sorted(keys):
            raise ValueError("steps are not in canonical order")
        for s in steps:
            if self.deletion_status == Status.COMPLETE:
                if s.phase != Phase.VERIFICATION or not s.evidence_id:
                    raise ValueError("COMPLETE allows only VERIFICATION steps with evidence")
            elif self.deletion_status == Status.INCOMPLETE:
                if s.phase == Phase.FINDING and not s.evidence_id:
                    raise ValueError("FINDING must cite evidence")
                if s.phase != Phase.FINDING and s.evidence_id:
                    raise ValueError(f"INCOMPLETE {s.phase} must have evidence_id \"\"")
        return self

    def steps_as_dicts(self) -> list[dict]:
        return [s.as_dict() for s in self.steps]
