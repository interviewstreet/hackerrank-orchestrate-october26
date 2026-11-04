"""Evidence discovery and reading for the Ghost Data deletion auditor.

Typical use from ``code/main.py``::

    from evidence import EvidenceScanner, SubjectIdentifiers

    scanner = EvidenceScanner(dataset_dir)
    scanner.load()                       # parse all evidence once
    hits = scanner.find_records(identifiers, audit_at)   # audit_at: tz-aware datetime

The scanner never decides deletion status or emits output steps.
"""

from .models import (
    ABSENT,
    COMPLETE,
    INCOMPLETE,
    INFERRED,
    LINKED,
    PRESENT,
    STRONG,
    UNKNOWN,
    WEAK,
    ResourceReference,
    AbsenceProof,
    EvidenceFile,
    ObservedRecord,
    ParseIssue,
    SnapshotScope,
    SubjectIdentifiers,
)

__all__ = [
    "ABSENT",
    "COMPLETE",
    "INCOMPLETE",
    "INFERRED",
    "LINKED",
    "PRESENT",
    "ResourceReference",
    "STRONG",
    "UNKNOWN",
    "WEAK",
    "AbsenceProof",
    "EvidenceFile",
    "EvidenceScanner",
    "ObservedRecord",
    "ParseIssue",
    "SnapshotScope",
    "SubjectIdentifiers",
]


def __getattr__(name):  # lazy import keeps `import evidence.models` light
    if name == "EvidenceScanner":
        from .scanner import EvidenceScanner

        return EvidenceScanner
    raise AttributeError(name)
