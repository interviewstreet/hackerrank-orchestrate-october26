"""Content-hash cache of LLM results (committed under code/cache/llm_cache.jsonl)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

from ..config import CACHE_DIR


def cache_key(task: str, model_alias: str, prompt: str, images: list[Path], variant: str = "") -> str:
    """`variant` ("backend:model") separates results of non-default backends; empty keeps the original key."""
    h = hashlib.sha256()
    for part in (task, model_alias, prompt):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    for img in images:
        h.update(hashlib.sha256(Path(img).read_bytes()).hexdigest().encode())
    if variant:
        h.update(b"\x00" + variant.encode("utf-8"))
    return h.hexdigest()


class LLMCache:
    def __init__(self, path: Path | None = None):
        # GDA_LLM_CACHE: another cache file (e.g. for experiments that must not touch the committed one)
        self.path = path or Path(os.environ.get("GDA_LLM_CACHE") or CACHE_DIR / "llm_cache.jsonl")
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._data[rec["key"]] = rec

    def get(self, key: str) -> dict | None:
        return self._data.get(key)

    def get_by_base(self, base: str) -> dict | None:
        """Exact entry for the variant-free key, else the first variant entry recorded for it (sorted by key)."""
        hit = self._data.get(base)
        if hit is not None:
            return hit
        return next((self._data[k] for k in sorted(self._data) if self._data[k].get("base") == base), None)

    def put(self, key: str, record: dict) -> None:
        with self._lock:
            rec = {"key": key, **record}
            self._data[key] = rec
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # rewrite sorted so the committed file is deterministic
            lines = [json.dumps(self._data[k], ensure_ascii=False, sort_keys=True) for k in sorted(self._data)]
            self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
