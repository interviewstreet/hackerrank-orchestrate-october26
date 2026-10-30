"""USD per million tokens (input, output). Source: Anthropic first-party pricing table (claude-api skill,
cached 2026-10-06). Unknown models need GDA_PRICE_OVERRIDE_<ALIAS>="in,out"."""
from __future__ import annotations

import os

PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
# Rough per-image / per-page input-token allowance used only for the pre-call budget estimate.
IMAGE_TOKENS_EST = 1600


class UnknownModelPrice(KeyError):
    pass


def price_for(model: str, alias: str = "") -> tuple[float, float]:
    for key in (alias, model):
        override = os.environ.get(f"GDA_PRICE_OVERRIDE_{key.upper().replace('-', '_')}") if key else None
        if override:
            a, b = override.split(",")
            return float(a), float(b)
    if model in PRICES:
        return PRICES[model]
    raise UnknownModelPrice(f"no price for model {model!r}; set GDA_PRICE_OVERRIDE_{(alias or model).upper()}")


def cost(model: str, tokens_in: int, tokens_out: int, alias: str = "") -> float:
    pin, pout = price_for(model, alias)
    return tokens_in / 1e6 * pin + tokens_out / 1e6 * pout
