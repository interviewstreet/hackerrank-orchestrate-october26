"""Evidence choice, kept separate from state (plan 9.7).

After the resolver and the policy fix the state, ``cite`` picks one evidence id among
the admissible statements that support that state. In each copy a statement supports the
state only if no contradicting statement of that copy is newer (same rule as the resolver).
Among supporters:

1. the strongest tier (row / read-back > scoped absence > activity read-back);
2. then the newest statement;
3. then the id that supports the state in the most physical copies;
4. then the lowest id (natural order).

Operation claims never reach this module (the resolver drops them).
"""

from __future__ import annotations

import re

from evidence.common import ABSENT, ANONYMIZED, IDENTIFIABLE, PRESENT, REDACTED, Identifiers
from policy import Decision, holds_subject
from resolver import ResourceState, Statement


def _natural(evidence_id: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", evidence_id))


def _supports(st: Statement, decision: Decision, violating: bool, keys: Identifiers) -> bool:
    attr = decision.attribute
    if attr == "exists":
        want = PRESENT if (violating or decision.check == "retain") else ABSENT
        return st.values.get("exists") == want
    if attr == "exposure":
        if st.values.get("exists") != PRESENT:
            return False
        treatment = st.values.get("treatment")
        if treatment is not None:
            if treatment not in (IDENTIFIABLE, ANONYMIZED, REDACTED):
                return False
            return (treatment == IDENTIFIABLE) == violating
        ids = st.values.get("exposed_ids")
        if decision.check == "restore":   # r5-#2: the statement shows the subject's own identifiers
            return holds_subject(ids, keys) == violating
        if isinstance(ids, Identifiers):
            hit = ids.direct() if decision.check == "direct" else ids.any()
            return hit == violating
        return False
    if attr in ("flow_state", "restore_state"):
        value = st.values.get(attr)
        bad = {"flow_state": "ACTIVE", "restore_state": "OPEN"}[attr]
        return value is not None and (value == bad) == violating
    return False


def _states(st: Statement, attr: str) -> bool:
    """True when the statement says something about ``attr`` (an absence speaks to exposure too)."""
    if attr in ("exists", "exposure"):
        return "exists" in st.values
    return attr in st.values


def cite(state: ResourceState, decision: Decision, violating: bool) -> tuple[str, list[Statement]]:
    """Return (evidence_id, supporting statements). ``""`` when nothing supports the state."""
    # A violation is cited from any copy in the violating state, never from a compliant copy.
    names = (decision.bad_copies or [decision.copy]) if violating else sorted(state.copies)
    copies = [state.copies[n] for n in names if n in state.copies]
    support: dict[str, list[Statement]] = {}
    for cs in copies:
        stating = [st for st in cs.statements if _states(st, decision.attribute)]
        backers = [st for st in stating if _supports(st, decision, violating, state.keys)]
        latest_contra = max((st.at for st in stating if st not in backers), default=None)
        for st in backers:
            if latest_contra is None or st.at >= latest_contra:
                support.setdefault(st.evidence_id, []).append(st)
    if not support:
        return "", []

    def score(item):
        _, sts = item
        return (max(s.rank for s in sts), max(s.at for s in sts), len({s.copy for s in sts}))

    best_key = max(score(i) for i in support.items())
    tied = sorted((eid for eid, sts in support.items() if score((eid, sts)) == best_key), key=_natural)
    return tied[0], support[tied[0]]
