"""
case_timeline.py — a per-case timeline for the website's time-travel slider.

Used only while P3's decide() returns no timeline; once P3 does, its
timeline is saved instead (audit_db.save_case). Display only: nothing here
changes a deletion decision.

Rows use the timeline table's columns (CONTRACTS.md section 2):
    time, system_id, resource_id, event, state_after, evidence_id

Events, all at or before audit_at:
    IDENTITY_CHANGE    user_audit_log change        evidence_id = audit_id   (record)
    DELETION_REQUESTED the request (requested_at)                            (record)
    <event_type>       system_activity.csv row      evidence_id = activity_id (claim)
                       e.g. DELETE_RECORD, SYNC_RECORD; state_after = reported result
    EVIDENCE_PROOF     direct store state from P2   evidence_id = file_id     (proof)
                       (snapshot, SQL row, read-back, document, screenshot)
    EVIDENCE_CLAIM     second-hand lookup ledger    evidence_id = file_id     (claim)
                       (P2 claim_only=True)
    ABSENCE_PROOF      complete snapshot without the resource (P2 absence_proofs) (proof)
    AUDIT              audit_at                                              (record)

Evidence events are placed at the file's captured_at (when the proof
existed). Several observations in the same file are ordered by their own
observed_at, so the last state seen in the file wins.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from utils import parse_ts

PROOF_EVENTS = ("EVIDENCE_PROOF", "ABSENCE_PROOF")
CLAIM_EVENTS = ("EVIDENCE_CLAIM",)

# order of events that share a timestamp
_PRIORITY = {"IDENTITY_CHANGE": 0, "DELETION_REQUESTED": 1, "activity": 2,
             "EVIDENCE_CLAIM": 3, "EVIDENCE_PROOF": 3, "ABSENCE_PROOF": 3, "AUDIT": 9}
_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _iso(dt: Optional[datetime]) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if dt else ""


def _ts(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        return parse_ts(str(value))
    except ValueError:
        return None


def _get(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def build_timeline(case: dict, identity=None, evidence: Optional[dict] = None,
                   lineage_edges: Optional[Iterable] = None) -> list[dict]:
    """
    Timeline rows for one case, oldest first. Returns [] when there is no
    evidence search (NOT_APPLICABLE, unresolved email, no audit_at).
    """
    audit_at = _ts(case.get("audit_at"))
    if evidence is None or audit_at is None:
        return []

    items: list[tuple] = []   # (time, priority, tiebreak, row)

    def add(time: Optional[datetime], kind: str, tiebreak, row: dict) -> None:
        if time is None or time > audit_at:
            return
        items.append((time, _PRIORITY.get(kind, 2), tiebreak,
                      {"time": _iso(time), **row}))

    for ch in getattr(identity, "history", None) or []:
        add(_ts(ch.event_time), "IDENTITY_CHANGE", ch.audit_id,
            {"system_id": "identity", "resource_id": ch.field_name,
             "event": "IDENTITY_CHANGE", "state_after": "CHANGED",
             "evidence_id": ch.audit_id})

    add(_ts(case.get("requested_at")), "DELETION_REQUESTED", "",
        {"system_id": "", "resource_id": "", "event": "DELETION_REQUESTED",
         "state_after": "", "evidence_id": ""})

    for e in lineage_edges or []:
        add(_ts(_get(e, "event_time")), "activity", _get(e, "activity_id", ""),
            {"system_id": _get(e, "target_system", ""),
             "resource_id": _get(e, "target_resource_id", ""),
             "event": _get(e, "event_type", ""),
             "state_after": _get(e, "reported_result", ""),
             "evidence_id": _get(e, "activity_id", "")})

    seen: set[tuple] = set()
    for rec in evidence.get("records", []) or []:
        kind = "EVIDENCE_CLAIM" if getattr(rec, "claim_only", False) else "EVIDENCE_PROOF"
        fid, sid, rid = (getattr(rec, k, "") or "" for k in ("evidence_id", "system_id",
                                                              "resource_id"))
        presence = getattr(rec, "presence", "") or ""
        observed = _ts(getattr(rec, "observed_at", None))
        key = (kind, fid, sid, rid, getattr(rec, "replica_or_table", None), presence,
               _iso(observed))
        if key in seen:
            continue
        seen.add(key)
        add(_ts(getattr(rec, "captured_at", None)), kind, (observed or _MIN, fid, rid),
            {"system_id": sid, "resource_id": rid, "event": kind,
             "state_after": presence, "evidence_id": fid})

    for (system_id, resource_id), proofs in (evidence.get("absence_proofs") or {}).items():
        for p in proofs or []:
            if getattr(p, "contradicted_by", ()):   # P2 found a record that contradicts it
                continue
            key = ("ABSENCE_PROOF", p.evidence_id, system_id, resource_id)
            if key in seen:
                continue
            seen.add(key)
            add(_ts(p.captured_at), "ABSENCE_PROOF", (_MIN, p.evidence_id, resource_id),
                {"system_id": system_id, "resource_id": resource_id, "event": "ABSENCE_PROOF",
                 "state_after": "ABSENT", "evidence_id": p.evidence_id})

    add(audit_at, "AUDIT", "", {"system_id": "", "resource_id": "", "event": "AUDIT",
                                "state_after": "", "evidence_id": ""})

    items.sort(key=lambda t: (t[0], t[1], str(t[2])))
    return [row for *_, row in items]
