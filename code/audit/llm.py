"""Thin Claude client: structured JSON calls, a content-addressed cache, and a usage ledger.

Every call is keyed by sha256(model + prompt version + input bytes). Results are stored in
`code/cache/llm_cache.json`, so a rerun of the pipeline is free and deterministic. Usage of
calls that actually reached the API is appended to `code/cache/usage_log.jsonl`, which the
usage report is built from.

The key is read from ANTHROPIC_API_KEY only. Without it, cached answers are still served,
and uncached requests raise `LLMUnavailable` so callers can fall back.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path

MODEL = os.environ.get("AUDIT_MODEL", "claude-opus-5-5")
# USD per million tokens (input, output), from Anthropic's published pricing
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "llm_cache.json"
USAGE_FILE = CACHE_DIR / "usage_log.jsonl"


class LLMUnavailable(RuntimeError):
    pass


class Claude:
    def __init__(self, model: str = MODEL, offline: bool = False):
        self.model = model
        self.offline = offline or not os.environ.get("ANTHROPIC_API_KEY")
        self._client = None
        CACHE_DIR.mkdir(exist_ok=True)
        self.cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
        self.session_calls = []  # usage of the calls made in this run

    def _api(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def _save(self):
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, indent=1, sort_keys=True, ensure_ascii=False))
        tmp.replace(CACHE_FILE)

    def json_call(self, purpose: str, prompt_version: str, system: str, content: list,
                  schema: dict, cache_material: bytes, max_tokens: int = 4000) -> dict:
        """One structured-output request. `content` is the user message content blocks."""
        key = hashlib.sha256(self.model.encode() + b"\0" + prompt_version.encode() + b"\0"
                             + cache_material).hexdigest()
        if key in self.cache:
            return self.cache[key]["result"]
        if self.offline:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set and no cached answer exists")
        client = self._api()
        last_err = None
        for attempt in range(4):
            try:
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": content}],
                    output_config={"effort": "low",
                                   "format": {"type": "json_schema", "schema": schema}},
                )
                break
            except Exception as e:  # rate limits / transient errors
                last_err = e
                time.sleep(2 ** attempt * 2)
        else:
            raise LLMUnavailable(f"Claude request failed: {last_err}")
        if resp.stop_reason == "refusal":
            raise LLMUnavailable("Claude refused the request")
        text = next(b.text for b in resp.content if b.type == "text")
        result = json.loads(text)
        u = resp.usage
        record = {"purpose": purpose, "model": self.model, "input_tokens": u.input_tokens,
                  "output_tokens": u.output_tokens,
                  "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                  "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
                  "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.session_calls.append(record)
        with open(USAGE_FILE, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        self.cache[key] = {"purpose": purpose, "result": result}
        self._save()
        return result


def image_block(path: Path) -> dict:
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout
