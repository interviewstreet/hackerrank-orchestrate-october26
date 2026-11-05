"""
audit_db.py — saves every case's pipeline results to audit.db (SQLite).

The website cannot run the Python pipeline, so main.py stores each case
here and export_web_data.py turns the database into static JSON files.

audit.db holds the real (fictional) identifiers from dataset/, unmasked.
It stays local; only the masked JSON export is meant to be published.

Tables (one row per item, every row keyed by case_id):
    cases          one row per request
    identities     every current and historical identifier of the subject
    evidence_hits  one row per (evidence record, matched identifier) from P2
    resources      P3 decision["resources"]  (CONTRACTS.md section 2)
    flows          P3 decision["flows"]
    timeline       P3 decision["timeline"]
    steps          P4 build_steps() output

resources / flows / timeline stay empty until P3's decide() returns them.

Re-running is safe: save_case() deletes the case's old rows in every table
before writing, all in one transaction. If an existing audit.db was made
with an older schema, connect() rebuilds it (everything in it is derived
from dataset/ by main.py, so nothing is lost).
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "audit.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id         TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    request_text    TEXT NOT NULL,
    reported_status TEXT NOT NULL,
    our_status      TEXT NOT NULL,
    classification  TEXT NOT NULL,
    requested_at    TEXT NOT NULL,
    audit_at        TEXT NOT NULL,
    language        TEXT NOT NULL,         -- en / es / pt / fr / ja / ko ('' if not classified)
    confidence      TEXT NOT NULL,         -- HIGH / LOW ('' if not classified)
    matched_signals TEXT NOT NULL,         -- JSON list, e.g. ["opt_out: marketing"]
    reason          TEXT NOT NULL          -- one plain-English sentence
);
CREATE TABLE IF NOT EXISTS identities (
    case_id       TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('email', 'phone', 'email_hash', 'name')),
    value         TEXT NOT NULL,
    is_historical INTEGER NOT NULL CHECK (is_historical IN (0, 1)),
    audit_id      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_hits (
    case_id            TEXT NOT NULL,
    file_id            TEXT NOT NULL,
    system_id          TEXT NOT NULL,
    resource_id        TEXT NOT NULL,
    matched_identifier TEXT NOT NULL,
    captured_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
    case_id            TEXT NOT NULL,
    system_id          TEXT NOT NULL,
    resource_id        TEXT NOT NULL,
    category           TEXT NOT NULL,
    required_treatment TEXT NOT NULL,
    state_at_audit     TEXT NOT NULL,
    satisfied          INTEGER NOT NULL,
    evidence_ids       TEXT NOT NULL       -- JSON array of ids, best first
);
CREATE TABLE IF NOT EXISTS flows (
    case_id         TEXT NOT NULL,
    system_id       TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    kind            TEXT NOT NULL,
    active_at_audit INTEGER NOT NULL,
    evidence_id     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS timeline (
    case_id     TEXT NOT NULL,
    seq         INTEGER NOT NULL,         -- order P3 returned (oldest first)
    time        TEXT NOT NULL,
    system_id   TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    event       TEXT NOT NULL,
    state_after TEXT NOT NULL,
    evidence_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    case_id     TEXT NOT NULL,
    step_no     INTEGER NOT NULL,
    phase       TEXT NOT NULL,
    system_id   TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    operation   TEXT NOT NULL,
    state       TEXT NOT NULL,
    evidence_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_identities_case    ON identities(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hits_case ON evidence_hits(case_id);
CREATE INDEX IF NOT EXISTS idx_resources_case     ON resources(case_id);
CREATE INDEX IF NOT EXISTS idx_flows_case         ON flows(case_id);
CREATE INDEX IF NOT EXISTS idx_timeline_case      ON timeline(case_id);
CREATE INDEX IF NOT EXISTS idx_steps_case         ON steps(case_id);
"""

TABLES = ("cases", "identities", "evidence_hits", "resources", "flows", "timeline", "steps")


def _expected_columns() -> dict[str, list[str]]:
    """{table: [column, ...]} as written in SCHEMA."""
    out: dict[str, list[str]] = {}
    for table, body in re.findall(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", SCHEMA, re.S):
        out[table] = [line.split()[0] for line in body.strip().splitlines()]
    return out


EXPECTED_COLUMNS = _expected_columns()


def _schema_is_current(conn: sqlite3.Connection) -> bool:
    for table, cols in EXPECTED_COLUMNS.items():
        got = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if got and got != cols:
            return False
    return True


def connect(path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Open (or create) audit.db and make sure every table exists with the
    current columns. An out-of-date audit.db is rebuilt empty.
    """
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    if not _schema_is_current(conn):
        with conn:
            for table in EXPECTED_COLUMNS:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Row builders (pure functions, easy to test)
# ---------------------------------------------------------------------------

def _s(value: Any) -> str:
    """Text for a NOT NULL column: None -> '', datetime -> ISO-8601 UTC."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _b(value: Any) -> int:
    return 1 if value else 0


def identity_rows(case_id: str, identity) -> list[tuple]:
    """
    Every identifier in the IdentityBundle, current first.

    audit_id is the user_audit_log row that explains the value:
      - historical value -> the change that replaced it (old_value)
      - current value    -> the latest change that set it (new_value), or ''
        if it was never changed.
    """
    if identity is None:
        return []
    history = list(getattr(identity, "history", []) or [])

    def norm(kind: str, v: str) -> str:
        return v.strip().lower() if kind == "email" else v.strip()

    def set_by(kind: str, value: str) -> str:
        found = ""
        for ch in history:                       # oldest first -> keep the latest
            if ch.field_name == kind and norm(kind, ch.new_value) == norm(kind, value):
                found = ch.audit_id
        return found

    def replaced_by(kind: str, value: str) -> str:
        for ch in history:
            if ch.field_name == kind and norm(kind, ch.old_value) == norm(kind, value):
                return ch.audit_id
        return ""

    uid = identity.user_id
    rows: list[tuple] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, historical: bool) -> None:
        if not value or not value.strip():
            return
        key = (kind, norm(kind, value))
        if key in seen:
            return
        seen.add(key)
        aid = replaced_by(kind, value) if historical else set_by(kind, value)
        rows.append((case_id, uid, kind, value, _b(historical), aid))

    add("email", identity.current_email, False)
    add("phone", identity.current_phone, False)
    add("email_hash", identity.current_email_hash, False)
    add("name", identity.current_name, False)
    for v in identity.historical_emails:
        add("email", v, True)
    for v in identity.historical_phones:
        add("phone", v, True)
    for v in identity.historical_email_hashes:
        add("email_hash", v, True)
    return rows


def evidence_rows(case_id: str, evidence: Optional[dict]) -> list[tuple]:
    """One row per (record, matched identifier) in evidence['records']."""
    if not evidence:
        return []
    rows: list[tuple] = []
    seen: set[tuple] = set()
    for rec in evidence.get("records", []) or []:
        matched = list(getattr(rec, "identifiers_matched", []) or []) or [""]
        for ident in matched:
            row = (case_id, _s(rec.evidence_id), _s(rec.system_id), _s(rec.resource_id),
                   _s(ident), _s(rec.captured_at))
            if row not in seen:
                seen.add(row)
                rows.append(row)
    return rows


def resource_rows(case_id: str, decision: Optional[dict]) -> list[tuple]:
    rows = []
    for r in (decision or {}).get("resources", []) or []:
        rows.append((case_id, _s(r.get("system_id")), _s(r.get("resource_id")),
                     _s(r.get("category")), _s(r.get("required_treatment")),
                     _s(r.get("state_at_audit")), _b(r.get("satisfied")),
                     json.dumps(list(r.get("evidence_ids") or []), ensure_ascii=False)))
    return rows


def flow_rows(case_id: str, decision: Optional[dict]) -> list[tuple]:
    rows = []
    for f in (decision or {}).get("flows", []) or []:
        rows.append((case_id, _s(f.get("system_id")), _s(f.get("resource_id")),
                     _s(f.get("kind")), _b(f.get("active_at_audit")),
                     _s(f.get("evidence_id"))))
    return rows


def timeline_rows(case_id: str, decision: Optional[dict]) -> list[tuple]:
    rows = []
    for i, t in enumerate((decision or {}).get("timeline", []) or [], start=1):
        rows.append((case_id, i, _s(t.get("time")), _s(t.get("system_id")),
                     _s(t.get("resource_id")), _s(t.get("event")),
                     _s(t.get("state_after")), _s(t.get("evidence_id"))))
    return rows


def step_rows(case_id: str, steps: Optional[Iterable[dict]]) -> list[tuple]:
    rows = []
    for s in steps or []:
        rows.append((case_id, int(s.get("step_no") or 0), _s(s.get("phase")),
                     _s(s.get("system_id")), _s(s.get("resource_id")),
                     _s(s.get("operation")), _s(s.get("state")),
                     _s(s.get("evidence_id"))))
    return rows


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def classifier_fields(result) -> tuple[str, str, str, str]:
    """(language, confidence, matched_signals JSON, reason) from a ClassificationResult."""
    if result is None:
        return "", "", "[]", ""
    return (_s(getattr(result, "language", "")), _s(getattr(result, "confidence", "")),
            json.dumps(list(getattr(result, "signals", []) or []), ensure_ascii=False),
            _s(getattr(result, "reason", "")))


def save_case(conn: sqlite3.Connection, case: dict, *, our_status: str,
              classification: str, classifier=None, identity=None,
              evidence: Optional[dict] = None, decision: Optional[dict] = None,
              steps: Optional[Iterable[dict]] = None) -> None:
    """
    Save one case's results. Any argument may be None when the pipeline
    stopped early (NOT_APPLICABLE, unresolved email, an error ...).
    *classifier* is the ClassificationResult; it fills language,
    confidence, matched_signals and reason.

    Old rows for this case_id are deleted first, in the same transaction,
    so running the pipeline twice never duplicates rows. If anything fails
    the transaction is rolled back and the error is raised.
    """
    cid = case["case_id"]
    rows = {
        "identities": identity_rows(cid, identity),
        "evidence_hits": evidence_rows(cid, evidence),
        "resources": resource_rows(cid, decision),
        "flows": flow_rows(cid, decision),
        "timeline": timeline_rows(cid, decision),
        "steps": step_rows(cid, steps),
    }
    case_row = (cid, _s(case.get("email")), _s(case.get("request_text")),
                _s(case.get("reported_status")), _s(our_status), _s(classification),
                _s(case.get("requested_at")), _s(case.get("audit_at")),
                *classifier_fields(classifier))

    with conn:  # one transaction: commit on success, roll back on error
        for table in TABLES:
            conn.execute(f"DELETE FROM {table} WHERE case_id = ?", (cid,))
        conn.execute(_insert_sql("cases"), case_row)
        for table, table_rows in rows.items():
            if table_rows:
                conn.executemany(_insert_sql(table), table_rows)


def _insert_sql(table: str) -> str:
    """INSERT with explicit column names, so column order never matters."""
    cols = EXPECTED_COLUMNS[table]
    return f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
