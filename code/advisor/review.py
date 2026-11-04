"""Deterministic triggers: which cases deserve a model second opinion (everything else gets a template, no model call)."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List

from engine.case_analyzer import EngineContext
from engine.contracts import CaseAuditResult
from engine.request_classifier import DEL_RE, NEG_RE

HEDGES = re.compile(r"\b(?:maybe|perhaps|not sure|unsure|might|could you also|instead|rather than|only)\b", re.IGNORECASE)


def _near_known_email(ec: EngineContext, email: str) -> str:
    e = (email or "").strip().lower()
    best, best_r = "", 0.0
    for known in ec.ctx.historical_email_index:
        if abs(len(known) - len(e)) > 2:
            continue
        r = SequenceMatcher(None, e, known).ratio()
        if r > best_r:
            best, best_r = known, r
    return best if best_r >= 0.9 and best != e else ""


def review_reasons(result: CaseAuditResult, request: Dict[str, str], ec: EngineContext) -> List[str]:
    reasons: List[str] = []
    status = result.identities[0]["resolution_status"] if result.identities else ""
    if result.deletion_status != "NOT_APPLICABLE" and status and status != "RESOLVED":
        reasons.append(f"identity is {status}")
        near = _near_known_email(ec, request["email"])
        if near:
            reasons.append("email closely resembles a different known customer address (possible lookalike)")
    text = request.get("request_text", "")
    if DEL_RE.search(text) and (NEG_RE.search(text) or HEDGES.search(text)):
        reasons.append("request wording mixes deletion language with limiting language")
    if result.deletion_status == "NOT_APPLICABLE" and DEL_RE.search(text):
        reasons.append("classified as not a deletion request although deletion words appear")
    if result.deletion_status != "NOT_APPLICABLE" and not result.steps:
        reasons.append("no records could be tied to this customer")
    return reasons
