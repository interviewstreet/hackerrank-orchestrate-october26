"""Shared data contracts for the ERASIGHT engine.

Observation / Coverage are the normalized evidence representation.
CaseAuditResult is the shared result contract consumed by Member 1's API/graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

FINDING, REMEDIATION, VERIFICATION = "FINDING", "REMEDIATION", "VERIFICATION"

# Operation order used for sorting inside each phase (problem statement table order).
OPERATION_ORDER = [
    "REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK",
    "DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD",
    "VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED",
    "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED",
]
OPERATION_STATE = {
    "REPORT_REMAINING_RECORD": ("FINDING", "PRESENT"), "REPORT_EXPOSED_PII": ("FINDING", "PRESENT"),
    "REPORT_ACTIVE_DATA_FLOW": ("FINDING", "ACTIVE"), "REPORT_RESTORE_RISK": ("FINDING", "ACTIVE"),
    "DISABLE_DATA_FLOW": ("REMEDIATION", "DISABLED"), "BLOCK_RESTORE": ("REMEDIATION", "BLOCKED"),
    "DELETE_RECORD": ("REMEDIATION", "ABSENT"), "REDACT_RECORD": ("REMEDIATION", "REDACTED"),
    "ANONYMIZE_RECORD": ("REMEDIATION", "ANONYMIZED"),
    "VERIFY_RECORD_ABSENT": ("VERIFICATION", "ABSENT"), "VERIFY_RECORD_PRESENT": ("VERIFICATION", "PRESENT"),
    "VERIFY_RECORD_REDACTED": ("VERIFICATION", "REDACTED"),
    "VERIFY_RECORD_ANONYMIZED": ("VERIFICATION", "ANONYMIZED"),
    "VERIFY_DATA_FLOW_DISABLED": ("VERIFICATION", "DISABLED"), "VERIFY_RESTORE_BLOCKED": ("VERIFICATION", "BLOCKED"),
}


@dataclass
class Observation:
    """One fact about one resource, taken from one evidence file."""
    evidence_id: str                 # manifest file_id (e.g. evidence_54)
    captured_at: str                 # manifest capture time of the file
    system_id: str                   # e.g. account_service
    resource_id: str                 # e.g. account_005
    data_category: str               # e.g. USER_PROFILE (matches deletion_rules.csv)
    state: str                       # PRESENT | ABSENT | ACTIVE | DISABLED | BLOCKED | REDACTED | ANONYMIZED
    observed_at: str = ""            # finer-grained time (log line / row), defaults to captured_at
    emails: List[str] = field(default_factory=list)
    user_refs: List[str] = field(default_factory=list)
    hashes: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)
    links: Dict[str, List[str]] = field(default_factory=dict)   # identifiers used only to LINK the record to a subject
    source_format: str = ""          # sql | json | log | txt | pdf | image
    file_captured_at: str = ""       # manifest capture time of the evidence FILE (governs usability and citation)
    locator: str = ""                # table / line / page reference for provenance
    confidence: float = 1.0          # <1 for OCR-derived facts

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Coverage:
    """Evidence file F, captured at T, is authoritative for system S (so absence from F means absent)."""
    evidence_id: str
    captured_at: str
    system_id: str
    collection: str = ""
    source_format: str = ""
    locator: str = ""
    replica: str = "primary"          # which copy this snapshot covers (primary, failover_replica, read_replica, ...)
    file_captured_at: str = ""


@dataclass
class IdentityResult:
    identity_id: str
    resolved_identifiers: List[Dict[str, Any]]
    matched_evidence: List[str]
    resolution_status: str           # RESOLVED | PARTIALLY_RESOLVED | AMBIGUOUS | UNRESOLVED
    confidence: float


@dataclass
class CaseAuditResult:
    case_id: str
    deletion_status: str             # COMPLETE | INCOMPLETE | NOT_APPLICABLE
    summary: Dict[str, int] = field(default_factory=lambda: {
        "systems_checked": 0, "findings_count": 0, "remediation_count": 0, "verification_count": 0})
    identities: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    graph_data: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: {"nodes": [], "edges": []})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
