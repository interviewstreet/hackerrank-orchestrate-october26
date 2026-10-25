"""Model fallback for request texts the rules mark UNSURE. One yes/no question per distinct text."""
from __future__ import annotations

import logging

from ..errors import ModelUnavailable
from .client import ModelClient
from .intent_rules import DELETE, OTHER

log = logging.getLogger(__name__)

SYSTEM = (
    "You classify customer privacy requests. Answer with JSON {\"deletion\": true|false}. "
    "true only if the customer asks for their account or personal data to be deleted, erased, "
    "or removed, or asks to confirm or finish such a deletion. false for access, export, "
    "correction, login help, marketing opt-out, or any request that keeps the account."
)


def make_fallback(client: ModelClient):
    def fallback(text: str) -> str | None:
        try:
            data = client.complete_json("intent", SYSTEM, f"Request text:\n{text}", max_tokens=20)
        except ModelUnavailable as exc:
            log.info("intent fallback unavailable: %s", exc)
            return None
        value = data.get("deletion")
        return DELETE if value is True else OTHER if value is False else None
    return fallback
