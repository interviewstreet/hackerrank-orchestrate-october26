"""Public evidence-scanner API used by the auditor (``code/main.py``).

Contract
--------
* :meth:`EvidenceScanner.load` parses the whole corpus once; every query after
  that is an index lookup.
* Every query takes ``audit_at`` and applies two cutoffs: the file's manifest
  ``captured_at`` and the observation's own ``observed_at`` must both be at or
  before ``audit_at``.
* The scanner reports what evidence shows. It never decides deletion status,
  never emits output steps, and never drops retained / tombstone / replica
  records; that is policy.
"""

from __future__ import annotations

import dataclasses
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Union

from .index import EvidenceIndex
from .manifest import ManifestReport, load_manifest
from .models import (
    ABSENT,
    COMPLETE,
    INCOMPLETE,
    LINKED,
    PRESENT,
    STRONG,
    WEAK,
    ResourceReference,
    UNKNOWN,
    AbsenceProof,
    EvidenceFile,
    ObservedRecord,
    ParseIssue,
    SnapshotScope,
    SubjectIdentifiers,
)
from .normalize import (
    default_category_for_resource,
    norm_email,
    norm_hash,
    norm_phone,
    norm_resource_id,
    parse_ts,
    system_for_resource,
)
from .parsers import parse_file

TimeLike = Union[datetime, str]
_EXPLICIT_OFFSET_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$", re.I)


def _as_utc(value: TimeLike) -> datetime:
    """Validate ``audit_at`` and return it as an aware UTC datetime.

    Accepts a timezone-aware ``datetime`` or an ISO-8601 string with an
    explicit offset (``Z`` or ``+HH:MM``). Naive datetimes and offset-less
    strings are rejected: guessing their zone would silently move the cutoff.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"audit_at must be timezone-aware, got naive datetime {value!r}")
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not _EXPLICIT_OFFSET_RE.search(s):
            raise ValueError(f"audit_at string must carry an explicit UTC offset (e.g. 'Z'): {value!r}")
        dt = parse_ts(s)
        if dt is None:
            raise ValueError(f"invalid audit_at: {value!r}")
        return dt
    raise TypeError(f"audit_at must be datetime or ISO-8601 str, got {type(value).__name__}")


class EvidenceScanner:
    def __init__(self, dataset_dir: Path | str, *, ocr_mode: str = "auto") -> None:
        self.dataset_dir = Path(dataset_dir)
        self.ocr_mode = ocr_mode
        self._manifest: Optional[ManifestReport] = None
        self._files: dict[str, EvidenceFile] = {}
        self._index = EvidenceIndex()
        self._issues: list[ParseIssue] = []
        self._file_stats: dict[str, dict] = {}
        self._loaded = False

    # ------------------------------------------------------------------ load
    def load(self) -> None:
        """Parse all manifest files once. Safe to call repeatedly."""
        if self._loaded:
            return
        self._manifest = load_manifest(self.dataset_dir)
        for fid in self._manifest.missing_on_disk:
            self._issues.append(ParseIssue(fid, "error", "listed in manifest but missing on disk"))
        for rel in self._manifest.unlisted_on_disk:
            self._issues.append(ParseIssue("-", "warning", f"file on disk not in manifest: {rel}"))
        for fid in self._manifest.unsupported:
            self._issues.append(ParseIssue(fid, "unsupported", "unsupported extension"))
        for fid in self._manifest.outside_evidence_dir:
            self._issues.append(ParseIssue(fid, "error", "manifest path is outside dataset/evidence/; not read"))
        skip = set(self._manifest.missing_on_disk) | set(self._manifest.outside_evidence_dir)
        for ev in self._manifest.files:
            self._files[ev.file_id] = ev
            if ev.file_id in skip:
                continue
            res = parse_file(ev, ocr_mode=self.ocr_mode)
            self._index.add_records(res.records)
            self._index.add_scopes(res.scopes)
            self._issues.extend(res.issues)
            self._file_stats[ev.file_id] = {
                "records": len(res.records),
                "scopes": len(res.scopes),
                "issues": len(res.issues),
                **res.stats,
            }
        self._loaded = True

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError("EvidenceScanner.load() must be called before querying")

    # ------------------------------------------------------------- metadata
    def files(self) -> list[EvidenceFile]:
        self._require_loaded()
        return list(self._files.values())

    def get_file(self, evidence_id: str) -> EvidenceFile:
        self._require_loaded()
        try:
            return self._files[evidence_id]
        except KeyError:
            raise KeyError(f"unknown evidence_id: {evidence_id}") from None

    def is_valid_evidence_id(self, evidence_id: str) -> bool:
        self._require_loaded()
        return evidence_id in self._files

    @property
    def issues(self) -> list[ParseIssue]:
        return list(self._issues)

    @property
    def records(self) -> list[ObservedRecord]:
        """All parsed observations (no cutoff applied)."""
        return list(self._index.records)

    @property
    def scopes(self) -> list[SnapshotScope]:
        return list(self._index.scopes)

    def file_stats(self) -> dict[str, dict]:
        return dict(self._file_stats)

    def summary(self) -> dict:
        self._require_loaded()
        by_ext = Counter(f.extension for f in self._files.values())
        recs_by_ext: Counter = Counter()
        for r in self._index.records:
            recs_by_ext[self._files[r.evidence_id].extension] += 1
        parsed_ok = [fid for fid, st in self._file_stats.items()
                     if not any(i.evidence_id == fid and i.severity in ("error", "unsupported") for i in self._issues)]
        return {
            "manifest_entries": len(self._files),
            "files_by_extension": dict(sorted(by_ext.items())),
            "files_parsed_without_error": len(parsed_ok),
            "files_with_records": sum(1 for st in self._file_stats.values() if st["records"]),
            "observations": len(self._index.records),
            "observations_by_extension": dict(sorted(recs_by_ext.items())),
            "presence": dict(Counter(r.presence for r in self._index.records)),
            "claim_only": sum(1 for r in self._index.records if r.claim_only),
            "snapshot_scopes": len(self._index.scopes),
            "index_terms": self._index.term_count(),
            "issues_by_severity": dict(Counter(i.severity for i in self._issues)),
            "missing_on_disk": list(self._manifest.missing_on_disk) if self._manifest else [],
            "unlisted_on_disk": list(self._manifest.unlisted_on_disk) if self._manifest else [],
        }

    # --------------------------------------------------------------- cutoff
    @staticmethod
    def _available(rec: ObservedRecord, audit_at: datetime) -> bool:
        return rec.captured_at <= audit_at and rec.observed_at <= audit_at

    # -------------------------------------------------------------- queries
    def find_records(
        self,
        identifiers: SubjectIdentifiers,
        audit_at: datetime,
        *,
        expand_links: bool = True,
    ) -> list[ObservedRecord]:
        """All observations linked to the subject and available at ``audit_at``.

        Every individual observation is returned: nothing is collapsed into a
        resource status, so replica copies, conflicting observations, their
        timestamps and ``claim_only`` flags are all preserved. Order is
        deterministic (observed_at, captured_at, evidence_id, ...).

        Direct matches use the subject's emails, phones, user_id, email hashes,
        exact full names and known resource ids. With ``expand_links`` (default)
        the resource ids of confirmed direct matches (plus resource ids /
        attachment file names they reference) are followed so that later,
        de-identified copies of the same resource (e.g. an anonymised analytics
        row) are included. Links are followed only through records available at
        ``audit_at``.

        Every returned copy carries an identity assessment:
        ``match_strength`` (STRONG / LINKED / WEAK), ``identity_conflict`` with
        ``conflict_details``, and ``linked_via``. Only confirmed observations
        (STRONG or LINKED, no conflict) seed link expansion: a name-only (WEAK)
        match, a conflicting record, and a claim-only record's cross-references
        are never followed. WEAK and conflicting records are still returned so
        that nothing is hidden, but they are not confirmed as the subject's.

        ``audit_at`` must be timezone-aware (an ISO string with an explicit
        offset is also accepted); see :func:`_as_utc`.
        """
        return self._find(identifiers, audit_at, expand_links=expand_links)

    def find_for_subject(
        self,
        identifiers: SubjectIdentifiers,
        audit_at: TimeLike,
        *,
        expand_links: bool = True,
    ) -> list[ObservedRecord]:
        """Backward-compatible alias of :meth:`find_records` (identical results)."""
        return self._find(identifiers, audit_at, expand_links=expand_links)

    def _find(self, identifiers: SubjectIdentifiers, audit_at: TimeLike, *, expand_links: bool) -> list[ObservedRecord]:
        self._require_loaded()
        cutoff = _as_utc(audit_at)
        subject = identifiers.normalized()
        terms = subject.terms()
        recs = self._index.records
        matched: dict[int, set[str]] = {}
        strength: dict[int, str] = {}
        via: dict[int, set[str]] = {}
        conflicts: dict[int, tuple[str, ...]] = {}

        def conflict_of(i: int) -> tuple[str, ...]:
            if i not in conflicts:
                conflicts[i] = identity_conflicts(recs[i], subject)
            return conflicts[i]

        for term in terms:
            for i in self._index.by_term(term):
                if self._available(recs[i], cutoff):
                    matched.setdefault(i, set()).add(f"{term[0]}:{term[1]}")
        for i, labels in matched.items():
            strength[i] = STRONG if any(not m.startswith("name:") for m in labels) else WEAK

        if expand_links:
            # rid / file name -> provenance of the confirmed observations it came from
            rid_via: dict[str, set[str]] = {}
            file_via: dict[str, set[str]] = {}
            for v in (v for k, v in terms if k == "resource_id"):
                rid_via.setdefault(v, set()).add("supplied:resource_ids")

            def seed_from(i: int) -> None:
                rec = recs[i]
                prov = f"{rec.evidence_id}@{rec.locator}"
                rid_via.setdefault(rec.resource_id.lower(), set()).add(prov)
                if rec.claim_only:
                    return  # a claim may point at its own resource, never at others
                for k, v in rec.linked_terms:
                    if k == "resource_id":
                        rid_via.setdefault(v, set()).add(prov)
                    elif k == "file_name":
                        file_via.setdefault(v, set()).add(prov)

            for i in list(matched):
                if strength[i] == STRONG and not conflict_of(i):
                    seed_from(i)
            frontier = list(rid_via)
            seen_rids: set[str] = set()
            while frontier:
                rid = frontier.pop()
                if rid in seen_rids:
                    continue
                seen_rids.add(rid)
                for i in self._index.by_resource(rid):
                    if i in matched or not self._available(recs[i], cutoff):
                        continue
                    matched[i] = {f"linked_resource_id:{rid}"}
                    strength[i] = LINKED
                    via[i] = set(rid_via[rid])
                    if not conflict_of(i):
                        before = set(rid_via)
                        seed_from(i)
                        frontier.extend(r for r in set(rid_via) - before if r not in seen_rids)
            for fn, provs in sorted(file_via.items()):
                for i in self._index.by_term(("file_name", fn)):
                    if i in matched or not self._available(recs[i], cutoff):
                        continue
                    matched[i] = {f"linked_file_name:{fn}"}
                    strength[i] = LINKED
                    via[i] = set(provs)

        out = []
        for i, labels in matched.items():
            details = conflict_of(i)
            out.append(dataclasses.replace(
                recs[i], identifiers_matched=sorted(labels), match_strength=strength[i],
                identity_conflict=bool(details), conflict_details=details,
                linked_via=tuple(sorted(via.get(i, ())))))
        out.sort(key=_record_sort_key)
        return out

    def latest_by_resource(
        self,
        identifiers: SubjectIdentifiers,
        audit_at: datetime,
        *,
        include_claims: bool = False,
        include_unconfirmed: bool = False,
    ) -> dict[tuple[str, str, Optional[str]], ObservedRecord]:
        """Latest **authoritative, confirmed** in-window observation per
        (system_id, resource_id, replica_or_table).

        Claim-only observations (lookup ledgers, handovers) are excluded, so a
        key whose only evidence is a claim does not appear here; those claims
        stay available through :meth:`find_records`. ``include_claims=True``
        restores the old behaviour (claims compete, losing ties to store state).

        Unconfirmed observations (name-only WEAK matches and records with an
        ``identity_conflict``) are excluded too, because a "latest state" must
        not be attributed to the subject on that basis; ``include_unconfirmed``
        lets them compete. Both stay visible in :meth:`find_records`.

        Replica copies are separate keys, so primary/replica drift is never
        collapsed. Ordering: observed_at, then manifest captured_at. An
        observation with presence UNKNOWN only wins when the key has no
        PRESENT/ABSENT observation.
        """
        hits = self._find(identifiers, audit_at, expand_links=True)
        if not include_claims:
            hits = [h for h in hits if not h.claim_only]
        if not include_unconfirmed:
            hits = [h for h in hits if h.is_confirmed]
        return latest_of(hits)

    def referenced_resources(
        self,
        identifiers: SubjectIdentifiers,
        audit_at: datetime,
    ) -> list[ResourceReference]:
        """Resource ids named inside the subject's confirmed observations.

        A reference is reported only when the referencing observation is
        in-window (both cutoffs), authoritative (not ``claim_only``) and
        confirmed for this subject (STRONG or LINKED, no identity conflict).
        Name-only matches, conflicting records, claims, other subjects'
        records and future-dated evidence never contribute. The referenced
        resource is returned as a pointer with full provenance; no
        observation is fabricated for it (see ``has_observations``).
        """
        cutoff = _as_utc(audit_at)
        refs: dict[tuple[str, str, str], ResourceReference] = {}
        for h in self._find(identifiers, cutoff, expand_links=True):
            if h.claim_only or not h.is_confirmed:
                continue
            own = h.resource_id.lower()
            for kind, value in h.linked_terms:
                if kind != "resource_id" or value == own:
                    continue
                field_name, original = _field_holding(h.raw_state, value)
                key = (value, h.evidence_id, h.locator)
                if key in refs:
                    continue
                refs[key] = ResourceReference(
                    resource_id=original or value,
                    system_id=system_for_resource(value),
                    source_evidence_id=h.evidence_id,
                    source_locator=h.locator,
                    source_system_id=h.system_id,
                    source_resource_id=h.resource_id,
                    source_field=field_name,
                    source_observed_at=h.observed_at,
                    source_captured_at=h.captured_at,
                    has_observations=bool(self._index.by_resource(value)) and any(
                        self._available(self._index.records[i], cutoff) for i in self._index.by_resource(value)),
                )
        return sorted(refs.values(), key=lambda r: (r.resource_id.lower(), r.source_observed_at,
                                                    r.source_evidence_id, r.source_locator))

    def records_for_resource(self, resource_id: str, audit_at: TimeLike,
                             system_id: Optional[str] = None) -> list[ObservedRecord]:
        """Every in-window observation of one resource, regardless of subject."""
        self._require_loaded()
        cutoff = _as_utc(audit_at)
        out = [r for r in (self._index.records[i] for i in self._index.by_resource(resource_id.strip()))
               if self._available(r, cutoff) and (system_id is None or r.system_id == system_id)]
        return sorted(out, key=_record_sort_key)

    def snapshot_scopes(self, audit_at: TimeLike, system_id: Optional[str] = None) -> list[SnapshotScope]:
        self._require_loaded()
        cutoff = _as_utc(audit_at)
        pool = self._index.scopes_for_system(system_id) if system_id else self._index.scopes
        return [s for s in pool if s.captured_at <= cutoff and self._files[s.evidence_id].captured_at <= cutoff]

    def absence_proofs(
        self,
        system_id: str,
        resource_id: str,
        audit_at: datetime,
        data_category: Optional[str] = None,
        *,
        include_unverified: bool = False,
    ) -> list[AbsenceProof]:
        """Snapshots (at or before ``audit_at``) of a whole collection of
        ``system_id`` that do **not** contain ``resource_id``. Newest first.

        Validity conditions (all must hold for a returned proof):
          * the snapshot and its file were captured at or before ``audit_at``;
          * it covers exactly ``system_id`` and the resource's data category
            (``data_category`` argument, else the category of the resource's
            own observations, else its id prefix; unknown -> ``[]``);
          * it does not list the resource;
          * ``completeness == COMPLETE``: a declared/enumerated collection, not
            inferred from sibling tables, and no parse issue in the file.

        ``include_unverified=True`` also returns INFERRED and INCOMPLETE
        candidates (clearly marked) for diagnostics; they are not proof.
        Out-of-scope snapshots (other system/category, captured later) are
        never returned. Each proof states which copy it covers
        (``replica_or_table``), its limitations and parse errors, and any later
        authoritative PRESENT observation of the same copy (``contradicted_by``).
        """
        self._require_loaded()
        cutoff = _as_utc(audit_at)
        rid = norm_resource_id(resource_id) or resource_id
        own = self.records_for_resource(rid, cutoff, system_id)
        if data_category:
            categories = {data_category}
        else:
            categories = {r.data_category for r in own if r.data_category}
            if not categories and default_category_for_resource(rid):
                categories = {default_category_for_resource(rid)}
        if not categories:
            return []
        file_errors: dict[str, list[str]] = {}
        for issue in self._issues:
            file_errors.setdefault(issue.evidence_id, []).append(f"{issue.severity}: {issue.message}")

        proofs = []
        for sc in self.snapshot_scopes(cutoff, system_id):
            if sc.contains(rid) or sc.data_category not in categories:
                continue
            errors = tuple(file_errors.get(sc.evidence_id, ()))
            completeness = sc.completeness
            if errors and completeness == COMPLETE:
                completeness = INCOMPLETE
            if completeness != COMPLETE and not include_unverified:
                continue
            limitations = list(sc.limitations)
            limitations.append(
                f"covers replica copy '{sc.replica_or_table}' only; the primary copy is not covered"
                if sc.replica_or_table else
                "covers the primary copy only; replica copies are not covered")
            if errors:
                limitations.append("the evidence file reported parse issues; the listing may be incomplete")
            contradicted = tuple(
                f"{r.evidence_id}@{r.locator}" for r in own
                if not r.claim_only and r.presence == PRESENT and r.replica_or_table == sc.replica_or_table
                and r.observed_at > sc.captured_at)
            if contradicted:
                limitations.append("the resource was observed PRESENT in this copy after the snapshot")
            proofs.append(AbsenceProof(
                evidence_id=sc.evidence_id, system_id=sc.system_id, resource_id=resource_id.strip(),
                data_category=sc.data_category, collection=sc.collection,
                replica_or_table=sc.replica_or_table, captured_at=sc.captured_at,
                scope_source=sc.scope_source, completeness=completeness,
                scope_record_count=len(sc.resource_ids), limitations=tuple(limitations),
                errors=errors, contradicted_by=contradicted))
        proofs.sort(key=lambda p: (p.captured_at, p.evidence_id, p.replica_or_table or "", p.collection or ""),
                    reverse=True)
        return proofs


# Payload fields that name the record's *owner* (used for conflict checks only;
# free text and query keys such as lookup_key are not ownership signals).
_OWNER_EMAIL_FIELDS = {"email", "owner_email", "customer_email", "requester_email", "uploaded_by", "subject_selector"}
_OWNER_PHONE_FIELDS = {"phone", "owner_phone", "requester_phone", "customer_phone"}
_OWNER_HASH_FIELDS = {"email_hash"}


def _owner_values(rec: ObservedRecord, fields: set[str], norm) -> set[str]:
    out = set()
    for k, v in rec.pii_fields.items():
        if k in fields:
            for item in (v if isinstance(v, list) else [v]):
                n = norm(item) if isinstance(item, str) else None
                if n:
                    out.add(n)
    return out


def identity_conflicts(rec: ObservedRecord, subject: SubjectIdentifiers) -> tuple[str, ...]:
    """Disagreements between a record's own identity signals and ``subject``.

    ``subject`` must be normalised. Only stable ownership signals are
    compared: the record's stored ``user_*`` reference, and (when that
    reference is the subject's) its owner email / phone / email_hash fields.
    A kind is only compared when the subject supplies that kind, so missing
    information is never reported as a conflict.
    """
    out: list[str] = []
    ref = rec.subject_reference
    uid = subject.user_id
    if uid and ref and ref != uid:
        out.append(f"record references {ref}, subject is {uid}")
    if uid and ref == uid:
        for kind, fields, norm, known in (
            ("email", _OWNER_EMAIL_FIELDS, norm_email, subject.emails),
            ("phone", _OWNER_PHONE_FIELDS, norm_phone, subject.phones),
            ("email_hash", _OWNER_HASH_FIELDS, norm_hash, subject.email_hashes),
        ):
            values = _owner_values(rec, fields, norm)
            if values and known and not (values & known):
                out.append(f"record carries subject's user_id but a different {kind}: {', '.join(sorted(values))}")
    return tuple(out)


def _field_holding(payload: dict, value_lower: str) -> tuple[Optional[str], Optional[str]]:
    """(field name, original value) of the first payload field equal to the id."""
    stack = [payload]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(v, str) and v.strip().lower() == value_lower:
                    return k, v.strip()
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return None, None


def _record_sort_key(r: ObservedRecord):
    return (r.observed_at, r.captured_at, r.evidence_id, r.system_id, r.resource_id, r.replica_or_table or "", r.locator)


_PRESENCE_RANK = {PRESENT: 1, ABSENT: 1, UNKNOWN: 0}


def latest_of(records: Iterable[ObservedRecord]) -> dict[tuple[str, str, Optional[str]], ObservedRecord]:
    best: dict[tuple[str, str, Optional[str]], ObservedRecord] = {}

    def rank(r: ObservedRecord):
        return (_PRESENCE_RANK.get(r.presence, 0), r.observed_at, r.captured_at, not r.claim_only, r.evidence_id, r.locator)

    for r in records:
        k = r.latest_key
        if k not in best or rank(r) > rank(best[k]):
            best[k] = r
    return dict(sorted(best.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "")))
