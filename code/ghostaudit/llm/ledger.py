"""Append-only call ledger (code/cache/ledger/<run_id>.jsonl): every call, cache hits flagged."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..config import CACHE_DIR

LEDGER_DIR = CACHE_DIR / "ledger"


class Ledger:
    def __init__(self, run_id: str | None = None, directory: Path | None = None):
        self.dir = directory or LEDGER_DIR
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = self.dir / f"{self.run_id}.jsonl"
        self.entries: list[dict] = []
        self._lock = threading.Lock()

    def record(self, **entry) -> None:
        with self._lock:
            self.entries.append(entry)
            self.dir.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def run_spend(self) -> float:
        return sum(e.get("cost_usd", 0.0) for e in self.entries if not e.get("cached"))

    def summary(self) -> dict:
        live = [e for e in self.entries if not e.get("cached")]
        return {"live_calls": len(live), "cache_hits": len(self.entries) - len(live), "spend_usd": self.run_spend()}


def total_spend(directory: Path | None = None) -> float:
    d = directory or LEDGER_DIR
    spent = 0.0
    if d.exists():
        for f in sorted(d.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = json.loads(line)
                    if not e.get("cached"):
                        spent += float(e.get("cost_usd", 0.0))
    return spent


def load_entries(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
