"""
policy_engine.py — Stage 3 (owner: Person 3).

PLACEHOLDER. Replace the body of decide() with the real policy logic.
Input is the P2 -> P3 dict (code/CONTRACTS.md, section 1); output is the
proposed P3 -> P4 dict (code/CONTRACTS.md, section 2 — PROPOSAL, P3 and P4
to confirm).
"""
from __future__ import annotations

from models import IdentityBundle


def decide(identity: IdentityBundle, evidence: dict, case: dict) -> dict:
    """
    Apply deletion_rules.csv to each resource and decide the case.

    Parameters
    ----------
    identity : IdentityBundle
        Use identity.history for identity-change dates and audit_ids.
    evidence : dict
        From evidence_search.find_records(): keys records,
        latest_by_resource, referenced_resources, absence_proofs,
        identifier_provenance (models.EVIDENCE_KEYS).
    case : dict
        The deletion_requests.csv row.

    Returns
    -------
    dict
        Must contain "deletion_status": "COMPLETE" or "INCOMPLETE".
        Proposed extra keys for build_steps(): resources, flows,
        restore_risks, timeline (see CONTRACTS.md).
        main.py reads only "deletion_status" and passes the whole dict to
        build_steps(). Placeholder: INCOMPLETE with nothing found.
    """
    return {
        "deletion_status": "INCOMPLETE",
        "case_id": case["case_id"],
        "resources": [],
        "flows": [],
        "restore_risks": [],
        "timeline": [],
    }
