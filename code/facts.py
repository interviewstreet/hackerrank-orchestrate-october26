"""Global fact store, built once per run from every extractor.

Observations and scopes stay as Python objects; an in-memory SQLite index answers the
two hot queries: "which observations carry this identifier" and "which observations
mention this resource", always with a time cutoff.
"""

from __future__ import annotations

import re
import sqlite3
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from parse_coverage import DEFERRED, ERROR, GROUNDING, PARSED, CoverageReport, FileCoverage
from evidence import extract_activity, extract_json, extract_log, extract_sql, extract_text
from evidence.common import Identifiers, Observation, Scope, ShapeError
from loaders import DATASET_DIR, REPO_ROOT, Dataset

EXTRACTORS = {"sql": extract_sql.extract, "json": extract_json.extract, "txt": extract_text.extract,
              "log": extract_log.extract}
ID_KINDS = ("emails", "user_ids", "phones", "hashes")   # names never link (plan 8.2)
OCR_CACHE = REPO_ROOT / ".cache" / "ocr"
# Catalog rows name a display reference for a resource: "linked export_1842 (NST-2026-0718-1842)".
RE_ALIAS = re.compile(r"\b(?:linked|confirmed) ([a-z]+(?:_[a-z]+)*_\d+) \(([^)]+)\)")
RE_USER = re.compile(r"^user_\d+$")


def catalog_aliases(data: Dataset) -> dict[str, tuple[str, str]]:
    """alias -> (system_id, resource_id) from LINK_RESOURCE_IDENTITY rows (aliases that are ids are skipped)."""
    aliases = {}
    for a in data.activity:
        if a.event_type != "LINK_RESOURCE_IDENTITY":
            continue
        for rid, alias in RE_ALIAS.findall(a.details):
            alias = alias.strip()
            if rid == a.resource_id and alias != rid and not RE_USER.match(alias) and len(alias) >= 6:
                aliases[alias] = (a.target_system, rid)
    return aliases


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class FactStore:
    def __init__(self):
        self.observations: dict[str, Observation] = {}
        self.scopes: list[Scope] = []
        self.coverage = CoverageReport()
        self._by_resource: dict[str, list[Observation]] = defaultdict(list)
        self._refs_to: dict[str, list[Observation]] = defaultdict(list)
        self._scopes_by_system: dict[str, list[Scope]] = defaultdict(list)
        self._rows_in_file: set[tuple[str, str, str]] = set()   # (file_id, resource_id, copy)
        self.grounding: dict[str, str] = {}   # file_id -> OCR text (grounding only, never facts)
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE obs (obs_id TEXT PRIMARY KEY, file_id TEXT, system_id TEXT, resource_id TEXT,
                              physical_copy TEXT, assertion TEXT, available_at TEXT, observed_at TEXT);
            CREATE TABLE ident (kind TEXT, value TEXT, obs_id TEXT);
            CREATE INDEX ident_kv ON ident(kind, value);
            CREATE INDEX obs_res ON obs(resource_id);
        """)

    # ------------------------------------------------------------ build

    @classmethod
    def build(cls, data: Dataset, dataset_dir: Path = DATASET_DIR, ocr_cache: Path | None = OCR_CACHE) -> "FactStore":
        store = cls()
        aliases = catalog_aliases(data)
        extractors = dict(EXTRACTORS, pdf=lambda ev, path: extract_text.extract_pdf(ev, path, aliases))
        for ev in data.evidence_files:
            fmt = ev.file_path.rsplit(".", 1)[-1].lower()
            item = FileCoverage(ev.file_id, ev.file_path, fmt, DEFERRED)
            if fmt == "png":
                text = extract_text.ocr_text(ev.abs_path(dataset_dir), ocr_cache)
                if text is not None:
                    store.grounding[ev.file_id] = text
                    item.status, item.family, item.grounding_chars = GROUNDING, "png_ocr", len(text)
            extractor = extractors.get(fmt)
            if extractor is not None:
                try:
                    result = extractor(ev, ev.abs_path(dataset_dir))
                except (ShapeError, ValueError, KeyError, TypeError) as exc:
                    item.status, item.error = ERROR, f"{type(exc).__name__}: {exc}"
                    if not isinstance(exc, ShapeError):
                        item.error += " | " + traceback.format_exc(limit=1).strip().splitlines()[-1]
                else:
                    item.status, item.family = PARSED, result.family
                    item.rows_parsed, item.scopes, item.skipped = result.rows_parsed, len(result.scopes), result.skipped
                    store.add(result.observations, result.scopes)
            store.coverage.add(item)
        activity = extract_activity.extract(data.activity)
        store.add(activity.observations, [])
        store.coverage.add(FileCoverage("system_activity", "system_activity.csv", "csv", PARSED,
                                        family=activity.family, rows_parsed=activity.rows_parsed))
        store.db.commit()
        return store

    def add(self, observations: list[Observation], scopes: list[Scope]) -> None:
        for obs in observations:
            if obs.obs_id in self.observations:
                raise ShapeError(f"duplicate observation id {obs.obs_id}")
            self.observations[obs.obs_id] = obs
            self._by_resource[obs.resource_id].append(obs)
            for ref in obs.refs:
                self._refs_to[ref].append(obs)
            if obs.source_kind != "activity":
                self._rows_in_file.add((obs.file_id, obs.resource_id, obs.physical_copy))
            self.db.execute("INSERT INTO obs VALUES (?,?,?,?,?,?,?,?)",
                            (obs.obs_id, obs.file_id, obs.system_id, obs.resource_id, obs.physical_copy,
                             obs.assertion, _iso(obs.available_at), _iso(obs.state_observed_at)))
            for kind in ID_KINDS:
                for value in getattr(obs.link_ids, kind):
                    self.db.execute("INSERT INTO ident VALUES (?,?,?)", (kind, value, obs.obs_id))
        for scope in scopes:
            self.scopes.append(scope)
            self._scopes_by_system[scope.system_id].append(scope)

    # ------------------------------------------------------------ queries

    @staticmethod
    def admissible(obs_or_scope, cutoff: datetime) -> bool:
        """Inclusive cutoff on both the file availability time and the inner state time."""
        observed = getattr(obs_or_scope, "state_observed_at", None) or obs_or_scope.observed_at
        return obs_or_scope.available_at <= cutoff and observed <= cutoff

    def linked(self, keys: Identifiers, cutoff: datetime) -> list[Observation]:
        """Observations whose link identifiers intersect ``keys``, admissible at ``cutoff``."""
        hits: set[str] = set()
        for kind in ID_KINDS:
            values = sorted(getattr(keys, kind))
            if not values:
                continue
            marks = ",".join("?" * len(values))
            rows = self.db.execute(
                f"SELECT DISTINCT i.obs_id FROM ident i JOIN obs o ON o.obs_id = i.obs_id "
                f"WHERE i.kind = ? AND i.value IN ({marks}) AND o.available_at <= ? AND o.observed_at <= ?",
                (kind, *values, _iso(cutoff), _iso(cutoff)))
            hits.update(r[0] for r in rows)
        return [self.observations[h] for h in sorted(hits)]

    def for_resource(self, resource_id: str, cutoff: datetime) -> list[Observation]:
        return [o for o in self._by_resource.get(resource_id, ()) if self.admissible(o, cutoff)]

    def referencing(self, resource_id: str, cutoff: datetime) -> list[Observation]:
        return [o for o in self._refs_to.get(resource_id, ()) if self.admissible(o, cutoff)]

    def activity_between(self, lo: datetime, hi: datetime) -> list[Observation]:
        """Activity observations whose event time lies in [lo, hi]."""
        rows = self.db.execute(
            "SELECT obs_id FROM obs WHERE file_id = obs_id AND observed_at >= ? AND observed_at <= ? "
            "ORDER BY observed_at, obs_id", (_iso(lo), _iso(hi)))
        return [self.observations[r[0]] for r in rows if self.observations[r[0]].source_kind == "activity"]

    def scopes_for(self, system_id: str, cutoff: datetime) -> list[Scope]:
        return [s for s in self._scopes_by_system.get(system_id, ()) if self.admissible(s, cutoff)]

    def file_has_row(self, file_id: str, resource_id: str, copy: str) -> bool:
        return (file_id, resource_id, copy) in self._rows_in_file

    def resource_ids(self) -> set[str]:
        return set(self._by_resource)
