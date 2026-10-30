"""system_activity.csv -> Observations. Workflow results are claims; only state checks and recreation
events are treated as observations (SPEC §2.3)."""
from __future__ import annotations

import re

from ..identity import norm_identifier
from ..loaders import EMAIL_RE
from ..models import Activity, Kind, Observation
from .records import RESOURCE_RE, USER_RE, system_for

ID = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d+"
# "<job> repopulated downstream resource X." and other wordings of a copy being written back
RECREATED_RE = re.compile(r"\b(?:repopulated|re-?populated|recreated|re-created|re-?indexed|restored|rehydrated|"
                          r"re-?synced)\b(?:\s+(?:the\s+)?(?:downstream|deleted|search|customer))*"
                          r"(?:\s+(?:resource|document|record|entry|profile|copy))?\s+(" + ID + r")\b", re.I)
FLOW_ACTIVE_RE = re.compile(r"\b(?:remains|still|is) (?:enabled|active|running|scheduled)\b", re.I)
RESTORE_OPEN_RE = re.compile(r"\bcan (?:still )?(?:be )?restored?\b|\brestore (?:access )?(?:remains|is still) "
                             r"(?:possible|allowed|open)\b", re.I)
RECREATING_EVENTS = {"SYNC_RECORD", "RESTORE_BACKUP", "INDEX_RECORD", "REINDEX_RECORD", "REFRESH_CACHE"}


def _obs(a: Activity, rid: str, kind: Kind, ids=frozenset(), attrs=None) -> Observation:
    base = {
        "event_type": a.event_type, "reported_result": a.reported_result, "source_system": a.source_system,
        "target_system": a.target_system, "details": a.details,
    }
    if attrs:
        base.update(attrs)
    return Observation(
        evidence_id=a.activity_id,
        observed_at=a.event_time,
        captured_at=a.event_time,
        system_id=system_for(rid, a.target_system),
        resource_id=rid,
        kind=kind,
        category=None,
        identifiers=frozenset(ids),
        location="activity",
        attrs=base,
    )


def extract(activities: list[Activity]) -> list[Observation]:
    out: list[Observation] = []
    for a in activities:
        d = a.details
        rid = a.resource_id
        restore_event = "RESTORE" in a.event_type or d.lower().startswith("restore")
        if a.event_type.startswith("CHECK") and not restore_event and FLOW_ACTIVE_RE.search(d):
            out.append(_obs(a, rid, Kind.FLOW_ACTIVE))
        elif a.event_type.startswith("CHECK") and restore_event and RESTORE_OPEN_RE.search(d):
            out.append(_obs(a, rid, Kind.RESTORE_ALLOWED))
        elif a.event_type in RECREATING_EVENTS and a.reported_result != "FAILED" and (m := RECREATED_RE.search(d)) \
                and m.group(1) != rid:
            downstream = m.group(1)
            src_kind = Kind.RESTORE_ALLOWED if restore_event else Kind.FLOW_ACTIVE
            out.append(_obs(a, rid, src_kind, attrs={"_refs": downstream, "_recreates": downstream}))
            out.append(_obs(a, downstream, Kind.RECREATED, attrs={"_refs": rid, "_recreated_by": rid}))
        elif a.event_type == "LINK_RESOURCE_IDENTITY":
            ids = set()
            for e in EMAIL_RE.findall(d):
                ids.add(norm_identifier("email", e))
            for u in USER_RE.findall(d):
                ids.add(norm_identifier("user_id", u))
            refs = {r for r in RESOURCE_RE.findall(d) if r != rid}
            attrs = {"_refs": " ".join(sorted(refs))} if refs else {}
            if "belongs only to" in d:
                attrs["exclusive_owner"] = "true"
            out.append(_obs(a, rid, Kind.LINK, ids, attrs))
        elif a.event_type == "CLASSIFY_REQUEST":
            out.append(_obs(a, rid, Kind.CLAIM, attrs={"non_deletion": str("non-deletion" in d).lower()}))
        else:
            out.append(_obs(a, rid, Kind.CLAIM))
    return out
