"""In-memory lookup structures built once from the four tables.

Every per-case step reads only from a Context. Nothing here touches the filesystem.
"""
from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass, field

from ..identifiers import norm_email
from ..models import Activity, Observation, Subject
from .files import EvidenceFile
from .identities import IdentityRow


@dataclass
class Context:
    files: dict[str, EvidenceFile]
    scopes: dict[str, tuple[tuple[str, str], ...]]    # evidence_id -> (system, observed_at) covered
    user_by_identifier: dict[str, str]
    identifiers_by_user: dict[str, frozenset[str]]
    activities: list[Activity]                        # sorted by event_time
    acts_by_resource: dict[str, list[Activity]]
    observations: list[Observation]
    obs_by_subject: dict[str, list[Observation]]
    obs_by_resource: dict[str, list[Observation]]     # each list sorted by observed_at
    parse_failures: list[dict]
    _worker: list[Activity] = field(default_factory=list, repr=False)
    _worker_times: list[str] = field(default_factory=list, repr=False)

    @classmethod
    def build(cls, files: list[EvidenceFile], scopes: dict[str, list],
              identities: list[IdentityRow], activities: list[Activity],
              observations: list[Observation], parse_failures: list[dict]) -> "Context":
        ids_by_user: dict[str, set[str]] = defaultdict(set)
        for r in identities:
            ids_by_user[r.user_id].add(r.identifier)

        acts_by_resource: dict[str, list[Activity]] = defaultdict(list)
        for a in activities:
            acts_by_resource[a.resource_id].append(a)

        obs_by_subject: dict[str, list[Observation]] = defaultdict(list)
        obs_by_resource: dict[str, list[Observation]] = defaultdict(list)
        for o in observations:
            obs_by_resource[o.resource_id].append(o)
            for s in o.subjects:
                obs_by_subject[s].append(o)
        for lst in obs_by_resource.values():
            lst.sort(key=lambda o: (o.observed_at, o.evidence_id))

        worker = [a for a in activities if a.source_system == "deletion_worker"]
        return cls(
            files={f.evidence_id: f for f in files},
            scopes={k: tuple(tuple(x) for x in v) for k, v in scopes.items()},
            user_by_identifier={r.identifier: r.user_id for r in identities},
            identifiers_by_user={u: frozenset(v) for u, v in ids_by_user.items()},
            activities=activities,
            acts_by_resource=dict(acts_by_resource),
            observations=observations,
            obs_by_subject=dict(obs_by_subject),
            obs_by_resource=dict(obs_by_resource),
            parse_failures=parse_failures,
            _worker=worker,
            _worker_times=[a.event_time for a in worker],
        )

    # --- lookups ---------------------------------------------------------

    def resolve_subject(self, email: str) -> Subject | None:
        user_id = self.user_by_identifier.get(norm_email(email))
        if user_id is None:
            return None
        return Subject(user_id, self.identifiers_by_user[user_id])

    def worker_actions(self, start: str, end: str) -> list[Activity]:
        """Deletion-worker activity with start <= event_time <= end, via binary search."""
        lo = bisect.bisect_left(self._worker_times, start)
        hi = bisect.bisect_right(self._worker_times, end)
        return self._worker[lo:hi]

    def owners_of(self, resource_id: str) -> set[str]:
        """user_ids that any observation, at any time, ties to this resource."""
        owners: set[str] = set()
        for o in self.obs_by_resource.get(resource_id, ()):
            for s in o.subjects:
                uid = self.user_by_identifier.get(s)
                if uid:
                    owners.add(uid)
        return owners
