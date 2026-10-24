"""Typed, time-stamped ownership links from a subject to resources (plan 8.2).

Edges (only those with time <= audit_at count):

* strong ``identifier``  - an observation row carries a subject email, user_id, phone or hash;
* strong ``catalog_link`` - a LINK_RESOURCE_IDENTITY activity names the subject;
* strong ``derived_from`` - a record names a linked resource as its source (``source_resource_id``);
* medium ``vision_identifier`` - a grounded vision row (``extract_vision``) carries a subject identifier;
* medium ``agent_link``  - an investigator LINK proposal that passed the code acceptance check;
* medium ``job_burst``   - the deletion worker touched the resource within ``JOB_WINDOW`` of this
  case's ``reported_at``, no other known request reported inside that window, and the subject
  has no strong target in that system yet (a fallback for systems where no file names the
  subject). Measured on the samples before use (config ``JOB_LINK_ENABLED``). Uniqueness guard:
  when the burst touches more than one resource in a system, that system gets no edge
  (flag ``job_burst_ambiguous:<system>``).

A target whose every edge predates ``requested_at`` is ``stale``: the link describes the
subject's data before the request, so the record is not a target of this request. The
planner excludes it entirely, even when evidence shows it PRESENT (trace flag
``stale_link:<id>``).

Each target keeps the free-text descriptions of its catalog links (``descriptions``); the
policy derives a category from them when the record states none (D10).

Names, numeric suffixes and row positions never link. A resource whose identifiers belong
only to another user is never a target (safety invariant).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from evidence.common import (
    OPERATION_CLAIM,
    OWNERSHIP_LINK,
    SNAPSHOT_ROW,
    STATE_READBACK,
    VISION_ROW,
    Identifiers,
    Observation,
)
from facts import FactStore
from identity import IdentityIndex, SubjectIdentity
from loaders import Dataset, Request, email_hash, normalize_phone

STRONG, MEDIUM = "strong", "medium"
JOB_LINK_ENABLED = True
JOB_WINDOW = timedelta(minutes=10)
JOB_SOURCE = "deletion_worker"
WINDOW_ASSIGNMENT_ENABLED = False  # Phase 5 experiment: sample precision 5/15, below the 0.9 gate
WINDOW_SYSTEM = "account_service"
LINKING_ASSERTIONS = (SNAPSHOT_ROW, STATE_READBACK, OWNERSHIP_LINK, VISION_ROW)


@dataclass(frozen=True)
class Edge:
    kind: str
    tier: str
    source_id: str      # obs_id / activity_id that proves the link
    at: datetime


@dataclass
class Target:
    system_id: str
    resource_id: str
    edges: list[Edge] = field(default_factory=list)
    shared_with: set[str] = field(default_factory=set)   # other users also linked to this record
    exclusive: bool = False                              # a catalog says it belongs only to the subject
    stale: bool = False                                  # every edge predates requested_at
    descriptions: list[str] = field(default_factory=list)  # catalog-link text about the record

    @property
    def key(self) -> tuple[str, str]:
        return (self.system_id, self.resource_id)

    @property
    def tier(self) -> str:
        return STRONG if any(e.tier == STRONG for e in self.edges) else MEDIUM


def subject_keys(subject: SubjectIdentity) -> Identifiers:
    return Identifiers(
        emails=set(subject.emails),
        user_ids={subject.user_id},
        phones={normalize_phone(p) for p in subject.phones if p},
        hashes=set(subject.email_hashes),
    )


class LinkIndex:
    def __init__(self, store: FactStore, data: Dataset, identities: IdentityIndex):
        self.store = store
        self.identities = identities
        self._owner: dict[tuple[str, str], set[str]] = {}
        for ident in data.identities:
            self._own("user_ids", ident.user_id, ident.user_id)
            self._own("emails", ident.email, ident.user_id)
            self._own("hashes", ident.email_hash, ident.user_id)
            self._own("phones", normalize_phone(ident.phone), ident.user_id)
        for entry in data.audit_log:
            kind = {"email": "emails", "email_hash": "hashes", "phone": "phones"}[entry.field_name]
            for value in (entry.old_value, entry.new_value):
                if kind == "phones":
                    value = normalize_phone(value)
                self._own(kind, value, entry.user_id)
                if kind == "emails" and value:
                    self._own("hashes", email_hash(value), entry.user_id)

    def _own(self, kind: str, value: str, user_id: str) -> None:
        if value:
            self._owner.setdefault((kind, value), set()).add(user_id)

    def owners(self, ids: Identifiers) -> set[str]:
        users: set[str] = set()
        for kind in ("emails", "user_ids", "phones", "hashes"):
            for value in getattr(ids, kind):
                users |= self._owner.get((kind, value), set())
        return users

    # ------------------------------------------------------------ targets

    def targets(self, subject: SubjectIdentity, req: Request, run_requests: list[Request],
                flags: list[str], extra_edges: Sequence[tuple] = (),
                window: Observation | None = None) -> dict[tuple[str, str], Target]:
        """``extra_edges``: accepted agent LINK proposals as (system, resource, source_id, at), medium.
        ``window``: the worker claim ``assign_windows`` gave this case, medium."""
        cutoff = req.audit_at
        keys = subject_keys(subject)
        found: dict[tuple[str, str], Target] = {}

        def edge(system_id, resource_id, kind, tier, source_id, at, exclusive=False, description=""):
            tgt = found.setdefault((system_id, resource_id), Target(system_id, resource_id))
            tgt.edges.append(Edge(kind, tier, source_id, at))
            tgt.exclusive = tgt.exclusive or exclusive
            if description:
                tgt.descriptions.append(description)

        for obs in self.store.linked(keys, cutoff):
            if obs.assertion not in LINKING_ASSERTIONS:
                continue
            if obs.assertion == VISION_ROW:
                # Model-read and grounded in OCR text, but still a reading: medium (plan 8.2).
                edge(obs.system_id, obs.resource_id, "vision_identifier", MEDIUM, obs.obs_id, obs.state_observed_at)
                continue
            kind = "catalog_link" if obs.assertion == OWNERSHIP_LINK else "identifier"
            edge(obs.system_id, obs.resource_id, kind, STRONG, obs.obs_id, obs.state_observed_at,
                 exclusive=bool(obs.fields.get("exclusive")),
                 description=str(obs.fields.get("details") or "") if kind == "catalog_link" else "")

        for tgt in list(found.values()):
            for obs in self.store.referencing(tgt.resource_id, cutoff):
                if obs.assertion in LINKING_ASSERTIONS and not (self.owners(obs.link_ids) - {subject.user_id}):
                    edge(obs.system_id, obs.resource_id, "derived_from", STRONG, obs.obs_id, obs.state_observed_at)

        for system_id, resource_id, source_id, at in extra_edges:
            edge(system_id, resource_id, "agent_link", MEDIUM, source_id, at)
        if window is not None and not any(t.system_id == WINDOW_SYSTEM for t in found.values()):
            edge(window.system_id, window.resource_id, "window_assignment", MEDIUM, window.obs_id,
                 window.state_observed_at)

        if JOB_LINK_ENABLED and req.reported_at is not None:
            strong_systems = {t.system_id for t in found.values() if t.tier == STRONG}
            burst: dict[str, list[Observation]] = {}
            for obs in self._job_burst(req, run_requests):
                if obs.system_id not in strong_systems:
                    burst.setdefault(obs.system_id, []).append(obs)
            for system_id, claims in sorted(burst.items()):
                if len({o.resource_id for o in claims}) > 1:
                    # Several resources in one system: the burst cannot say which one is the subject's.
                    flags.append(f"job_burst_ambiguous:{system_id}")
                    continue
                for obs in claims:
                    edge(obs.system_id, obs.resource_id, "job_burst", MEDIUM, obs.obs_id, obs.state_observed_at)

        self._check_ownership(found, subject, cutoff, flags)
        _flag_links(found, req, flags)
        return found

    def _check_ownership(self, found: dict[tuple[str, str], Target], subject: SubjectIdentity, cutoff,
                         flags: list[str]) -> None:
        """Every admissible observation of each candidate: drop a record owned only by another user."""
        for key, tgt in list(found.items()):
            owners: set[str] = set()
            for obs in self.store.for_resource(tgt.resource_id, cutoff):
                if obs.assertion in LINKING_ASSERTIONS:
                    owners |= self.owners(obs.link_ids)
            others = owners - {subject.user_id}
            subject_linked = subject.user_id in owners or any(e.kind == "catalog_link" for e in tgt.edges)
            if others and not subject_linked:
                flags.append(f"dropped_foreign:{tgt.resource_id}")
                del found[key]
            elif others:
                tgt.shared_with = others

    # ------------------------------------------------------------ window assignment (experiment)

    def window_candidates(self, req: Request, subject_id: str) -> list[tuple[float, Observation]]:
        """Worker DELETE_RECORD claims on ``WINDOW_SYSTEM`` inside [requested_at, reported_at] for a
        subject with no record there. Excluded: accounts named by any evidence file at ``audit_at``
        (their owner is readable there) and accounts linked to another user."""
        if req.requested_at is None or req.reported_at is None:
            return []
        hi = min(req.reported_at, req.audit_at)
        out = []
        for obs in self.store.activity_between(req.requested_at, hi):
            if (obs.system_id != WINDOW_SYSTEM or obs.fields.get("event_type") != "DELETE_RECORD"
                    or obs.fields.get("source_system") != JOB_SOURCE):
                continue
            seen = self.store.for_resource(obs.resource_id, req.audit_at)
            if any(o.source_kind != "activity" for o in seen):
                continue
            owners: set[str] = set()
            for o in seen:
                if o.assertion in LINKING_ASSERTIONS:
                    owners |= self.owners(o.link_ids)
            if owners - {subject_id}:
                continue
            out.append((abs((req.reported_at - obs.state_observed_at).total_seconds()), obs))
        return out


    def _job_burst(self, req: Request, run_requests: list[Request]):
        if req.reported_at is None:
            return
        lo, hi = req.reported_at - JOB_WINDOW, req.reported_at + JOB_WINDOW
        rivals = [r.reported_at for r in run_requests if r.case_id != req.case_id and r.reported_at is not None]
        for obs in self.store.activity_between(lo, hi):
            if obs.fields.get("source_system") != JOB_SOURCE or obs.assertion != OPERATION_CLAIM:
                continue
            if obs.available_at > req.audit_at:
                continue
            if any(abs(at - obs.state_observed_at) <= JOB_WINDOW for at in rivals):
                continue  # another request reported in the same window: not unique
            yield obs


def assign_windows(candidates: dict[str, list[tuple[float, Observation]]],
                   order: dict[str, int]) -> dict[str, Observation]:
    """Global one-to-one assignment, nearest first: every (case, account) pair sorted by time distance
    to the case's ``reported_at``; a pair is taken when neither side is taken yet. Deterministic."""
    pairs = sorted((cost, order[case_id], obs.resource_id, case_id, obs)
                   for case_id, cands in candidates.items() for cost, obs in cands)
    taken_cases: dict[str, Observation] = {}
    taken_accounts: set[str] = set()
    for _, _, rid, case_id, obs in pairs:
        if case_id in taken_cases or rid in taken_accounts:
            continue
        taken_cases[case_id] = obs
        taken_accounts.add(rid)
    return taken_cases


def _flag_links(found: dict[tuple[str, str], Target], req: Request, flags: list[str]) -> None:
    """A target whose links all predate ``requested_at`` is stale (the planner drops it, D-stale);
    a target linked only by a medium heuristic is flagged ``M:<kind>``."""
    for tgt in found.values():
        if req.requested_at is not None and all(e.at < req.requested_at for e in tgt.edges):
            tgt.stale = True
            flags.append(f"stale_link:{tgt.resource_id}")
        for kind in ("job_burst", "window_assignment"):
            if all(e.kind == kind for e in tgt.edges):
                flags.append(f"M:{kind}:{tgt.resource_id}")
