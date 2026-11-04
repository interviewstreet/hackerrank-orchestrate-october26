"""
evidence_search.py — Stage 2 adapter to P2's evidence scanner (code/evidence/).

P2 owns discovery, parsing, normalisation and provenance
(``evidence.integration.find_case_evidence``); this module only connects P1's
pipeline to it and returns the P2 -> P3 dict (code/CONTRACTS.md, section 1):

    SubjectIdentifiers(**identity.as_subject_kwargs())   (inside P2's layer)
        -> {records, latest_by_resource, referenced_resources,
            absence_proofs, identifier_provenance}        (models.EVIDENCE_KEYS)

The scanner is loaded once per process (``get_scanner``) and shared with the
policy engine (P3), so both see the same parsed evidence. ``cache_only`` OCR:
screenshots are read from the committed OCR cache, so a run needs no OCR
engine and is deterministic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from evidence import EvidenceScanner
from evidence.integration import find_case_evidence
from models import EVIDENCE_KEYS, IdentityBundle

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"

_SCANNER: Optional[EvidenceScanner] = None


def get_scanner(dataset_dir: Path | str = DATASET_DIR) -> EvidenceScanner:
    """Process-wide scanner shared by find_records() and the policy engine."""
    global _SCANNER
    if _SCANNER is None:
        _SCANNER = EvidenceScanner(dataset_dir, ocr_mode="cache_only")
        _SCANNER.load()
    return _SCANNER


def set_scanner(scanner: EvidenceScanner) -> None:
    global _SCANNER
    _SCANNER = scanner


def find_records(identity: IdentityBundle, case: dict) -> dict:
    """Return evidence for one case in the P2 -> P3 contract format.

    ``case["audit_at"]`` must be an aware datetime (main.py passes it parsed)
    or an ISO-8601 string with an explicit offset; P2 raises otherwise.
    """
    findings = find_case_evidence(identity, case, scanner=get_scanner())

    # Convert P2 ResourceReference objects into the contract's dict format.
    referenced_resources = [
        {
            "system_id": ref.system_id,
            "resource_id": ref.resource_id,
            "via": "linked_record",
            "source_id": ref.source_evidence_id,
        }
        for ref in findings["referenced_resources"]
    ]

    # Contract format: "kind:value" -> evidence ids where that identifier matched.
    identifier_provenance: dict[str, list[str]] = {}
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
