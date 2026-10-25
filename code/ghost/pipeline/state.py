"""Step 4: the state of each resource at audit_at, and the file that proves it."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Observation
from ..parsers.base import _SEVERITY
from ..tables.context import Context


@dataclass(frozen=True)
class ResourceState:
    system_id: str
    resource_id: str
    category: str
    result: str
    evidence_id: str          # file that proves the state; "" when no eligible evidence
    retention_until: str | None
    source: str               # "observation" | "scope" | "none"


def state_at(ctx: Context, resource_id: str, audit_at: str, use_scope: bool = True) -> ResourceState | None:
    """Newest eligible observation (file captured at or before audit_at) wins.

    Silence is weaker than an explicit observation: a snapshot that covers the resource's system
    but omits the resource proves absence only when no eligible file observes the resource at all
    (labeled cases 05 and 21 confirm an explicit row is never overridden by an omission).
    Returns None when the resource was never observed at all.
    """
    history = ctx.obs_by_resource.get(resource_id, [])
    if not history:
        return None
    eligible = [o for o in history if o.captured_at <= audit_at]
    known = history[-1]  # for system/category when nothing eligible
    best: Observation | None = None
    for o in eligible:
        if best is None or (o.observed_at, _SEVERITY.get(o.result, 0)) >= (best.observed_at, _SEVERITY.get(best.result, 0)):
            best = o

    if best is not None:
        return ResourceState(best.system_id, resource_id, best.category, best.result,
                             best.evidence_id, best.retention_until, "observation")

    absent_at, absent_file = "", ""
    if use_scope:
        seen_files = {o.evidence_id for o in history}
        for eid, entries in ctx.scopes.items():
            if eid in seen_files or ctx.files[eid].captured_at > audit_at:
                continue
            for system, at in entries:
                if system == known.system_id and at > absent_at:
                    absent_at, absent_file = at, eid

    if absent_file:
        return ResourceState(known.system_id, resource_id, known.category, "NOT_FOUND",
                             absent_file, None, "scope")
    return ResourceState(known.system_id, resource_id, known.category, known.result, "",
                         known.retention_until, "none")
