"""
step_builder.py — Stage 4 (owner: Person 4).

PLACEHOLDER. Replace the body of build_steps() with the real step builder.
"""
from __future__ import annotations


def build_steps(decision: dict) -> list[dict]:
    """
    Turn a decision from policy_engine.decide() into the ordered step list.

    Each step must have exactly: step_no, phase, system_id, resource_id,
    operation, state, evidence_id (AGENTS.md §6.3-§6.4). Steps are numbered
    from 1, ordered FINDING -> REMEDIATION -> VERIFICATION.

    main.py serialises the returned list as steps_json.
    Placeholder: empty list.
    """
    return []
