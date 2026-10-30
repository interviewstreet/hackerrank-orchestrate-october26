"""Local `claude -p` backend: uses the logged-in Claude subscription; cost comes from `total_cost_usd`."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import BackendResponse, BackendUnavailable


class ClaudeCLIBackend:
    provider = "anthropic (claude_cli)"

    def __init__(self, binary: str | None = None, timeout: int = 600):
        self.binary = binary or shutil.which("claude")
        if not self.binary:
            raise BackendUnavailable("claude CLI not found on PATH")
        self.timeout = timeout

    def build_command(self, model: str, images: list[Path]) -> list[str]:
        cmd = [self.binary, "-p", "--output-format", "json", "--model", model]
        if images:
            cmd += ["--allowedTools", "Read"]
            for d in sorted({str(Path(i).resolve().parent) for i in images}):
                cmd += ["--add-dir", d]
        else:
            cmd += ["--allowedTools", ""]
        return cmd

    def call(self, prompt: str, images: list[Path], model: str, max_tokens: int, json_mode: bool = False) -> BackendResponse:
        if images:
            listing = "\n".join(f"- {Path(i).resolve()}" for i in images)
            prompt = f"{prompt}\n\nUse the Read tool to open these files:\n{listing}\n"
        # run outside the repository so project instructions (CLAUDE.md/AGENTS.md) are not loaded
        with tempfile.TemporaryDirectory(prefix="gda_cli_") as cwd:
            proc = subprocess.run(self.build_command(model, images), input=prompt, capture_output=True,
                                  text=True, timeout=self.timeout, cwd=cwd)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({proc.returncode}): {proc.stderr[:300]}")
        return parse_output(proc.stdout, model, self.provider)


def parse_output(stdout: str, model: str, provider: str) -> BackendResponse:
    data = json.loads(stdout)
    usage = data.get("usage") or {}
    tokens_in = int(usage.get("input_tokens", 0)) + int(usage.get("cache_creation_input_tokens", 0)) \
        + int(usage.get("cache_read_input_tokens", 0))
    tokens_out = int(usage.get("output_tokens", 0))
    models = list((data.get("modelUsage") or {}).keys())
    return BackendResponse(
        text=str(data.get("result") or ""),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=models[0] if len(models) == 1 else model,
        provider=provider,
        cost_usd=float(data.get("total_cost_usd") or 0.0),
    )
