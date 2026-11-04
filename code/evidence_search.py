"""
evidence_search.py — Stage 2 adapter to P2's evidence scanner (code/evidence/).

P2 owns discovery, parsing, normalisation and provenance; this module only
connects P1's IdentityBundle to it:

    SubjectIdentifiers(**identity.as_subject_kwargs())  ->  scanner.find_records()

The scanner is loaded once per process (``get_scanner``) and shared with the
policy engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from evidence import EvidenceScanner, ObservedRecord, SubjectIdentifiers
from models import IdentityBundle
from utils import parse_ts

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"

_SCANNER: Optional[EvidenceScanner] = None


def get_scanner(dataset_dir: Path | str = DATASET_DIR) -> EvidenceScanner:
    """Process-wide scanner. ``cache_only`` OCR: screenshots are read from the
    committed OCR cache, so a run needs no OCR engine and is deterministic."""
    global _SCANNER
    if _SCANNER is None:
        _SCANNER = EvidenceScanner(dataset_dir, ocr_mode="cache_only")
        _SCANNER.load()
    return _SCANNER


def set_scanner(scanner: EvidenceScanner) -> None:
    global _SCANNER
    _SCANNER = scanner


def find_records(identity: IdentityBundle, case: dict) -> list[ObservedRecord]:
    """Every observation of the subject available at the case's audit_at.

    Returns P2 ObservedRecord objects (all copies, conflicts and claim-only
    observations preserved, deterministic order).
    """
    audit_at = parse_ts(case.get("audit_at"), context=f"{case.get('case_id')} audit_at")
    if audit_at is None:
        return []
    ids = SubjectIdentifiers(**identity.as_subject_kwargs())
    return get_scanner().find_records(ids, audit_at)
