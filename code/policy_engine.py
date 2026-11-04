"""
policy_engine.py — Stage 3 (owner: Person 3).

PLACEHOLDER. Replace the body of decide() with the real policy logic.
"""
from __future__ import annotations

from models import IdentityBundle


def decide(identity: IdentityBundle, records: list[dict], case: dict) -> dict:
    """
    Apply deletion_rules.csv to each record and decide the case.

    Parameters
    ----------
    identity : IdentityBundle
    records : list[dict]
        From evidence_search.find_records().
    case : dict
        The deletion_requests.csv row.

    Returns
    -------
    dict
        Must contain "deletion_status": "COMPLETE" or "INCOMPLETE".
        Add whatever else build_steps() needs (findings, remediation,
        verification, ...). main.py reads only "deletion_status" and
        passes the whole dict to build_steps().
        Placeholder: INCOMPLETE with nothing else.
    """
    return {"deletion_status": "INCOMPLETE", "case_id": case["case_id"]}
