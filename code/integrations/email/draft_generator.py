"""Turn an audit result into an email draft. Drafts are never sent from here; they only enter the approval workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import templates

REQUESTER, INTERNAL = "requester", "internal"


@dataclass
class DraftContent:
    subject: str
    body_text: str
    meta: Dict[str, Any] = field(default_factory=dict)


def _as_dict(case: Any) -> Dict[str, Any]:
    return case.to_dict() if hasattr(case, "to_dict") else dict(case)


def build_draft(case: Any, *, explanation: Optional[str] = None, review_needed: bool = False, review_reason: str = "",
                audience: str = REQUESTER) -> DraftContent:
    """case is a CaseAuditResult or its to_dict().

    audience="requester" (default): customer-safe wording from the engine's counts only.
    audience="internal": also appends the advisory explanation (which may name internal resource ids) and any
    human-review flag, for a privacy analyst to read before approving.
    """
    c = _as_dict(case)
    status = c.get("deletion_status", "")
    if status not in templates.BODIES:
        raise ValueError(f"cannot draft an email for status {status!r}")
    summary = c.get("summary") or {}
    fields = {"case_id": c["case_id"], "systems_checked": summary.get("systems_checked", 0),
              "findings_count": summary.get("findings_count", 0), "remediation_count": summary.get("remediation_count", 0)}
    subject = templates.SUBJECTS[status].format(**fields)
    body = templates.BODIES[status].format(**fields)
    if audience == INTERNAL:
        if explanation:
            body += templates.INTERNAL_NOTE.format(explanation=explanation.strip())
        if review_needed:
            body += templates.REVIEW_NOTE.format(reason=review_reason or "see the audit result")
    elif audience != REQUESTER:
        raise ValueError("audience must be 'requester' or 'internal'")
    meta = {"deletion_status": status, "audience": audience, "review_needed": bool(review_needed),
            "explanation_used": bool(explanation) and audience == INTERNAL}
    return DraftContent(subject=subject, body_text=body, meta=meta)
