"""Step 4: the state of each resource at audit_at, and the file that proves it."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Observation
from ..parsers.base import _SEVERITY, system_for
from ..tables.context import Context


_CATEGORY_BY_SYSTEM = {"account_service": "USER_PROFILE"}


@dataclass(frozen=True)
class ResourceState:
    system_id: str
    resource_id: str
    category: str
    result: str
    evidence_id: str          # file that proves the state; "" when no eligible evidence
    retention_until: str | None
    source: str               # "observation" | "scope" | "activity" | "none"


def state_at(ctx: Context, resource_id: str, audit_at: str, use_scope: bool = True) -> ResourceState | None:
    history = ctx.obs_by_resource.get(resource_id, [])
    if not history:
        return _unobserved(ctx, resource_id, audit_at, use_scope)
    return _observed(ctx, resource_id, history, audit_at, use_scope)


def _unobserved(ctx: Context, resource_id: str, audit_at: str, use_scope: bool) -> ResourceState | None:
    """A resource known only from the activity stream (a window-linked account, say).

    A covering snapshot captured before audit_at proves it absent; otherwise its state is unknown
    and only a verification without evidence can be emitted.
    """
    system = system_for(resource_id)
    category = _CATEGORY_BY_SYSTEM.get(system)
    if not system or category is None:
        return None
    if use_scope:
        absent_at, absent_file = "", ""
        for eid, entries in ctx.scopes.items():
            if ctx.files[eid].captured_at > audit_at:
                continue
            for sys_id, at in entries:
                if sys_id == system and (at, eid) > (absent_at, absent_file):
                    absent_at, absent_file = at, eid
        if absent_file:
            return ResourceState(system, resource_id, category, "NOT_FOUND", absent_file, None, "scope")
    return ResourceState(system, resource_id, category, "NOT_FOUND", "", None, "activity")


def _observed(ctx: Context, resource_id: str, history: list, audit_at: str, use_scope: bool) -> ResourceState:
    """Newest eligible observation (file captured at or before audit_at) wins.

    Silence is weaker than an explicit observation: a snapshot that covers the resource's system
    but omits the resource proves absence only when no eligible file observes the resource at all
    (labeled cases 05 and 21 confirm an explicit row is never overridden by an omission).
    Returns None when the resource was never observed at all.
    """
    eligible = [o for o in history if o.captured_at <= audit_at]
    known = history[-1]  # for system/category when nothing eligible
    best: Observation | None = None
    for o in eligible:
        if best is None or (o.observed_at, _SEVERITY.get(o.result, 0)) >= (best.observed_at, _SEVERITY.get(best.result, 0)):
            best = o

    if best is not None:
        return ResourceState(best.system_id, resource_id, best.category, best.result,
                             best.evidence_id, best.retention_until, "observation")
    # Observed only in files captured after audit_at: the link is valid, the state is not citable.
    return ResourceState(known.system_id, resource_id, known.category, known.result, "",
                         known.retention_until, "none")
