"""Minimal Resend client (standard library only). The HTTP layer is injectable so tests never touch the network."""
from __future__ import annotations

import html
import json
import urllib.error
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

from .errors import EmailNotConfigured, ResendError

API_URL = "https://api.resend.com/emails"
# transport(method, url, headers, body, timeout) -> (http_status, response_body_bytes)
Transport = Callable[[str, str, Dict[str, str], bytes, float], Tuple[int, bytes]]


def urllib_transport(method: str, url: str, headers: Dict[str, str], body: bytes, timeout: float) -> Tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:      # noqa: S310 (fixed https URL)
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def text_to_html(text: str) -> str:
    """Escape the plain-text body and keep its paragraphs, so the HTML part can never contain injected markup."""
    paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    return "".join("<p>" + html.escape(p).replace("\n", "<br>") + "</p>" for p in paras)


class ResendClient:
    def __init__(self, api_key: str, from_email: str, transport: Optional[Transport] = None,
                 url: str = API_URL, timeout: float = 15.0):
        self._api_key = api_key
        self.from_email = from_email
        self._transport = transport or urllib_transport
        self._url = url
        self._timeout = timeout

    @property
    def can_send(self) -> bool:
        return bool(self._api_key and self.from_email)

    def send(self, *, to: str, subject: str, text: str, idempotency_key: str) -> str:
        """Send one email and return Resend's email id. Raises ResendError on any failure."""
        if not self.can_send:
            raise EmailNotConfigured("RESEND_API_KEY and RESEND_FROM_EMAIL must be set to send")
        payload = {"from": self.from_email, "to": [to], "subject": subject, "text": text, "html": text_to_html(text)}
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                   "Idempotency-Key": idempotency_key, "User-Agent": "erasight-email/1.0"}
        try:
            status, raw = self._transport("POST", self._url, headers, json.dumps(payload).encode("utf-8"), self._timeout)
        except Exception as e:                    # timeout / DNS / TLS: the outcome is unknown, a retry reuses the same key
            raise ResendError(f"network error: {type(e).__name__}", status=0, name="network_error", retryable=True) from None
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            data = {}
        if 200 <= status < 300 and isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        name = str(data.get("name", "")) if isinstance(data, dict) else ""
        msg = str(data.get("message", "")) if isinstance(data, dict) else ""
        retryable = status in (429, 500, 502, 503, 504) or name == "concurrent_idempotent_requests"
        raise ResendError(f"Resend returned HTTP {status}" + (f" {name}: {msg}" if name or msg else ""),
                          status=status, name=name, retryable=retryable)
