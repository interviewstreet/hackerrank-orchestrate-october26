"""analyze_case(request, engine_context) -> CaseAuditResult  (the shared contract with Member 1)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .contracts import (CaseAuditResult, OPERATION_ORDER, OPERATION_STATE)
from .dataset_loader import DatasetContext, load_dataset
from .evidence_loader import EvidenceStore, load_evidence
from .evidence_matcher import GlobalLinks, claimed_resources, infer_by_activity
from .ghost_detector import detect_findings
from .identity_resolver import resolve_subject
from .policy_engine import Decision, evaluate
from .remediation_planner import plan_remediation
from .request_classifier import DELETION_REQUESTED, classify_request
from .state_reconstructor import reconstruct
from .util import category_for_resource
from .verification_planner import plan_verification


@dataclass
class EngineContext:
    ctx: DatasetContext
    store: EvidenceStore
    links: GlobalLinks


def build_context(dataset_dir) -> EngineContext:
    ctx = load_dataset(dataset_dir)
    store = load_evidence(ctx)
    return EngineContext(ctx, store, GlobalLinks(ctx, store))


def _sort_key(step: Dict[str, str]):
    return (OPERATION_ORDER.index(step["operation"]), step["system_id"], step["resource_id"])


def _category_of(store: EvidenceStore, resource_id: str) -> tuple:
    """(system_id, category) from the evidence if available, otherwise from the resource-id prefix."""
    sys_p, cat_p = category_for_resource(resource_id)
    for o in store.by_resource.get(resource_id, []):
        if o.data_category and o.system_id:
            return o.system_id, o.data_category
    return sys_p or "", cat_p or ""


def _all_requests(ec: "EngineContext", request: Dict[str, str]) -> List[Dict[str, str]]:
    """Sample and main requests share one worker activity stream, so they compete for the same activities."""
    seen, out = set(), []
    base = ec.ctx.sample_requests if any(r["case_id"] == request["case_id"] for r in ec.ctx.sample_requests) \
        else ec.ctx.requests
    for r in base:
        if r["case_id"] not in seen:
            seen.add(r["case_id"])
            out.append(r)
    return out


def _arbitrate(ec: "EngineContext", request: Dict[str, str], cands: List[str]) -> List[str]:
    """Several unowned worker activities compete for the same reported_at. When exactly as many deletion cases
    share that report time (and status) as there are candidates, the worker handled them in request order:
    case k (by case_id) takes the k-th activity (by event time). Otherwise stay ambiguous (return [])."""
    pool = _all_requests(ec, request)
    peers = sorted(r["case_id"] for r in pool
                   if r["reported_at"] == request["reported_at"] and r["reported_status"] == request["reported_status"]
                   and classify_request(r["request_text"]) == DELETION_REQUESTED)
    if len(peers) != len(cands) or request["case_id"] not in peers:
        return []
    times = {a["resource_id"]: a["event_time"] for a in ec.ctx.activities}
    ordered = sorted(cands, key=lambda c: times.get(c, ""))
    return [ordered[peers.index(request["case_id"])]]


def _pick_for_complete_peer(ec: "EngineContext", request: Dict[str, str], cands: List[str]) -> str:
    """Candidates compete among the cases that share this report time and are complete without them."""
    if not cands:
        return ""
    pool = _all_requests(ec, request)
    cache = ec.__dict__.setdefault("_peer_cache", {})
    eligible = []
    for r in sorted((r for r in pool if r["reported_at"] == request["reported_at"]), key=lambda r: r["case_id"]):
        if r["case_id"] not in cache:
            cache[r["case_id"]] = analyze_case(r, ec, _peer_pass=True).deletion_status
        if cache[r["case_id"]] == "COMPLETE":
            eligible.append(r["case_id"])
    if request["case_id"] not in eligible:
        return ""
    times = {a["resource_id"]: a["event_time"] for a in ec.ctx.activities}
    if len(cands) > len(eligible):          # prefer records the evidence actually shows (citable at audit_at)
        shown = [c for c in cands if any((o.observed_at or o.captured_at) <= request["audit_at"]
                                         and (o.file_captured_at or o.captured_at) <= request["audit_at"]
                                         for o in ec.store.by_resource.get(c, []))]
        cands = shown or cands
    ordered = sorted(cands, key=lambda c: times.get(c, ""))
    k = eligible.index(request["case_id"])   # earlier case_id <-> earlier worker activity; surplus belongs to others
    return ordered[k] if k < len(ordered) else ""


def analyze_case(request: Dict[str, str], ec: EngineContext, _peer_pass: bool = False) -> CaseAuditResult:
    cid, audit_at = request["case_id"], request["audit_at"]
    result = CaseAuditResult(case_id=cid, deletion_status="NOT_APPLICABLE")

    if classify_request(request["request_text"]) != DELETION_REQUESTED:
        return result                                    # no deletion authorized -> no investigation, steps_json=[]

    subject = resolve_subject(ec.ctx, cid, request["email"], audit_at)
    result.identities = [{
        "identity_id": f"IDENTITY-{subject.user_id or 'NONE'}", "resolved_identifiers": subject.identifiers(),
        "matched_evidence": [], "resolution_status": subject.status, "confidence": subject.confidence}]
    if subject.status != "RESOLVED":
        result.deletion_status = "INCOMPLETE"            # cannot prove anything about an unresolved identity
        return result

    claims = claimed_resources(ec.store, subject, audit_at, request["requested_at"])          # resource_id -> reasons
    inferred: Dict[str, str] = {}

    def has(prefix: str) -> bool:
        return any(r.startswith(prefix) for r in claims)

    if not has("account_"):                                         # absent accounts carry no identifier: use activity
        for match_status in (True, False):
            cands = infer_by_activity(ec.ctx, ec.links, subject, request,
                                      event_type="DELETE_RECORD", target_system="account_service",
                                      before_min=90, after_min=10, match_status=match_status)
            if len(cands) == 1:
                claims[cands[0]] = ["activity:reported_at proximity (unique, unowned)"]
                inferred[cands[0]] = "activity"
                break
            if len(cands) > 1:
                cands = _arbitrate(ec, request, cands)
                if cands:
                    claims[cands[0]] = ["activity:reported_at proximity (ordered among peers)"]
                    inferred[cands[0]] = "activity"
                break
            if cands:
                break
    # An anonymization the worker performed on a record that carries no identifier can only support a *compliant*
    # verification, so it is attributed only to cases that are otherwise complete (peer-pass decides who those are).
    if not _peer_pass and not any(r.startswith("analytics_") for r in claims):
        cands = infer_by_activity(ec.ctx, ec.links, subject, request, event_type="ANONYMIZE_RECORD",
                                  target_system="analytics_platform", before_min=45, after_min=10, match_status=False)
        cands = [c for c in cands if c not in claims]
        pick = _pick_for_complete_peer(ec, request, cands)
        if pick:
            claims[pick] = ["activity:reported_at proximity (ordered among complete peers)"]
            inferred[pick] = "activity"

    decisions: List[Decision] = []
    used_systems = set()
    for rid in sorted(claims):
        system_id, category = _category_of(ec.store, rid)
        if not category:
            continue
        rs = reconstruct(ec.store, rid, system_id, category, audit_at)
        d = evaluate(ec.ctx, rs, audit_at)
        if d is None:
            continue
        decisions.append(d)
        used_systems.add(system_id)

    violations = [d for d in decisions if not d.compliant]
    complete = (bool(decisions) or _peer_pass) and not violations      # nothing found at all is "cannot prove", not "proved gone"
    result.deletion_status = "COMPLETE" if complete else "INCOMPLETE"

    findings = detect_findings(decisions)
    rows = ([dict(r, phase="FINDING") for r in findings]
            + [dict(r, phase="REMEDIATION") for r in plan_remediation(violations)]
            + [dict(r, phase="VERIFICATION") for r in plan_verification(decisions, complete)])
    phase_rank = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
    rows.sort(key=lambda r: (phase_rank[r["phase"]],) + _sort_key(r))
    steps = []
    for n, r in enumerate(rows, 1):
        phase, state = OPERATION_STATE[r["operation"]]
        steps.append({"step_no": n, "phase": phase, "system_id": r["system_id"], "resource_id": r["resource_id"],
                      "operation": r["operation"], "state": state, "evidence_id": r["evidence_id"]})
    result.steps = steps
    result.findings = findings
    result.summary = {"systems_checked": len(used_systems), "findings_count": len(findings),
                      "remediation_count": sum(1 for s in steps if s["phase"] == "REMEDIATION"),
                      "verification_count": sum(1 for s in steps if s["phase"] == "VERIFICATION")}
    cited = sorted({s["evidence_id"] for s in steps if s["evidence_id"]})
    result.evidence = [{"evidence_id": e, "file_path": ec.ctx.manifest[e]["file_path"],
                        "captured_at": ec.ctx.manifest[e]["captured_at"]} for e in cited if e in ec.ctx.manifest]
    result.identities[0]["matched_evidence"] = cited
    nodes = [{"id": f"user:{subject.user_id}", "type": "subject", "label": subject.name}]
    edges = []
    for d in decisions:
        nodes.append({"id": d.resource_id, "type": d.category, "system": d.system_id,
                      "status": "COMPLIANT" if d.compliant else "VIOLATION", "label": d.resource_id})
        edges.append({"source": f"user:{subject.user_id}", "target": d.resource_id,
                      "relation": "inferred_from_activity" if d.resource_id in inferred else "identifier_match"})
    result.graph_data = {"nodes": nodes, "edges": edges}
    return result
