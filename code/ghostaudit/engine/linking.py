"""Ownership: which resources belong to the deletion subject.

1. Direct links: an observation (captured <= audit_at) carries one of the subject's identifiers (current or
   historical email, its sha256, phone, user_id), or a data-catalog LINK activity names them.
2. Workflow links: account deletions and policy actions in `system_activity.csv` rarely carry identifiers.
   A deletion workflow runs inside [requested_at, reported_at]; its later steps follow the profile deletion
   with a fixed sub-minute cadence. The cadence is *learned* from workflows whose account and follow-up
   resources are both directly linked to the same person, then used to attach un-linked steps (a 404 account,
   an already anonymized analytics profile) to the right workflow. Every activity is still only a claim:
   linking says "this resource belongs to the subject", never "this resource is in state X".
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..identity import IdentityResolver, Subject
from ..models import Activity, Case, Kind
from ..evidence.store import ObservationStore

LINK_TYPES = {"email", "email_hash", "user_id", "phone"}
WORKFLOW_HORIZON = timedelta(hours=4)
REPORT_SLACK = timedelta(minutes=10)
READBACK_WINDOW = timedelta(hours=24)  # verification readbacks are captured shortly before the audit   # a workflow may log its last profile write just after reporting
PROFILE_DELETE_MARKERS = ("primary profile", "Target resource: account_")


def is_profile_deletion(a: Activity) -> bool:
    return a.event_type == "DELETE_RECORD" and a.resource_id.startswith("account_") and \
        any(m in a.details for m in PROFILE_DELETE_MARKERS)


def is_workflow_step(a: Activity) -> bool:
    return a.source_system == "deletion_worker" or (a.event_type == "SYNC_RECORD" and a.target_system == "account_service"
                                                    and "checkpoint" in a.details)


@dataclass
class Linker:
    store: ObservationStore
    resolver: IdentityResolver
    activities: list[Activity]
    cadence: dict = field(default_factory=dict)      # step class -> accepted (delta mod 30 s) phases
    spacing: dict = field(default_factory=dict)      # step class -> seconds between consecutive steps
    cadence_hist: Counter = field(default_factory=Counter)
    lead_range: tuple | None = None
    first_phase: dict = field(default_factory=dict)  # step class -> accepted (delta mod 60 s) of 1st step
    model: dict | None = None                         # frozen workflow model (see export_model)

    def __post_init__(self):
        self.profile_deletions = sorted((a for a in self.activities if is_profile_deletion(a)),
                                        key=lambda a: (a.event_time, a.activity_id))
        self.steps = sorted((a for a in self.activities if is_workflow_step(a) and not is_profile_deletion(a)),
                            key=lambda a: (a.event_time, a.activity_id))
        # identifier -> user_ids (for "owned by somebody else" checks)
        self.owner_index: dict = defaultdict(set)
        for uid in self.resolver.identities:
            for ident in self.resolver.subject_for_user(uid).identifiers:
                if ident[0] in LINK_TYPES:
                    self.owner_index[ident].add(uid)
        if self.model:
            self.cadence = {k: set(v) for k, v in self.model["cadence"].items()}
            self.spacing = dict(self.model.get("spacing", {}))
            self.first_phase = {k: set(v) for k, v in self.model.get("first_phase", {}).items()}
            lr = self.model.get("lead_range_minutes")
            self.lead_range = tuple(lr) if lr else None
        else:
            self._learn_cadence()

    def export_model(self) -> dict:
        """The learned workflow model: properties of the deletion worker, not facts about any person."""
        return {
            "cadence": {k: sorted(v) for k, v in sorted(self.cadence.items())},
            "spacing": {k: round(v, 2) for k, v in sorted(self.spacing.items())},
            "first_phase": {k: sorted(v) for k, v in sorted(self.first_phase.items())},
            "lead_range_minutes": [round(x, 2) for x in self.lead_range] if self.lead_range else None,
            "phase_histogram": {f"{c}:{p}": n for (c, p), n in sorted(self.cadence_hist.items())},
        }

    # ---------- direct links ----------
    def owners(self, resource_id: str, as_of: datetime | None) -> set[str]:
        out: set[str] = set()
        for o in self.store.by_resource(resource_id):
            if as_of is not None and o.captured_at > as_of:
                continue
            for ident in o.identifiers:
                if ident[0] in LINK_TYPES:
                    out |= self.owner_index.get(ident, set())
        return out

    def direct_resources(self, subject: Subject, as_of: datetime) -> dict[str, set[str]]:
        found: dict[str, set[str]] = defaultdict(set)
        for ident in sorted(subject.identifiers):
            if ident[0] not in LINK_TYPES:
                continue
            for o in self.store.by_identifier(*ident):
                if o.captured_at <= as_of:
                    found[o.resource_id].add(o.evidence_id)
        # recreation edges: a flow/backup that repopulated an owned resource is part of the subject's footprint
        for rid in list(found):
            for o in self.store.by_resource(rid):
                if o.captured_at <= as_of and o.attrs.get("_recreated_by"):
                    found[o.attrs["_recreated_by"]].add(o.evidence_id)
        return found

    def late_retained(self, subject: Subject, as_of: datetime) -> dict[str, list]:
        """Retained records of the subject known only from a file exported after `as_of` whose own snapshot
        time is at or before it. Such a record existed at the audit, but the file cannot be cited, so it may
        only add an uncited post-remediation check to an INCOMPLETE case (never a finding or a verdict)."""
        found: dict[str, list] = defaultdict(list)
        for ident in sorted(subject.identifiers):
            if ident[0] not in LINK_TYPES:
                continue
            for o in self.store.by_identifier(*ident):
                if o.captured_at > as_of and o.observed_at <= as_of and o.kind == Kind.RETAINED:
                    found[o.resource_id].append(o)
        return found

    # ---------- workflow cadence ----------
    @staticmethod
    def phase(delta: timedelta) -> int:
        return int(delta.total_seconds()) % 30

    @staticmethod
    def step_class(a: Activity) -> str:
        return "policy" if a.details.startswith("Policy action completed") else "result"

    def _learn_cadence(self):
        hist: Counter = Counter()
        gaps: dict = defaultdict(Counter)
        for acc in self.profile_deletions:
            owners = self.owners(acc.resource_id, None)
            if len(owners) != 1:
                continue
            same = [st for st in self._following(acc) if self.owners(st.resource_id, None) == owners]
            for st in same:
                hist[(self.step_class(st), self.phase(st.event_time - acc.event_time))] += 1
            for cls in ("policy", "result"):
                times = [st.event_time for st in same if self.step_class(st) == cls]
                for a, b in zip(times, times[1:]):
                    gaps[cls][round((b - a).total_seconds())] += 1
        self.cadence_hist = hist
        # minute-phase of the earliest identifiable step of each class (the chain's first step relative to the
        # profile deletion is whole minutes plus a fixed number of seconds)
        first: dict = defaultdict(Counter)
        for acc in self.profile_deletions:
            owners = self.owners(acc.resource_id, None)
            if len(owners) != 1:
                continue
            for cls in ("policy", "result"):
                same = [st for st in self._following(acc) if self.step_class(st) == cls
                        and self.owners(st.resource_id, None) == owners]
                if same:
                    first[cls][int((same[0].event_time - acc.event_time).total_seconds()) % 60] += 1
        for cls, counts in first.items():
            total = sum(counts.values())
            peak = [p for p, n in counts.items() if n >= max(3, 0.1 * total)]
            self.first_phase[cls] = {(p + d) % 60 for p in peak for d in (-1, 0, 1)}
        for cls in ("policy", "result"):
            counts = {p: n for (c, p), n in hist.items() if c == cls}
            total = sum(counts.values())
            peak = [p for p, n in counts.items() if total and n >= max(3, 0.05 * total)]
            self.cadence[cls] = {(p + d) % 30 for p in peak for d in (-1, 0, 1)}
            if gaps[cls]:
                # the most common gap between consecutive steps is the spacing (averaged over +-2 s jitter)
                mode = max(gaps[cls].items(), key=lambda kv: (kv[1], -kv[0]))[0]
                near = [(g, n) for g, n in gaps[cls].items() if abs(g - mode) <= 2]
                self.spacing[cls] = sum(g * n for g, n in near) / sum(n for _, n in near)

    def _following(self, acc: Activity):
        end = acc.event_time + WORKFLOW_HORIZON
        for st in self.steps:
            if acc.event_time < st.event_time <= end:
                yield st

    def in_cadence(self, acc: Activity, step: Activity) -> bool:
        return self.phase(step.event_time - acc.event_time) in self.cadence.get(self.step_class(step), set())

    def on_lattice(self, anchor: Activity, step: Activity) -> bool:
        """Steps of one workflow are whole multiples of the learned spacing apart (+-1.5 s)."""
        sp = self.spacing.get(self.step_class(step))
        if not sp or self.step_class(anchor) != self.step_class(step):
            return True
        d = abs((step.event_time - anchor.event_time).total_seconds())
        k = round(d / sp)
        return abs(d - k * sp) <= 1.5 + 0.5 * k

    # ---------- per-case workflow ----------
    def chain_owners(self, acc: Activity, as_of: datetime) -> Counter:
        """Who the cadence-consistent steps following `acc` belong to (identifier-linked steps only)."""
        votes: Counter = Counter()
        for st in self._following(acc):
            if st.event_time <= as_of and self.in_cadence(acc, st):
                for uid in self.owners(st.resource_id, as_of):
                    votes[uid] += 1
        return votes

    def workflow_candidates(self, case: Case, subject: Subject, direct: dict[str, set[str]],
                            lead_range: tuple[float, float] | None = None,
                            cutoff: datetime | None = None) -> list[tuple[float, Activity]]:
        if not subject.user_id:
            # timing proves nothing about who a deletion belonged to; without a resolved person (an unknown
            # email) no workflow may be attached, so no verdict can rest on timing alone
            return []
        as_of = min(case.audit_at, cutoff) if cutoff else case.audit_at
        lo, hi = case.requested_at, min(case.reported_at + REPORT_SLACK, as_of)
        uid = subject.user_id
        scored = []
        for acc in self.profile_deletions:
            if not (lo <= acc.event_time <= hi):
                continue
            owners = self.owners(acc.resource_id, as_of)
            if owners and uid not in owners:
                continue
            score = 100.0 if uid in owners else 0.0
            votes = self.chain_owners(acc, as_of)
            mine = votes.get(uid, 0)
            others = sum(n for u, n in votes.items() if u != uid)
            if mine:
                score += 20.0 * mine
            elif others:
                score -= 50.0
            # the subject's earliest identifiable step of each class must sit on the chain's first-step phase
            for cls in ("policy", "result"):
                phases = self.first_phase.get(cls)
                own = [st for st in self._following(acc) if st.event_time <= as_of
                       and self.step_class(st) == cls and st.resource_id in direct]
                if phases and own:
                    ok = int((own[0].event_time - acc.event_time).total_seconds()) % 60 in phases
                    score += 15.0 if ok else -15.0
            # a post-deletion readback of exactly this account before the audit is corroborating evidence
            if any(o.explicit and o.location != "activity" and case.reported_at <= o.captured_at <= as_of
                   and as_of - o.captured_at <= READBACK_WINDOW for o in self.store.by_resource(acc.resource_id)):
                score += 8.0
            lead = (case.reported_at - acc.event_time).total_seconds() / 60.0
            if lead_range and lead_range[0] <= lead <= lead_range[1]:
                score += 5.0
            scored.append((score, acc))
        # ties: the workflow closest to the moment the request was reported on
        scored.sort(key=lambda x: (-x[0], abs((case.reported_at - x[1].event_time).total_seconds()), x[1].activity_id))
        return scored

    def workflow_steps(self, acc: Activity, subject: Subject, as_of: datetime) -> list[Activity]:
        """Policy steps of the workflow that started with `acc`, excluding resources owned by someone else."""
        cands = []
        for st in self._following(acc):
            if st.event_time > as_of or not self.in_cadence(acc, st):
                continue
            owners = self.owners(st.resource_id, as_of)
            if owners and subject.user_id not in owners:
                continue
            cands.append((st, subject.user_id in owners))
        anchors = [st for st, mine in cands if mine]
        out = []
        for st, mine in cands:
            if mine:
                out.append(st)
                continue
            # Only a completed policy action can leave a record with nothing to link it by (anonymized / redacted).
            # A failed step leaves identifiers in place, so it must be linked by identifier, never by timing alone.
            if self.step_class(st) != "policy":
                continue
            same_class = [a for a in anchors if self.step_class(a) == self.step_class(st)]
            # one workflow runs one kind of chain: an un-linked step must fit the subject's own steps
            if anchors and not same_class:
                continue
            out.append(st)
        return out


def learn_lead_range(linker: Linker, items) -> tuple[float, float] | None:
    """Minutes between a profile deletion and the workflow's reported_at claim, from cases whose account is
    directly linked to the requester (the 5th-95th percentile band)."""
    leads = []
    for c, s, _ in items:
        if not s.user_id:
            continue
        for acc in linker.profile_deletions:
            if c.requested_at <= acc.event_time <= c.reported_at and s.user_id in linker.owners(acc.resource_id, c.audit_at):
                leads.append((c.reported_at - acc.event_time).total_seconds() / 60.0)
    if len(leads) < 5:
        return None
    leads.sort()
    return leads[int(0.05 * (len(leads) - 1))], leads[int(0.95 * (len(leads) - 1))]


def assign_workflows(linker: Linker, items: list[tuple[Case, Subject, dict]],
                     cutoff: datetime | None = None) -> dict[str, Activity | None]:
    """Global one-to-one assignment of profile-deletion workflows to cases, using only evidence and activity
    available at `cutoff` (so eliminating a workflow never relies on facts newer than the audited case).

    Forced choices (a single candidate) are made first, then the most decisive ones (largest lead over the
    runner-up); each assignment removes that workflow from every other case's candidates."""
    if linker.lead_range is None:
        linker.lead_range = learn_lead_range(linker, items)
    if cutoff is not None:
        items = [(c, s, linker.direct_resources(s, min(c.audit_at, cutoff)) if c.audit_at > cutoff else d)
                 for c, s, d in items if c.requested_at <= cutoff]
    cand = {c.case_id: linker.workflow_candidates(c, s, d, linker.lead_range, cutoff) for c, s, d in items}
    assigned: dict[str, Activity | None] = {}
    taken: set[str] = set()
    pending = dict(cand)
    while pending:
        best = []
        for cid, lst in pending.items():
            avail = [(s, a) for s, a in lst if a.activity_id not in taken]
            if not avail:
                continue
            top = avail[0][0]
            margin = top - avail[1][0] if len(avail) > 1 else float("inf")
            best.append((-margin, -top, cid, avail[0][1]))
        if not best:
            break
        # most decisive first: a forced choice (infinite margin) or the largest lead over the runner-up
        best.sort(key=lambda x: x[:3])
        cid, acc = best[0][2], best[0][3]
        assigned[cid] = acc
        taken.add(acc.activity_id)
        del pending[cid]
    for cid in cand:
        assigned.setdefault(cid, None)
    return assigned
