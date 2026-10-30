"""ObservationStore: every observation indexed by identifier and by resource, plus snapshot coverage."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from ..models import Observation


@dataclass(frozen=True)
class Coverage:
    """A snapshot that asserts it holds every record of `system_id` (at `location`, '*' = all)."""
    evidence_id: str
    captured_at: datetime
    system_id: str
    location: str
    present: frozenset  # resource ids of that system present in the snapshot


@dataclass
class ObservationStore:
    observations: list[Observation] = field(default_factory=list)
    coverage: list[Coverage] = field(default_factory=list)
    report: dict = field(default_factory=dict)  # per-file extraction stats
    unreadable: list = field(default_factory=list)  # (file_id, captured_at) of evidence that could not be read
    unread_text: dict = field(default_factory=dict)  # file_id -> OCR text of such a file (None: contents unknown)

    def __post_init__(self):
        self._by_id: dict = defaultdict(list)
        self._by_res: dict = defaultdict(list)
        for o in self.observations:
            self._index(o)

    def _index(self, o: Observation):
        for ident in o.identifiers:
            self._by_id[ident].append(o)
        self._by_res[o.resource_id].append(o)

    def add(self, o: Observation):
        self.observations.append(o)
        self._index(o)

    def by_identifier(self, kind: str, value: str) -> list[Observation]:
        return list(self._by_id.get((kind, value), []))

    def by_resource(self, resource_id: str) -> list[Observation]:
        return list(self._by_res.get(resource_id, []))

    def resources(self) -> list[str]:
        return sorted(self._by_res)

    def all(self) -> list[Observation]:
        return list(self.observations)
