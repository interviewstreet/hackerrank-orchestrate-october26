"""Step 1: decide whether the request authorises deletion. Rules first, model only when unsure."""
from __future__ import annotations

import logging
from typing import Callable

from ..llm.intent_rules import DELETE, OTHER, UNSURE, classify

log = logging.getLogger(__name__)

Fallback = Callable[[str], "str | None"]  # returns DELETE / OTHER, or None when unavailable


class IntentClassifier:
    """Classifies each distinct text once; identical texts can never get different answers."""

    def __init__(self, fallback: Fallback | None = None) -> None:
        self._fallback = fallback
        self._cache: dict[str, tuple[str, str]] = {}

    def __call__(self, text: str) -> tuple[str, str]:
        key = " ".join(text.split())
        if key not in self._cache:
            self._cache[key] = self._decide(key)
        return self._cache[key]

    def _decide(self, text: str) -> tuple[str, str]:
        label, reason = classify(text)
        if label != UNSURE:
            return label, f"rules: {reason}"
        if self._fallback is not None:
            answer = self._fallback(text)
            if answer in (DELETE, OTHER):
                return answer, "model fallback"
        # Safer default for an audit: treat as deletion and flag for review.
        log.warning("intent unsure and no model answer; defaulting to DELETE: %.80s", text)
        return DELETE, "default DELETE (unsure, no model answer)"
