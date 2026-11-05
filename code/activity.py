"""
activity.py — system_activity.csv: claims, links and recreation signals
(owner: Person 3).

Activity rows are *claims*: a reported SUCCESS never proves a resulting state.
They are used for three things only:

1. Explicit identity links. ``LINK_RESOURCE_IDENTITY`` rows say which subject
   a resource belongs to ("Data catalog linked X to <email> and <user_id>").
2. Recreation risks. Rows that report an *observed* ongoing process are state
   signals, not action claims: a connector status check that "confirmed that
   data flow X remains enabled", a restore-access check that "confirmed that
   archive X can still be restored", and connector/restore jobs that
   "repopulated downstream resource Y".
3. Workflow linkage. A deletion workflow names the resources it worked on,
   but de-identified copies (a 404 account lookup, an anonymised analytics
   row) carry no identifier of their own. ``WorkflowLinker`` attributes such
   resources to a request through the request's own workflow window, using a
   deterministic one-resource-per-request assignment across all requests and
   never assigning a resource that evidence ties to a different subject.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from utils import parse_ts

_TARGET_RE = re.compile(r"Target resource:\s*([A-Za-z0-9_\-]+)")
_REPOPULATED_RE = re.compile(r"repopulated downstream resource\s+([A-Za-z0-9_\-]+)", re.I)
_LINK_RE = re.compile(
    r"linked\s+(?P<rid>[A-Za-z0-9_\-]+)\s*\((?P<alias>[^)]*)\)\s+to\s+(?P<email>\S+@\S+?)\s+and\s+(?P<uid>user_\d+)",
    re.I)
_ATTACH_RE = re.compile(
    r"confirmed\s+(?P<rid>[A-Za-z0-9_\-]+)\s*\((?P<alias>[^)]*)\)\s+belongs only to\s+(?P<email>\S+@\S+?)\s+and\s+(?P<uid>user_\d+)",
    re.I)
_FLOW_ENABLED_RE = re.compile(r"data flow\s+(\S+)\s+remains enabled", re.I)
_RESTORABLE_RE = re.compile(r"archive\s+(\S+)\s+can still be restored", re.I)
_NON_DELETION_RE = re.compile(r"non-deletion", re.I)
_SUBMITTED_RE = re.compile(r"submitted primary profile", re.I)
_POLICY_DONE_RE = re.compile(r"Policy action completed for", re.I)

# How long after reported_at a request's own workflow may still be logging.
WORKFLOW_GRACE = timedelta(hours=1)


@dataclass(frozen=True)
class Activity:
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str

    @property
    def target_resource(self) -> Optional[str]:
        m = _TARGET_RE.search(self.details)
        return m.group(1) if m else None

    @property
    def repopulated_resource(self) -> Optional[str]:
        m = _REPOPULATED_RE.search(self.details)
        return m.group(1) if m else None


@dataclass(frozen=True)
class IdentityLink:
    activity_id: str
    event_time: datetime
    system_id: str
    resource_id: str
    alias: str
    email: str
    user_id: str
    subject_only: bool


@dataclass(frozen=True)
class RiskSignal:
    """An observed recreation path: a flow still enabled, an archive still
    restorable, or a job that repopulated a downstream resource."""
    activity_id: str
    event_time: datetime
    kind: str               # "DATA_FLOW" | "BACKUP"
    system_id: str          # system that owns the flow / archive
    resource_id: str        # the flow / archive
    downstream_resource: Optional[str]  # resource it recreated, if stated


class ActivityLog:
    def __init__(self, rows: list[Activity]):
        self.rows = sorted(rows, key=lambda a: (a.event_time, a.activity_id))
        self.by_resource: dict[str, list[Activity]] = defaultdict(list)
        self.links: list[IdentityLink] = []
        self.risks: list[RiskSignal] = []
        self.non_deletion_resources: set[str] = set()
        for a in self.rows:
            self.by_resource[a.resource_id.lower()].append(a)
            if a.target_resource and a.target_resource.lower() != a.resource_id.lower():
                self.by_resource[a.target_resource.lower()].append(a)
            self._index(a)

    @classmethod
    def load(cls, path: str | Path) -> "ActivityLog":
        rows = []
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t = parse_ts(r["event_time"], context=r["activity_id"])
                if t is None:
                    continue
                rows.append(Activity(
                    activity_id=r["activity_id"].strip(), event_time=t,
                    event_type=r["event_type"].strip(), source_system=r["source_system"].strip(),
                    target_system=r["target_system"].strip(), resource_id=r["resource_id"].strip(),
                    reported_result=r["reported_result"].strip().upper(), details=r["details"] or ""))
        return cls(rows)

    def _index(self, a: Activity) -> None:
        if a.event_type == "LINK_RESOURCE_IDENTITY" and a.reported_result == "SUCCESS":
            m = _ATTACH_RE.search(a.details) or _LINK_RE.search(a.details)
            if m:
                self.links.append(IdentityLink(
                    a.activity_id, a.event_time, a.target_system, m.group("rid"),
                    m.group("alias").strip(), m.group("email").rstrip(".,;").lower(),
                    m.group("uid"), subject_only=bool(_ATTACH_RE.search(a.details))))
        if a.event_type == "CLASSIFY_REQUEST" and _NON_DELETION_RE.search(a.details):
            self.non_deletion_resources.add(a.resource_id.lower())
        if a.reported_result != "SUCCESS":
            return
        if a.event_type == "CHECK_DATA_FLOW":
            m = _FLOW_ENABLED_RE.search(a.details)
            if m:
                self.risks.append(RiskSignal(a.activity_id, a.event_time, "DATA_FLOW",
                                             a.target_system, m.group(1).rstrip("."), None))
        elif a.event_type == "CHECK_RESTORE_ACCESS":
            m = _RESTORABLE_RE.search(a.details)
            if m:
                self.risks.append(RiskSignal(a.activity_id, a.event_time, "BACKUP",
                                             a.target_system, m.group(1).rstrip("."), None))
        elif a.repopulated_resource:
            kind = "BACKUP" if a.event_type == "RESTORE_BACKUP" else "DATA_FLOW"
            owner = a.source_system  # the connector / restore job owner
            self.risks.append(RiskSignal(a.activity_id, a.event_time, kind, owner,
                                         a.resource_id, a.repopulated_resource))

    # ----------------------------------------------------------- queries
    def links_for_user(self, user_id: str, audit_at: datetime) -> list[IdentityLink]:
        return [l for l in self.links if l.user_id == user_id and l.event_time <= audit_at]

    def risks_until(self, audit_at: datetime) -> list[RiskSignal]:
        return [r for r in self.risks if r.event_time <= audit_at]

    def for_resource(self, resource_id: str, audit_at: datetime) -> list[Activity]:
        return [a for a in self.by_resource.get(resource_id.lower(), []) if a.event_time <= audit_at]


# --------------------------------------------------------------------------
# workflow linkage
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowCase:
    case_id: str
    user_id: str
    requested_at: datetime
    reported_at: datetime
    audit_at: datetime
    has_account: bool       # identity evidence already names the account
    has_analytics: bool     # identity evidence already names an analytics record
    evidence_files: frozenset = frozenset()  # files holding the subject's own records


ACCOUNT_SLOT = "account"
ANALYTICS_SLOT = "analytics"


def _slot_of(a: Activity) -> Optional[str]:
    """Which kind of de-identified resource a workflow activity names."""
    if a.source_system != "deletion_worker":
        return None
    if a.event_type == "DELETE_RECORD" and a.target_system == "account_service" and (
            _SUBMITTED_RE.search(a.details) or a.target_resource):
        return ACCOUNT_SLOT
    if a.event_type == "ANONYMIZE_RECORD" and a.target_system == "analytics_platform" and (
            _POLICY_DONE_RE.search(a.details) or a.target_resource):
        return ANALYTICS_SLOT
    return None


class WorkflowLinker:
    """Deterministic assignment of workflow-named resources to requests.

    A candidate pair (request, activity) requires:
      * the activity names an account submission or an analytics
        anonymisation (``_slot_of``);
      * it happened inside the request's workflow window
        [requested_at, reported_at + WORKFLOW_GRACE] and before audit_at;
      * the request does not already have that kind of resource from its
        own identifiers;
      * no evidence links the resource to a *different* subject, and the
        resource is not the subject of a non-deletion intake decision.
    Pairs are taken greedily: explicit "Target resource" rows first, then
    resources observed (at or before audit_at) in an evidence file that also
    holds the subject's own identity-matched records — the same read-back
    or export that checked the subject's other systems — then the smallest
    distance to reported_at, ties broken by case and activity id. Each
    request receives at most one resource per slot and each resource goes to
    at most one request.
    """

    def __init__(self, log: ActivityLog, cases: Iterable[WorkflowCase],
                 owners: dict[str, set[str]],
                 resource_files: Optional[dict[str, list[tuple[str, datetime]]]] = None,
                 slots: Optional[set[str]] = None):
        resource_files = resource_files or {}
        self.assignments: dict[str, dict[str, Activity]] = defaultdict(dict)
        self.case_ids: set[str] = set()
        pairs = []
        cases = list(cases)
        self.case_ids = {c.case_id for c in cases}
        for a in log.rows:
            slot = _slot_of(a)
            if slot is None or (slots is not None and slot not in slots):
                continue
            rid = (a.target_resource or a.resource_id).lower()
            if rid in log.non_deletion_resources:
                continue
            for c in cases:
                if slot == ACCOUNT_SLOT and c.has_account:
                    continue
                if slot == ANALYTICS_SLOT and c.has_analytics:
                    continue
                if not (c.requested_at <= a.event_time <= min(c.reported_at + WORKFLOW_GRACE, c.audit_at)):
                    continue
                other = owners.get(rid, set()) - {c.user_id}
                if other:
                    continue
                explicit = 0 if a.target_resource else 1
                files = {f for f, t in resource_files.get(rid, []) if t <= c.audit_at}
                colocated = 0 if files & c.evidence_files else 1
                dist = abs((c.reported_at - a.event_time).total_seconds())
                pairs.append((explicit, colocated, dist, c.case_id, a.activity_id, slot, rid, a))
        pairs.sort(key=lambda p: p[:5])
        used_resources: set[tuple[str, str]] = set()
        for explicit, colocated, dist, case_id, _aid, slot, rid, a in pairs:
            if slot in self.assignments[case_id] or (slot, rid) in used_resources:
                continue
            self.assignments[case_id][slot] = a
            used_resources.add((slot, rid))

    def resources_for(self, case_id: str) -> dict[str, Activity]:
        return dict(self.assignments.get(case_id, {}))

    def merge(self, other: "WorkflowLinker") -> None:
        for case_id, slots in other.assignments.items():
            for slot, act in slots.items():
                self.assignments[case_id].setdefault(slot, act)
