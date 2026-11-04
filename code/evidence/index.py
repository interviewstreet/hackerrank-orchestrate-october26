"""Inverted indexes over parsed observations and snapshot scopes."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import ObservedRecord, SnapshotScope


class EvidenceIndex:
    def __init__(self) -> None:
        self.records: list[ObservedRecord] = []
        self.scopes: list[SnapshotScope] = []
        self._by_term: dict[tuple[str, str], list[int]] = defaultdict(list)
        self._by_resource: dict[str, list[int]] = defaultdict(list)
        self._scopes_by_system: dict[str, list[int]] = defaultdict(list)

    def add_records(self, records: Iterable[ObservedRecord]) -> None:
        for rec in records:
            i = len(self.records)
            self.records.append(rec)
            self._by_resource[rec.resource_id.lower()].append(i)
            for term in rec.linked_terms:
                self._by_term[term].append(i)

    def add_scopes(self, scopes: Iterable[SnapshotScope]) -> None:
        for sc in scopes:
            self._scopes_by_system[sc.system_id].append(len(self.scopes))
            self.scopes.append(sc)

    def by_term(self, term: tuple[str, str]) -> list[int]:
        return self._by_term.get(term, [])

    def by_resource(self, resource_id: str) -> list[int]:
        return self._by_resource.get(resource_id.lower(), [])

    def scopes_for_system(self, system_id: str) -> list[SnapshotScope]:
        return [self.scopes[i] for i in self._scopes_by_system.get(system_id, [])]

    def term_count(self) -> int:
        return len(self._by_term)
