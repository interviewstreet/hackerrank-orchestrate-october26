"""Team-written evaluation cases (beyond the 32 public samples).

Each case perturbs a public sample request in a way whose correct outcome follows from the problem statement, so the
expected result is reasoned independently of the engine. Run:  python3 code/evaluation/custom_cases.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from engine.case_analyzer import EngineContext, analyze_case, build_context   # noqa: E402


@dataclass
class Custom:
    name: str
    base: str                                    # public sample case the request is derived from
    overrides: Dict[str, str]
    expectation: str
    check: Callable[..., Tuple[bool, str]]      # (result, base_result, ec) -> (ok, detail)


def _keys(res):
    return [(s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"]) for s in res.steps]


def lookalike(res, base, ec):
    ok = (res.deletion_status == "INCOMPLETE" and not res.steps
          and res.identities[0]["resolution_status"] == "UNRESOLVED")
    return ok, f"status={res.deletion_status} steps={len(res.steps)} identity={res.identities[0]['resolution_status']}"


def same_as_base(res, base, ec):
    ok = res.deletion_status == base.deletion_status and _keys(res) == _keys(base)
    return ok, f"status={res.deletion_status} (base {base.deletion_status}), steps {len(res.steps)} vs {len(base.steps)}"


def not_applicable(res, base, ec):
    ok = res.deletion_status == "NOT_APPLICABLE" and res.steps == []
    return ok, f"status={res.deletion_status} steps={len(res.steps)}"


def no_late_evidence(res, base, ec):
    audit = res.__dict__.get("_audit_at", "")
    late = [s["evidence_id"] for s in res.steps if s["evidence_id"] and ec.ctx.manifest[s["evidence_id"]]["captured_at"] > audit]
    return (not late and res.deletion_status != "COMPLETE"), f"status={res.deletion_status} late_citations={late}"


def other_user_flow_excluded(res, base, ec):
    flows = {s["resource_id"] for s in res.steps if s["resource_id"].startswith("data_flow_")}
    ok = "data_flow_1121" not in flows and any(s["operation"] == "DISABLE_DATA_FLOW" for s in res.steps)
    return ok, f"data flows in steps={sorted(flows)}"


CASES: List[Custom] = [
    Custom("lookalike_identity", "case_01", {"email": "amina.elmasri@gmai1.com"},
           "A one-character lookalike email must not be merged with the real customer: UNRESOLVED, INCOMPLETE, no invented steps.",
           lookalike),
    Custom("email_normalisation", "case_15", {"email": "  Lucia-Torres@GMAIL.com "},
           "Case and whitespace in the request email must not change the audit result.", same_as_base),
    Custom("multilingual_deletion", "case_26",
           {"request_text": "Por favor, elimine mi cuenta y todos mis datos personales."},
           "A Spanish deletion request is still a deletion request: same audit as the English original.", same_as_base),
    Custom("negated_request", "case_01",
           {"request_text": "Please do not delete my account. I only want to update my phone number."},
           "A request that explicitly declines deletion is NOT_APPLICABLE with no steps.", not_applicable),
    Custom("audit_before_evidence", "case_26", {"audit_at": "2026-09-02T09:00:00Z"},
           "Auditing at a moment before later evidence existed: no step may cite evidence captured after audit_at.",
           no_late_evidence),
    Custom("other_users_active_flow", "case_15", {},
           "An integration screenshot that mentions this customer next to another customer's flow: only the customer's own "
           "active flow is disabled, never the other customer's.", other_user_flow_excluded),
]


def run_all(ec: EngineContext | None = None):
    ec = ec or build_context(ROOT / "dataset")
    samples = {r["case_id"]: r for r in ec.ctx.sample_requests}
    out = []
    for c in CASES:
        req = dict(samples[c.base]); req.update(c.overrides)
        base = analyze_case(samples[c.base], ec)
        res = analyze_case(req, ec)
        res.__dict__["_audit_at"] = req["audit_at"]
        ok, detail = c.check(res, base, ec)
        out.append((c, ok, detail))
    return out


if __name__ == "__main__":
    results = run_all()
    for c, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {c.name:26s} {detail}")
    print(f"{sum(ok for _, ok, _ in results)}/{len(results)} custom cases passed")
