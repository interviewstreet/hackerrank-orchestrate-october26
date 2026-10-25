"""Explicit resource facts written into system_activity.csv free text.

LINK_RESOURCE_IDENTITY (data_catalog): "Data catalog linked <rid> (<alias>) to <email> and <user_id>."
  An authoritative person<->resource link, with the alias under which the resource appears in
  documents (a statement number, a file name, a user reference). Each row is written minutes after
  the screenshot or PDF it describes is captured, which pairs documents with their resource.
RESTORE_BACKUP: "Restore job repopulated downstream resource <rid>." A restore recreated data.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ..config import ACTIVITY_CSV
from ..dataset_io import read_csv
from ..identifiers import norm_email

log = logging.getLogger(__name__)

_LINK = re.compile(r"\b(?:linked|confirmed)\s+(\w+)\s+\(([^)]*)\)\s+(?:to|belongs only to)\s+"
                   r"([^\s;,]+@[^\s;,]+?)\s+and\s+(user_\d+)")
_RESTORE = re.compile(r"repopulated downstream resource\s+(\w+)")


@dataclass(frozen=True)
class CatalogLink:
    activity_id: str
    event_time: str
    resource_id: str
    alias: str
    identifiers: tuple[str, ...]
    exclusive: bool          # "belongs only to": attachment owned by the subject alone


@dataclass(frozen=True)
class RestoreEdge:
    activity_id: str
    event_time: str
    backup_id: str
    resource_id: str
    result: str


def build_catalog() -> tuple[list[CatalogLink], list[RestoreEdge]]:
    rows = read_csv(ACTIVITY_CSV, ("activity_id", "event_time", "event_type", "resource_id",
                                   "reported_result", "details"))
    links, restores = [], []
    for r in rows:
        details = r["details"] or ""
        if r["event_type"] == "LINK_RESOURCE_IDENTITY":
            m = _LINK.search(details)
            if not m:
                log.warning("%s: identity link not understood: %.80s", r["activity_id"], details)
                continue
            rid, alias, email, user = m.groups()
            links.append(CatalogLink(r["activity_id"], r["event_time"], rid, alias.strip(),
                                     tuple(sorted({norm_email(email.rstrip(".")), user})),
                                     "belongs only" in details))
        elif r["event_type"] == "RESTORE_BACKUP":
            m = _RESTORE.search(details)
            if m:
                restores.append(RestoreEdge(r["activity_id"], r["event_time"], r["resource_id"],
                                            m.group(1), r["reported_result"]))
    log.info("catalog: %d identity links, %d restore edges", len(links), len(restores))
    return links, restores
