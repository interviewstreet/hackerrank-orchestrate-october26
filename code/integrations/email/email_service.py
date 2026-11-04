"""Orchestrates the email workflow: draft -> approval -> guarded send -> webhook reconciliation."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from .approval_service import ApprovalService, clean_actor
from .config import EmailConfig
from .draft_generator import REQUESTER, build_draft
from .errors import EmailNotConfigured, InvalidTransition, ResendError
from .models import EmailRecord, EmailState, content_hash, idempotency_key, normalize_recipient
from .resend_client import ResendClient
from .store import EmailStore, new_id
from .webhook_handler import parse_event, verify_webhook

DEFAULT_KIND = "audit_result"
# Delivery events in the order they normally happen; a later event never moves delivery_status backwards.
_RANK = {"sent": 1, "delivery_delayed": 2, "delivered": 3, "bounced": 4, "complained": 4, "suppressed": 4, "failed": 4}
_ACCEPTED = {"sent", "delivery_delayed", "delivered", "bounced", "complained", "suppressed"}   # Resend accepted the email


class EmailService:
    def __init__(self, store: EmailStore, client: ResendClient, config: Optional[EmailConfig] = None):
        self.store = store
        self.client = client
        self.config = config or EmailConfig()
        self.approvals = ApprovalService(store)

    # ---- drafting ----
    def create_draft(self, case_id: str, recipient: str, subject: str, body_text: str, *, kind: str = DEFAULT_KIND,
                     meta: Optional[Dict[str, Any]] = None, actor: str = "system") -> Tuple[EmailRecord, bool]:
        """One email per case + recipient + kind. A second call returns the existing email (created=False)."""
        if not case_id.strip() or not subject.strip() or not body_text.strip():
            raise ValueError("case_id, subject and body are required")
        if "\n" in subject or "\r" in subject:
            raise ValueError("subject must be a single line")
        rcpt = normalize_recipient(recipient)
        rec = EmailRecord(id=new_id(), case_id=case_id.strip(), recipient=rcpt, kind=kind.strip(), subject=subject.strip(),
                          body_text=body_text, state=EmailState.DRAFT.value, meta=meta or {},
                          idempotency_key=idempotency_key(case_id, rcpt, kind))
        return self.store.create(rec, clean_actor(actor))

    def create_draft_from_case(self, case: Any, recipient: str, *, explanation: Optional[str] = None,
                               review_needed: bool = False, review_reason: str = "", audience: str = REQUESTER,
                               kind: str = DEFAULT_KIND, actor: str = "system") -> Tuple[EmailRecord, bool]:
        d = build_draft(case, explanation=explanation, review_needed=review_needed, review_reason=review_reason,
                        audience=audience)
        case_id = (case.to_dict() if hasattr(case, "to_dict") else case)["case_id"]
        return self.create_draft(case_id, recipient, d.subject, d.body_text, kind=kind, meta=d.meta, actor=actor)

    def edit_draft(self, email_id: str, subject: str, body_text: str, actor: str) -> EmailRecord:
        """Content can change only while the email is a DRAFT; nothing already submitted or approved can be edited."""
        who = clean_actor(actor)
        if not subject.strip() or not body_text.strip() or "\n" in subject:
            raise ValueError("subject (one line) and body are required")
        rec = self.store.update_fields(email_id, [EmailState.DRAFT], who, "draft edited",
                                       subject=subject.strip(), body_text=body_text)
        return rec or self._not_draft(email_id)

    def redraft(self, email_id: str, subject: str, body_text: str, actor: str) -> EmailRecord:
        """REJECTED -> DRAFT with new content (revision + 1)."""
        who = clean_actor(actor)
        if not subject.strip() or not body_text.strip() or "\n" in subject:
            raise ValueError("subject (one line) and body are required")
        cur = self.store.get(email_id)
        rec = self.store.transition(email_id, [EmailState.REJECTED], EmailState.DRAFT, who, "re-drafted after rejection",
                                    subject=subject.strip(), body_text=body_text, revision=cur.revision + 1,
                                    rejected_by="", rejected_at="", rejection_reason="")
        if rec is None:
            raise InvalidTransition(f"only a REJECTED email can be re-drafted (it is {self.store.get(email_id).state})",
                                    self.store.get(email_id).state)
        return rec

    # ---- approval ----
    def submit_for_approval(self, email_id: str, actor: str) -> EmailRecord:
        return self.approvals.submit(email_id, actor)

    def approve(self, email_id: str, approver: str) -> EmailRecord:
        return self.approvals.approve(email_id, approver)

    def reject(self, email_id: str, approver: str, reason: str = "") -> EmailRecord:
        return self.approvals.reject(email_id, approver, reason)

    # ---- sending ----
    def send(self, email_id: str, actor: str) -> EmailRecord:
        """Send an APPROVED email. Safe to call twice: a SENT email is returned unchanged and never re-sent."""
        who = clean_actor(actor)
        rec = self.store.get(email_id)
        if rec.state == EmailState.SENT.value:
            return rec
        self.approvals.assert_send_allowed(rec)                  # raises NotApproved / ContentChanged
        if not (self.client.can_send):
            raise EmailNotConfigured("RESEND_API_KEY and RESEND_FROM_EMAIL must be set to send")
        claimed = self.store.transition(email_id, [EmailState.APPROVED], EmailState.SENDING, who, "send started")
        if claimed is None:                                      # another request claimed it first
            cur = self.store.get(email_id)
            if cur.state == EmailState.SENT.value:
                return cur
            raise InvalidTransition(f"email is {cur.state}; another request is already sending it", cur.state)
        try:
            resend_id = self.client.send(to=claimed.recipient, subject=claimed.subject, text=claimed.body_text,
                                         idempotency_key=claimed.idempotency_key)
        except ResendError as e:
            return self._finish(email_id, who, EmailState.FAILED, last_error=str(e)[:500])
        except Exception as e:                                   # never leave an email stuck in SENDING
            return self._finish(email_id, who, EmailState.FAILED, last_error=f"unexpected {type(e).__name__}")
        return self._finish(email_id, who, EmailState.SENT, resend_id=resend_id, sent_at=self.store.now(), last_error="")

    # ---- webhooks ----
    def handle_webhook(self, headers: Mapping[str, str], body: bytes, now: Optional[float] = None) -> Dict[str, Any]:
        """Verify, then apply a Resend delivery event. Raises WebhookVerificationError / WebhookConfigError."""
        svix_id = verify_webhook(self.config.webhook_secret, headers, body, now=now)
        event = parse_event(body)
        if not self.store.record_webhook(svix_id):
            return {"handled": False, "reason": "duplicate"}
        etype = event["type"]
        status = etype.split(".", 1)[1] if etype.startswith("email.") else ""
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        rec = self.store.find_by_resend_id(str(data.get("email_id", "")))
        if status not in _RANK or rec is None:
            return {"handled": False, "reason": "ignored_event" if status not in _RANK else "unknown_email"}
        fields: Dict[str, Any] = {}
        if _RANK[status] >= _RANK.get(rec.delivery_status, 0):
            fields["delivery_status"] = status
        if rec.state == EmailState.SENDING.value:                # reconcile an email whose send call never reported back
            to = EmailState.FAILED if status == "failed" else EmailState.SENT if status in _ACCEPTED else None
            if to is not None:
                if to is EmailState.SENT:
                    fields["sent_at"] = self.store.now()
                self.store.transition(rec.id, [EmailState.SENDING], to, "resend-webhook", f"webhook {etype}", **fields)
                return {"handled": True, "email_id": rec.id, "delivery_status": status}
        if fields:
            self.store.update_fields(rec.id, list(EmailState), "resend-webhook", f"webhook {etype}", **fields)
        return {"handled": True, "email_id": rec.id, "delivery_status": status}

    # ---- helpers ----
    def _finish(self, email_id: str, actor: str, to: EmailState, **fields: Any) -> EmailRecord:
        rec = self.store.transition(email_id, [EmailState.SENDING], to, actor, "send " + to.value.lower(), **fields)
        return rec or self.store.get(email_id)                   # a webhook may already have settled it

    def _not_draft(self, email_id: str) -> EmailRecord:
        state = self.store.get(email_id).state
        raise InvalidTransition(f"only a DRAFT can be edited (it is {state})", state)


def build_service_from_env(env: Optional[Mapping[str, str]] = None, client: Optional[ResendClient] = None,
                           store: Optional[EmailStore] = None) -> EmailService:
    cfg = EmailConfig.from_env(env)
    return EmailService(store or EmailStore(cfg.db_path), client or ResendClient(cfg.api_key, cfg.from_email), cfg)
