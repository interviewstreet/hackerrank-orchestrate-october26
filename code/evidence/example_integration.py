"""Minimal integration example for other modules (run: python code/evidence/example_integration.py)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `evidence` importable from code/

from evidence import EvidenceScanner, SubjectIdentifiers  # noqa: E402

DATASET = Path(__file__).resolve().parents[2] / "dataset"

scanner = EvidenceScanner(DATASET)  # ocr_mode="cache_only" to forbid running OCR
scanner.load()                      # once per process, before the case loop

# Built by the identity module (current + historical identifiers) and the
# activity module (resource ids taken from system_activity.csv).
subject = SubjectIdentifiers(
    user_id="user_05",
    emails=frozenset({"leila.haddad@yahoo.com"}),
    phones=frozenset({"+212 6 48 27 15 93"}),
    resource_ids=frozenset({"account_005"}),
)
audit_at = datetime(2026, 9, 8, 13, 40, tzinfo=timezone.utc)  # must be timezone-aware

# 1. every observation (claims included, nothing collapsed)
for rec in scanner.find_records(subject, audit_at):
    print(rec.evidence_id, rec.system_id, rec.resource_id, rec.replica_or_table, rec.presence,
          "claim" if rec.claim_only else "store", rec.identifiers_matched)

# 3. latest authoritative observation per copy (claim-only observations excluded)
for (system_id, resource_id, replica), rec in scanner.latest_by_resource(subject, audit_at).items():
    print("latest:", system_id, resource_id, replica or "primary", rec.presence, rec.evidence_id)

# 2. COMPLETE absence proofs only (pass include_unverified=True to see INFERRED/INCOMPLETE candidates)
for proof in scanner.absence_proofs("account_service", "account_005", audit_at):
    print("absent from:", proof.evidence_id, proof.collection, proof.replica_or_table or "primary",
          proof.completeness, proof.scope_source, "valid" if proof.is_valid_proof else "contradicted")
