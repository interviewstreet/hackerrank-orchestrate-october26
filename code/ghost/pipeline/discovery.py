"""Step 3: which resources belong to this person.

Link view: any observation, in any file at any time, whose subjects include one of the person's
identifiers. Later files may establish the link; they are never cited for state (step 4).
"""
from __future__ import annotations

from ..models import Request, Subject
from ..tables.context import Context


def linked_resources(ctx: Context, subject: Subject) -> set[str]:
    found: set[str] = set()
    for identifier in subject.identifiers:
        for o in ctx.obs_by_subject.get(identifier, ()):
            found.add(o.resource_id)
    return found


def discover(ctx: Context, request: Request, subject: Subject, linkage=None) -> tuple[set[str], list[str]]:
    """Return (resource_ids, notes): identifier links plus window links from the global linkage."""
    found = linked_resources(ctx, subject)
    if linkage is None:
        return found, []
    extra, notes = linkage.for_case(request.case_id)
    return found | extra, list(notes)
