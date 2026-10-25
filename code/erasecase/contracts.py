"""Versioned, strict data contracts shared by every EraseCase stage."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DeletionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


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


STEP_RULES: dict[Operation, tuple[Phase, StepState]] = {
    Operation.REPORT_REMAINING_RECORD: (Phase.FINDING, StepState.PRESENT),
    Operation.REPORT_EXPOSED_PII: (Phase.FINDING, StepState.PRESENT),
    Operation.REPORT_ACTIVE_DATA_FLOW: (Phase.FINDING, StepState.ACTIVE),
    Operation.REPORT_RESTORE_RISK: (Phase.FINDING, StepState.ACTIVE),
    Operation.DISABLE_DATA_FLOW: (Phase.REMEDIATION, StepState.DISABLED),
    Operation.BLOCK_RESTORE: (Phase.REMEDIATION, StepState.BLOCKED),
    Operation.DELETE_RECORD: (Phase.REMEDIATION, StepState.ABSENT),
    Operation.REDACT_RECORD: (Phase.REMEDIATION, StepState.REDACTED),
    Operation.ANONYMIZE_RECORD: (Phase.REMEDIATION, StepState.ANONYMIZED),
    Operation.VERIFY_RECORD_ABSENT: (Phase.VERIFICATION, StepState.ABSENT),
    Operation.VERIFY_RECORD_PRESENT: (Phase.VERIFICATION, StepState.PRESENT),
    Operation.VERIFY_RECORD_REDACTED: (Phase.VERIFICATION, StepState.REDACTED),
    Operation.VERIFY_RECORD_ANONYMIZED: (Phase.VERIFICATION, StepState.ANONYMIZED),
    Operation.VERIFY_DATA_FLOW_DISABLED: (Phase.VERIFICATION, StepState.DISABLED),
    Operation.VERIFY_RESTORE_BLOCKED: (Phase.VERIFICATION, StepState.BLOCKED),
}


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC offset")


class DeletionRequest(StrictModel):
    case_id: str = Field(min_length=1)
    email: str = Field(min_length=3)
    requested_at: datetime
    reported_status: str = Field(min_length=1)
    reported_at: datetime
    audit_at: datetime
    request_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_times(self) -> DeletionRequest:
        for name in ("requested_at", "reported_at", "audit_at"):
            _require_aware(getattr(self, name), name)
        return self


class IdentifierFact(StrictModel):
    subject_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    normalized_value: str = Field(min_length=1)
    original_value: str = Field(min_length=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_id: str = Field(min_length=1)


class Observation(StrictModel):
    observation_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    system_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    captured_at: datetime
    event_at: datetime | None = None
    state: str = Field(min_length=1)
    facts: dict[str, Any] = Field(default_factory=dict)


class ResourceLink(StrictModel):
    source_system_id: str = Field(min_length=1)
    source_resource_id: str = Field(min_length=1)
    target_system_id: str = Field(min_length=1)
    target_resource_id: str = Field(min_length=1)
    relationship: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)


class PolicyObligation(StrictModel):
    rule_id: str = Field(min_length=1)
    data_category: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    required_action: str = Field(min_length=1)


class OutputStep(StrictModel):
    step_no: int = Field(ge=1)
    phase: Phase
    system_id: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    operation: Operation
    state: StepState
    evidence_id: str

    @model_validator(mode="after")
    def validate_operation(self) -> OutputStep:
        expected_phase, expected_state = STEP_RULES[self.operation]
        if (self.phase, self.state) != (expected_phase, expected_state):
            raise ValueError(
                f"{self.operation} requires phase={expected_phase} and state={expected_state}"
            )
        if self.phase is Phase.FINDING and not self.evidence_id:
            raise ValueError("finding steps require participant-visible evidence")
        if self.phase is Phase.REMEDIATION and self.evidence_id:
            raise ValueError("future remediation steps require an empty evidence_id")
        return self


class CaseAssessment(StrictModel):
    case_id: str = Field(min_length=1)
    deletion_status: DeletionStatus
    steps: tuple[OutputStep, ...] = ()

    @model_validator(mode="after")
    def validate_sequence(self) -> CaseAssessment:
        if self.deletion_status is DeletionStatus.NOT_APPLICABLE and self.steps:
            raise ValueError("NOT_APPLICABLE requires no steps")
        if self.deletion_status is DeletionStatus.COMPLETE and any(
            step.phase is not Phase.VERIFICATION for step in self.steps
        ):
            raise ValueError("COMPLETE permits evidence-backed verification steps only")
        phase_order = {Phase.FINDING: 0, Phase.REMEDIATION: 1, Phase.VERIFICATION: 2}
        if [step.step_no for step in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("step_no values must be consecutive from 1")
        if [phase_order[step.phase] for step in self.steps] != sorted(
            phase_order[step.phase] for step in self.steps
        ):
            raise ValueError("steps must be ordered FINDING, REMEDIATION, VERIFICATION")
        if self.deletion_status is DeletionStatus.COMPLETE and any(
            not step.evidence_id for step in self.steps
        ):
            raise ValueError("COMPLETE verification steps require evidence")
        if self.deletion_status is DeletionStatus.INCOMPLETE and any(
            step.phase is Phase.VERIFICATION and step.evidence_id for step in self.steps
        ):
            raise ValueError("future INCOMPLETE verification steps require empty evidence_id")
        return self


class ModelCallRecord(StrictModel):
    call_id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    returned_model: str | None = None
    provider: str | None = None
    attempts: int = Field(ge=1)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    latency_ms: int = Field(ge=0)
    outcome: str = Field(min_length=1)
