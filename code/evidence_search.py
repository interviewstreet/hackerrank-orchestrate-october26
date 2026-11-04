"""P2 evidence-search adapter for P1's main pipeline."""

from __future__ import annotations

from models import EVIDENCE_KEYS, IdentityBundle
from evidence.integration import find_case_evidence


def find_records(identity: IdentityBundle, case: dict) -> dict:
    """Return evidence in the P1 -> P2 -> P3 contract format."""

    findings = find_case_evidence(identity, case)

    # Convert P2 ResourceReference objects into P1's dictionary format.
    referenced_resources = [
        {
            "system_id": ref.system_id,
            "resource_id": ref.resource_id,
            "via": "linked_record",
            "source_id": ref.source_evidence_id,
        }
        for ref in findings["referenced_resources"]
    ]

    # Convert P2's detailed provenance into P1's expected format.
    identifier_provenance = {}

    for record in findings["records"]:
        for identifier in record.identifiers_matched:
            evidence_ids = identifier_provenance.setdefault(identifier, [])

            if record.evidence_id not in evidence_ids:
                evidence_ids.append(record.evidence_id)

    result = {
        "records": findings["records"],
        "latest_by_resource": findings["latest_by_resource"],
        "referenced_resources": referenced_resources,
        "absence_proofs": findings["absence_proofs"],
        "identifier_provenance": identifier_provenance,
    }

    if set(result.keys()) != set(EVIDENCE_KEYS):
        raise RuntimeError("P2 evidence output does not match EVIDENCE_KEYS")

    return result