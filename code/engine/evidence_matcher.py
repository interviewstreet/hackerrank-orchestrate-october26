"""Evidence matching: which resources belong to the subject, based on identifier evidence usable at audit_at."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from .contracts import Observation
from .evidence_loader import EvidenceStore
from .identity_resolver import Subject


def usable(o: Observation, audit_at: str) -> bool:
    """A fact may be used if the event it describes happened at or before audit_at."""
    return (o.observed_at or o.captured_at) <= audit_at and (o.file_captured_at or o.captured_at) <= audit_at


def citable(o_captured_at: str, audit_at: str) -> bool:
    """Evidence may only be cited if the file itself was captured at or before audit_at."""
    return o_captured_at <= audit_at


def claimed_resources(store: EvidenceStore, subject: Subject, audit_at: str) -> Dict[str, List[str]]:
    """resource_id -> reasons it is tied to the subject (exact identifier matches only)."""
    claims: Dict[str, List[str]] = defaultdict(list)
    if subject.status != "RESOLVED":
        return claims

    def hit(o: Observation, why: str):
        if (o.observed_at or o.captured_at) <= audit_at and why not in claims[o.resource_id]:
            claims[o.resource_id].append(why)

    for e in subject.emails:
        for o in store.by_email.get(e, []):
            hit(o, f"email:{e}")
    for o in store.by_user_ref.get(subject.user_id, []):
        hit(o, f"user_id:{subject.user_id}")
    for h in subject.hashes:
        for o in store.by_hash.get(h, []):
            hit(o, "email_hash")
    # A resource explicitly attributed (user_ref) to someone else is not the subject's, even if a lookalike
    # identifier of the subject is mentioned in some artifact about it.
    for rid in list(claims):
        refs = {u for o in store.by_resource.get(rid, []) for u in o.user_refs}
        if refs and subject.user_id not in refs:
            del claims[rid]
    return dict(claims)


# ---------------------------------------------------------------------------------------------------------------------
# Activity-based inference for resources that carry no identifier at all (404 account lookups, anonymized analytics).
# ---------------------------------------------------------------------------------------------------------------------
from datetime import datetime

_STATUS_TO_RESULT = {"COMPLETE": "SUCCESS", "PARTIALLY_COMPLETE": "PARTIAL", "NOT_STARTED": "FAILED"}


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


class GlobalLinks:
    """resource_id -> the set of users that identifier evidence ties it to (across ALL users)."""

    def __init__(self, ctx, store: EvidenceStore):
        self.owners: Dict[str, Set[str]] = defaultdict(set)
        for o in store.observations:
            ids = list(dict.fromkeys(o.emails + o.links.get("emails", [])))
            for e in ids:
                for u in ctx.historical_email_index.get(e, []):
                    self.owners[o.resource_id].add(u)
            for u in dict.fromkeys(o.user_refs + o.links.get("user_refs", [])):
                if u in ctx.identities:
                    self.owners[o.resource_id].add(u)
            for h in dict.fromkeys(o.hashes + o.links.get("hashes", [])):
                for u in ctx.hash_index.get(h, []):
                    self.owners[o.resource_id].add(u)


def infer_by_activity(ctx, links: GlobalLinks, subject: Subject, request: Dict[str, str], *, event_type: str,
                      target_system: str, before_min: int, after_min: int, match_status: bool) -> List[str]:
    """Worker activities close to reported_at that can be attributed to nobody else. Returns candidate resource ids."""
    rep = _t(request["reported_at"])
    want_result = _STATUS_TO_RESULT.get(request["reported_status"])
    out: List[str] = []
    for a in ctx.activities:
        if a["source_system"] != "deletion_worker" or a["event_type"] != event_type or a["target_system"] != target_system:
            continue
        d = (_t(a["event_time"]) - rep).total_seconds() / 60
        if not (-before_min <= d <= after_min):
            continue
        if match_status and a["reported_result"] != want_result:
            continue
        owners = links.owners.get(a["resource_id"], set())
        if owners and subject.user_id not in owners:
            continue
        if a["resource_id"] not in out:
            out.append(a["resource_id"])
    return out
