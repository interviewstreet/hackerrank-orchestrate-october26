"""State of each physical copy of a target resource at ``audit_at`` (plan 8.3).

Rules:

* only admissible observations count (``available_at`` and inner time both <= audit_at);
* operation claims, sync facts and ownership links never set state;
* a file's scope proves ABSENT for a copy only when the scope applies to the subject
  (full snapshot, or a subject-scoped listing that names one of the subject's identifiers)
  and the file has no row for the resource in that copy;
* per copy and per attribute, one swappable dominance rule (``DOMINANCE``):
  ``newest_wins`` (default): the newest ``state_observed_at`` wins, because state changes over
  time (a deletion after a snapshot is the common case); the tier (row / read-back > scoped
  absence > activity read-back) breaks ties only at the same timestamp.
  ``tier_first`` (plan 9.4 as first written) is kept so both can be scored;
* equal key and different values give CONFLICT; no statement gives UNKNOWN.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from evidence.common import (
    ABSENT,
    ACTIVITY_READBACK,
    AGENT_READBACK,
    PRESENT,
    SNAPSHOT_ROW,
    STATE_READBACK,
    VISION_ROW,
    Identifiers,
    Observation,
    Scope,
)
from evidence.extract_vision import grounded
from facts import FactStore
from links import Target

UNKNOWN, CONFLICT = "UNKNOWN", "CONFLICT"
SCOPED_ABSENCE = "scoped_absence"
# Tier "vision" (model-read, grounded) sits below parsed text rows; agent read-backs are lowest.
RANK = {SNAPSHOT_ROW: 3, STATE_READBACK: 3, SCOPED_ABSENCE: 2, VISION_ROW: 2, ACTIVITY_READBACK: 1,
        AGENT_READBACK: 1}
DOMINANCE = "newest_wins"
ATTRIBUTES = ("exists", "treatment", "flow_state", "restore_state", "exposed_ids")


@dataclass
class Statement:
    """One admissible statement about a copy. ``obs`` is None for a scoped absence."""
    copy: str
    at: datetime
    rank: int
    evidence_id: str
    values: dict
    obs: Observation | None = None
    scope: Scope | None = None


@dataclass
class CopyState:
    copy: str
    values: dict = field(default_factory=dict)        # attribute -> value | UNKNOWN | CONFLICT
    proof: dict = field(default_factory=dict)         # attribute -> Statement that set it
    statements: list[Statement] = field(default_factory=list)

    def get(self, attr: str):
        return self.values.get(attr, UNKNOWN)


@dataclass
class ResourceState:
    target: Target
    copies: dict[str, CopyState] = field(default_factory=dict)
    record_type: str = ""
    collection: str = ""
    record_types: set[str] = field(default_factory=set)   # every stated record type (r3-#4)

    @property
    def known(self) -> bool:
        return bool(self.copies)


def _scope_applies(scope: Scope, keys: Identifiers) -> bool:
    if scope.subjects is None:
        return True
    return any(getattr(scope.subjects, k) & getattr(keys, k) for k in ("emails", "user_ids", "phones", "hashes"))


def shown_identifiers(obs: Observation, keys: Identifiers) -> Identifiers | None:
    """r5-#1: a present screen row that names no identifier of its own. The subject's strong
    identifiers (email, phone, email hash) in the row's OCR region (``extract_vision.row_region``)
    are identifiers the record shows. A name alone does not count. ``None``: none shown."""
    if obs.assertion != VISION_ROW or obs.exists != PRESENT or obs.exposed_ids is not None:
        return None
    region = str(obs.fields.get("id_region") or "")
    shown = Identifiers(emails={e for e in keys.emails if grounded(e, region)},
                        phones={p for p in keys.phones if grounded(p, region)},
                        hashes={h for h in keys.hashes if grounded(h, region)})
    return shown if shown.direct() else None


def statements_for(store: FactStore, target: Target, keys: Identifiers, cutoff,
                   extra: Sequence[Observation] = ()) -> tuple[list[Statement], list]:
    """``extra``: case-local observations (accepted agent STATE proposals), same cutoff rules.
    Only targets that are already linked reach this point: an exposure never creates a target."""
    out: list[Statement] = []
    observations = store.for_resource(target.resource_id, cutoff)
    observations += [o for o in extra if o.resource_id == target.resource_id and store.admissible(o, cutoff)]
    for obs in observations:
        if obs.system_id != target.system_id or obs.assertion not in RANK:
            continue
        values = {a: getattr(obs, a) for a in ATTRIBUTES if getattr(obs, a) is not None}
        shown = shown_identifiers(obs, keys)
        if shown is not None:
            values["exposed_ids"] = shown
        if obs.exists == ABSENT:
            values.pop("exposed_ids", None)
        out.append(Statement(obs.physical_copy, obs.state_observed_at, RANK[obs.assertion], obs.file_id,
                             values, obs=obs))
    # A listing of one collection says nothing about a record of another (or of an unknown) collection.
    collections = {o.collection for o in observations if o.system_id == target.system_id and o.collection}
    for scope in store.scopes_for(target.system_id, cutoff):
        if (not _scope_applies(scope, keys)
                or (scope.collection and scope.collection not in collections)
                or store.file_has_row(scope.file_id, target.resource_id, scope.physical_copy)):
            continue
        out.append(Statement(scope.physical_copy, scope.observed_at, RANK[SCOPED_ABSENCE], scope.file_id,
                             {"exists": ABSENT}, scope=scope))
    return out, observations


def resolve(store: FactStore, target: Target, keys: Identifiers, cutoff,
            extra: Sequence[Observation] = ()) -> ResourceState:
    statements, observations = statements_for(store, target, keys, cutoff, extra)
    state = ResourceState(target)
    for obs in observations:
        if obs.system_id == target.system_id:
            state.record_type = state.record_type or obs.record_type
            state.collection = state.collection or obs.collection
            if obs.record_type:
                state.record_types.add(obs.record_type)
    for st in statements:
        state.copies.setdefault(st.copy, CopyState(st.copy)).statements.append(st)
    for cs in state.copies.values():
        cs.statements.sort(key=lambda s: (s.at, s.rank, s.evidence_id))
        for attr in ATTRIBUTES:
            stating = [s for s in cs.statements if attr in s.values]
            if not stating:
                continue
            best = max(stating, key=_dominance)
            peers = [s for s in stating if _dominance(s) == _dominance(best)]
            distinct = {_fingerprint(s.values[attr]) for s in peers}
            if len(distinct) > 1:
                cs.values[attr] = CONFLICT
            else:
                cs.values[attr] = best.values[attr]
            cs.proof[attr] = min(peers, key=lambda s: s.evidence_id)
        # A newer absence makes older identifier/treatment statements moot.
        if cs.values.get("exists") == ABSENT:
            for attr in ("treatment", "exposed_ids"):
                if attr in cs.proof and cs.proof[attr].at <= cs.proof["exists"].at:
                    cs.values.pop(attr), cs.proof.pop(attr)
    return state


def newest_wins(st: Statement) -> tuple:
    return (st.at, st.rank)


def tier_first(st: Statement) -> tuple:
    return (st.rank, st.at)


DOMINANCE_RULES = {"newest_wins": newest_wins, "tier_first": tier_first}


def _dominance(st: Statement) -> tuple:
    return DOMINANCE_RULES[DOMINANCE](st)


def _fingerprint(value):
    return tuple((k, tuple(v)) for k, v in sorted(value.as_dict().items())) if isinstance(value, Identifiers) else value


def exists_rollup(state: ResourceState) -> str:
    """PRESENT if any copy is present; ABSENT only if every known copy is absent."""
    values = [cs.get("exists") for cs in state.copies.values()]
    if not values:
        return UNKNOWN
    if PRESENT in values:
        return PRESENT
    if CONFLICT in values:
        return CONFLICT
    if all(v == ABSENT for v in values):
        return ABSENT
    return UNKNOWN
