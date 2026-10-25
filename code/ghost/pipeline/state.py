"""Step 4: the state of each resource at audit_at, and the file that proves it."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Observation
from ..parsers.base import _SEVERITY, system_for
from ..tables.context import Context


_CATEGORY_BY_SYSTEM = {"account_service": "USER_PROFILE"}
_NO_OMISSION_INFERENCE = frozenset({"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE",
                                    "DATA_FLOW", "ACCOUNT_TOMBSTONE"})


def _latest_covering(ctx: Context, system: str, audit_at: str) -> str:
    """Newest file captured at or before audit_at whose scope covers the system, or ''."""
    best_at, best_file = "", ""
    for eid, entries in ctx.scopes.items():
        if ctx.files[eid].captured_at > audit_at:
            continue
        for sys_id, at in entries:
            if sys_id == system and (at, eid) > (best_at, best_file):
                best_at, best_file = at, eid
    return best_file


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
        absent_file = _latest_covering(ctx, system, audit_at)
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
    # Observed only in files captured after audit_at: those files may link the resource but cannot
    # describe it at audit_at. For deletable records, a covering snapshot taken before audit_at that
    # omits the resource is the citable state. Retained records are never inferred absent from an
    # omission (sample case_30 keeps audit_record_1707 present although an export omits it).
    if use_scope and known.category not in _NO_OMISSION_INFERENCE:
        covering = _latest_covering(ctx, known.system_id, audit_at)
        if covering:
            return ResourceState(known.system_id, resource_id, known.category, "NOT_FOUND",
                                 covering, None, "scope")
    return ResourceState(known.system_id, resource_id, known.category, known.result, "",
                         known.retention_until, "none")
