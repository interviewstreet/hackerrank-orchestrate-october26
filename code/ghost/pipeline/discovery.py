"""Step 3: which resources belong to this person.

Link view: any observation, in any file at any time, whose subjects include one of the person's
identifiers. Later files may establish the link; they are never cited for state (step 4).
"""
from __future__ import annotations

from ..models import Request, Subject
from ..tables.context import Context


def linked_resources(ctx: Context, subject: Subject, since: str = "", until: str = "9999") -> set[str]:
    """Resources tied to the person by an identifier in any observation.

    A not-found result carries only the key that was looked up, so it links the person to that
    resource id only when the lookup happened after the request (`since`): an older miss says
    nothing about who owned the id (sample case_17: a March lookup, an August request).
    A data-catalog link documents one investigation, so it counts only inside the case's own
    [request, audit] window (sample cases 03, 07, 17 exclude catalog links from other months).
    """
    found: set[str] = set()
    for identifier in subject.identifiers:
        for o in ctx.obs_by_subject.get(identifier, ()):
            if o.result == "NOT_FOUND" and o.observed_at < since:
                continue
            found.add(o.resource_id)
        for at, rid in ctx.catalog_by_identifier.get(identifier, ()):
            if since <= at <= until:
                found.add(rid)
    # A restore from one of the person's backups recreates data: the restored copy is theirs too.
    for edge in ctx.restores:
        if edge.backup_id in found and edge.event_time <= until:
            found.add(edge.resource_id)
    return found


def discover(ctx: Context, request: Request, subject: Subject, linkage=None) -> tuple[set[str], list[str]]:
    """Return (resource_ids, notes): identifier links plus window links from the global linkage."""
    found = linked_resources(ctx, subject, since=request.requested_at, until=request.audit_at)
    if linkage is None:
        return found, []
    extra, notes = linkage.for_case(request.case_id)
    return found | extra, list(notes)
