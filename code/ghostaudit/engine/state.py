"""Point-in-time state reconstruction for one resource (SPEC §5 step 4) and the evidence that proves it."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..models import Kind, Observation

STATE_KINDS = {
    Kind.PRESENT, Kind.ABSENT, Kind.REDACTED, Kind.ANONYMIZED, Kind.RETAINED, Kind.FLOW_ACTIVE,
    Kind.FLOW_DISABLED, Kind.RESTORE_ALLOWED, Kind.RESTORE_BLOCKED, Kind.RECREATED,
}
# When one evidence item holds several locations (primary + replicas) the most exposing one wins.
EXPOSURE_RANK = {
    Kind.PRESENT: 9, Kind.RECREATED: 9, Kind.FLOW_ACTIVE: 8, Kind.RESTORE_ALLOWED: 8, Kind.RETAINED: 7,
    Kind.REDACTED: 4, Kind.ANONYMIZED: 4, Kind.FLOW_DISABLED: 3, Kind.RESTORE_BLOCKED: 3, Kind.ABSENT: 1,
}


@dataclass
class ResourceState:
    kind: Kind | None
    evidence_id: str = ""
    decided_by: list = field(default_factory=list)   # [(evidence_id, kind, explicit)]
    category: str | None = None
    attrs: dict = field(default_factory=dict)


def _normalize(kind: Kind) -> Kind:
    return Kind.PRESENT if kind == Kind.RECREATED else kind


def reconstruct(observations: list[Observation], audit_at: datetime) -> ResourceState:
    """Latest evidence item at or before audit_at decides; explicit facts beat inferred absence at equal time.

    The cited evidence is the latest *explicit* observation that agrees with the final state and is not older
    than any observation that disagrees with it; inferred absence is cited only when nothing explicit agrees.
    """
    obs = [o for o in observations if o.captured_at <= audit_at and o.kind in STATE_KINDS]
    if not obs:
        return ResourceState(None)
    groups: dict[tuple, list[Observation]] = {}
    for o in obs:
        groups.setdefault((o.captured_at, o.evidence_id), []).append(o)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0][0], any(o.explicit for o in kv[1]), kv[0][1]))

    def group_kind(items: list[Observation]) -> Kind:
        explicit = [o for o in items if o.explicit] or items
        return _normalize(max(explicit, key=lambda o: (EXPOSURE_RANK.get(o.kind, 0), o.observed_at)).kind)

    timeline = [(key, group_kind(items), items) for key, items in ordered]
    final = timeline[-1][1]
    # walk back over the agreeing tail to find the evidence to cite
    agreeing = []
    for key, kind, items in reversed(timeline):
        if kind != final:
            break
        agreeing.append((key, items))
    explicit_agreeing = [(k, it) for k, it in agreeing if any(o.explicit for o in it)]
    cite_key, cite_items = (explicit_agreeing or agreeing)[0]
    category = None
    attrs: dict = {}
    for _, _, items in timeline:
        for o in items:
            if o.category:
                category = o.category if category in (None, "SUPPORT_MESSAGE") or o.category == "SUPPORT_ATTACHMENT" else category
            attrs.update({k: v for k, v in o.attrs.items() if not k.startswith("_")})
    return ResourceState(
        kind=final,
        evidence_id=cite_key[1],
        decided_by=[(k[1], kd.value, any(o.explicit for o in it)) for k, kd, it in timeline[-3:]],
        category=category,
        attrs=attrs,
    )
