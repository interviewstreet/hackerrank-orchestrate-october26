"""Links that only the activity stream can provide.

Two kinds of resources never carry the subject's identifiers in evidence:

* the primary account once it is deleted (a 404 lookup has no profile), and
* records already anonymized or redacted by the deletion worker.

For those, the activity stream is the only bridge. The deletion worker processes a
request about an hour before the workflow reports its status, so its activity rows sit
in a window around `reported_at`. Several requests often share one reporting batch, so
the matching is done globally: evidence links are fixed first, every resource is given
to at most one case, and the remaining ambiguity is resolved with the batch's timing
signature (each case's policy actions are scheduled on a fixed cadence, so they share a
sub-minute phase).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from .evidence import prefix_of

STATUS_RESULT = {"COMPLETE": "SUCCESS", "PARTIALLY_COMPLETE": "PARTIAL", "NOT_STARTED": "FAILED"}
POLICY_EVENTS = {"ANONYMIZE_RECORD", "REDACT_RECORD", "DISABLE_DATA_FLOW", "BLOCK_RESTORE",
                 "RETAIN_RECORD", "DELETE_RECORD", "CHECK_DATA_FLOW", "CHECK_RESTORE_ACCESS"}


STORY_MARKERS = ("reported the requested operation", "completed some internal work",
                 "stopped after the target system")


def is_story(activity: dict) -> bool:
    """Hand-entered workflow notes use a different wording from the batch worker."""
    return any(m in activity["details"] for m in STORY_MARKERS)


def _phase(seconds: float) -> float:
    return seconds % 30


def _phase_dist(a: float, b: float) -> float:
    d = abs(a - b) % 30
    return min(d, 30 - d)


class ActivityLinker:
    def __init__(self, auditor):
        from .engine import ts
        self.ts = ts
        self.a = auditor
        self.links = defaultdict(dict)  # case_id -> {resource_id: [(activity_id, reason)]}
        self.case_story = {}  # case_id -> whether its deletion activity is a hand-entered note

    def links_for(self, cid):
        return self.links.get(cid, {})

    def assign(self):
        self._assign_accounts()
        self._assign_unlinked_policy_resources()

    # ------------------------------------------------------------ accounts

    def _assign_accounts(self):
        ts = self.ts
        acts = [x for x in self.a.activity
                if x["event_type"] == "DELETE_RECORD" and x["target_system"] == "account_service"]
        non_deletion = {x["resource_id"] for x in self.a.activity if x["event_type"] == "CLASSIFY_REQUEST"}
        owner = {}
        for cid, c in self.a.cases.items():
            for rid in c["links"]:
                if prefix_of(rid) == "account":
                    owner.setdefault(rid, set()).add(cid)
        pairs = []
        for cid, c in self.a.cases.items():
            if any(prefix_of(r) == "account" for r in c["links"]):
                continue
            req = c["req"]
            rep = ts(req["reported_at"])
            want = STATUS_RESULT.get(req["reported_status"])
            for x in acts:
                t = ts(x["event_time"])
                if not (rep - timedelta(hours=2) <= t <= rep + timedelta(minutes=15)):
                    continue
                rid = x["resource_id"]
                if rid in non_deletion or (rid in owner and cid not in owner[rid]):
                    continue
                score = 20 * (x["reported_result"] == want)
                # a case that is otherwise compliant is proven by an absent lookup of its
                # account; an incomplete case's account is typically never looked up
                observed_absent = any(o.state == "ABSENT" and self.a.in_window(o, ts(req["requested_at"]), ts(req["audit_at"]))
                                      for o in self.a.obs_by_res.get(rid, []))
                observed_any = bool(self.a.obs_by_res.get(rid))
                if c.get("prelim_complete"):
                    score += 5 * observed_absent
                else:
                    score += 5 * (not observed_any)
                score -= abs((t - rep).total_seconds() + 3600) / 7200
                pairs.append((score, cid, rid, x["activity_id"]))
        pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
        taken_case, taken_res = set(), set(owner)
        for score, cid, rid, aid in pairs:
            if cid in taken_case or rid in taken_res:
                continue
            taken_case.add(cid)
            taken_res.add(rid)
            self.links[cid][rid] = [(aid, "account deletion activity for this request")]
            self.case_story[cid] = is_story(next(x for x in acts if x["activity_id"] == aid))

    # ------------------------------------------------------------ unlinked policy targets

    def _assign_unlinked_policy_resources(self):
        ts = self.ts
        identified = {o.resource_id for o in self.a.obs if o.idents} | set(self.a.activity_links)
        pol = [x for x in self.a.activity
               if x["source_system"] == "deletion_worker" and x["event_type"] in POLICY_EVENTS
               and x["target_system"] != "account_service"]
        # phase signature of each case, from its evidence-linked policy actions
        sig = defaultdict(list)
        for cid, c in self.a.cases.items():
            rep = ts(c["req"]["reported_at"])
            for x in pol:
                if x["resource_id"] in c["links"]:
                    d = (ts(x["event_time"]) - rep).total_seconds()
                    if -2400 < d < 9000:
                        sig[cid].append(_phase(d))
        ambiguous = []
        for x in pol:
            rid = x["resource_id"]
            if rid in identified:
                continue
            t = ts(x["event_time"])
            cands = []
            for cid, c in self.a.cases.items():
                rep = ts(c["req"]["reported_at"])
                d = (t - rep).total_seconds()
                story = is_story(x)
                if cid in self.case_story and self.case_story[cid] != story:
                    continue
                if (story and abs(d) <= 900) or (not story and -2400 < d < 9000):
                    if t <= ts(c["req"]["audit_at"]):
                        cands.append((cid, d))
            if not cands:
                continue
            known = [(min(_phase_dist(_phase(d), s) for s in sig[cid]), cid)
                     for cid, d in cands if sig.get(cid)]
            close = sorted(k for k in known if k[0] <= 1.5)
            if close:
                self._give(close[0][1], rid, x)
                continue
            unknown = sorted(cid for cid, d in cands if not sig.get(cid))
            if len(unknown) == 1:
                self._give(unknown[0], rid, x)
            elif unknown:
                ambiguous.append((x, unknown))
        # ties: spread resources over the candidate cases, one per category per case
        for x, unknown in ambiguous:
            p = prefix_of(x["resource_id"])
            free = [c for c in unknown if not any(prefix_of(r) == p for r in self.links[c])]
            self._give((free or unknown)[0], x["resource_id"], x)

    def _give(self, cid, rid, x):
        self.links[cid].setdefault(rid, []).append((x["activity_id"], "policy action in this request's batch"))
