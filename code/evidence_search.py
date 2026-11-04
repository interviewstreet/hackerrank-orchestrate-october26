"""
evidence_search.py — Stage 2 (owner: Person 2).

PLACEHOLDER. Replace the body of find_records() with the real search
(e.g. a call into P2's EvidenceScanner). The return shape is the P2 -> P3
contract in code/CONTRACTS.md, section 1.
"""
from __future__ import annotations

from models import EVIDENCE_KEYS, IdentityBundle, empty_evidence  # noqa: F401


def find_records(identity: IdentityBundle, case: dict) -> dict:
    """
    Find every record, data flow and restore path that concerns this subject.

    Parameters
    ----------
    identity : IdentityBundle
        From IdentityResolver.resolve(). Build P2's SubjectIdentifiers with
        SubjectIdentifiers(**identity.as_subject_kwargs()).
    case : dict
        The deletion_requests.csv row (case_id, email, requested_at,
        reported_status, reported_at, audit_at, request_text).
        Only use evidence captured at or before case["audit_at"].

    Returns
    -------
    dict with exactly the keys in models.EVIDENCE_KEYS:
        records               list[ObservedRecord]
        latest_by_resource    dict[(system_id, resource_id, replica_or_table), ObservedRecord]
        referenced_resources  list[dict]
        absence_proofs        dict[(system_id, resource_id), list[AbsenceProof]]
        identifier_provenance dict[str, list[str]]
    main.py rejects the case (INCOMPLETE, []) if a key is missing.
    Placeholder: every key present, all empty.
    """
    return empty_evidence()
