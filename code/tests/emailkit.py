"""Shared helpers for the email tests. Nothing here can reach the network: Resend is always a fake transport."""
from __future__ import annotations

import json
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from integrations.email import EmailConfig, EmailService, EmailStore, ResendClient

SECRET = "whsec_" + "dGVzdC1zZWNyZXQtZm9yLWVyYXNpZ2h0LXRlc3Rz"          # fake, test-only
API_KEY = "re_test_FAKE_KEY_NOT_REAL"


class FakeResend:
    """Records every request; replies with a scripted (status, json) or raises."""

    def __init__(self, replies: Optional[List] = None, delay: float = 0.0):
        self.calls: List[Dict] = []
        self.replies = list(replies or [])
        self.delay = delay
        self._lock = threading.Lock()
        self._n = 0

    def __call__(self, method, url, headers, body, timeout) -> Tuple[int, bytes]:
        with self._lock:
            self._n += 1
            n = self._n
            self.calls.append({"method": method, "url": url, "headers": dict(headers), "json": json.loads(body)})
            reply = self.replies.pop(0) if self.replies else (200, {"id": f"resend_{n}"})
        if self.delay:
            time.sleep(self.delay)
        if isinstance(reply, Exception):
            raise reply
        status, data = reply
        return status, json.dumps(data).encode()


OPEN_STORES: list = []


def close_open_stores() -> None:
    while OPEN_STORES:
        OPEN_STORES.pop().close()


def make_service(fake: Optional[FakeResend] = None, *, configured: bool = True) -> Tuple[EmailService, FakeResend]:
    fake = fake or FakeResend()
    cfg = EmailConfig(api_key=API_KEY if configured else "", from_email="Privacy <privacy@example.test>" if configured else "",
                      webhook_secret=SECRET, db_path=":memory:")
    client = ResendClient(cfg.api_key, cfg.from_email, transport=fake)
    store = EmailStore(":memory:")
    OPEN_STORES.append(store)
    return EmailService(store, client, cfg), fake


def approved_email(svc: EmailService, case_id: str = "case_01", to: str = "person@example.test"):
    rec, _ = svc.create_draft(case_id, to, "Subject", "Body text")
    svc.submit_for_approval(rec.id, "analyst")
    return svc.approve(rec.id, "reviewer")


Clock = Callable[[], float]
