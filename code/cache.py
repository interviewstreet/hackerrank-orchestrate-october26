"""Small, atomic persistent JSON cache for model results."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / "cache.json"


def _load() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    try:
        value = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def get(key: str) -> str | None:
    return _load().get(key)


def set(key: str, value: str):
    data = _load()
    data[str(key)] = str(value)
    tmp = CACHE_PATH.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        tmp.replace(CACHE_PATH)
    finally:
        # A failed replace must not leave a submission artifact behind.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def make_key(case_id: str, prompt: str) -> str:
    return hashlib.sha256((case_id + prompt).encode("utf-8")).hexdigest()
