"""Anthropic Messages API backend (official `anthropic` SDK, key from ANTHROPIC_API_KEY)."""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from . import BackendResponse, BackendUnavailable


def content_blocks(prompt: str, images: list[Path]) -> list[dict]:
    blocks: list[dict] = []
    for img in images:
        data = base64.standard_b64encode(Path(img).read_bytes()).decode("ascii")
        if Path(img).suffix.lower() == ".pdf":
            blocks.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}})
        else:
            media = mimetypes.guess_type(str(img))[0] or "image/png"
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
    blocks.append({"type": "text", "text": prompt})
    return blocks


class AnthropicBackend:
    provider = "anthropic"

    def __init__(self, client=None):
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise BackendUnavailable("ANTHROPIC_API_KEY is not set")
            try:
                import anthropic
            except ImportError as exc:
                raise BackendUnavailable("pip install anthropic") from exc
            client = anthropic.Anthropic()
        self.client = client

    def call(self, prompt: str, images: list[Path], model: str, max_tokens: int, json_mode: bool = False) -> BackendResponse:
        msg = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content_blocks(prompt, images)}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
        return BackendResponse(text=text, tokens_in=msg.usage.input_tokens, tokens_out=msg.usage.output_tokens,
                               model=model, provider=self.provider)
