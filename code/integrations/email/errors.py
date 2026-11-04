"""Exceptions raised by the email integration. None of them ever carries a secret."""
from __future__ import annotations


class EmailError(Exception):
    """Base class."""


class EmailNotFound(EmailError):
    pass


class InvalidTransition(EmailError):
    """The email is not in a state that allows the requested action."""

    def __init__(self, message: str, state: str = ""):
        super().__init__(message)
        self.state = state


class NotApproved(InvalidTransition):
    """Send was attempted without a human approval."""


class ContentChanged(EmailError):
    """The stored content no longer matches what the approver approved."""


class EmailNotConfigured(EmailError):
    """RESEND_API_KEY or RESEND_FROM_EMAIL is missing, so nothing can be sent."""


class WebhookConfigError(EmailError):
    """RESEND_WEBHOOK_SECRET is missing, so webhooks cannot be verified (and are therefore refused)."""


class WebhookVerificationError(EmailError):
    """Signature, timestamp or header check failed."""


class ResendError(EmailError):
    """The Resend API (or the network) refused or failed a send."""

    def __init__(self, message: str, status: int = 0, name: str = "", retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.name = name
        self.retryable = retryable
