"""Authenticated HTTP adapter for the email workflow, for the standard-library server in code/server.py.

No web framework and no second server: `handle()` takes the parts of one request and returns (status, dict).
Member 1's server keeps its own Host/Origin/CSRF checks and calls this for every path under /api/email (see
INTEGRATION_PLAN.md for the ten lines to add). What this adapter adds on top of those checks:

* Identity comes from the server. Every route needs `Authorization: Bearer <token>`; the token is mapped to an operator
  name (operators.py) and that name is the actor/approver in the audit trail. An `actor`/`approver` in the body is ignored.
* Fail closed: no operators configured, or no EMAIL_ALLOWED_RECIPIENTS, means every route answers 503.
* The approver cannot be the person who drafted or submitted the email (unless EMAIL_ALLOW_SELF_APPROVAL=1).
* Recipients must be on the allowlist, at draft time and again at send time.
* Failed logins are rate limited; sending is one at a time with a minimum gap.
Nothing here sends mail by itself: approval and the content-hash check in EmailService still gate every send.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from .email_service import EmailService
from .errors import (ContentChanged, EmailNotConfigured, EmailNotFound, InvalidTransition, RecipientNotAllowed,
                     SeparationOfDuties)
from .operators import MAX_TOKEN_LEN, Operators

PREFIX = "/api/email"
MAX_BODY = 64 * 1024
EMAIL_ID = re.compile(r"^[0-9a-f]{32}$")
CASE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CaseProvider = Callable[[str], Optional[Dict[str, Any]]]
Response = Tuple[int, Dict[str, Any]]


class _Bad(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _text(body: Mapping[str, Any], key: str, *, required: bool = False, max_len: int = 20000,
          default: Optional[str] = None) -> Optional[str]:
    value = body.get(key, default)
    if value is None:
        if required:
            raise _Bad(422, f"'{key}' is required")
        return None
    if not isinstance(value, str) or len(value) > max_len or (required and not value.strip()):
        raise _Bad(422, f"'{key}' must be text of at most {max_len} characters")
    return value


class EmailHttpAdapter:
    def __init__(self, service: EmailService, operators: Operators, *, case_provider: Optional[CaseProvider] = None,
                 clock: Callable[[], float] = time.monotonic, max_failures: int = 10, window: float = 60.0,
                 min_send_gap: float = 2.0):
        self.service = service
        self.operators = operators
        self.case_provider = case_provider
        self._clock = clock
        self._max_failures, self._window, self._min_gap = max_failures, window, min_send_gap
        self._failures: List[float] = []
        self._last_send = -1e9
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()

    # ---- entry point -------------------------------------------------------------------------------------------
    def handle(self, method: str, target: str, headers: Mapping[str, str], body: bytes = b"") -> Response:
        parts = urlsplit(target)
        if not (parts.path == PREFIX or parts.path.startswith(PREFIX + "/")):
            return 404, {"error": "Endpoint not found."}
        route = parts.path[len(PREFIX):] or "/"
        h = {str(k).lower(): str(v) for k, v in headers.items()}
        if not self.operators.enabled:
            return 503, {"error": "Email actions are disabled: no operators are configured on the server."}
        if not self.service.config.allowed_recipients:
            return 503, {"error": "Email actions are disabled: no allowed recipients are configured on the server."}
        operator = self._authenticate(h.get("authorization", ""))
        if isinstance(operator, tuple):
            return operator
        try:
            return self._dispatch(method.upper(), route, parse_qs(parts.query), h, body, operator)
        except _Bad as e:
            return e.status, {"error": str(e)}
        except EmailNotFound as e:
            return 404, {"error": str(e)}
        except (InvalidTransition, ContentChanged) as e:
            return 409, {"error": str(e)}
        except (RecipientNotAllowed, SeparationOfDuties) as e:
            return 403, {"error": str(e)}
        except EmailNotConfigured as e:
            return 503, {"error": str(e)}
        except ValueError as e:
            return 422, {"error": str(e)}
        except Exception:                                               # never leak internals or secrets
            return 500, {"error": "Unexpected error. No email was sent unless it shows as SENT."}

    # ---- authentication ----------------------------------------------------------------------------------------
    def _authenticate(self, header: str):
        now = self._clock()
        with self._lock:
            self._failures = [t for t in self._failures if now - t < self._window]
            if len(self._failures) >= self._max_failures:
                return 429, {"error": "Too many failed logins. Wait a minute and try again."}
        scheme, _, token = header.partition(" ")
        name = self.operators.authenticate(token.strip()) if scheme.lower() == "bearer" and len(token) <= MAX_TOKEN_LEN else None
        if name is None:
            with self._lock:
                self._failures.append(now)
            return 401, {"error": "A valid operator login token is required."}
        return name

    # ---- routing -----------------------------------------------------------------------------------------------
    def _dispatch(self, method: str, route: str, query: Dict[str, List[str]], h: Mapping[str, str], raw: bytes,
                  operator: str) -> Response:
        svc = self.service
        if route == "/status":
            self._only(method, "GET")
            cfg = svc.config
            return 200, {"operator": operator, "can_send": svc.client.can_send,
                         "separate_approver_required": not cfg.allow_self_approval,
                         "allowed_recipients": list(cfg.allowed_recipients)}
        if route == "/emails":
            self._only(method, "GET")
            limit = self._int(query.get("limit", ["200"])[0])
            rows = svc.store.list(case_id=query.get("case_id", [None])[0] or None,
                                  state=query.get("state", [None])[0] or None, limit=limit)
            return 200, {"emails": [r.to_dict() for r in rows]}
        if route == "/drafts":
            self._only(method, "POST")
            return self._create_draft(self._json(h, raw), operator)
        m = re.fullmatch(r"/emails/([^/]+)(?:/(draft|redraft|submit|approve|reject|send))?", route)
        if not m or not EMAIL_ID.match(m.group(1)):
            return 404, {"error": "Endpoint not found."}
        email_id, action = m.group(1), m.group(2)
        if action is None:
            self._only(method, "GET")
            return 200, {"email": svc.store.get(email_id).to_dict(), "events": svc.store.events(email_id)}
        self._only(method, "PUT" if action == "draft" else "POST")
        body = self._json(h, raw, allow_empty=action in ("submit", "approve", "send"))
        if action in ("draft", "redraft"):
            subject, text = _text(body, "subject", required=True, max_len=200), _text(body, "body", required=True)
            fn = svc.edit_draft if action == "draft" else svc.redraft
            return 200, {"email": fn(email_id, subject, text, operator).to_dict()}
        if action == "submit":
            return 200, {"email": svc.submit_for_approval(email_id, operator).to_dict()}
        if action == "approve":
            return 200, {"email": svc.approve(email_id, operator).to_dict()}
        if action == "reject":
            return 200, {"email": svc.reject(email_id, operator, _text(body, "reason", max_len=500, default="")).to_dict()}
        return self._send(email_id, operator)

    @staticmethod
    def _only(method: str, allowed: str) -> None:
        if method != allowed:
            raise _Bad(405, f"Use {allowed} for this endpoint.")

    @staticmethod
    def _int(value: str) -> int:
        try:
            return max(1, min(int(value), 1000))
        except ValueError:
            raise _Bad(422, "'limit' must be a number")

    @staticmethod
    def _json(h: Mapping[str, str], raw: bytes, allow_empty: bool = False) -> Dict[str, Any]:
        if len(raw) > MAX_BODY:
            raise _Bad(413, "Request body is too large.")
        if not raw.strip():
            if allow_empty:
                return {}
            raise _Bad(400, "A JSON object body is required.")
        if not h.get("content-type", "").lower().startswith("application/json"):
            raise _Bad(415, "Send Content-Type: application/json.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise _Bad(400, "The body is not valid JSON.")
        if not isinstance(data, dict):
            raise _Bad(400, "The body must be a JSON object.")
        return data

    # ---- actions -----------------------------------------------------------------------------------------------
    def _create_draft(self, body: Dict[str, Any], operator: str) -> Response:
        case_id = _text(body, "case_id", required=True, max_len=64)
        if not CASE_ID.match(case_id or ""):
            raise _Bad(422, "'case_id' has invalid characters")
        recipient = _text(body, "recipient", required=True, max_len=254)
        subject, text = _text(body, "subject", max_len=200), _text(body, "body")
        if subject and text:
            rec, created = self.service.create_draft(case_id, recipient, subject, text, actor=operator)
        else:
            case = self.case_provider(case_id) if self.case_provider else None
            if case is None:
                raise _Bad(422, "Give both subject and body, or use a case the server can generate a draft for.")
            audience = _text(body, "audience", max_len=20, default="requester")
            if audience not in ("requester", "internal"):
                raise _Bad(422, "'audience' must be requester or internal")
            rec, created = self.service.create_draft_from_case(
                case, recipient, explanation=_text(body, "explanation", max_len=2000),
                review_needed=bool(body.get("review_needed", False)),
                review_reason=_text(body, "review_reason", max_len=500, default="") or "", audience=audience, actor=operator)
        return (201 if created else 200), {"created": created, "email": rec.to_dict()}

    def _send(self, email_id: str, operator: str) -> Response:
        if not self._send_lock.acquire(blocking=False):
            return 409, {"error": "Another email is being sent. Please wait."}
        try:
            now = self._clock()
            if now - self._last_send < self._min_gap:
                return 429, {"error": "Please wait a moment before sending another email."}
            rec = self.service.send(email_id, operator)            # a refused send (not approved, ...) does not use up the gap
            self._last_send = now
            return 200, {"email": rec.to_dict()}
        finally:
            self._send_lock.release()
