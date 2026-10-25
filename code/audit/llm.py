"""Thin LLM wrapper: env-var key, temperature 0, JSON-only, retries,
disk cache keyed by SHA-256(model+prompt), and token accounting.

Only used for request-intent classification (and optionally vision). The
deterministic pipeline runs fully with --no-llm, in which case no network
call is made and this module is never used to produce output.csv.
Supports the Anthropic Messages API shape via stdlib urllib (no SDK needed).
"""
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

from .config import CACHE_DIR, EVALUATION_DIR

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "intent_classifier.md"


class LLMNotConfigured(RuntimeError):
    pass


class LLMClient:
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
        self.model = os.environ.get("LLM_MODEL", "claude-haiku-4-5")
        env = os.environ
        self.api_key = env.get("ANTHROPIC_API_KEY", "")
        if self.provider == "anthropic" and not self.api_key:
            raise LLMNotConfigured(
                "No API key set (expected ANTHROPIC_API_KEY in environment). "
                "Re-run with --no-llm for the rule-based classifier.")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache_file = CACHE_DIR / "llm_cache.json"
        self.cache = {}
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except ValueError:
                self.cache = {}
        self.stats = {"provider": self.provider, "model": self.model,
                      "calls": 0, "cache_hits": 0, "input_tokens": 0,
                      "output_tokens": 0}

    def _save_cache(self):
        self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")

    def complete_json(self, prompt):
        key = hashlib.sha256(f"{self.model}\n{prompt}".encode()).hexdigest()
        if key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[key]
        if self.provider != "anthropic":
            raise LLMNotConfigured(f"Unsupported LLM_PROVIDER={self.provider}")
        body = json.dumps({
            "model": self.model, "max_tokens": 4096, "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        last_err = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages", data=body,
                    headers={"x-api-key": self.api_key,
                             "anthropic-version": "2023-06-01",
                             "content-type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
                text = "".join(block.get("text", "") for block
                               in data.get("content", []))
                usage = data.get("usage", {})
                self.stats["calls"] += 1
                self.stats["input_tokens"] += usage.get("input_tokens", 0)
                self.stats["output_tokens"] += usage.get("output_tokens", 0)
                parsed = json.loads(text)
                self.cache[key] = parsed
                self._save_cache()
                self.save_usage_stats()
                return parsed
            except Exception as exc:  # retry with backoff; never log the key
                last_err = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def save_usage_stats(self):
        EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
        (EVALUATION_DIR / "usage_stats.json").write_text(
            json.dumps(self.stats, indent=2), encoding="utf-8")
