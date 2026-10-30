"""audit_case(case, ctx) -> CaseResult: the per-case decision procedure of SPEC §5."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..evidence import ocr
from ..evidence.records import system_for
from ..evidence.store import ObservationStore
from ..identity import IdentityResolver, Subject
from ..intent import DELETE, IntentLabel
from ..models import Activity, Case, CaseResult, Kind, Observation, Step
from .linking import Linker, assign_workflows
from .planner import ResourcePlan, build_steps
from .policy import Policy
from .state import ResourceState, reconstruct

log = logging.getLogger(__name__)

# Systems whose records only need an existence check when inferring absence from a full snapshot.
IMPLICIT_ABSENCE_TREATMENTS = {"DELETE"}


# Safety margin for the earlier-lifecycle rule: a leftover seen recently is always reported (a missed leftover is a
# false COMPLETE, the costliest error), even if it was last seen during an earlier request of the same person.
EARLIER_LIFECYCLE_MIN_AGE = timedelta(days=90)


@dataclass
class AuditContext:
    store: ObservationStore
    resolver: IdentityResolver
    policy: Policy
    linker: Linker
    intents: dict[str, IntentLabel]
    workflows: dict[str, Activity | None] = field(default_factory=dict)
    subjects: dict[str, Subject] = field(default_factory=dict)
    direct: dict[str, dict] = field(default_factory=dict)

    def prepare(self, cases: list[Case]) -> None:
        """Resolve subjects and assign deletion workflows across every known request at once."""
        items = []
        self._requests_by_user: dict[str, list[Case]] = {}
        for c in cases:
            s = self.resolver.resolve(c.email, c.requested_at) or self.resolver.bare_subject(c.email)
            self.subjects[c.case_id] = s
            self.direct[c.case_id] = self.linker.direct_resources(s, c.audit_at)
            items.append((c, s, self.direct[c.case_id]))
            if s.user_id:
                self._requests_by_user.setdefault(s.user_id, []).append(c)
        self._items = items
        self._by_cutoff: dict = {}

    def earlier_audit(self, case: Case, subject: Subject) -> datetime | None:
        """audit_at of the subject's latest earlier deletion request that was audited before this one was made."""
        prev = [p.audit_at for p in getattr(self, "_requests_by_user", {}).get(subject.user_id or "", [])
                if p.case_id != case.case_id and p.audit_at <= case.requested_at]
        return max(prev) if prev else None

    def workflow_for(self, case: Case) -> Activity | None:
        """The deletion workflow of `case`, from an assignment computed with information up to its audit_at."""
        key = case.audit_at
        if key not in self._by_cutoff:
            self._by_cutoff[key] = assign_workflows(self.linker, self._items, cutoff=key)
        return self._by_cutoff[key].get(case.case_id)


def _implicit_absences(store: ObservationStore, system_id: str, resource_id: str, audit_at: datetime) -> list[Observation]:
    out = []
    for cov in store.coverage:
        if cov.system_id == system_id and cov.captured_at <= audit_at and resource_id not in cov.present:
            out.append(Observation(cov.evidence_id, cov.captured_at, cov.captured_at, system_id, resource_id,
                                   Kind.ABSENT, None, frozenset(), "snapshot", {}, explicit=False))
    return out


def _last_seen(observations: list[Observation], audit_at: datetime) -> datetime:
    seen = [o.captured_at for o in observations if o.captured_at <= audit_at]
    return max(seen) if seen else datetime.min.replace(tzinfo=audit_at.tzinfo)


def _category(observations: list[Observation], audit_at: datetime) -> str | None:
    cats = [o.category for o in observations if o.captured_at <= audit_at and o.category]
    if "SUPPORT_ATTACHMENT" in cats:
        return "SUPPORT_ATTACHMENT"
    if "MARKETING_PROFILE" in cats:
        return "MARKETING_PROFILE"
    for c in cats:
        if c not in {"DATA_FLOW"}:
            return c
    return None


def audit_case(case: Case, ctx: AuditContext) -> CaseResult:
    label = ctx.intents.get(case.request_text)
    trace: dict = {"case_id": case.case_id, "intent": label.__dict__ if label else None}
    if label is not None and label.label != DELETE:
        return CaseResult(case.case_id, "NOT_APPLICABLE", [], trace)

    subject = ctx.subjects.get(case.case_id) or ctx.resolver.resolve(case.email, case.requested_at) \
        or ctx.resolver.bare_subject(case.email)
    direct = ctx.direct.get(case.case_id) or ctx.linker.direct_resources(subject, case.audit_at)
    trace["subject"] = {"user_id": subject.user_id, "identifiers": sorted(f"{k}:{v}" for k, v in subject.identifiers)}

    owned: dict[str, str] = {rid: "identifier" for rid in direct}
    workflow = ctx.workflow_for(case)
    account_id = None
    if workflow is not None:
        account_id = workflow.resource_id
        owned.setdefault(account_id, "workflow")
        for st in ctx.linker.workflow_steps(workflow, subject, case.audit_at):
            owned.setdefault(st.resource_id, "workflow")
    trace["workflow"] = workflow.activity_id if workflow else None

    # A record not observed since the audit of the same person's earlier deletion request, and not for months,
    # belongs to that request's lifecycle: nothing about it was seen during this one.
    earlier = ctx.earlier_audit(case, subject)
    plans: list[ResourcePlan] = []
    for rid in sorted(owned):
        observations = ctx.store.by_resource(rid)
        system_id = _system_of(rid, observations, case.audit_at)
        if system_id == "unknown":
            continue
        category = _category(observations, case.audit_at)
        state = reconstruct(observations, case.audit_at)
        decision = ctx.policy.decide(system_id, category, state.attrs, case.audit_at)
        if decision.treatment in IMPLICIT_ABSENCE_TREATMENTS and state.kind is None:
            # absence inferred from a full snapshot is only a fallback when nothing explicit observed the record
            state = reconstruct(observations + _implicit_absences(ctx.store, system_id, rid, case.audit_at), case.audit_at)
        if system_id == "account_service":
            # one primary profile per request: other directly linked accounts only matter if still present
            if account_id and rid != account_id and state.kind != Kind.PRESENT:
                continue
            if state.kind is None:
                # nothing observed it: the deletion is only the workflow's claim, so the absence is unproven (an
                # uncited post-remediation check in an INCOMPLETE case, never cited proof of a COMPLETE one)
                state = ResourceState(Kind.ABSENT, "")
        if state.kind is None:
            continue
        last = _last_seen(observations, case.audit_at)
        if system_id != "account_service" and earlier is not None and last <= earlier \
                and last < case.requested_at - EARLIER_LIFECYCLE_MIN_AGE:
            trace.setdefault("earlier_lifecycle", []).append(rid)
            continue
        state.category = category
        plans.append(ResourcePlan(system_id, rid, decision, state, owned[rid]))

    if not plans:
        return _no_resource(case, ctx, subject, direct, trace)

    if any(not p.compliant for p in plans):
        planned = {p.resource_id for p in plans}
        for rid, obs in sorted(ctx.linker.late_retained(subject, case.audit_at).items()):
            if rid in planned or any(o.captured_at <= case.audit_at for o in ctx.store.by_resource(rid)):
                continue
            system_id = _system_of(rid, obs, None)
            category = next((o.category for o in obs if o.category), None)
            decision = ctx.policy.decide(system_id, category, {}, case.audit_at)
            if decision.treatment != "RETAIN":
                continue
            plans.append(ResourcePlan(system_id, rid, decision, ResourceState(Kind.RETAINED, "", category=category),
                                      "late_export"))

    status, steps = build_steps(plans)
    if status == "COMPLETE":
        _flag_unverified(case, ctx, trace, subject, [p.resource_id for p in plans])
    trace["resources"] = [
        {"system_id": p.system_id, "resource_id": p.resource_id, "link": p.link, "category": p.decision.category,
         "treatment": p.decision.treatment, "rule_id": p.decision.rule_id, "state": p.state.kind.value,
         "evidence_id": p.state.evidence_id, "decided_by": p.state.decided_by, "compliant": p.compliant}
        for p in plans
    ]
    return CaseResult(case.case_id, status, steps, trace)


def _system_of(rid: str, observations: list, as_of) -> str:
    """The system a resource lives in: its id prefix, else the system its own evidence names (an origin_system
    column, a log line's service) for resource ids outside the known prefixes."""
    system_id = system_for(rid)
    if system_id != "unknown":
        return system_id
    named = sorted({o.system_id for o in observations if o.system_id != "unknown" and o.location != "activity"
                    and (as_of is None or o.captured_at <= as_of)})
    return named[0] if named else "unknown"


def _flag_unverified(case: Case, ctx: AuditContext, trace: dict, subject: Subject, resource_ids=()) -> None:
    """A COMPLETE verdict is only as good as the evidence that was read: evidence captured during the request
    (requested_at..audit_at) whose contents are unknown (an unreadable screenshot/PDF) could hold a leftover copy.
    The verdict is kept (there is no finding to report) but marked, counted in the run summary, and makes the run
    exit 4 unless GDA_STRICT_EVIDENCE=0.

    When OCR text of such a file exists and shows none of the subject's identifiers and none of their resource
    ids, the file is about somebody else and is not counted. With no OCR text every request in the window counts."""
    values = [v for _, v in sorted(subject.identifiers)] + list(resource_ids)
    unread = []
    for fid, at in sorted(ctx.store.unreadable):
        if not case.requested_at <= at <= case.audit_at:
            continue
        text = ctx.store.unread_text.get(fid)
        if text and text.strip() and not ocr.mentions(text, values):
            trace.setdefault("unread_evidence_about_others", []).append(fid)
            continue
        unread.append(fid)
    if unread:
        trace["unverified_evidence"] = unread


def _no_resource(case: Case, ctx: AuditContext, subject: Subject, direct: dict, trace: dict) -> CaseResult:
    """Defined behaviour when no resource of the subject is observable at audit_at.

    The deletion was authorized and the evidence shows nothing remaining, so the case is COMPLETE with no steps:
    there is no proof to cite. A profile deletion in the request window is only the workflow's claim (it may even
    report FAILED, or belong to another request), so it is recorded in the trace but never cited as proof of
    absence. NOT_APPLICABLE is reserved for requests that do not authorize deletion."""
    cands = ctx.linker.workflow_candidates(case, subject, direct, ctx.linker.lead_range, case.audit_at)
    if cands:
        acc = cands[0][1]
        trace["unproven_workflow"] = f"{acc.activity_id} {acc.resource_id} {acc.reported_result} (a claim, not cited)"
    trace["note"] = "no observable resource of the subject"
    log.warning("%s: authorized deletion with no observable footprint; COMPLETE without steps", case.case_id)
    _flag_unverified(case, ctx, trace, subject)
    return CaseResult(case.case_id, "COMPLETE", [], trace)
