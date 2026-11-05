"""Audit-time state reconstruction: what did a resource look like at audit_at?

Rules
  * A fact is usable only if the event it describes is at or before audit_at.
  * Evidence may be CITED only if the file itself was captured at or before audit_at.
  * The latest usable observation wins. Several replica tables in the same snapshot are merged (presence wins).
  * Absence is established either by an explicit "not found" result or by a later snapshot that covers the system
    and does not contain the record.
  * Workflow statuses and worker "SUCCESS" results are never used as proof of state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .contracts import Observation
from .evidence_loader import EvidenceStore

PRESENCE_RANK = {"ACTIVE": 5, "PRESENT": 4, "BLOCKED": 3, "DISABLED": 3, "REDACTED": 3, "ANONYMIZED": 3, "ABSENT": 0}
# retained by policy: a snapshot that omits them says nothing about the record having been removed
RETAINED_CATEGORIES = ("SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE")
SNAPSHOT_FORMATS = ("sql", "json")          # formats that are full point-in-time snapshots (absence can be inferred)


@dataclass
class ResourceState:
    resource_id: str
    system_id: str
    category: str
    state: str                         # ACTIVE | PRESENT | BLOCKED | DISABLED | REDACTED | ANONYMIZED | ABSENT | UNKNOWN
    exposed: bool = False              # still carries direct identifiers
    exposed_fields: List[str] = field(default_factory=list)
    evidence_id: str = ""              # citable evidence supporting `state` ('' if none can be cited)
    basis: str = "unknown"             # observed | absent_from_snapshot | unknown
    observations: List[Observation] = field(default_factory=list)
    retention_until: str = ""
    note: str = ""


def effective_time(o: Observation) -> str:
    return o.observed_at or o.captured_at


def exposure(o: Observation, category: str) -> List[str]:
    """Identifier kinds the record itself still contains (lookup keys are NOT part of the record)."""
    out: List[str] = []
    if o.emails:
        out.append("email")
    if o.hashes:
        out.append("email_hash")
    if o.phones:
        out.append("phone")
    if o.names:
        out.append("name")
    if category in ("ANALYTICS_PROFILE", "PRODUCT_TELEMETRY") and o.user_refs:
        out.append("user_reference")
    if o.attrs.get("identifiable") is True and not out:
        out.append("identifiable")
    return out


def _file_time(o: Observation) -> str:
    return o.file_captured_at or o.captured_at


def reconstruct(store: EvidenceStore, resource_id: str, system_id: str, category: str, audit_at: str) -> ResourceState:
    # usable = the event happened by audit_at AND the evidence file itself existed by audit_at
    obs = [o for o in store.by_resource.get(resource_id, [])
           if effective_time(o) <= audit_at and _file_time(o) <= audit_at]
    state = ResourceState(resource_id, system_id, category, "UNKNOWN")
    state.observations = sorted(obs, key=lambda o: (effective_time(o), o.evidence_id))

    latest_t = ""
    seen_labels = {"primary"}
    if obs:
        latest = max(obs, key=lambda o: (effective_time(o), _file_time(o), o.evidence_id))
        latest_t = effective_time(latest)
        group = [o for o in obs if o.evidence_id == latest.evidence_id and effective_time(o) == latest_t]
        best = max(group, key=lambda o: PRESENCE_RANK.get(o.state, 1))
        state.state = best.state
        fields: List[str] = []
        for o in group:
            if o.state in ("PRESENT", "ACTIVE", "UNKNOWN"):
                for f in exposure(o, category):
                    if f not in fields:
                        fields.append(f)
        state.exposed_fields = fields
        state.exposed = bool(fields) and state.state in ("PRESENT", "ACTIVE")
        state.basis = "observed"
        state.evidence_id = latest.evidence_id if best is latest else best.evidence_id
        # copies that still hold the record: absence later must be shown for each of these replicas
        seen_labels = {o.attrs.get("replica", "primary") for o in group if o.state in ("PRESENT", "ACTIVE")} or {"primary"}
        for o in group:
            ru = o.attrs.get("retention_until")
            if ru:
                state.retention_until = str(ru)

    # absence inferred from a later full snapshot that covers every copy where the record was last seen
    if state.state != "ABSENT" and system_id and category not in RETAINED_CATEGORIES:
        by_file: dict = {}
        for c in store.coverage_by_system.get(system_id, []):
            if c.source_format not in SNAPSHOT_FORMATS or c.captured_at > audit_at or (c.file_captured_at or c.captured_at) > audit_at:
                continue
            if c.captured_at <= latest_t:
                continue
            by_file.setdefault(c.evidence_id, {"t": c.captured_at, "labels": set()})["labels"].add(c.replica)
        best_file = None
        for fid, info in by_file.items():
            if not seen_labels <= info["labels"]:
                continue
            if any(o.evidence_id == fid for o in store.by_resource.get(resource_id, [])):
                continue
            if best_file is None or info["t"] > by_file[best_file]["t"]:
                best_file = fid
        if best_file is not None:
            state.state, state.basis, state.exposed, state.exposed_fields = "ABSENT", "absent_from_snapshot", False, []
            state.evidence_id = best_file
            state.note = f"not present in {best_file} (captured {by_file[best_file]['t']}) which covers {system_id}"
    return state
