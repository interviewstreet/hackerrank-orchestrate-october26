"""Transactional local run state and usage accounting."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .contracts import CONTRACT_VERSION, ModelCallRecord

SCHEMA_VERSION = 1


class RunStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def _initialize(self) -> None:
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_calls (
                    call_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                """
            )
            expected = {
                "schema_version": str(SCHEMA_VERSION),
                "contract_version": CONTRACT_VERSION,
            }
            for key, value in expected.items():
                row = connection.execute(
                    "SELECT value FROM metadata WHERE key = ?", (key,)
                ).fetchone()
                if row is not None and row[0] != value:
                    raise RuntimeError(f"incompatible run store {key}: {row[0]}")
                connection.execute(
                    "INSERT OR IGNORE INTO metadata(key, value) VALUES (?, ?)",
                    (key, value),
                )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def record_model_call(self, record: ModelCallRecord) -> None:
        payload = json.dumps(record.model_dump(mode="json"), sort_keys=True)
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO model_calls(call_id, payload_json) VALUES (?, ?)",
                (record.call_id, payload),
            )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
