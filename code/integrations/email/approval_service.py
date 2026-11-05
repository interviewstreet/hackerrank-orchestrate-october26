"""The human approval gate. Only these methods can move an email to APPROVED, and only from PENDING_APPROVAL."""
from __future__ import annotations

import re

from .errors import ContentChanged, InvalidTransition, SeparationOfDuties
from .models import EmailRecord, EmailState
from .store import EmailStore

_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_actor(actor: str) -> str:
    a = _CTRL.sub(" ", actor or "").strip()
    if not a or len(a) > 120:
        raise ValueError("an identified person (1-120 characters) is required")
    return a


class ApprovalService:
    def __init__(self, store: EmailStore, allow_self_approval: bool = False):
        self._store = store
        self._allow_self = allow_self_approval

    _AUTHOR_NOTES = ("created", "draft edited", "re-drafted after rejection", "submitted for approval")

    def _authors(self, email_id: str) -> set:
        """People who drafted, edited, re-drafted or submitted this email. Reviewers and senders are not authors, and the
        automatic 'system' and webhook actors are not people."""
        return {e["actor"].strip().lower() for e in self._store.events(email_id)
                if e["note"] in self._AUTHOR_NOTES} - {"system", "resend-webhook", ""}

    def submit(self, email_id: str, actor: str) -> EmailRecord:
        """DRAFT -> PENDING_APPROVAL (also FAILED -> PENDING_APPROVAL: a failed send needs approval again)."""
        who = clean_actor(actor)
        rec = self._store.transition(email_id, [EmailState.DRAFT, EmailState.FAILED], EmailState.PENDING_APPROVAL, who,
                                     "submitted for approval", approved_by="", approved_at="", approved_hash="", last_error="")
        return rec or self._refuse(email_id, "only a DRAFT or FAILED email can be submitted for approval")

    def approve(self, email_id: str, approver: str) -> EmailRecord:
        who = clean_actor(approver)
        current = self._store.get(email_id)
        if not self._allow_self and who.lower() in self._authors(email_id):
            raise SeparationOfDuties("the approver must be a different person from whoever drafted or submitted this email")
        rec = self._store.transition(email_id, [EmailState.PENDING_APPROVAL], EmailState.APPROVED, who, "approved",
                                     approved_by=who, approved_at=self._store.now(), approved_hash=current.content_hash)
        return rec or self._refuse(email_id, "only a PENDING_APPROVAL email can be approved")

    def reject(self, email_id: str, approver: str, reason: str = "") -> EmailRecord:
        who = clean_actor(approver)
        reason = _CTRL.sub(" ", reason or "").strip()[:500]
        rec = self._store.transition(email_id, [EmailState.PENDING_APPROVAL], EmailState.REJECTED, who,
                                     "rejected: " + reason if reason else "rejected", rejected_by=who,
                                     rejected_at=self._store.now(), rejection_reason=reason)
        return rec or self._refuse(email_id, "only a PENDING_APPROVAL email can be rejected")

    def assert_send_allowed(self, rec: EmailRecord) -> None:
        """The send-time check: approved, and the content is exactly what was approved."""
        if rec.state != EmailState.APPROVED.value:
            from .errors import NotApproved
            raise NotApproved(f"email is {rec.state}; only an APPROVED email can be sent", rec.state)
        if not rec.approved_by or rec.approved_hash != rec.content_hash:
            raise ContentChanged("the email content differs from what was approved")

    def _refuse(self, email_id: str, msg: str) -> EmailRecord:
        state = self._store.get(email_id).state
        raise InvalidTransition(f"{msg} (it is {state})", state)
