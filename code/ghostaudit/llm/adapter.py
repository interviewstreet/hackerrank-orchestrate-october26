"""LLMAdapter: cache -> budget -> backend -> ledger. Backends: claude_cli | anthropic | openai | ollama | replay | offline.

`replay` and `offline` never touch the network: replay serves the committed cache, offline ignores it so
every caller uses its deterministic heuristic.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import BACKENDS, llm_backend
from .backends import BackendUnavailable, get_backend
from .budget import Budget
from .cache import LLMCache, cache_key
from .ledger import Ledger
from .pricing import cost as price_cost

log = logging.getLogger(__name__)

MODEL_ALIASES = {
    "fast": ("GDA_MODEL_FAST", "claude-haiku-5-5"),
    "vision": ("GDA_MODEL_VISION", "claude-sonnet-5-5"),
}
# per-backend defaults when GDA_MODEL_FAST / GDA_MODEL_VISION are not set (Claude ids mean nothing to Ollama)
BACKEND_DEFAULT_MODELS = {
    "ollama": {"fast": "qwen3:8b", "vision": "qwen2.5vl:7b"},
}
# backends whose results are cached under their own key (the original keys belong to the Anthropic models)
VARIANT_BACKENDS = {"ollama", "openai"}
TASK_ALIAS = {"intent": "fast", "extract_visual": "vision", "extract_files": "vision"}
MAX_TOKENS = {"intent": 4000, "extract_visual": 8000, "extract_files": 4000}


@dataclass
class LLMResult:
    text: str
    parsed_json: object
    usage: dict
    model: str
    provider: str
    cached: bool
    cost_usd: float = 0.0
    extra: dict = field(default_factory=dict)


def parse_json(text: str):
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if fence:
        t = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = t.find(opener), t.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except json.JSONDecodeError:
                continue
    return None


class LLMAdapter:
    def __init__(self, backend: str | None = None, cache: LLMCache | None = None, ledger: Ledger | None = None,
                 budget: Budget | None = None, backend_impl=None):
        self.backend_name = backend or llm_backend()
        self.cache = cache or LLMCache()
        self.ledger = ledger or Ledger()
        self.budget = budget or Budget(self.ledger)
        self._backend = backend_impl
        self._backend_error = None
        if self.backend_name not in BACKENDS:
            log.warning("unknown GDA_LLM_BACKEND %r (expected one of %s): using the committed cache only",
                        self.backend_name, ", ".join(BACKENDS))
        if self._backend is None and self.backend_name not in {"replay", "offline"}:
            try:
                self._backend = get_backend(self.backend_name)
            except BackendUnavailable as exc:
                self._backend_error = str(exc)
                log.warning("LLM backend %s unavailable (%s): using cache/offline only", self.backend_name, exc)

    def resolve_model(self, task: str, model: str | None) -> tuple[str, str]:
        alias = model or TASK_ALIAS.get(task, "fast")
        if alias in MODEL_ALIASES:
            env_name, default = MODEL_ALIASES[alias]
            default = BACKEND_DEFAULT_MODELS.get(self.backend_name, {}).get(alias, default)
            return alias, os.environ.get(env_name, default)
        return alias, alias

    def complete(self, *, task: str, prompt: str, images: list[Path] | None = None, model: str | None = None,
                 json_schema: dict | None = None) -> LLMResult | None:
        images = [Path(i) for i in (images or [])]
        alias, model_id = self.resolve_model(task, model)
        base = cache_key(task, alias, prompt, images)
        variant = f"{self.backend_name}:{model_id}" if self.backend_name in VARIANT_BACKENDS else ""
        key = cache_key(task, alias, prompt, images, variant) if variant else base
        if self.backend_name != "offline":
            # replay serves the default entry, else any variant recorded for the same request
            hit = self.cache.get(key) if variant else self.cache.get_by_base(base)
            if hit is not None:
                return self._cached(task, hit, model_id, json_schema)
        if self._backend is None:
            return None
        result = self._live(task, prompt, images, alias, model_id, json_schema, key, base if variant else "")
        if result is None and variant:
            # e.g. a PDF a local vision model cannot read: fall back to what the cache already knows
            hit = self.cache.get_by_base(base)
            if hit is not None:
                return self._cached(task, hit, model_id, json_schema)
        return result

    def _cached(self, task: str, hit: dict, model_id: str, json_schema) -> LLMResult:
        self.ledger.record(task=task, model=hit.get("model", model_id), provider=hit.get("provider", ""),
                           tokens_in=0, tokens_out=0, cost_usd=0.0, cached=True, key=hit["key"])
        return LLMResult(hit["text"], parse_json(hit["text"]) if json_schema is not None else None,
                         {"in": 0, "out": 0}, hit.get("model", model_id), hit.get("provider", ""), True)

    def _live(self, task: str, prompt: str, images: list[Path], alias: str, model_id: str, json_schema,
              key: str, base: str) -> LLMResult | None:
        max_tokens = MAX_TOKENS.get(task, 4000)
        attempts = 2 if json_schema is not None else 1
        for attempt in range(attempts):
            estimate = self.budget.estimate(model_id, alias, prompt, len(images), max_tokens)
            if not self.budget.reserve(estimate):
                log.warning("LLM budget exhausted: %s falls back", task)
                return None
            try:
                resp = self._backend.call(prompt, images, model_id, max_tokens, json_mode=json_schema is not None)
            except Exception as exc:  # network / CLI failure -> fallback, never crash the run
                log.warning("LLM call failed for %s: %s", task, exc)
                self.budget.release(estimate)
                return None
            self.budget.release(estimate)
            spent = resp.cost_usd if resp.cost_usd is not None else price_cost(resp.model, resp.tokens_in, resp.tokens_out, alias)
            self.ledger.record(task=task, model=resp.model, provider=resp.provider, tokens_in=resp.tokens_in,
                               tokens_out=resp.tokens_out, cost_usd=spent, cached=False, key=key, attempt=attempt)
            parsed = parse_json(resp.text) if json_schema is not None else None
            if json_schema is not None and parsed is None:
                log.warning("unparseable JSON from %s (attempt %d)", task, attempt + 1)
                continue
            record = {"task": task, "model": resp.model, "provider": resp.provider, "text": resp.text,
                      "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out, "cost_usd": spent}
            if base:
                record["base"] = base
            self.cache.put(key, record)
            return LLMResult(resp.text, parsed, {"in": resp.tokens_in, "out": resp.tokens_out}, resp.model,
                             resp.provider, False, spent)
        return None

    def spend_line(self) -> str:
        s = self.ledger.summary()
        return (f"LLM spend: ${self.budget.spent():.2f} / ${self.budget.limit:.2f} "
                f"({s['live_calls']} live calls, {s['cache_hits']} cache hits) backend={self.backend_name}")
