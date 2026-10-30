"""Spending limit enforced before every non-cached LLM call (SPEC §6.1)."""
from __future__ import annotations

import os
import threading

from ..config import EXIT_BUDGET_EXCEEDED
from .ledger import Ledger, total_spend
from .pricing import IMAGE_TOKENS_EST, price_for


class BudgetExceeded(RuntimeError):
    exit_code = EXIT_BUDGET_EXCEEDED


class Budget:
    def __init__(self, ledger: Ledger, limit_usd: float | None = None, scope: str | None = None,
                 on_exceed: str | None = None):
        self.ledger = ledger
        self.limit = float(os.environ.get("GDA_BUDGET_USD", "3.00")) if limit_usd is None else limit_usd
        self.scope = (scope or os.environ.get("GDA_BUDGET_SCOPE", "total")).lower()
        self.on_exceed = (on_exceed or os.environ.get("GDA_BUDGET_ON_EXCEED", "fallback")).lower()
        self._lock = threading.Lock()
        self._reserved = 0.0
        self._previous = total_spend(ledger.dir) if self.scope == "total" else 0.0

    def spent(self) -> float:
        return self._previous + self.ledger.run_spend()

    def estimate(self, model: str, alias: str, prompt: str, n_images: int, max_output_tokens: int) -> float:
        try:
            pin, pout = price_for(model, alias)
        except KeyError:
            return 0.0  # CLI backends report their own cost; unknown price -> rely on the reported cost
        tokens_in = len(prompt) / 3.5 + n_images * IMAGE_TOKENS_EST
        return tokens_in / 1e6 * pin + max_output_tokens / 1e6 * pout

    def reserve(self, estimate: float) -> bool:
        """Check-and-reserve atomically. Returns False (fallback) or raises (abort) when over budget."""
        with self._lock:
            committed = self.spent() + self._reserved
            if committed >= self.limit or committed + estimate > self.limit:
                if self.on_exceed == "abort":
                    raise BudgetExceeded(f"LLM budget ${self.limit:.2f} would be exceeded")
                return False
            self._reserved += estimate
            return True

    def release(self, estimate: float) -> None:
        with self._lock:
            self._reserved = max(0.0, self._reserved - estimate)
