"""Run configuration: ZenMux endpoint, model, prompt versions, prices, paths (plan 7.3, D18).

No secrets live here. The API key is read from the process environment, or else from the
repo-root ``.env`` file (stdlib parser below). A real environment variable always overrides
``.env``. The key value is never printed, logged, traced or cached: only ``has_api_key()``
leaves this module, plus ``api_key()`` for the HTTP header in ``llm_client``.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
ENV_FILE = REPO_ROOT / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    """``KEY=value`` lines; ``#`` comments, blank lines, ``export`` and matching quotes allowed."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


_ENV_FILE_VALUES = _read_env_file(ENV_FILE)


def setting(name: str, default: str = "") -> str:
    """Environment variable, else ``.env`` value, else ``default``."""
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()
    return _ENV_FILE_VALUES.get(name, "").strip() or default


# ------------------------------------------------------------------ ZenMux / model
BASE_URL = setting("ZENMUX_BASE_URL", "https://zenmux.ai/api/v1").rstrip("/")
# The project key may call only the -contributor variant of Muse Spark 1.3 (user decision, 2026-10-24).
MODEL_ID = setting("ZENMUX_MODEL", "meta/muse-spark-1.3-contributor")
# USD per 1M tokens (input, output, cached input), from the ZenMux model list "pricings" (2026-10-24).
PRICES = {
    "meta/muse-spark-1.3-contributor": (0.10, 0.20, 0.002),
    "meta/muse-spark-1.3": (1.25, 4.25, 0.15),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimated cost; None for a model without a price entry."""
    if model not in PRICES:
        return None
    price_in, price_out, _ = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000

TIMEOUT_S = 90.0
MAX_RETRIES = 2            # transport retries per call (backoff 2 s, 4 s)
SCHEMA_RETRIES = 1         # one retry that includes the validation error
AGENT_MAX_ITERATIONS = 4
AGENT_TOKEN_BUDGET = 40_000   # per case, input + output
INTENT_BATCH_SIZE = 20

PROMPT_VERSIONS = {"vision": "vision_extract_v1", "intent": "intent_v1", "agent": "agent_v1"}
PROMPTS_DIR = CODE_DIR / "prompts"
CACHE_DIR = REPO_ROOT / ".cache" / "llm"
SNAPSHOT_FILE = CODE_DIR / "llm_snapshot.py"


def api_key() -> str:
    return setting("ZENMUX_API_KEY")


def has_api_key() -> bool:
    return bool(api_key())


def offline() -> bool:
    """``ZENMUX_OFFLINE=1`` forces snapshot replay even when a key is present."""
    return setting("ZENMUX_OFFLINE", "0").lower() in ("1", "true", "yes")
