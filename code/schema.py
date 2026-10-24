"""Single source of truth for the output contract (decision D21).

Enums, the allowed phase/operation/state table, the canonical step order and the
Pydantic v2 models live here. The validator, the pipeline, the intent rules, the
prompts (JSON schema) and every LLM-output check import from this module only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationInfo, field_validator, model_validator

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
    def _allowed_pair(self) -> Step:
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
    def _row_rules(self) -> OutputRow:
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


# ------------------------------------------------------------------ LLM contracts (D18-D21)
#
# Every model uses extra="forbid": the model cannot add fields such as a status or steps.
# Checks that need run data (known systems, the texts sent, the rows opened) read the
# Pydantic validation context; a model validated without that context is rejected.
# Flow: parse -> on schema failure one retry with the error -> else deterministic fallback.
# Grounding (vision) and acceptance (agent) checks run after this validation, never instead.

RE_LLM_RESOURCE_ID = r"^[a-z][a-z_]*_\d+$"
RE_TEXT_ID = r"^[0-9a-f]{12}$"


class RawState(StrEnum):
    """What the evidence shows. Code maps it to the resolver's internal state."""
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    IDENTIFIABLE = "IDENTIFIABLE"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
    UNREADABLE = "UNREADABLE"


def _context(info: ValidationInfo, key: str):
    ctx = info.context or {}
    if key not in ctx:
        raise ValueError(f"validation context {key!r} is required")
    return ctx[key]


class VisionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_id: str
    resource_id: str = Field(pattern=RE_LLM_RESOURCE_ID)
    category: str | None
    observed_state: RawState
    identifier: str | None          # email / phone / user_id / hash as shown; None: no direct identifier
    observed_at: datetime | None    # UTC; None when the image shows no time
    source_text: str = Field(max_length=200)   # the exact line as read; used for grounding

    @field_validator("system_id")
    @classmethod
    def _known_system(cls, value: str, info: ValidationInfo) -> str:
        if value not in _context(info, "known_systems"):
            raise ValueError(f"unknown system_id {value!r}")
        return value

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and value not in _context(info, "known_categories"):
            raise ValueError(f"unknown category {value!r}")
        return value

    @field_validator("observed_at")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class VisionExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    rows: list[VisionRow] = Field(max_length=200)
    unreadable: bool = False
    injection_suspected: bool = False   # the image holds instructions aimed at the reader
    notes: str = Field(default="", max_length=300)

    @field_validator("file_id")
    @classmethod
    def _same_file(cls, value: str, info: ValidationInfo) -> str:
        if value != _context(info, "file_id"):
            raise ValueError(f"file_id {value!r} is not the file sent")
        return value


class IntentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text_id: str = Field(pattern=RE_TEXT_ID)    # sha256 prefix of the request text, never the case_id
    label: Literal["DELETE", "VERIFY_DELETE", "NOT_DELETION"]
    confidence: Literal["high", "low"]
    quote: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def _quote_in_text(self, info: ValidationInfo) -> IntentItem:
        texts = _context(info, "texts")
        if self.text_id not in texts:
            raise ValueError(f"text_id {self.text_id} was not sent")
        if self.quote not in texts[self.text_id]:
            raise ValueError(f"quote for {self.text_id} is not an exact substring of the text")
        return self


class IntentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IntentItem]

    @model_validator(mode="after")
    def _covers_batch(self, info: ValidationInfo) -> IntentBatch:
        sent = set(_context(info, "texts"))
        got = [i.text_id for i in self.items]
        if len(got) != len(set(got)):
            raise ValueError("duplicate text_id in batch")
        if set(got) != sent:
            raise ValueError(f"batch must cover exactly the text_ids sent (missing {sorted(sent - set(got))}, "
                             f"extra {sorted(set(got) - sent)})")
        return self


class AgentProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["LINK", "STATE"]
    case_id: str
    system_id: str
    resource_id: str = Field(pattern=RE_LLM_RESOURCE_ID)
    user_identifier: str | None = None
    proposed_state: RawState | None = None
    evidence_ids: list[str] = Field(min_length=1, max_length=5)
    quotes: list[str] = Field(min_length=1, max_length=5)
    reason: str = Field(max_length=300)

    @field_validator("quotes")
    @classmethod
    def _quote_length(cls, value: list[str]) -> list[str]:
        if any(not q or len(q) > 200 for q in value):
            raise ValueError("each quote needs 1..200 characters")
        return value

    @model_validator(mode="after")
    def _typed_and_quoted(self, info: ValidationInfo) -> AgentProposal:
        if self.case_id != _context(info, "case_id"):
            raise ValueError("case_id is not the case under investigation")
        if self.kind == "LINK" and not self.user_identifier:
            raise ValueError("LINK needs user_identifier")
        if self.kind == "STATE" and self.proposed_state is None:
            raise ValueError("STATE needs proposed_state")
        texts = _context(info, "evidence_text")   # evidence id -> raw text opened in this loop
        cited = [texts[e] for e in self.evidence_ids if e in texts]
        for quote in self.quotes:
            if not any(quote in text for text in cited):
                raise ValueError(f"quote {quote[:40]!r} is not an exact substring of a cited row")
        return self


class LLMUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Literal["vision", "intent", "agent"]
    ref_id: str                 # file_id, text_id or case_id
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    retries: int = Field(ge=0)
    cache_hit: bool


class AgentAction(BaseModel):
    """One investigator turn: exactly one tool call. There is no tool that writes output."""
    model_config = ConfigDict(extra="forbid")

    tool: Literal["search_evidence", "read_evidence", "query_facts", "submit_proposal", "stop"]
    query: str | None = Field(default=None, max_length=200)     # search_evidence / query_facts
    file_id: str | None = Field(default=None, max_length=40)    # read_evidence
    proposal: AgentProposal | None = None                       # submit_proposal

    @model_validator(mode="after")
    def _arguments(self) -> AgentAction:
        need = {"search_evidence": "query", "query_facts": "query", "read_evidence": "file_id",
                "submit_proposal": "proposal"}.get(self.tool)
        if need and getattr(self, need) in (None, ""):
            raise ValueError(f"{self.tool} needs {need}")
        return self
