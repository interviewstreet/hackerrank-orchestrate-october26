"""SQLite persistence for the startup tables.

The cache is valid only while the dataset and the table-building code are unchanged:
a fingerprint over both is stored in the meta table and compared on load.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

from ..config import DATASET_DIR, TABLES_DB
from ..models import Activity, Observation
from .files import EvidenceFile
from .identities import IdentityRow

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_CODE_DIR = Path(__file__).resolve().parents[1]  # code/ghost
_FINGERPRINT_SOURCES = ("tables", "parsers", "identifiers.py", "models.py")

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE files (
    evidence_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
    origin TEXT NOT NULL, captured_at TEXT NOT NULL, sha256 TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE identities (
    identifier TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL,
    current INTEGER NOT NULL, audit_id TEXT
);
CREATE INDEX idx_identities_user ON identities(user_id);
CREATE TABLE activities (
    activity_id TEXT PRIMARY KEY, event_time TEXT NOT NULL, event_type TEXT NOT NULL,
    source_system TEXT NOT NULL, target_system TEXT NOT NULL, resource_id TEXT NOT NULL,
    result TEXT NOT NULL
);
CREATE INDEX idx_activities_resource ON activities(resource_id);
CREATE INDEX idx_activities_window ON activities(target_system, event_type, event_time);
CREATE TABLE observations (
    id INTEGER PRIMARY KEY, evidence_id TEXT NOT NULL, captured_at TEXT NOT NULL,
    system_id TEXT NOT NULL, resource_id TEXT NOT NULL, category TEXT NOT NULL,
    result TEXT NOT NULL, subjects TEXT NOT NULL, retention_until TEXT, raw_ref TEXT NOT NULL
);
CREATE INDEX idx_observations_resource ON observations(resource_id, captured_at);
"""


def fingerprint() -> str:
    """Hash of every dataset file (path, size, mtime) plus the table-building source code."""
    h = hashlib.sha256(f"schema={SCHEMA_VERSION}".encode())
    for p in sorted(DATASET_DIR.rglob("*")):
        if p.is_file():
            st = p.stat()
            h.update(f"{p.relative_to(DATASET_DIR)}|{st.st_size}|{st.st_mtime_ns}".encode())
    for name in _FINGERPRINT_SOURCES:
        target = _CODE_DIR / name
        for p in sorted(target.rglob("*.py")) if target.is_dir() else [target]:
            h.update(p.read_bytes())
    return h.hexdigest()


def save(files: list[EvidenceFile], scopes: dict[str, list[str]], identities: list[IdentityRow],
         activities: list[Activity], observations: list[Observation], fp: str,
         path: Path = TABLES_DB) -> None:
    """Write all tables in one transaction to a temp file, then swap it in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        with con:
            con.executescript(SCHEMA)
            con.executemany(
                "INSERT INTO files VALUES (?,?,?,?,?,?,?)",
                [(f.evidence_id, f.path, f.kind, f.origin, f.captured_at, f.sha256,
                  json.dumps(sorted(scopes.get(f.evidence_id, [])))) for f in files])
            con.executemany(
                "INSERT INTO identities VALUES (?,?,?,?,?)",
                [(r.identifier, r.user_id, r.kind, int(r.current), r.audit_id) for r in identities])
            con.executemany(
                "INSERT INTO activities VALUES (?,?,?,?,?,?,?)",
                [(a.activity_id, a.event_time, a.event_type, a.source_system, a.target_system,
                  a.resource_id, a.result) for a in activities])
            con.executemany(
                "INSERT INTO observations (evidence_id, captured_at, system_id, resource_id, category,"
                " result, subjects, retention_until, raw_ref) VALUES (?,?,?,?,?,?,?,?,?)",
                [(o.evidence_id, o.captured_at, o.system_id, o.resource_id, o.category, o.result,
                  json.dumps(list(o.subjects)), o.retention_until, o.raw_ref) for o in observations])
            con.executemany("INSERT INTO meta VALUES (?,?)",
                            [("fingerprint", fp), ("schema_version", str(SCHEMA_VERSION))])
    finally:
        con.close()
    tmp.replace(path)
    log.info("cache saved: %s", path)


def load(fp: str, path: Path = TABLES_DB):
    """Return the cached tables, or None when the cache is missing or stale.

    One SELECT per table: no per-row or per-case queries ever hit SQLite.
    """
    if not path.is_file():
        log.info("cache: none at %s", path)
        return None
    con = sqlite3.connect(path)
    try:
        stored = dict(con.execute("SELECT key, value FROM meta"))
        if stored.get("fingerprint") != fp:
            log.info("cache: stale (dataset or table code changed), rebuilding")
            return None
        files, scopes = [], {}
        for row in con.execute("SELECT evidence_id, path, kind, origin, captured_at, sha256, scope"
                               " FROM files ORDER BY evidence_id"):
            files.append(EvidenceFile(*row[:6]))
            scopes[row[0]] = json.loads(row[6])
        identities = [IdentityRow(i, u, k, bool(c), a) for i, u, k, c, a in con.execute(
            "SELECT identifier, user_id, kind, current, audit_id FROM identities ORDER BY identifier")]
        activities = [Activity(*row) for row in con.execute(
            "SELECT activity_id, event_time, event_type, source_system, target_system, resource_id,"
            " result FROM activities ORDER BY event_time, activity_id")]
        observations = [
            Observation(e, c, s, r, cat, res, tuple(json.loads(subj)), ret, ref)
            for e, c, s, r, cat, res, subj, ret, ref in con.execute(
                "SELECT evidence_id, captured_at, system_id, resource_id, category, result, subjects,"
                " retention_until, raw_ref FROM observations ORDER BY id")]
    except sqlite3.DatabaseError as exc:
        log.warning("cache: unreadable (%s), rebuilding", exc)
        return None
    finally:
        con.close()
    log.info("cache: loaded %s", path)
    return files, scopes, identities, activities, observations
