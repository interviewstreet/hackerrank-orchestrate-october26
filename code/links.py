"""Typed, time-stamped ownership links from a subject to resources (plan 8.2).

Edges (only those with time <= audit_at count):

* strong ``identifier``  - an observation row carries a subject email, user_id, phone or hash;
* strong ``catalog_link`` - a LINK_RESOURCE_IDENTITY activity names the subject;
* strong ``derived_from`` - a record names a linked resource as its source (``source_resource_id``);
* medium ``job_burst``   - the deletion worker touched the resource within ``JOB_WINDOW`` of this
  case's ``reported_at``, no other known request reported inside that window, and the subject
  has no strong target in that system yet (a fallback for systems where no file names the
  subject). Measured on the samples before use (config ``JOB_LINK_ENABLED``).

A target whose every edge predates ``requested_at`` is ``stale``: the link describes the
subject's data before the request. The planner reports it only as a proven violation (a
stale record that still exists is a finding; an old link alone is not a deletion target).

Names, numeric suffixes and row positions never link. A resource whose identifiers belong
only to another user is never a target (safety invariant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from evidence.common import OPERATION_CLAIM, OWNERSHIP_LINK, SNAPSHOT_ROW, STATE_READBACK, Identifiers
from facts import FactStore
from identity import IdentityIndex, SubjectIdentity
from loaders import Dataset, Request, email_hash, normalize_phone

STRONG, MEDIUM = "strong", "medium"
JOB_LINK_ENABLED = True
JOB_WINDOW = timedelta(minutes=10)
JOB_SOURCE = "deletion_worker"
LINKING_ASSERTIONS = (SNAPSHOT_ROW, STATE_READBACK, OWNERSHIP_LINK)


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
                flags: list[str]) -> dict[tuple[str, str], Target]:
        cutoff = req.audit_at
        keys = subject_keys(subject)
        found: dict[tuple[str, str], Target] = {}

        def edge(system_id, resource_id, kind, tier, source_id, at, exclusive=False):
            tgt = found.setdefault((system_id, resource_id), Target(system_id, resource_id))
            tgt.edges.append(Edge(kind, tier, source_id, at))
            tgt.exclusive = tgt.exclusive or exclusive

        for obs in self.store.linked(keys, cutoff):
            if obs.assertion not in LINKING_ASSERTIONS:
                continue
            kind = "catalog_link" if obs.assertion == OWNERSHIP_LINK else "identifier"
            edge(obs.system_id, obs.resource_id, kind, STRONG, obs.obs_id, obs.state_observed_at,
                 exclusive=bool(obs.fields.get("exclusive")))

        for tgt in list(found.values()):
            for obs in self.store.referencing(tgt.resource_id, cutoff):
                if obs.assertion in LINKING_ASSERTIONS and not (self.owners(obs.link_ids) - {subject.user_id}):
                    edge(obs.system_id, obs.resource_id, "derived_from", STRONG, obs.obs_id, obs.state_observed_at)

        if JOB_LINK_ENABLED and req.reported_at is not None:
            strong_systems = {t.system_id for t in found.values()}
            for obs in self._job_burst(req, run_requests):
                if obs.system_id in strong_systems:
                    continue
                edge(obs.system_id, obs.resource_id, "job_burst", MEDIUM, obs.obs_id, obs.state_observed_at)

        # Ownership check over every admissible observation of each candidate.
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
        for tgt in found.values():
            if req.requested_at is not None and all(e.at < req.requested_at for e in tgt.edges):
                tgt.stale = True
                flags.append(f"stale_link:{tgt.resource_id}")
            if all(e.kind == "job_burst" for e in tgt.edges):
                flags.append(f"M:job_burst:{tgt.resource_id}")
        return found

    def _job_burst(self, req: Request, run_requests: list[Request]):
        lo, hi = req.reported_at - JOB_WINDOW, req.reported_at + JOB_WINDOW
        rivals = [r for r in run_requests if r.case_id != req.case_id and r.reported_at is not None]
        for obs in self.store.activity_between(lo, hi):
            if obs.fields.get("source_system") != JOB_SOURCE or obs.assertion != OPERATION_CLAIM:
                continue
            if obs.available_at > req.audit_at:
                continue
            if any(abs(r.reported_at - obs.state_observed_at) <= JOB_WINDOW for r in rivals):
                continue  # another request reported in the same window: not unique
            yield obs
