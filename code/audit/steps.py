"""Deterministic step ordering/numbering and status-specific rules."""
import json
from .constants import OP_RANK, OP_PHASE, OP_STATE, PHASES

def make_step(operation, system_id, resource_id, evidence_id=""):
    return {"phase": OP_PHASE[operation], "system_id": system_id,
            "resource_id": resource_id, "operation": operation,
            "state": OP_STATE[operation], "evidence_id": evidence_id or ""}

def sort_key(s):
    return (PHASES.index(s["phase"]), OP_RANK[s["operation"]],
            s["system_id"], s["resource_id"])

def finalize(status, steps):
    """Dedupe, order, number. Enforce evidence rules per status."""
    if status == "NOT_APPLICABLE":
        return []
    seen, uniq = set(), []
    for s in steps:
        k = (s["operation"], s["system_id"], s["resource_id"])
        if k not in seen:
            seen.add(k); uniq.append(dict(s))
    if status == "COMPLETE":
        uniq = [s for s in uniq if s["phase"] == "VERIFICATION"]
    else:  # INCOMPLETE: only findings carry evidence
        for s in uniq:
            if s["phase"] != "FINDING":
                s["evidence_id"] = ""
    uniq.sort(key=sort_key)
    for i, s in enumerate(uniq, 1):
        s["step_no"] = i
    return uniq

def dumps(steps):
    return json.dumps(steps, separators=(",", ":"))
