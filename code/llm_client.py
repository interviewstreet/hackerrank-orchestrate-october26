"""One client for every model call: vision, intent and the investigator agent (plan 7.3).

* Transport: ZenMux OpenAI-compatible ``/chat/completions`` (stdlib ``urllib``), timeout per
  call, at most ``config.MAX_RETRIES`` transport retries with backoff, temperature 0,
  JSON-schema output.
* ``structured()``: cache -> live call -> ``schema`` validation -> one retry that includes
  the validation error -> on a second failure ``None`` (the caller keeps the deterministic
  result) and a flag. Never raises for model or network trouble.
* Modes: ``live`` (key present) or ``replay`` (no key or ``ZENMUX_OFFLINE=1``): replay
  reads ``llm_snapshot.py``; a snapshot miss returns ``None`` with a flag.
* One ``schema.LLMUsage`` record per logical call. The API key never leaves the header.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ValidationError

import config
from llm_cache import LLMCache, cache_key
from schema import LLMUsage

LIVE, REPLAY = "live", "replay"
RETRY_HTTP = {408, 409, 425, 429, 500, 502, 503, 504}


class TransportError(RuntimeError):
    pass


class Transport(Protocol):
    def complete(self, body: dict) -> tuple[dict, int]: ...


class ZenMuxTransport:
    def __init__(self, base_url: str = config.BASE_URL, timeout: float = config.TIMEOUT_S,
                 max_retries: int = config.MAX_RETRIES, sleep=time.sleep):
        if not base_url.startswith("https://"):
            raise ValueError("ZENMUX_BASE_URL must use https")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.timeout, self.max_retries, self.sleep = timeout, max_retries, sleep

    def complete(self, body: dict) -> tuple[dict, int]:
        """Return (response JSON, transport retries used)."""
        data = json.dumps(body).encode("utf-8")
        last = ""
        for attempt in range(self.max_retries + 1):
            if attempt:
                self.sleep(2 ** attempt)
            request = urllib.request.Request(self.url, data=data, headers={  # noqa: S310 - https checked in __init__
                "Authorization": "Bearer " + config.api_key(), "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                    return json.load(response), attempt
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}"
                if exc.code not in RETRY_HTTP:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = type(exc).__name__
        raise TransportError(last)


class FakeTransport:
    """Scripted transport for tests: each reply is a content string, a dict, or an exception."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.bodies: list[dict] = []

    def complete(self, body: dict) -> tuple[dict, int]:
        self.bodies.append(body)
        if not self.replies:
            raise TransportError("no scripted reply")
        reply = self.replies.pop(0)
        if callable(reply):
            reply = reply(body)
        if isinstance(reply, Exception):
            raise reply
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return {"choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20}}, 0


@dataclass
class CallResult:
    value: BaseModel | None
    flag: str = ""               # "", schema_fallback, transport_fallback, snapshot_miss, budget
    usage: LLMUsage | None = None
    error: str = ""


def render_prompt(name: str, **values: str) -> tuple[str, str]:
    """(system, user) text of ``prompts/<name>.md``; ``{{KEY}}`` placeholders are filled."""
    text = (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    values.setdefault("SYSTEM_RULES", __import__("safety").SYSTEM_RULES)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if left:
        raise ValueError(f"prompt {name}: unfilled {left}")
    _, _, rest = text.partition("## System")
    system, _, user = rest.partition("## User")
    return system.strip(), user.strip()


def _content(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""
    content = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.S)
    if fenced:
        return fenced.group(1)
    if content.startswith("{"):
        return content
    # Prose around the object: keep the longest JSON object in the reply. The schema still
    # validates it; free text is discarded (D20).
    decoder, best = json.JSONDecoder(), ""
    for match in re.finditer(r"\{", content):
        try:
            obj, end = decoder.raw_decode(content, match.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and end - match.start() > len(best):
            best = content[match.start():end]
    return best or content


def _tokens(response: dict) -> tuple[int, int]:
    usage = response.get("usage") or {}
    return int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


@dataclass
class LLMClient:
    transport: Transport | None = None
    cache: LLMCache = field(default_factory=LLMCache)
    mode: str = LIVE
    model: str = config.MODEL_ID
    usage: list[LLMUsage] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)   # per-call trace rows (no message content)

    @classmethod
    def from_config(cls, offline: bool | None = None) -> LLMClient:
        replay = config.offline() if offline is None else offline
        if replay or not config.has_api_key():
            return cls(transport=None, mode=REPLAY)
        return cls(transport=ZenMuxTransport(), mode=LIVE)

    def _record(self, purpose, ref_id, tin, tout, latency, retries, hit, flag) -> LLMUsage:
        use = LLMUsage(purpose=purpose, ref_id=ref_id, model=self.model, input_tokens=tin, output_tokens=tout,
                       latency_ms=latency, retries=retries, cache_hit=hit)
        self.usage.append(use)
        self.calls.append({**use.model_dump(), "flag": flag})
        return use

    def structured(self, purpose: str, ref_id: str, messages: list[dict], model_cls: type[BaseModel],
                   context: dict, prompt_version: str, schema_mode: str = "json_schema") -> CallResult:
        """``schema_mode``: ``json_schema`` (constrained output) or ``json_object`` (the schema is in
        the prompt; used where constrained decoding drops optional fields)."""
        key = cache_key({"messages": messages, "schema": model_cls.__name__}, prompt_version, self.model)
        stored = self.cache.replay(key) if self.mode == REPLAY else self.cache.get(key)
        if stored is not None:
            try:
                value = model_cls.model_validate(stored["result"], context=context)
            except ValidationError as exc:
                stored, error = None, f"stored result invalid: {exc.error_count()} errors"
            else:
                self.cache.mark_used(key, stored)
                return CallResult(value, usage=self._record(purpose, ref_id, 0, 0, 0, 0, True, ""))
        if self.mode == REPLAY or self.transport is None:
            return CallResult(None, "snapshot_miss", self._record(purpose, ref_id, 0, 0, 0, 0, False, "snapshot_miss"))

        response_format = ({"type": "json_object"} if schema_mode == "json_object" else
                           {"type": "json_schema", "json_schema": {"name": model_cls.__name__, "strict": False,
                                                                   "schema": model_cls.model_json_schema()}})
        body = {"model": self.model, "temperature": 0, "messages": list(messages), "response_format": response_format}
        tin = tout = retries = 0
        started = time.monotonic()
        error = ""
        for attempt in range(config.SCHEMA_RETRIES + 1):
            try:
                response, used = self.transport.complete(body)
            except TransportError as exc:
                latency = int((time.monotonic() - started) * 1000)
                return CallResult(None, "transport_fallback",
                                  self._record(purpose, ref_id, tin, tout, latency, retries + config.MAX_RETRIES,
                                               False, "transport_fallback"), str(exc))
            retries += used + (1 if attempt else 0)
            a, b = _tokens(response)
            tin, tout = tin + a, tout + b
            content = _content(response)
            try:
                value = model_cls.model_validate_json(content, context=context)
            except ValidationError as exc:
                error = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:8])
                body = dict(body, messages=[
                    *messages,
                    {"role": "assistant", "content": content[:4000]},
                    {"role": "user", "content": "Your JSON failed validation: " + error[:1500]
                     + ". Return the corrected JSON object only."}])
                continue
            latency = int((time.monotonic() - started) * 1000)
            record = {"purpose": purpose, "ref_id": ref_id, "model": self.model, "prompt_version": prompt_version,
                      "result": value.model_dump(mode="json")}
            self.cache.put(key, record)
            self.cache.mark_used(key, record)
            return CallResult(value, usage=self._record(purpose, ref_id, tin, tout, latency, retries, False, ""))
        latency = int((time.monotonic() - started) * 1000)
        return CallResult(None, "schema_fallback",
                          self._record(purpose, ref_id, tin, tout, latency, retries, False, "schema_fallback"), error)

    def totals(self) -> dict:
        out: dict[str, dict] = {}
        for u in self.usage:
            t = out.setdefault(u.purpose, {"calls": 0, "live_calls": 0, "cache_hits": 0, "input_tokens": 0,
                                           "output_tokens": 0, "retries": 0})
            t["calls"] += 1
            t["live_calls"] += 0 if u.cache_hit else int(u.input_tokens > 0)
            t["cache_hits"] += int(u.cache_hit)
            t["input_tokens"] += u.input_tokens
            t["output_tokens"] += u.output_tokens
            t["retries"] += u.retries
        return out
