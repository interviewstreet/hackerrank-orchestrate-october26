"""Ollama backend: local models through the HTTP API (standard library only, no key).

OLLAMA_HOST selects the server (default http://127.0.0.1:11434). Default models when GDA_MODEL_FAST /
GDA_MODEL_VISION are unset: qwen3:8b (intent) and qwen2.5vl:7b (vision). Vision models take raster images only:
a PDF is rendered to page images with poppler's `pdftoppm` (first MAX_PDF_PAGES pages); without it the call
raises and the adapter falls back to whatever the cache holds. JSON tasks use Ollama's JSON mode, and thinking is
off (deterministic, short answers). Local calls cost $0; models tagged `:cloud` run on ollama.com and are
labelled as such in the ledger.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from . import BackendResponse, BackendUnavailable

DEFAULT_HOST = "http://127.0.0.1:11434"
SEED = 7
MAX_PDF_PAGES = 4
PDF_DPI = 150


def host_url() -> str:
    host = (os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).strip().rstrip("/")
    return host if host.startswith(("http://", "https://")) else f"http://{host}"


class OllamaBackend:
    def __init__(self, host: str | None = None, timeout: int = 600):
        self.host = (host or host_url()).rstrip("/")
        self.timeout = timeout
        try:
            with urllib.request.urlopen(f"{self.host}/api/version", timeout=3) as r:
                self.version = json.load(r).get("version", "")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise BackendUnavailable(f"no Ollama server at {self.host} ({exc})") from exc

    def call(self, prompt: str, images: list[Path], model: str, max_tokens: int, json_mode: bool = False) -> BackendResponse:
        message = {"role": "user", "content": prompt}
        if images:
            message["images"] = [base64.b64encode(b).decode("ascii") for i in images for b in _raster_pages(Path(i))]
        body = {"model": model, "stream": False, "messages": [message], "think": False,
                "options": {"temperature": 0, "seed": SEED, "num_predict": max_tokens}}
        if json_mode:
            body["format"] = "json"
        req = urllib.request.Request(f"{self.host}/api/chat", json.dumps(body).encode("utf-8"),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.load(r)
        provider = "ollama (cloud)" if model.endswith(":cloud") else "ollama (local)"
        return BackendResponse(text=data["message"]["content"], tokens_in=int(data.get("prompt_eval_count") or 0),
                               tokens_out=int(data.get("eval_count") or 0), model=model, provider=provider,
                               cost_usd=0.0)


def _raster_pages(path: Path) -> list[bytes]:
    """Image bytes to send: the file itself, or a PDF's first pages rendered to PNG."""
    if path.suffix.lower() != ".pdf":
        return [path.read_bytes()]
    if not shutil.which("pdftoppm"):
        raise ValueError("Ollama vision models take raster images; install poppler-utils (pdftoppm) to read PDFs")
    with tempfile.TemporaryDirectory(prefix="gda_pdf_") as tmp:
        subprocess.run(["pdftoppm", "-r", str(PDF_DPI), "-l", str(MAX_PDF_PAGES), "-png", str(path), str(Path(tmp) / "page")],
                       capture_output=True, timeout=120, check=True)
        return [p.read_bytes() for p in sorted(Path(tmp).glob("page*.png"))]
