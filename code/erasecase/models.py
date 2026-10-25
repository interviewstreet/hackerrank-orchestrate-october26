"""OpenRouter boundary, configuration loading, and bounded access probes."""

from __future__ import annotations

import base64
import io
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
SEMANTIC_CANDIDATES = (
    "openai/gpt-6.1-sol",
    "anthropic/claude-sonnet-5.5",
)
VISION_CANDIDATE = "google/gemini-3.8-flash"


class ProviderError(RuntimeError):
    """A safe provider failure that never includes credential material."""


def load_local_environment() -> Path:
    """Load exactly the root .env without replacing an existing OS value."""

    path = ROOT / ".env"
    load_dotenv(dotenv_path=path, override=False)
    return path


def has_openrouter_key() -> bool:
    load_local_environment()
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


@dataclass(frozen=True)
class ProbeResult:
    model: str
    returned_model: str
    provider: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    latency_ms: int
    value: str


def estimate_probe_cost(
    model: dict[str, Any], *, input_tokens: int, output_tokens: int, images: int = 0
) -> float:
    """Reserve catalog-priced cost before dispatch; fail closed on unknown pricing."""

    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        raise ProviderError("model catalog omitted pricing")

    def price(name: str, *, required: bool = True) -> float:
        raw = pricing.get(name)
        if raw is None and not required:
            return 0.0
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"model catalog has invalid {name} pricing") from exc
        if value < 0:
            raise ProviderError(f"model catalog has negative {name} pricing")
        return value

    return (
        price("request", required=False)
        + price("prompt") * input_tokens
        + price("completion") * output_tokens
        + price("image", required=images > 0) * images
    )


class OpenRouterClient:
    def __init__(self, *, connect_timeout: float = 10, read_timeout: float = 60) -> None:
        load_local_environment()
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise ProviderError("OPENROUTER_API_KEY is not configured")
        self._headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kernelKain/hackerrank-orchestrate-october26",
            "X-Title": "EraseCase",
        }
        self._timeout = (connect_timeout, read_timeout)
        self._session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._session.request(
                method,
                f"{OPENROUTER_BASE_URL}{path}",
                headers=self._headers,
                timeout=self._timeout,
                **kwargs,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            status = getattr(exc.response, "status_code", None)
            suffix = f" (HTTP {status})" if status else ""
            raise ProviderError(f"OpenRouter request failed{suffix}") from exc
        except ValueError as exc:
            raise ProviderError("OpenRouter returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderError("OpenRouter returned an unexpected response shape")
        return payload

    def current_key_metadata(self) -> dict[str, Any]:
        return self._request("GET", "/key")

    def models(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/models")
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderError("OpenRouter model catalog has no data list")
        return [item for item in data if isinstance(item, dict)]

    def structured_probe(
        self,
        *,
        model: str,
        prompt: str,
        image_data_url: str | None = None,
    ) -> ProbeResult:
        content: str | list[dict[str, Any]] = prompt
        if image_data_url:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]
        body = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_completion_tokens": 256,
            "usage": {"include": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "erasecase_probe",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                },
            },
        }
        if model.startswith("openai/"):
            body["reasoning"] = {"effort": "minimal"}
        started = time.monotonic()
        payload = self._request("POST", "/chat/completions", json=body)
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        choices = payload.get("choices")
        choice = choices[0] if isinstance(choices, list) and choices else {}
        message = choice.get("message") if isinstance(choice, dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        try:
            import json

            parsed = json.loads(content)
            value = parsed["value"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            choice_error = choice.get("error") if isinstance(choice, dict) else None
            error_code = choice_error.get("code") if isinstance(choice_error, dict) else None
            cost = usage.get("cost")
            safe_details = (
                f"id={payload.get('id', 'missing')} "
                f"model={payload.get('model', model)} "
                f"finish_reason={choice.get('finish_reason') if isinstance(choice, dict) else None} "
                f"content_type={type(content).__name__} "
                f"error_code={error_code} cost_usd={cost}"
            )
            raise ProviderError(
                f"OpenRouter probe violated the strict response contract ({safe_details})"
            ) from exc
        if not isinstance(value, str) or not value:
            raise ProviderError("OpenRouter probe returned an empty value")
        return ProbeResult(
            model=model,
            returned_model=str(payload.get("model") or model),
            provider=payload.get("provider") if isinstance(payload.get("provider"), str) else None,
            input_tokens=usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None,
            output_tokens=usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None,
            cost_usd=float(usage["cost"]) if isinstance(usage.get("cost"), (int, float)) else None,
            latency_ms=latency_ms,
            value=value,
        )


def synthetic_probe_image() -> str:
    image = Image.new("RGB", (256, 96), "white")
    ImageDraw.Draw(image).text((18, 34), "ERASECASE 42", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
