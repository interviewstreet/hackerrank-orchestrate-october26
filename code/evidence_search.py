"""
evidence_search.py — Stage 2 (owner: Person 2).

PLACEHOLDER. Replace the body of find_records() with the real search.
"""
from __future__ import annotations

from models import IdentityBundle


def find_records(identity: IdentityBundle, case: dict) -> list[dict]:
    """
    Find every record, data flow and restore path that concerns this subject.

    Parameters
    ----------
    identity : IdentityBundle
        From IdentityResolver.resolve(). Search with identity.all_emails(),
        all_phones(), all_email_hashes() and user_id.
    case : dict
        The deletion_requests.csv row (case_id, email, requested_at,
        reported_status, reported_at, audit_at, request_text).
        Only use evidence captured at or before case["audit_at"].

    Returns
    -------
    list[dict]
        One dict per relevant record or process. Placeholder: empty list.
    """
    return []
