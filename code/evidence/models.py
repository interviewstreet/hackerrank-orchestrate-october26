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

# Match strength of a query result (ObservedRecord.match_strength)
STRONG = "STRONG"  # direct match on email / phone / email_hash / user_id / supplied resource_id
LINKED = "LINKED"  # reached from a confirmed observation via resource id / attachment file name
WEAK = "WEAK"      # exact full-name match only; never establishes ownership
MATCH_STRENGTHS = (STRONG, LINKED, WEAK)


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

    Query-time fields (set on the copies returned by find_records; empty on
    the stored corpus records):
      match_strength    STRONG  matched directly by email / phone / email_hash /
                                user_id / supplied resource_id;
                        LINKED  reached by following a resource id or attachment
                                file name from a confirmed (STRONG, non-conflicting,
                                non-claim) observation; see ``linked_via``;
                        WEAK    matched by an exact full name only. A name alone
                                never establishes ownership.
      identity_conflict True when the record's own identity signals disagree
                        with the subject (e.g. the subject's email but another
                        user_id). The record is still returned, unconfirmed.
      conflict_details  human-readable description of each disagreement.
      linked_via        for LINKED records: "evidence_id@locator" of the
                        observation(s) the link was followed from, or
                        "supplied:resource_ids" for caller-supplied ids.
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
    # --- query-time identity assessment (see docstring) --------------------
    match_strength: str = ""
    identity_conflict: bool = False
    conflict_details: tuple[str, ...] = ()
    linked_via: tuple[str, ...] = ()

    @property
    def latest_key(self) -> tuple[str, str, Optional[str]]:
        return (self.system_id, self.resource_id, self.replica_or_table)

    @property
    def is_confirmed(self) -> bool:
        """STRONG or LINKED, and no identity conflict."""
        return self.match_strength in (STRONG, LINKED) and not self.identity_conflict


@dataclass(frozen=True)
class ResourceReference:
    """A resource id named *inside* a confirmed, authoritative, in-window
    observation of the subject (e.g. ``source_resource_id``).

    It is a pointer, not an observation: the referenced resource may have no
    observation at all (``has_observations`` is False). Use
    ``EvidenceScanner.records_for_resource`` / ``absence_proofs`` on it.

    Fields:
      resource_id          the referenced id, as written in the evidence.
      system_id            owning system inferred from the id prefix (or None).
      source_evidence_id   manifest file_id of the referencing observation.
      source_locator       locator of the referencing observation in that file.
      source_system_id, source_resource_id   the referencing observation.
      source_field         payload field holding the reference, if identifiable.
      source_observed_at, source_captured_at timestamps of the referencing observation.
      has_observations     whether the referenced resource has any in-window
                           observation in the corpus (subject-independent).
    """

    resource_id: str
    system_id: Optional[str]
    source_evidence_id: str
    source_locator: str
    source_system_id: str
    source_resource_id: str
    source_field: Optional[str]
    source_observed_at: datetime
    source_captured_at: datetime
    has_observations: bool


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
