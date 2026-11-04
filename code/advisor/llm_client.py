"""Minimal Anthropic Messages API client (stdlib only) plus a scriptable fake for tests."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


@dataclass
class UsageLog:
    """Truthful accounting of every model call (feeds usage_report.md)."""
    provider: str = "Anthropic"
    model: str = DEFAULT_MODEL
    calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    per_case: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def add(self, case_id: str, inp: int, out: int) -> None:
        self.calls += 1
        self.input_tokens += inp
        self.output_tokens += out
        c = self.per_case.setdefault(case_id, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        c["calls"] += 1; c["input_tokens"] += inp; c["output_tokens"] += out

    def to_dict(self) -> dict:
        return {"provider": self.provider, "model": self.model, "calls": self.calls, "failed_calls": self.failed_calls,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "per_case": self.per_case}


class ModelUnavailable(RuntimeError):
    pass


class AnthropicClient:
    """Reads ANTHROPIC_API_KEY from the environment; the key is never logged or written anywhere."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 60):
        self.model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self._key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.timeout = timeout
        self.usage = UsageLog(model=self.model)

    @property
    def available(self) -> bool:
        return bool(self._key)

    def complete(self, case_id: str, system: str, user: str, max_tokens: int = 600) -> str:
        if not self._key:
            raise ModelUnavailable("ANTHROPIC_API_KEY is not set")
        body = json.dumps({"model": self.model, "max_tokens": max_tokens, "temperature": 0, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "content-type": "application/json", "x-api-key": self._key, "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:   # never include headers/key in errors
            self.usage.failed_calls += 1
            raise ModelUnavailable(f"model call failed: {type(e).__name__}") from None
        u = data.get("usage", {})
        self.usage.add(case_id, int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)))
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


class FakeClient:
    """Test double: returns scripted text and records prompts. Never touches the network."""

    def __init__(self, reply: Callable[[str, str], str] | str = "{}", tokens: Tuple[int, int] = (100, 50)):
        self._reply, self._tokens = reply, tokens
        self.model = "fake-model"
        self.available = True
        self.usage = UsageLog(provider="fake", model="fake-model")
        self.prompts: List[Tuple[str, str]] = []

    def complete(self, case_id: str, system: str, user: str, max_tokens: int = 600) -> str:
        self.prompts.append((system, user))
        self.usage.add(case_id, *self._tokens)
        return self._reply(system, user) if callable(self._reply) else self._reply
