"""Resend webhooks are signed with Svix. Verify the signature on the RAW body before trusting anything in it."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Mapping, Optional

from .errors import WebhookConfigError, WebhookVerificationError

TOLERANCE_SECONDS = 300


def _header(headers: Mapping[str, str], name: str) -> str:
    for k, v in headers.items():
        if k.lower() == name:
            return v or ""
    return ""


def sign(secret: str, svix_id: str, timestamp: str, body: bytes) -> str:
    """The v1 signature Svix would send (used by the verifier and by tests)."""
    key = _decode_secret(secret)
    mac = hmac.new(key, f"{svix_id}.{timestamp}.".encode("utf-8") + body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")


def _decode_secret(secret: str) -> bytes:
    if not secret:
        raise WebhookConfigError("RESEND_WEBHOOK_SECRET is not set; webhooks are refused")
    raw = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise WebhookConfigError("RESEND_WEBHOOK_SECRET is not a valid whsec_ secret") from None


def verify_webhook(secret: str, headers: Mapping[str, str], body: bytes, now: Optional[float] = None,
                   tolerance: int = TOLERANCE_SECONDS) -> str:
    """Return the svix-id if the message is authentic and fresh; raise WebhookVerificationError otherwise."""
    _decode_secret(secret)                                   # a bad or missing secret is a config problem, not a bad request
    svix_id, ts, sigs = (_header(headers, "svix-id"), _header(headers, "svix-timestamp"), _header(headers, "svix-signature"))
    if not (svix_id and ts and sigs):
        raise WebhookVerificationError("missing svix headers")
    try:
        sent = int(ts)
    except ValueError:
        raise WebhookVerificationError("bad timestamp") from None
    if abs((time.time() if now is None else now) - sent) > tolerance:
        raise WebhookVerificationError("timestamp outside tolerance")
    expected = sign(secret, svix_id, ts, body)
    for part in sigs.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig.encode("utf-8"), expected.encode("utf-8")):
            return svix_id
    raise WebhookVerificationError("signature mismatch")


def parse_event(body: bytes) -> Dict[str, Any]:
    try:
        ev = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise WebhookVerificationError("body is not JSON") from None
    if not isinstance(ev, dict) or not isinstance(ev.get("type"), str):
        raise WebhookVerificationError("body is not a Resend event")
    return ev
