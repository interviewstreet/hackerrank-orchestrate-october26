"""Per-case JSONL trace: facts used, edges, rules fired, steps (plan 8, D19).

One JSON object per case. The trace holds evidence ids, resource ids and decisions;
identifier values are reduced to their kinds and counts, so no personal data is written.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from evidence.common import Identifiers


def _ids(value) -> dict:
    return {k: len(v) for k, v in value.as_dict().items()} if isinstance(value, Identifiers) else value


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Identifiers):
        return _ids(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in (sorted(value) if isinstance(value, set) else value)]
    return value


def item_record(item) -> dict:
    tgt, state, d = item.target, item.state, item.decision
    return {
        "system_id": tgt.system_id, "resource_id": tgt.resource_id, "tier": tgt.tier,
        "edges": [{"kind": e.kind, "tier": e.tier, "source": e.source_id, "at": e.at} for e in tgt.edges],
        "shared_with_other_users": len(tgt.shared_with),
        "copies": {name: {"values": cs.values,
                          "proof": {a: s.evidence_id for a, s in cs.proof.items()},
                          "statements": [{"evidence_id": s.evidence_id, "rank": s.rank, "at": s.at,
                                          "values": s.values} for s in cs.statements]}
                   for name, cs in sorted(state.copies.items())},
        "category": d.category, "rule_id": d.rule_id, "outcome": d.outcome, "check": d.check,
        "copy": d.copy, "hypothesis": d.hypothesis, "reason": d.reason,
        "evidence_id": item.evidence_id,
    }


def case_record(result, items) -> dict:
    return _jsonable({
        "case_id": result.case_id, "status": result.status, "intent": result.intent,
        "user_id": result.subject.user_id if result.subject else None,
        "flags": result.flags, "error": result.error,
        "targets": [item_record(i) for i in items],
        "steps": result.steps,
        "agent": getattr(result, "agent_log", []),
        "model_calls": getattr(result, "model_calls", []),   # usage rows only, never message content
    })


class TraceWriter:
    def __init__(self, path: Path | None):
        self.path = path
        self._handle = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = open(path, "w", encoding="utf-8", newline="\n")  # noqa: SIM115 - kept open for the run; closed in close()

    def write(self, record: dict) -> None:
        if self._handle is not None:
            self._handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
