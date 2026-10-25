"""OpenAI client wrapper: disk cache, retries, token accounting.

Every call is cached under cache/llm/<sha256(kind, model, prompt, payload)>.json, so a rerun costs
nothing. Usage (calls, input/output tokens per model) accumulates in cache/usage.json for the
usage report. Without a key, or with --offline, every call raises ModelUnavailable.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

from ..config import LLM_CACHE_DIR, USAGE_JSON, Settings
from ..errors import ModelUnavailable

log = logging.getLogger(__name__)

# USD per 1M tokens (input, output). Used only for the usage report estimate.
PRICES = {"gpt-4.1-mini": (0.40, 1.60), "gpt-4.1-nano": (0.10, 0.40), "gpt-4o-mini": (0.15, 0.60)}


class ModelClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        self.usage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # --- public API -------------------------------------------------------------
    def complete_json(self, kind: str, system: str, user: str, image: Path | None = None,
                      max_tokens: int = 1500) -> dict:
        """One chat completion returning a JSON object, cached by content."""
        image_bytes = image.read_bytes() if image else b""
        key = hashlib.sha256(json.dumps([kind, self.settings.model, system, user]).encode()
                             + image_bytes).hexdigest()
        cached = LLM_CACHE_DIR / f"{key}.json"
        if cached.is_file():
            self.usage[self.settings.model]["cache_hits"] += 1
            return json.loads(cached.read_text(encoding="utf-8"))["response"]

        client = self._get_client()
        content: list | str = user
        if image is not None:
            b64 = base64.b64encode(image_bytes).decode()
            content = [{"type": "text", "text": user},
                       {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]
        messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=self.settings.model, messages=messages, temperature=0,
                    max_tokens=max_tokens, response_format={"type": "json_object"})
                break
            except Exception as exc:  # network, rate limit, server error
                last_exc = exc
                log.warning("%s call failed (attempt %d/3): %s", kind, attempt + 1, exc)
                time.sleep(2 ** attempt)
        else:
            raise ModelUnavailable(f"{kind}: {last_exc}")

        u = self.usage[self.settings.model]
        u["calls"] += 1
        u[f"calls_{kind}"] += 1
        u["input_tokens"] += resp.usage.prompt_tokens
        u["output_tokens"] += resp.usage.completion_tokens
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError as exc:
            raise ModelUnavailable(f"{kind}: model returned invalid JSON") from exc
        cached.write_text(json.dumps({"kind": kind, "model": self.settings.model,
                                      "response": data}, indent=1), encoding="utf-8")
        return data

    def save_usage(self, cases: int) -> None:
        report = {"cases": cases, "models": {}}
        for model, u in sorted(self.usage.items()):
            pin, pout = PRICES.get(model, (0.0, 0.0))
            cost = u["input_tokens"] / 1e6 * pin + u["output_tokens"] / 1e6 * pout
            report["models"][model] = {**dict(u), "estimated_cost_usd": round(cost, 6),
                                       "provider": "openai"}
        USAGE_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # --- internals ----------------------------------------------------------------
    def _get_client(self):
        if self.settings.offline or not self.settings.openai_api_key:
            raise ModelUnavailable("no OPENAI_API_KEY configured or running offline")
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ModelUnavailable("openai package not installed") from exc
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client
