"""SQLite outbox: the single source of truth for email state.

State changes are one conditional UPDATE (`... WHERE state IN (allowed)`), so two requests racing to approve or send
the same email cannot both win, even across processes. Every change also writes an audit event.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .errors import EmailNotFound
from .models import EmailRecord, EmailState, TRANSITIONS

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL, recipient TEXT NOT NULL, kind TEXT NOT NULL,
  subject TEXT NOT NULL, body_text TEXT NOT NULL, state TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE, revision INTEGER NOT NULL DEFAULT 1, meta TEXT NOT NULL DEFAULT '{}',
  approved_by TEXT NOT NULL DEFAULT '', approved_at TEXT NOT NULL DEFAULT '', approved_hash TEXT NOT NULL DEFAULT '',
  rejected_by TEXT NOT NULL DEFAULT '', rejected_at TEXT NOT NULL DEFAULT '', rejection_reason TEXT NOT NULL DEFAULT '',
  resend_id TEXT NOT NULL DEFAULT '', delivery_status TEXT NOT NULL DEFAULT '', last_error TEXT NOT NULL DEFAULT '',
  sent_at TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS emails_case ON emails(case_id);
CREATE INDEX IF NOT EXISTS emails_resend ON emails(resend_id);
CREATE TABLE IF NOT EXISTS email_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, email_id TEXT NOT NULL, at TEXT NOT NULL,
  from_state TEXT NOT NULL, to_state TEXT NOT NULL, actor TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS webhook_events (svix_id TEXT PRIMARY KEY, received_at TEXT NOT NULL);
"""

_UPDATABLE = {"subject", "body_text", "meta", "revision", "approved_by", "approved_at", "approved_hash", "rejected_by",
              "rejected_at", "rejection_reason", "resend_id", "delivery_status", "last_error", "sent_at"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(row: sqlite3.Row) -> EmailRecord:
    d = dict(row)
    d["meta"] = json.loads(d.get("meta") or "{}")
    return EmailRecord(**d)


class EmailStore:
    def __init__(self, path: str = ":memory:", clock: Callable[[], str] = utc_now):
        self._clock = clock
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self._db.row_factory = sqlite3.Row
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    # ---- reads ----
    def get(self, email_id: str) -> EmailRecord:
        with self._lock:
            row = self._db.execute("SELECT * FROM emails WHERE id=?", (email_id,)).fetchone()
        if row is None:
            raise EmailNotFound(f"no email with id {email_id}")
        return _record(row)

    def find_by_key(self, key: str) -> Optional[EmailRecord]:
        with self._lock:
            row = self._db.execute("SELECT * FROM emails WHERE idempotency_key=?", (key,)).fetchone()
        return _record(row) if row else None

    def find_by_resend_id(self, resend_id: str) -> Optional[EmailRecord]:
        if not resend_id:
            return None
        with self._lock:
            row = self._db.execute("SELECT * FROM emails WHERE resend_id=?", (resend_id,)).fetchone()
        return _record(row) if row else None

    def list(self, case_id: Optional[str] = None, state: Optional[str] = None, limit: int = 200) -> List[EmailRecord]:
        q, args = "SELECT * FROM emails WHERE 1=1", []
        if case_id:
            q += " AND case_id=?"; args.append(case_id)
        if state:
            q += " AND state=?"; args.append(state)
        q += " ORDER BY created_at, id LIMIT ?"; args.append(max(1, min(limit, 1000)))
        with self._lock:
            return [_record(r) for r in self._db.execute(q, args).fetchall()]

    def events(self, email_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT at, from_state, to_state, actor, note FROM email_events "
                                    "WHERE email_id=? ORDER BY seq", (email_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- writes ----
    def create(self, rec: EmailRecord, actor: str) -> Tuple[EmailRecord, bool]:
        """Insert unless the idempotency key already exists. Returns (record, created)."""
        now = self._clock()
        rec.created_at = rec.updated_at = now
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO emails (id, case_id, recipient, kind, subject, body_text, state, idempotency_key,"
                " revision, meta, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rec.id, rec.case_id, rec.recipient, rec.kind, rec.subject, rec.body_text, rec.state,
                 rec.idempotency_key, rec.revision, json.dumps(rec.meta, sort_keys=True), now, now))
            if cur.rowcount == 1:
                self._event(rec.id, "", rec.state, actor, "created")
                return rec, True
        existing = self.find_by_key(rec.idempotency_key)
        assert existing is not None
        return existing, False

    def transition(self, email_id: str, from_states: Iterable[EmailState], to_state: EmailState, actor: str,
                   note: str = "", **fields: Any) -> Optional[EmailRecord]:
        """Atomically move email_id from any of from_states to to_state. Returns the new record, or None if the
        email was not in one of from_states (someone else got there first, or the action is not allowed)."""
        froms = [EmailState(s) for s in from_states]
        for f in froms:
            if to_state not in TRANSITIONS[f]:
                raise ValueError(f"illegal transition {f.value} -> {to_state.value}")
        bad = set(fields) - _UPDATABLE
        if bad:
            raise ValueError(f"cannot set {sorted(bad)}")
        sets = ["state=?", "updated_at=?"] + [f"{k}=?" for k in fields]
        args: List[Any] = [to_state.value, self._clock()] + [json.dumps(v, sort_keys=True) if k == "meta" else v
                                                              for k, v in fields.items()]
        marks = ",".join("?" for _ in froms)
        with self._lock, self._db:
            prev = self._db.execute("SELECT state FROM emails WHERE id=?", (email_id,)).fetchone()
            if prev is None:
                raise EmailNotFound(f"no email with id {email_id}")
            cur = self._db.execute(f"UPDATE emails SET {', '.join(sets)} WHERE id=? AND state IN ({marks})",
                                   args + [email_id] + [f.value for f in froms])
            if cur.rowcount != 1:
                return None
            self._event(email_id, prev["state"], to_state.value, actor, note)
        return self.get(email_id)

    def update_fields(self, email_id: str, only_in: Iterable[EmailState], actor: str, note: str = "",
                      **fields: Any) -> Optional[EmailRecord]:
        """Change non-state fields (content, delivery status) without changing state, only while in only_in."""
        bad = set(fields) - _UPDATABLE
        if bad or not fields:
            raise ValueError(f"cannot set {sorted(bad)}" if bad else "nothing to update")
        states = [EmailState(s).value for s in only_in]
        sets = ["updated_at=?"] + [f"{k}=?" for k in fields]
        args = [self._clock()] + [json.dumps(v, sort_keys=True) if k == "meta" else v for k, v in fields.items()]
        with self._lock, self._db:
            row = self._db.execute("SELECT state FROM emails WHERE id=?", (email_id,)).fetchone()
            if row is None:
                raise EmailNotFound(f"no email with id {email_id}")
            cur = self._db.execute(f"UPDATE emails SET {', '.join(sets)} WHERE id=? AND state IN "
                                   f"({','.join('?' for _ in states)})", args + [email_id] + states)
            if cur.rowcount != 1:
                return None
            if note:
                self._event(email_id, row["state"], row["state"], actor, note)
        return self.get(email_id)

    def record_webhook(self, svix_id: str) -> bool:
        """True the first time a webhook message id is seen, False for a redelivery."""
        with self._lock, self._db:
            cur = self._db.execute("INSERT OR IGNORE INTO webhook_events (svix_id, received_at) VALUES (?,?)",
                                   (svix_id, self._clock()))
            return cur.rowcount == 1

    def _event(self, email_id: str, frm: str, to: str, actor: str, note: str) -> None:
        self._db.execute("INSERT INTO email_events (email_id, at, from_state, to_state, actor, note) VALUES (?,?,?,?,?,?)",
                         (email_id, self._clock(), frm, to, actor, note))

    def now(self) -> str:
        return self._clock()

    def close(self) -> None:
        with self._lock:
            self._db.close()


def new_id() -> str:
    return uuid.uuid4().hex
