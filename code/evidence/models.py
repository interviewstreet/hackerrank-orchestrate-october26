"""Data model shared by the evidence scanner and the auditor.

The scanner only *discovers and reads* evidence. Nothing in this module makes
policy decisions (COMPLETE / INCOMPLETE, remediation, output steps).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Presence values for ObservedRecord.presence
PRESENT = "PRESENT"
ABSENT = "ABSENT"
UNKNOWN = "UNKNOWN"
PRESENCE_VALUES = (PRESENT, ABSENT, UNKNOWN)

# Completeness of a snapshot scope / absence proof
COMPLETE = "COMPLETE"      # the evidence enumerates the whole collection/table
INFERRED = "INFERRED"      # coverage inferred (e.g. from sibling tables); not proof by default
INCOMPLETE = "INCOMPLETE"  # the file had parse issues; never proof by default
COMPLETENESS_VALUES = (COMPLETE, INFERRED, INCOMPLETE)


@dataclass(frozen=True)
class EvidenceFile:
    """One row of ``dataset/evidence_files.csv``."""

    file_id: str
    file_path: str  # as written in the manifest (POSIX, relative to dataset/)
    origin: str
    captured_at: datetime
    absolute_path: Path

    @property
    def extension(self) -> str:
        return self.absolute_path.suffix.lower().lstrip(".")


@dataclass(frozen=True)
class SubjectIdentifiers:
    """Identifier set for one deletion subject, built by identity resolution.

    Values may be passed un-normalised; use :meth:`normalized` (the scanner
    does this itself) to get the canonical forms used for index lookups.
    """

    user_id: Optional[str] = None
    emails: frozenset[str] = field(default_factory=frozenset)
    phones: frozenset[str] = field(default_factory=frozenset)
    email_hashes: frozenset[str] = field(default_factory=frozenset)
    names: frozenset[str] = field(default_factory=frozenset)
    resource_ids: frozenset[str] = field(default_factory=frozenset)

    def normalized(self) -> "SubjectIdentifiers":
        from .normalize import (
            norm_email,
            norm_hash,
            norm_name,
            norm_phone,
            norm_resource_id,
            norm_user_id,
        )

        def _set(values, fn):
            return frozenset(v for v in (fn(x) for x in values or ()) if v)

        return SubjectIdentifiers(
            user_id=norm_user_id(self.user_id) if self.user_id else None,
            emails=_set(self.emails, norm_email),
            phones=_set(self.phones, norm_phone),
            email_hashes=_set(self.email_hashes, norm_hash),
            names=_set(self.names, norm_name),
            resource_ids=_set(self.resource_ids, norm_resource_id),
        )

    def terms(self) -> set[tuple[str, str]]:
        """Normalised (kind, value) index terms for this subject."""
        n = self.normalized()
        out: set[tuple[str, str]] = set()
        if n.user_id:
            out.add(("user_id", n.user_id))
        out.update(("email", v) for v in n.emails)
        out.update(("phone", v) for v in n.phones)
        out.update(("email_hash", v) for v in n.email_hashes)
        out.update(("name", v) for v in n.names)
        out.update(("resource_id", v) for v in n.resource_ids)
        return out


@dataclass
class ObservedRecord:
    """A single normalised fact read from one evidence file.

    Fields:
      evidence_id       manifest ``file_id`` to cite (always a manifest entry).
      system_id         owning system, e.g. ``account_service``.
      resource_id       resource as written in the evidence (original casing).
      data_category     deletion_rules category hint (USER_PROFILE, ...), or None.
      collection        source collection / table / export section, if any.
      replica_or_table  None for the primary copy, else the replica name.
      observed_at       when the state was observed (snapshot time, line time, ...).
      captured_at       manifest capture time of the file.
      presence          PRESENT | ABSENT | UNKNOWN.
      pii_fields        non-null direct identifiers *stored in* the record.
      identifiers_matched  filled by queries: which subject terms matched.
      raw_state         full cleaned payload plus parser context (result,
                        enabled, restore_allowed, table, trace_id, ...).
      claim_only        True for second-hand lookup ledgers (a system
                        *reporting* a lookup result); False for direct store
                        state (snapshots, SQL rows, completed read-backs, PII
                        scans, documents, screenshots).
      source_format, locator, subject_reference, linked_terms: provenance and
                        linking data (``linked_terms`` are normalised index terms).
    """

    evidence_id: str
    system_id: str
    resource_id: str
    data_category: Optional[str]
    collection: Optional[str]
    replica_or_table: Optional[str]  # None = primary / system-of-record copy
    observed_at: datetime
    captured_at: datetime
    presence: str
    pii_fields: dict[str, Any]
    identifiers_matched: list[str]
    raw_state: dict[str, Any]
    claim_only: bool
    # --- additions beyond the original interface (all optional) -----------
    source_format: str = ""  # json | sql | log | pdf | png | txt
    locator: str = ""  # line number / table / JSON path inside the file
    subject_reference: Optional[str] = None  # stable user_id when exposed
    linked_terms: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    @property
    def latest_key(self) -> tuple[str, str, Optional[str]]:
        return (self.system_id, self.resource_id, self.replica_or_table)


@dataclass(frozen=True)
class SnapshotScope:
    """A point-in-time snapshot that enumerates a whole collection.

    If a resource of ``system_id``/``data_category`` is *not* listed in
    ``resource_ids``, the snapshot is evidence that it was absent from that
    copy at ``captured_at``. Lookup ledgers and logs never create scopes.

    ``scope_source`` says how the scope was established:
    ``collection_snapshot`` / ``collection_dump`` (JSON), ``sql_table``,
    ``inventory_snapshot_scope`` (declared in the dump), or
    ``sql_sibling_inference`` (collection seen only in another table of the
    same dump -> ``completeness == INFERRED``).
    """

    evidence_id: str
    system_id: str
    data_category: Optional[str]
    collection: Optional[str]
    replica_or_table: Optional[str]
    captured_at: datetime
    resource_ids: frozenset[str]  # lower-cased
    scope_source: str = "collection_snapshot"
    completeness: str = COMPLETE
    limitations: tuple[str, ...] = ()

    def contains(self, resource_id: str) -> bool:
        return resource_id.lower() in self.resource_ids


@dataclass(frozen=True)
class AbsenceProof:
    """One snapshot showing ``resource_id`` was absent from one copy.

    Returned by :meth:`EvidenceScanner.absence_proofs`.

    Fields:
      evidence_id         manifest ``file_id`` of the snapshot.
      system_id, data_category, collection, replica_or_table
                          the exact scope: which system, category, collection/
                          table and copy (None = primary) the snapshot covers.
      resource_id         the resource asked about (as passed by the caller).
      captured_at         verification timestamp: when the snapshot was taken
                          (also available as ``verified_at``).
      scope_source        how the scope was established (see SnapshotScope).
      completeness        COMPLETE | INFERRED | INCOMPLETE. Only COMPLETE
                          proofs are returned unless ``include_unverified``.
      scope_record_count  how many resources the snapshot listed.
      limitations         human-readable caveats (copy covered, inference, ...).
      errors              parse issues reported for the evidence file.
      contradicted_by     in-window authoritative PRESENT observations of the
                          same copy *after* the snapshot, as "evidence_id@locator".
    """

    evidence_id: str
    system_id: str
    resource_id: str
    data_category: Optional[str]
    collection: Optional[str]
    replica_or_table: Optional[str]
    captured_at: datetime
    scope_source: str = ""
    completeness: str = COMPLETE
    scope_record_count: int = 0
    limitations: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    contradicted_by: tuple[str, ...] = ()

    @property
    def verified_at(self) -> datetime:
        return self.captured_at

    @property
    def is_valid_proof(self) -> bool:
        """COMPLETE and not contradicted by a later PRESENT observation of the same copy."""
        return self.completeness == COMPLETE and not self.contradicted_by


@dataclass(frozen=True)
class ParseIssue:
    evidence_id: str
    severity: str  # "error" | "warning" | "unsupported"
    message: str
