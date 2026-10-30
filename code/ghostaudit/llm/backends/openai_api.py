"""OpenAI backend (official `openai` SDK, key from OPENAI_API_KEY). Prices must be supplied through
GDA_PRICE_OVERRIDE_<ALIAS> because no OpenAI price table is shipped."""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from . import BackendResponse, BackendUnavailable


def content_parts(prompt: str, images: list[Path]) -> list[dict]:
    parts: list[dict] = [{"type": "text", "text": prompt}]
    for img in images:
        data = base64.standard_b64encode(Path(img).read_bytes()).decode("ascii")
        if Path(img).suffix.lower() == ".pdf":
            parts.append({"type": "file", "file": {"filename": Path(img).name, "file_data": f"data:application/pdf;base64,{data}"}})
        else:
            media = mimetypes.guess_type(str(img))[0] or "image/png"
            parts.append({"type": "image_url", "image_url": {"url": f"data:{media};base64,{data}"}})
    return parts


class OpenAIBackend:
    provider = "openai"

    def __init__(self, client=None):
        if client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise BackendUnavailable("OPENAI_API_KEY is not set")
            try:
                import openai
            except ImportError as exc:
                raise BackendUnavailable("pip install openai") from exc
            client = openai.OpenAI()
        self.client = client

    def call(self, prompt: str, images: list[Path], model: str, max_tokens: int, json_mode: bool = False) -> BackendResponse:
        resp = self.client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": content_parts(prompt, images)}],
        )
        return BackendResponse(text=resp.choices[0].message.content or "", tokens_in=resp.usage.prompt_tokens,
                               tokens_out=resp.usage.completion_tokens, model=model, provider=self.provider)
