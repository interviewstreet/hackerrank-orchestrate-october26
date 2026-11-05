"""Settings read from environment variables only (never hardcoded, never logged)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple


def parse_allowed(raw: str) -> Tuple[str, ...]:
    items = [x.strip().lower() for x in (raw or "").replace(";", ",").split(",")]
    return tuple(dict.fromkeys(x for x in items if x))


@dataclass(frozen=True)
class EmailConfig:
    api_key: str = field(default="", repr=False)            # RESEND_API_KEY
    from_email: str = ""                                    # RESEND_FROM_EMAIL (a sender verified in Resend)
    webhook_secret: str = field(default="", repr=False)     # RESEND_WEBHOOK_SECRET (starts with whsec_)
    db_path: str = "email_outbox.db"                        # EMAIL_DB_PATH (SQLite outbox; ":memory:" for tests)
    # EMAIL_ALLOWED_RECIPIENTS: comma-separated addresses ("a@x.com") or whole domains ("@x.com"). Empty = no restriction
    # in the core; the HTTP adapter refuses to start sending unless this is set.
    allowed_recipients: Tuple[str, ...] = ()
    # EMAIL_ALLOW_SELF_APPROVAL=1 lets the person who drafted/submitted an email also approve it (one-person demos only).
    allow_self_approval: bool = False

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "EmailConfig":
        e = os.environ if env is None else env
        return cls(api_key=e.get("RESEND_API_KEY", "").strip(),
                   from_email=e.get("RESEND_FROM_EMAIL", "").strip(),
                   webhook_secret=e.get("RESEND_WEBHOOK_SECRET", "").strip(),
                   db_path=e.get("EMAIL_DB_PATH", "").strip() or "email_outbox.db",
                   allowed_recipients=parse_allowed(e.get("EMAIL_ALLOWED_RECIPIENTS", "")),
                   allow_self_approval=e.get("EMAIL_ALLOW_SELF_APPROVAL", "").strip().lower() in ("1", "true", "yes"))

    def recipient_allowed(self, address: str) -> bool:
        """True when no allowlist is set, or the address (or its domain) is on it."""
        if not self.allowed_recipients:
            return True
        a = (address or "").strip().lower()
        domain = a.rsplit("@", 1)[-1] if "@" in a else ""
        return any(a == item or (item.startswith("@") and domain == item[1:]) for item in self.allowed_recipients)

    @property
    def can_send(self) -> bool:
        return bool(self.api_key and self.from_email)

    @property
    def can_verify_webhooks(self) -> bool:
        return bool(self.webhook_secret)
