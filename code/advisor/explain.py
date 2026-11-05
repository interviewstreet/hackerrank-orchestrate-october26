"""Plain-language explanations: a deterministic template for every case, optionally refined by a model."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

from engine.contracts import CaseAuditResult

SYSTEM_PROMPT = (
    "You are an assistant that explains the result of a personal-data deletion audit to a privacy analyst. "
    "You are given the audit result produced by a deterministic engine. The status and steps are final: never change, "
    "dispute or add to them. Use only resource ids and evidence ids that appear in the audit result; never invent any. "
    "Reply with a single JSON object: {\"summary\": string (max 90 words, plain language), "
    "\"review_needed\": boolean, \"review_reason\": string (empty if not needed)}."
)

ID_RE = re.compile(r"\b(?:account|search|analytics|support|export|data_flow|backup|audit_record|tombstone|legal_hold|marketing|"
                   r"object|cache)_\d+\b|\bevidence_\d+\b")


def template_explanation(result: CaseAuditResult) -> str:
    s = result.deletion_status
    if s == "NOT_APPLICABLE":
        return "The request does not ask for deletion, so no audit steps are needed."
    ident = result.identities[0]["resolution_status"] if result.identities else "UNRESOLVED"
    if ident != "RESOLVED":
        return ("The customer could not be matched to exactly one account, so deletion cannot be proven. "
                "No records were attributed to this request; a person should confirm the identity first.")
    rem = sorted({st["resource_id"] for st in result.steps if st["phase"] == "REMEDIATION"})
    found = sorted({st["resource_id"] for st in result.steps if st["phase"] == "FINDING"})
    if s == "COMPLETE":
        return (f"Deletion is complete. {result.summary.get('verification_count', 0)} verification checks across "
                f"{result.summary.get('systems_checked', 0)} systems confirm the data is gone or properly handled at audit time.")
    if not result.steps:
        return "No records tied to this customer could be proven removed, so the deletion is treated as incomplete."
    return (f"Deletion is incomplete. Data still exists or can reappear in {len(found)} place(s): {', '.join(found)}. "
            f"{len(rem)} remediation step(s) are planned: {', '.join(rem)}, followed by verification checks.")


def allowed_ids(result: CaseAuditResult) -> Set[str]:
    ids = {st["resource_id"] for st in result.steps} | {st["evidence_id"] for st in result.steps if st["evidence_id"]}
    return ids | {e["evidence_id"] for e in result.evidence}


def build_prompt(result: CaseAuditResult, request: Dict[str, str], reasons: List[str]) -> str:
    payload = {
        "request_text": request.get("request_text", ""),
        "engine_status": result.deletion_status,
        "identity": result.identities[0] if result.identities else {},
        "steps": [{k: st[k] for k in ("phase", "resource_id", "operation", "evidence_id")} for st in result.steps],
        "why_a_second_look": reasons,
    }
    return json.dumps(payload, ensure_ascii=False)


CLAIMS_COMPLETE = re.compile(r"\b(?:is|was|has been|fully|now) (?:fully |now )?(?:complete|completed|deleted|erased)\b|\bdeletion (?:is|was) complete\b", re.I)
CLAIMS_INCOMPLETE = re.compile(r"\b(?:incomplete|not (?:yet )?(?:complete|completed|deleted|erased)|still exists?|remains?|remaining)\b", re.I)
NEGATED_CONTEXT = re.compile(r"\bnot (?:a |an )?(?:deletion|erasure)\b|\bno deletion\b|\bnot applicable\b", re.I)


def contradicts_status(text: str, status: str) -> bool:
    """True if the model's wording claims an outcome that contradicts the engine's status."""
    if status == "INCOMPLETE":
        return bool(CLAIMS_COMPLETE.search(text)) and not CLAIMS_INCOMPLETE.search(text)
    if status == "COMPLETE":
        return bool(CLAIMS_INCOMPLETE.search(text)) and not CLAIMS_COMPLETE.search(text)
    if status == "NOT_APPLICABLE":
        return bool(CLAIMS_COMPLETE.search(text)) and not NEGATED_CONTEXT.search(text)
    return False


def parse_and_validate(raw: str, result: CaseAuditResult) -> Optional[Dict[str, Any]]:
    """Accept the model's JSON only if it is well-formed and cites nothing the engine did not produce."""
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data.get("summary"), str) or not isinstance(data.get("review_needed"), bool):
        return None
    reason = data.get("review_reason", "")
    if not isinstance(reason, str):
        return None
    allowed = allowed_ids(result)
    if any(i not in allowed for i in ID_RE.findall(data["summary"] + " " + reason)):
        return None                                                    # invented identifier -> reject the whole answer
    if len(data["summary"].split()) > 140:
        return None
    if contradicts_status(data["summary"], result.deletion_status):
        return None                                                    # wording disagrees with the engine -> reject
    return {"summary": data["summary"].strip(), "review_needed": data["review_needed"], "review_reason": reason.strip()}
