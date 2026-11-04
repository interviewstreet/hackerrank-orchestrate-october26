"""Settings read from environment variables only (never hardcoded, never logged)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class EmailConfig:
    api_key: str = field(default="", repr=False)            # RESEND_API_KEY
    from_email: str = ""                                    # RESEND_FROM_EMAIL (a sender verified in Resend)
    webhook_secret: str = field(default="", repr=False)     # RESEND_WEBHOOK_SECRET (starts with whsec_)
    db_path: str = "email_outbox.db"                        # EMAIL_DB_PATH (SQLite outbox; ":memory:" for tests)

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "EmailConfig":
        e = os.environ if env is None else env
        return cls(api_key=e.get("RESEND_API_KEY", "").strip(),
                   from_email=e.get("RESEND_FROM_EMAIL", "").strip(),
                   webhook_secret=e.get("RESEND_WEBHOOK_SECRET", "").strip(),
                   db_path=e.get("EMAIL_DB_PATH", "").strip() or "email_outbox.db")

    @property
    def can_send(self) -> bool:
        return bool(self.api_key and self.from_email)

    @property
    def can_verify_webhooks(self) -> bool:
        return bool(self.webhook_secret)
