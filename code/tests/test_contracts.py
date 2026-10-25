from __future__ import annotations

import pytest
from pydantic import ValidationError

from erasecase.contracts import CaseAssessment, OutputStep


def step(**overrides: object) -> OutputStep:
    values: dict[str, object] = {
        "step_no": 1,
        "phase": "FINDING",
        "system_id": "account_service",
        "resource_id": "account_005",
        "operation": "REPORT_REMAINING_RECORD",
        "state": "PRESENT",
        "evidence_id": "evidence_01",
    }
    values.update(overrides)
    return OutputStep.model_validate(values)


def test_output_step_accepts_exact_contract() -> None:
    parsed = step()
    assert set(parsed.model_dump()) == {
        "step_no",
        "phase",
        "system_id",
        "resource_id",
        "operation",
        "state",
        "evidence_id",
    }


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"state": "ABSENT"}, "requires phase"),
        ({"evidence_id": ""}, "finding steps require"),
        ({"unexpected": True}, "Extra inputs"),
    ],
)
def test_output_step_rejects_contract_violations(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        step(**overrides)


def test_not_applicable_requires_empty_steps() -> None:
    with pytest.raises(ValidationError, match="NOT_APPLICABLE requires no steps"):
        CaseAssessment(case_id="case_001", deletion_status="NOT_APPLICABLE", steps=(step(),))


def test_incomplete_requires_consecutive_phase_order() -> None:
    verification = step(
        step_no=1,
        phase="VERIFICATION",
        operation="VERIFY_RECORD_ABSENT",
        state="ABSENT",
        evidence_id="",
    )
    finding = step(step_no=2)
    with pytest.raises(ValidationError, match="ordered FINDING"):
        CaseAssessment(
            case_id="case_001",
            deletion_status="INCOMPLETE",
            steps=(verification, finding),
        )
