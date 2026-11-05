"""Case advisor: template for all cases, model second opinion only where the deterministic triggers fire."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from engine.case_analyzer import EngineContext, analyze_case
from engine.contracts import CaseAuditResult

from .explain import SYSTEM_PROMPT, build_prompt, parse_and_validate, template_explanation
from .llm_client import ModelUnavailable
from .review import review_reasons


def advise_case(result: CaseAuditResult, request: Dict[str, str], ec: EngineContext, client: Optional[Any] = None) -> Dict[str, Any]:
    reasons = review_reasons(result, request, ec)
    advice: Dict[str, Any] = {
        "case_id": result.case_id, "deletion_status": result.deletion_status, "source": "template",
        "explanation": template_explanation(result), "review_needed": bool(reasons),
        "review_reason": "; ".join(reasons), "triggers": reasons, "model_note": ""}
    if not reasons or client is None or not getattr(client, "available", False):
        return advice
    try:
        raw = client.complete(result.case_id, SYSTEM_PROMPT, build_prompt(result, request, reasons))
    except ModelUnavailable as e:
        advice["model_note"] = str(e)
        return advice
    parsed = parse_and_validate(raw, result)
    if parsed is None:
        advice["model_note"] = "model answer rejected (malformed or cited an id the engine did not produce)"
        return advice
    advice.update(source="model", explanation=parsed["summary"],
                  review_needed=advice["review_needed"] or parsed["review_needed"],
                  review_reason=parsed["review_reason"] or advice["review_reason"])
    return advice


def advise_all(requests: Iterable[Dict[str, str]], ec: EngineContext, client: Optional[Any] = None,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
    out, calls = [], 0
    for r in requests:
        res = analyze_case(r, ec)
        use = client if (limit is None or calls < limit) else None
        a = advise_case(res, r, ec, use)
        calls += bool(a["source"] == "model" or a["model_note"] or (use is not None and a["triggers"]))   # attempts, not just successes
        out.append(a)
    return out
