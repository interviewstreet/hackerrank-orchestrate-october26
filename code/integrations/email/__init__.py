"""Resend email integration: human-approved, duplicate-safe outbound email for deletion-audit results.

Mount in Member 1's FastAPI app:
    from integrations.email import build_service_from_env
    from integrations.email.router import create_email_router
    app.include_router(create_email_router(build_service_from_env()))
"""
from .config import EmailConfig
from .email_service import EmailService, build_service_from_env
from .errors import (ContentChanged, EmailError, EmailNotConfigured, EmailNotFound, InvalidTransition, NotApproved,
                     ResendError, WebhookConfigError, WebhookVerificationError)
from .models import EmailRecord, EmailState
from .resend_client import ResendClient
from .store import EmailStore

__all__ = ["EmailConfig", "EmailService", "build_service_from_env", "EmailRecord", "EmailState", "EmailStore",
           "ResendClient", "EmailError", "EmailNotFound", "InvalidTransition", "NotApproved", "ContentChanged",
           "EmailNotConfigured", "ResendError", "WebhookConfigError", "WebhookVerificationError"]
