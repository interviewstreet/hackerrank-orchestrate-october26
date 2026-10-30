"""LLM backends. Each exposes `call(prompt, images, model, max_tokens, json_mode=False) -> BackendResponse`."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackendResponse:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    provider: str
    cost_usd: float | None = None  # None -> computed from pricing.py


class BackendUnavailable(RuntimeError):
    """The backend cannot run here (no key, no CLI). Callers fall back to replay/offline."""


def get_backend(name: str):
    if name == "claude_cli":
        from .claude_cli import ClaudeCLIBackend
        return ClaudeCLIBackend()
    if name == "anthropic":
        from .anthropic_api import AnthropicBackend
        return AnthropicBackend()
    if name == "ollama":
        from .ollama import OllamaBackend
        return OllamaBackend()
    if name == "openai":
        from .openai_api import OpenAIBackend
        return OpenAIBackend()
    return None  # replay / offline: cache only
