"""Minimal Anthropic Messages API client (stdlib only) plus a scriptable fake for tests."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
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


class OpenAICompatibleClient:
    """Chat-completions client for any OpenAI-style gateway (e.g. an LLM router).

    Settings come from the environment / .env: LLM_API_KEY, LLM_BASE_URL (ending in /v1), LLM_MODEL.
    The key is sent only in the Authorization header and is never logged or included in errors.
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: int = 90):
        self._key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "")).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", "")
        self.timeout = timeout
        host = urllib.parse.urlparse(self.base_url).netloc if self.base_url else "unknown"
        self.usage = UsageLog(provider=os.environ.get("LLM_PROVIDER_NAME", host), model=self.model or "unset")
        self.last_error = ""

    @property
    def available(self) -> bool:
        return bool(self._key and self.base_url and self.model)

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
                                     method="POST", headers={"content-type": "application/json",
                                                             "authorization": "Bearer " + self._key})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def complete(self, case_id: str, system: str, user: str, max_tokens: int = 600) -> str:
        if not self.available:
            raise ModelUnavailable("LLM_API_KEY, LLM_BASE_URL and LLM_MODEL must all be set")
        payload = {"model": self.model, "messages": [{"role": "system", "content": system},
                                                     {"role": "user", "content": user}]}
        data = None
        for token_param in ("max_tokens", "max_completion_tokens"):      # gateways differ on the parameter name
            try:
                data = self._post(dict(payload, **{token_param: max_tokens}))
                break
            except urllib.error.HTTPError as e:
                self.last_error = f"HTTP {e.code}"
                if e.code != 400:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                self.last_error = type(e).__name__
                break
        if data is None:
            self.usage.failed_calls += 1
            raise ModelUnavailable(f"model call failed ({self.last_error})")
        u = data.get("usage") or {}
        self.usage.add(case_id, int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0)))
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            self.usage.failed_calls += 1
            raise ModelUnavailable("model reply had no content") from None


def make_client(provider: Optional[str] = None):
    """LLM_PROVIDER=openai (default; OpenAI-compatible gateway) or anthropic."""
    provider = (provider or os.environ.get("LLM_PROVIDER", "openai")).lower()
    return AnthropicClient() if provider == "anthropic" else OpenAICompatibleClient()
