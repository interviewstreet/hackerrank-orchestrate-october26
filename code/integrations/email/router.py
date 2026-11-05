"""FastAPI router for the email workflow. Member 1 mounts it; this file never touches api.py, the frontend or Slack.

    from integrations.email import build_service_from_env
    from integrations.email.router import create_email_router
    app.include_router(create_email_router(build_service_from_env(), dependencies=[Depends(require_login)]))

`dependencies` (Member 1's auth) is applied to every route EXCEPT the Resend webhook, which authenticates itself with
its Svix signature. Approve/reject/send must sit behind real authentication: the approver name in the body is recorded
in the audit trail but is only as trustworthy as the login Member 1 puts in front of it.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .email_service import EmailService
from .errors import (ContentChanged, EmailNotConfigured, EmailNotFound, InvalidTransition, RecipientNotAllowed,
                     SeparationOfDuties, WebhookConfigError, WebhookVerificationError)

CaseProvider = Callable[[str], Optional[Dict[str, Any]]]     # case_id -> CaseAuditResult.to_dict(), or None


class DraftIn(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    recipient: str = Field(min_length=3, max_length=254)
    subject: Optional[str] = Field(default=None, max_length=200)
    body: Optional[str] = Field(default=None, max_length=20000)
    explanation: Optional[str] = Field(default=None, max_length=2000)    # advisory text, used for audience=internal
    review_needed: bool = False
    review_reason: str = Field(default="", max_length=500)
    audience: str = Field(default="requester", pattern="^(requester|internal)$")
    actor: str = Field(default="system", min_length=1, max_length=120)


class EditIn(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    actor: str = Field(min_length=1, max_length=120)


class ActorIn(BaseModel):
    actor: str = Field(min_length=1, max_length=120)


class ApproveIn(BaseModel):
    approver: str = Field(min_length=1, max_length=120)


class RejectIn(BaseModel):
    approver: str = Field(min_length=1, max_length=120)
    reason: str = Field(default="", max_length=500)


def _http(e: Exception) -> HTTPException:
    if isinstance(e, EmailNotFound):
        return HTTPException(404, str(e))
    if isinstance(e, (InvalidTransition, ContentChanged)):
        return HTTPException(409, str(e))
    if isinstance(e, (RecipientNotAllowed, SeparationOfDuties)):
        return HTTPException(403, str(e))
    if isinstance(e, EmailNotConfigured):
        return HTTPException(503, str(e))
    if isinstance(e, ValueError):
        return HTTPException(422, str(e))
    raise e


def create_email_router(service: EmailService, *, dependencies: Optional[Sequence[Any]] = None,
                       case_provider: Optional[CaseProvider] = None, prefix: str = "/email") -> APIRouter:
    deps = list(dependencies or [])
    router = APIRouter(prefix=prefix, tags=["email"])

    def call(fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as e:                                       # mapped to a clean HTTP error, or re-raised
            raise _http(e)

    @router.post("/drafts", status_code=201, dependencies=deps)
    def create_draft(body: DraftIn) -> Dict[str, Any]:
        def go() -> Dict[str, Any]:
            if body.subject and body.body:
                rec, created = service.create_draft(body.case_id, body.recipient, body.subject, body.body, actor=body.actor)
            else:
                case = case_provider(body.case_id) if case_provider else None
                if case is None:
                    raise ValueError("give both subject and body, or configure a case_provider so the draft can be generated")
                rec, created = service.create_draft_from_case(
                    case, body.recipient, explanation=body.explanation, review_needed=body.review_needed,
                    review_reason=body.review_reason, audience=body.audience, actor=body.actor)
            return {"created": created, "email": rec.to_dict()}
        return call(go)

    @router.get("/emails", dependencies=deps)
    def list_emails(case_id: Optional[str] = None, state: Optional[str] = None,
                    limit: int = Query(200, ge=1, le=1000)) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in service.store.list(case_id=case_id, state=state, limit=limit)]

    @router.get("/emails/{email_id}", dependencies=deps)
    def get_email(email_id: str) -> Dict[str, Any]:
        return call(lambda: {"email": service.store.get(email_id).to_dict(), "events": service.store.events(email_id)})

    @router.put("/emails/{email_id}/draft", dependencies=deps)
    def edit_draft(email_id: str, body: EditIn) -> Dict[str, Any]:
        return call(lambda: service.edit_draft(email_id, body.subject, body.body, body.actor).to_dict())

    @router.post("/emails/{email_id}/redraft", dependencies=deps)
    def redraft(email_id: str, body: EditIn) -> Dict[str, Any]:
        return call(lambda: service.redraft(email_id, body.subject, body.body, body.actor).to_dict())

    @router.post("/emails/{email_id}/submit", dependencies=deps)
    def submit(email_id: str, body: ActorIn) -> Dict[str, Any]:
        return call(lambda: service.submit_for_approval(email_id, body.actor).to_dict())

    @router.post("/emails/{email_id}/approve", dependencies=deps)
    def approve(email_id: str, body: ApproveIn) -> Dict[str, Any]:
        return call(lambda: service.approve(email_id, body.approver).to_dict())

    @router.post("/emails/{email_id}/reject", dependencies=deps)
    def reject(email_id: str, body: RejectIn) -> Dict[str, Any]:
        return call(lambda: service.reject(email_id, body.approver, body.reason).to_dict())

    @router.post("/emails/{email_id}/send", dependencies=deps)
    def send(email_id: str, body: ActorIn) -> Dict[str, Any]:
        return call(lambda: service.send(email_id, body.actor).to_dict())

    @router.post("/webhooks/resend")                                  # no `deps`: authenticated by its Svix signature
    async def resend_webhook(request: Request) -> Dict[str, Any]:
        raw = await request.body()
        try:
            return service.handle_webhook(request.headers, raw)
        except WebhookConfigError as e:
            raise HTTPException(503, str(e))
        except WebhookVerificationError as e:
            raise HTTPException(400, str(e))

    return router
