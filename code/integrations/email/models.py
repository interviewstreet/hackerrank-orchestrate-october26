"""Email workflow states, the allowed transitions between them, and the stored record."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional


class EmailState(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


S = EmailState
# DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED -> SENDING -> SENT | FAILED  (the PRD workflow).
# Two extra edges keep it usable without ever skipping a human: a REJECTED email can be re-drafted, and a FAILED
# email must be submitted for approval again (it never goes straight back to APPROVED).
TRANSITIONS: Dict[EmailState, FrozenSet[EmailState]] = {
    S.DRAFT: frozenset({S.PENDING_APPROVAL}),
    S.PENDING_APPROVAL: frozenset({S.APPROVED, S.REJECTED}),
    S.APPROVED: frozenset({S.SENDING}),
    S.REJECTED: frozenset({S.DRAFT}),
    S.SENDING: frozenset({S.SENT, S.FAILED}),
    S.SENT: frozenset(),
    S.FAILED: frozenset({S.PENDING_APPROVAL}),
}

EMAIL_RE = re.compile(r"^[^\s@<>,;\"']+@[^\s@<>,;\"']+\.[^\s@<>,;\"']+$")


def normalize_recipient(addr: str) -> str:
    a = (addr or "").strip().lower()
    if not EMAIL_RE.match(a) or len(a) > 254:
        raise ValueError("recipient must be a single valid email address")
    return a


def idempotency_key(case_id: str, recipient: str, kind: str) -> str:
    """One stable key per case + recipient + kind. Also sent to Resend, so a retry can never double-send."""
    raw = f"{case_id.strip()}\n{normalize_recipient(recipient)}\n{kind.strip()}"
    return "erasight-email-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def content_hash(subject: str, body_text: str) -> str:
    return hashlib.sha256(f"{subject}\n\n{body_text}".encode("utf-8")).hexdigest()


@dataclass
class EmailRecord:
    id: str
    case_id: str
    recipient: str
    kind: str
    subject: str
    body_text: str
    state: str
    idempotency_key: str
    revision: int = 1
    meta: Dict[str, Any] = field(default_factory=dict)
    approved_by: str = ""
    approved_at: str = ""
    approved_hash: str = ""          # content hash at approval; send refuses if the content differs
    rejected_by: str = ""
    rejected_at: str = ""
    rejection_reason: str = ""
    resend_id: str = ""
    delivery_status: str = ""
    last_error: str = ""
    sent_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def content_hash(self) -> str:
        return content_hash(self.subject, self.body_text)
