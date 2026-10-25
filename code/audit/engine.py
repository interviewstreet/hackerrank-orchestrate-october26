"""Deterministic audit engine: identity -> linked resources -> state at audit_at -> steps."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .data import IdentityIndex, read_csv
from .evidence import (RESOURCE_RE, RETAINED_CATEGORIES, Observation, category_of, extract_idents, parse_all,
                       system_of)

FIND_ORDER = ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK"]
REM_ORDER = ["DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD"]
VER_ORDER = ["VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED",
             "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED"]
OP_STATE = {
    "REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED", "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED", "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT", "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED", "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED", "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

# treatment -> (finding op, remediation op, verification op)
TREATMENT_OPS = {
    "DELETE": ("REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
    "REDACT": ("REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
    "ANONYMIZE": ("REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
}


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class ResourceView:
    system_id: str
    resource_id: str
    category: str
    state: str = "UNKNOWN"
    evidence_id: str = ""
    observed_at: str = ""
    via: list = field(default_factory=list)  # why it is linked to the subject


@dataclass
class CaseResult:
    case_id: str
    status: str
    steps: list
    user_id: str | None = None
    resources: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


class Auditor:
    def __init__(self, dataset: Path, visual_facts: dict | None = None):
        self.dataset = dataset
        self.rules = read_csv(dataset / "deletion_rules.csv")
        self.treatment = {r["data_category"]: r["required_action"] for r in self.rules}
        self.treatment.setdefault("SECONDARY_IDENTIFIER", "DELETE")
        self.ids = IdentityIndex(read_csv(dataset / "user_identities.csv"),
                                 read_csv(dataset / "user_audit_log.csv"))
        self.activity = read_csv(dataset / "system_activity.csv")
        self.obs, self.unparsed = parse_all(dataset, visual_facts)
        self.coverage = [o for o in self.obs if o.category == "COVERAGE"]
        self.obs = [o for o in self.obs if o.category != "COVERAGE"]
        self.obs_by_res = defaultdict(list)
        for o in self.obs:
            self.obs_by_res[o.resource_id].append(o)
        self.ident_to_res = defaultdict(set)
        for o in self.obs:
            for i in o.idents:
                self.ident_to_res[i].add(o.resource_id)
        self._link_activity_identities()
        # full SQL snapshots: file -> (capture time, systems with rows)
        self.sql_snapshots = {}
        manifest = {r["file_id"]: r for r in read_csv(dataset / "evidence_files.csv")}
        for o in self.obs:
            if manifest[o.file_id]["file_path"].endswith(".sql"):
                entry = self.sql_snapshots.setdefault(o.file_id, (o.available_at, set()))
                entry[1].add(o.system_id)

    # ------------------------------------------------------------ linking

    def _link_activity_identities(self):
        """LINK_RESOURCE_IDENTITY activity rows tie a resource to an email and a user id."""
        self.activity_links = defaultdict(list)  # resource -> [(activity_id, time, idents)]
        for a in self.activity:
            if a["event_type"] == "LINK_RESOURCE_IDENTITY" and a["reported_result"] == "SUCCESS":
                self.activity_links[a["resource_id"]].append(
                    (a["activity_id"], a["event_time"], extract_idents(a["details"])))

    def in_window(self, o: Observation, start: datetime, cutoff: datetime) -> bool:
        """Evidence counts for a case if it was captured after the request and by the audit."""
        return ts(o.available_at) <= cutoff and start <= ts(o.observed_at) <= cutoff

    def linked_resources(self, idents: set, requested_at: str, audit_at: str) -> dict:
        """resource_id -> list of reasons, using evidence from the case window."""
        found = defaultdict(list)
        start, cutoff = ts(requested_at), ts(audit_at)
        for o in self.obs:
            if not self.in_window(o, start, cutoff):
                continue
            hit = o.idents & idents
            if hit:
                found[o.resource_id].append((o.file_id, sorted(hit)[0]))
        for rid, links in self.activity_links.items():
            for aid, t, li in links:
                if start <= ts(t) <= cutoff and li & idents:
                    found[rid].append((aid, sorted(li & idents)[0]))
        return found

    def later_links(self, idents: set, requested_at: str, audit_at: str, horizon_days: int = 14) -> dict:
        """Links seen only in evidence exported shortly after the audit. They are never used
        to judge state; they only name resources (the account, retained audit records)
        whose existence is independent of when the export ran."""
        found = defaultdict(list)
        start, cutoff = ts(requested_at), ts(audit_at)
        horizon = cutoff + timedelta(days=horizon_days)
        for o in self.obs:
            if self.in_window(o, start, cutoff):
                continue
            if ts(o.observed_at) < start or ts(o.available_at) > horizon:
                continue
            hit = o.idents & idents
            if hit:
                found[o.resource_id].append((o.file_id, sorted(hit)[0]))
        return found

    # ------------------------------------------------------------ state

    def state_at(self, rid: str, requested_at: str, audit_at: str) -> ResourceView:
        start, cutoff = ts(requested_at), ts(audit_at)
        cands = [o for o in self.obs_by_res.get(rid, []) if self.in_window(o, start, cutoff)]
        view = ResourceView(system_of(rid), rid, category_of(rid))
        if not cands:
            return view
        cands.sort(key=lambda o: (ts(o.observed_at), ts(o.available_at)))
        last_t = ts(cands[-1].observed_at)
        latest = [o for o in cands if ts(o.observed_at) == last_t]
        # among simultaneous observations (primary + replica tables), the worst state wins
        severity = {"PRESENT": 5, "RESTORABLE": 5, "ACTIVE": 5, "RETAINED": 3, "REDACTED": 2,
                    "ANONYMIZED": 2, "DISABLED": 2, "BLOCKED": 2, "ABSENT": 1}
        best = max(latest, key=lambda o: (severity.get(o.state, 0), ts(o.available_at)))
        view.state = best.state
        view.category = self._category(rid, cands)
        view.system_id = best.system_id
        view.evidence_id = best.file_id
        view.observed_at = best.observed_at
        return view

    def _category(self, rid, cands):
        cats = [o.category for o in cands if o.category]
        # specific categories found in evidence beat the prefix default
        for c in reversed(cats):
            if c != category_of(rid):
                return c
        return cats[-1] if cats else category_of(rid)

    # ------------------------------------------------------------ planning

    def plan(self, views: list[ResourceView]):
        findings, rems, vers = [], [], []
        for v in views:
            cat, st = v.category, v.state
            ev = v.evidence_id
            if cat == "DATA_FLOW":
                if st == "ACTIVE":
                    findings.append(("REPORT_ACTIVE_DATA_FLOW", v, ev))
                    rems.append(("DISABLE_DATA_FLOW", v))
                vers.append(("VERIFY_DATA_FLOW_DISABLED", v, ev if st == "DISABLED" else ""))
                continue
            if cat == "BACKUP_ARCHIVE":
                if st == "RESTORABLE":
                    findings.append(("REPORT_RESTORE_RISK", v, ev))
                    rems.append(("BLOCK_RESTORE", v))
                vers.append(("VERIFY_RESTORE_BLOCKED", v, ev if st == "BLOCKED" else ""))
                continue
            treatment = self.treatment.get(cat, "DELETE")
            if treatment == "RETAIN":
                vers.append(("VERIFY_RECORD_PRESENT", v, ev if st in ("RETAINED", "PRESENT") else ""))
                continue
            f_op, r_op, v_op = TREATMENT_OPS[treatment]
            compliant = {"DELETE": ("ABSENT",), "REDACT": ("REDACTED", "ABSENT"),
                         "ANONYMIZE": ("ANONYMIZED", "ABSENT")}[treatment]
            if st == "UNKNOWN" or st in compliant:
                if treatment != "DELETE" and st == "ABSENT":
                    vers.append(("VERIFY_RECORD_ABSENT", v, ev))
                else:
                    vers.append((v_op, v, ev))
            else:
                findings.append((f_op, v, ev))
                rems.append((r_op, v))
                vers.append((v_op, v, ""))
        return findings, rems, vers

    def build_steps(self, findings, rems, vers, complete: bool):
        def key(order):
            return lambda t: (order.index(t[0]), t[1].system_id, t[1].resource_id)
        steps = []
        if not complete:
            for op, v, ev in sorted(findings, key=key(FIND_ORDER)):
                steps.append(("FINDING", v, op, ev))
            for op, v in sorted(rems, key=key(REM_ORDER)):
                steps.append(("REMEDIATION", v, op, ""))
        for op, v, ev in sorted(vers, key=key(VER_ORDER)):
            steps.append(("VERIFICATION", v, op, ev if complete else ""))
        out = []
        for i, (phase, v, op, ev) in enumerate(steps, 1):
            out.append({"step_no": i, "phase": phase, "system_id": v.system_id,
                        "resource_id": v.resource_id, "operation": op,
                        "state": OP_STATE[op], "evidence_id": ev})
        return out

    # ------------------------------------------------------------ case

    def prepare(self, requests: list[dict], intents: dict):
        """Global pass over all deletion cases: resolve identities, evidence links,
        then the activity-only links (account deletions, anonymized records), which
        need all cases at once because several cases share one deletion batch."""
        from .activity_links import ActivityLinker
        self.cases = {}
        for req in requests:
            if not intents.get(req["case_id"], True):
                continue
            ident = self.ids.resolve(req["email"])
            links = self.linked_resources(ident.idents(), req["requested_at"], req["audit_at"]) if ident else {}
            later = self.later_links(ident.idents(), req["requested_at"], req["audit_at"]) if ident else {}
            later = {k: v for k, v in later.items() if k not in links}
            # an account named only by a later export is still this subject's account
            if not any(category_of(r) == "USER_PROFILE" for r in links):
                for rid in [r for r in later if category_of(r) == "USER_PROFILE"]:
                    links[rid] = later.pop(rid)
            self.cases[req["case_id"]] = {"req": req, "ident": ident, "links": links, "later": later}
        for case in self.cases.values():
            req = case["req"]
            views = [self.state_at(rid, req["requested_at"], req["audit_at"]) for rid in case["links"]]
            case["prelim_complete"] = not self.plan(views)[0]
        self.linker = ActivityLinker(self)
        self.linker.assign()

    def audit(self, req: dict, is_deletion: bool) -> CaseResult:
        cid = req["case_id"]
        if not is_deletion:
            return CaseResult(cid, "NOT_APPLICABLE", [])
        case = self.cases[cid]
        ident = case["ident"]
        if not ident:
            return CaseResult(cid, "INCOMPLETE", [], notes=["identity not resolved"])
        links = {k: list(v) for k, v in case["links"].items()}
        for rid, why in self.linker.links_for(cid).items():
            links.setdefault(rid, []).extend(why)
        views = {}
        for rid, why in links.items():
            v = self.state_at(rid, req["requested_at"], req["audit_at"])
            v.via = why
            views[rid] = v
        self.fill_absence_evidence(views, req)
        # a record known only from the activity stream (e.g. a retained legal hold) cites that
        # activity when nothing in the evidence files shows it
        for v in views.values():
            if not v.evidence_id:
                acts = sorted(a for a, _ in v.via if str(a).startswith("activity_"))
                if acts:
                    v.evidence_id = acts[0]
        findings, rems, vers = self.plan(list(views.values()))
        complete = not findings
        if not complete:
            # retained records named by a later export must still be verified as kept
            for rid, why in case["later"].items():
                if category_of(rid) in RETAINED_CATEGORIES and rid not in views:
                    v = ResourceView(system_of(rid), rid, category_of(rid), "RETAINED", "", "", why)
                    views[rid] = v
                    vers.append(("VERIFY_RECORD_PRESENT", v, ""))
        steps = self.build_steps(findings, rems, vers, complete)
        return CaseResult(cid, "COMPLETE" if complete else "INCOMPLETE", steps,
                          user_id=ident.user_id, resources=views)

    def fill_absence_evidence(self, views: dict, req: dict):
        """A record never observed in the window is taken as absent when a full snapshot of
        its system (database dump or collection snapshot) captured in the window omits it."""
        start, cutoff = ts(req["requested_at"]), ts(req["audit_at"])
        covers = [(o.file_id, o.available_at, o.observed_at, o.system_id) for o in self.coverage]
        covers += [(fid, avail, avail, sysid) for fid, (avail, systems) in self.sql_snapshots.items()
                   for sysid in systems]
        for v in views.values():
            if v.state != "UNKNOWN" or v.category != "USER_PROFILE":
                continue
            seen_in = {o.file_id for o in self.obs_by_res.get(v.resource_id, [])}
            best = None
            for fid, avail, t, sysid in covers:
                if sysid != v.system_id or fid in seen_in:
                    continue
                if ts(avail) <= cutoff and start <= ts(t) <= cutoff:
                    if best is None or (ts(t), ts(avail)) > (ts(best[2]), ts(best[1])):
                        best = (fid, avail, t)
            if best:
                v.state, v.evidence_id, v.observed_at = "ABSENT", best[0], best[2]
