"""Steps 1-6 for one request."""
from __future__ import annotations

import logging

from ..models import CaseResult, Request, Step
from ..tables.context import Context
from .discovery import discover
from .intent import IntentClassifier
from .policy import Policy
from .state import state_at

log = logging.getLogger(__name__)


class CasePipeline:
    def __init__(self, ctx: Context, policy: Policy, intent: IntentClassifier, linkage=None) -> None:
        self.ctx, self.policy, self.intent, self.linkage = ctx, policy, intent, linkage

    def run(self, req: Request) -> CaseResult:
        label, why = self.intent(req.request_text)                       # step 1
        if label != "DELETE":
            return CaseResult(req.case_id, "NOT_APPLICABLE", notes=[f"intent: {why}"])
        notes = [] if why.startswith("rules") else [f"intent: {why}"]

        subject = self.ctx.resolve_subject(req.email)                    # step 2
        if subject is None:
            return CaseResult(req.case_id, "INCOMPLETE", notes=["subject not resolved"])

        resources, disc_notes = discover(self.ctx, req, subject, self.linkage)         # step 3
        notes += disc_notes

        findings, remediations, verifications = [], [], []
        for rid in sorted(resources):
            st = state_at(self.ctx, rid, req.audit_at)                    # step 4
            if st is None:
                notes.append(f"{rid}: never observed")
                continue
            expired = bool(st.retention_until) and st.retention_until < req.audit_at
            t = self.policy.treat(st.category, st.result, expired)        # step 5
            if t is None:
                notes.append(f"{rid}: category {st.category} not in rules")
                continue
            if t.verification is None and not t.violation:
                notes.append(f"{rid}: {st.category} {st.result} needs no step")
                continue
            if t.violation and not st.evidence_id:
                # A finding must cite evidence available at audit_at. Without it the violation is
                # only suspected (seen in later files), so only the end-state check is emitted.
                notes.append(f"{rid}: {st.result} seen only after audit_at, verification only")
            elif t.violation:
                findings.append(Step("FINDING", st.system_id, rid, t.finding, st.evidence_id))
                remediations.append(Step("REMEDIATION", st.system_id, rid, t.remediation))
            verifications.append((Step("VERIFICATION", st.system_id, rid, t.verification, ""),
                                  st.evidence_id))

        if findings:                                                       # step 6
            steps = findings + remediations + [v for v, _ in verifications]
            return CaseResult(req.case_id, "INCOMPLETE", steps, notes)
        steps = [Step(v.phase, v.system_id, v.resource_id, v.operation, ev) for v, ev in verifications]
        missing = [s.resource_id for s in steps if not s.evidence_id]
        if missing:
            notes.append(f"COMPLETE without evidence for {missing}")
        return CaseResult(req.case_id, "COMPLETE", steps, notes)
