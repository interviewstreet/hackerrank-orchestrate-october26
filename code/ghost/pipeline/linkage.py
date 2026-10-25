"""Window linkage: resources whose records no longer name anyone.

A fully deleted account carries no email, so evidence alone cannot tie it to a person. The
deletion worker's activity can: it acted on the account between the request and the report.
Several requests often share a window, so assignment is global over every request (evaluation
and sample files share one activity stream), computed once:

accounts (exactly one per request)
  1. candidates: worker DELETE_RECORD on account_service in [requested_at, reported_at + 15 min]
     whose result matches the reported status (fallback: any result when none matches), and that
     no evidence ties to another person or another request
  2. elimination: a request with one candidate takes it; it leaves every other request's list
  3. remaining conflicts, in (reported_at, case number) order: nearest event to reported_at
     (rounded to the hour), earliest first; every such choice is recorded for review
downstream records (analytics, support, search, tombstones, ...)
  linked only when exactly one request can claim the record and it appears in one of that
  request's own evidence files (measured: guessing here costs more than it gains)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ..config import REPORTED_TO_RESULT
from ..models import Activity, Request, Subject
from ..tables.context import Context
from .discovery import linked_resources

log = logging.getLogger(__name__)

SLACK = timedelta(minutes=15)
_TS = "%Y-%m-%dT%H:%M:%SZ"
_DOWNSTREAM = ("ANONYMIZE_RECORD", "REDACT_RECORD", "DELETE_RECORD")


def _dt(ts: str) -> datetime:
    return datetime.strptime(ts, _TS).replace(tzinfo=timezone.utc)


def _num(case_id: str) -> int:
    tail = case_id.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else 0


@dataclass
class Linkage:
    resources: dict[str, set[str]] = field(default_factory=dict)   # case_id -> extra resources
    notes: dict[str, list[str]] = field(default_factory=dict)      # case_id -> review notes

    def for_case(self, case_id: str) -> tuple[set[str], list[str]]:
        return self.resources.get(case_id, set()), self.notes.get(case_id, [])


def build_linkage(ctx: Context, requests: list[Request], is_deletion) -> Linkage:
    reqs = {r.case_id: r for r in requests if is_deletion(r.request_text)}
    subjects: dict[str, Subject] = {}
    for cid, r in reqs.items():
        s = ctx.resolve_subject(r.email)
        if s is not None:
            subjects[cid] = s
    linked = {cid: linked_resources(ctx, s, since=reqs[cid].requested_at) for cid, s in subjects.items()}
    claimed: dict[str, set[str]] = defaultdict(set)
    for cid, rs in linked.items():
        for rid in rs:
            claimed[rid].add(cid)

    def free(rid: str, cid: str) -> bool:
        others = ctx.owners_of(rid) - {subjects[cid].user_id}
        return not others and not (claimed.get(rid, set()) - {cid})

    def window(cid: str) -> list[Activity]:
        r = reqs[cid]
        end = (_dt(r.reported_at) + SLACK).strftime(_TS)
        return ctx.worker_actions(r.requested_at, end)

    out = Linkage()
    note = lambda cid, msg: out.notes.setdefault(cid, []).append(msg)

    # --- accounts -----------------------------------------------------------------
    cands: dict[str, dict[str, Activity]] = {}
    for cid in subjects:
        if any(x.startswith("account_") for x in linked[cid]):
            continue  # evidence already names this person's account
        events = [a for a in window(cid) if a.event_type == "DELETE_RECORD"
                  and a.target_system == "account_service" and free(a.resource_id, cid)]
        want = REPORTED_TO_RESULT.get(reqs[cid].reported_status)
        matching = [a for a in events if a.result == want] or events
        cands[cid] = {a.resource_id: a for a in matching}

    assigned: dict[str, str] = {}  # account -> case

    def eliminate() -> None:
        changed = True
        while changed:
            changed = False
            for cid, cs in cands.items():
                for k in [k for k in cs if assigned.get(k, cid) != cid]:
                    del cs[k]
                    changed = True
                if len(cs) == 1:
                    k = next(iter(cs))
                    if k not in assigned:
                        assigned[k] = cid
                        changed = True

    eliminate()
    conflicts = sorted((c for c, cs in cands.items() if len(cs) > 1 and c not in assigned.values()),
                       key=lambda c: (reqs[c].reported_at, _num(c)))
    for cid in conflicts:
        cs = {k: a for k, a in cands[cid].items() if k not in assigned}
        if not cs:
            continue
        rep = _dt(reqs[cid].reported_at)
        pick = min(cs, key=lambda k: (round(abs((rep - _dt(cs[k].event_time)).total_seconds()) / 3600),
                                      cs[k].event_time))
        assigned[pick] = cid
        note(cid, f"account {pick} chosen among {sorted(cs)} by time proximity")
        eliminate()

    for account, cid in assigned.items():
        out.resources.setdefault(cid, set()).add(account)
    for cid, cs in cands.items():
        if cid not in assigned.values():
            note(cid, "no account found in the deletion window")

    # --- downstream records -------------------------------------------------------
    claims: dict[str, set[str]] = defaultdict(set)
    for cid, s in subjects.items():
        r = reqs[cid]
        files = {o.evidence_id for i in s.identifiers for o in ctx.obs_by_subject.get(i, ())
                 if o.captured_at <= r.audit_at}
        for a in window(cid):
            rid = a.resource_id
            if (a.event_type not in _DOWNSTREAM or a.target_system == "account_service"
                    or rid in linked[cid] or not free(rid, cid)):
                continue
            if any(o.evidence_id in files for o in ctx.obs_by_resource.get(rid, ())):
                claims[rid].add(cid)
    for rid, cids in claims.items():
        if len(cids) == 1:
            out.resources.setdefault(next(iter(cids)), set()).add(rid)
        else:
            for cid in cids:
                note(cid, f"{rid} also claimable by {sorted(cids - {cid})}, not linked")

    log.info("linkage: %d accounts assigned (%d by proximity), %d downstream records linked",
             len(assigned), sum("proximity" in n for ns in out.notes.values() for n in ns),
             sum(1 for cids in claims.values() if len(cids) == 1))
    return out
