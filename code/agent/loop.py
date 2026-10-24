"""Investigator loop and the code acceptance check (plan 7.4, DESIGN.md section 4).

Runs only for items the deterministic pass leaves UNPROVEN (no statement) or in CONFLICT.
One loop per item; each turn is one ``schema.AgentAction`` (one tool call). Caps:
``config.AGENT_MAX_ITERATIONS`` turns, ``config.AGENT_TOKEN_BUDGET`` tokens per case, and the
client's retries. The agent never sets status or steps: an accepted proposal only adds a
case-local observation (STATE) or a medium edge (LINK); the resolver and policy still decide.

Acceptance (after schema validation, which already checked the quotes are exact substrings):

1. every cited id was opened with ``read_evidence`` in this loop and exists at ``audit_at``;
2. the system is known; for STATE the record is the one under investigation; a LINK to a record
   that is already a target of the case is rejected (``link_exists``);
3. one quote names the resource id (OCR noise allowed) and - for LINK - a subject identifier
   in the same quote; ``user_identifier`` must be one of the subject's identifiers;
4. for STATE, the claimed state matches the cited file's parsed rows for that resource, or,
   for raw text without parsed rows, a state word in the quote that names the resource.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

import config
import safety
from agent.tools import Corpus
from evidence.common import AGENT_READBACK, Identifiers, Observation
from evidence.extract_vision import grounded, state_fields
from llm_client import LLMClient, render_prompt
from schema import AgentAction, AgentProposal, RawState

PROMPT = config.PROMPT_VERSIONS["agent"]

NEGATIVE = r"not[ _]found|absent|deleted|removed|missing|no results|\b404\b|rows=\"?0\b|purged"
STATE_WORDS = {
    RawState.FOUND: r"\bfound\b|present|exists|available|listed|retained|rows=\"?[1-9]|\b200\b",
    RawState.PRESENT: r"\bfound\b|present|exists|available|listed|retained|rows=\"?[1-9]|\b200\b",
    RawState.NOT_FOUND: NEGATIVE,
    RawState.ABSENT: NEGATIVE,
    RawState.IDENTIFIABLE: r"identifiable|@|\+\d",
    RawState.REDACTED: r"redact|masked|\*\*\*",
    RawState.ANONYMIZED: r"anonymi[sz]",
    RawState.ACTIVE: r"\bactive\b|enabled|running|enabled=\"?true",
    RawState.DISABLED: r"disabled|paused|stopped|inactive|enabled=\"?false",
    RawState.BLOCKED: r"blocked|denied|not allowed|restore_allowed=\"?false",
}


@dataclass
class AgentStats:
    runs: int = 0
    turns: int = 0
    proposals: int = 0
    accepted: int = 0
    rejected: Counter = field(default_factory=Counter)
    stopped: int = 0
    fallbacks: Counter = field(default_factory=Counter)
    over_budget: int = 0


@dataclass
class Outcome:
    observations: list[Observation] = field(default_factory=list)
    edges: list[tuple] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)


def _subject_hit(quote: str, keys: Identifiers) -> bool:
    low = quote.lower()
    digits = re.sub(r"\D", "", quote)
    return (any(e in low for e in keys.emails) or any(h in low for h in keys.hashes)
            or any(re.search(rf"\b{re.escape(u)}\b", quote) for u in keys.user_ids)
            or any(p and len(p) >= 7 and p in digits for p in keys.phones))


def _is_subject_identifier(value: str, keys: Identifiers) -> bool:
    return _subject_hit(value, keys) and (value.lower() in keys.emails or value in keys.user_ids
                                          or value.lower() in keys.hashes
                                          or re.sub(r"\D", "", value) in keys.phones)


def _state_matches(p: AgentProposal, category: str, parsed: list[Observation], quotes: list[str]) -> bool:
    want = state_fields(p.proposed_state, category)
    if want is None:
        return False
    stating = [o for o in parsed if all(getattr(o, k) is not None for k in want)]
    if stating:   # parsed rows that state every claimed attribute decide (newest first)
        latest = max(stating, key=lambda o: (o.state_observed_at, o.obs_id))
        return all(getattr(latest, k) == v for k, v in want.items())
    for quote in quotes:
        if not grounded(p.resource_id, quote):
            continue
        low = quote.lower()
        if p.proposed_state in (RawState.FOUND, RawState.PRESENT) and re.search(NEGATIVE, low):
            continue   # "not found" also contains "found"
        if re.search(STATE_WORDS[p.proposed_state], low):
            return True
    return False


def accept(p: AgentProposal, *, item_key: tuple[str, str], category: str, keys: Identifiers, opened: dict[str, str],
           corpus: Corpus, cutoff, known_systems: set[str], linked: set = frozenset()) -> tuple[bool, str]:
    for eid in p.evidence_ids:
        if eid not in opened:
            return False, "cited_not_opened"
        if not corpus.visible(eid, cutoff):
            return False, "cited_after_audit_at"
    if p.system_id not in known_systems:
        return False, "unknown_system"
    naming = [q for q in p.quotes if grounded(p.resource_id, q)]
    if not naming:
        return False, "resource_not_in_quote"
    if p.kind == "LINK":
        if (p.system_id, p.resource_id) in linked:
            return False, "link_exists"
        if not _is_subject_identifier(p.user_identifier or "", keys):
            return False, "identifier_not_subject"
        if not any(_subject_hit(q, keys) for q in naming):
            return False, "no_subject_identifier_in_row"
        return True, ""
    if (p.system_id, p.resource_id) != item_key:
        return False, "not_investigated_record"
    parsed = [o for eid in p.evidence_ids for o in corpus.store.for_resource(p.resource_id, cutoff)
              if o.file_id == eid and o.system_id == p.system_id and o.assertion != "operation_claim"]
    if not _state_matches(p, category, parsed, naming):
        return False, "state_mismatch"
    return True, ""


def _facts_block(item) -> str:
    rows = []
    for name, cs in sorted(item.state.copies.items()):
        rows.append(f"copy {name}: " + json.dumps({k: str(v) for k, v in cs.values.items()}, sort_keys=True))
    for e in item.target.edges:
        rows.append(f"link {e.kind} ({e.tier}) from {e.source_id.split('#')[0]} at {e.at.isoformat()}")
    return safety.wrap("facts", "\n".join(rows) or "no statements")


def investigate(case_id: str, item, *, keys: Identifiers, subject_ids: list[str], cutoff, client: LLMClient,
                corpus: Corpus, known_systems: set[str], stats: AgentStats, budget: list[int],
                linked: set = frozenset()) -> Outcome:
    """``linked``: (system, resource) pairs already targets of this case (a LINK to them adds nothing)."""
    out = Outcome()
    stats.runs += 1
    target, decision = item.target, item.decision
    reason = decision.reason or ("no admissible statement" if not item.state.copies else "statements do not decide")
    system, user = render_prompt(
        PROMPT, MAX_ITERATIONS=str(config.AGENT_MAX_ITERATIONS),
        SCHEMA=json.dumps(AgentAction.model_json_schema(), sort_keys=True), CASE_ID=case_id,
        AUDIT_AT=cutoff.strftime("%Y-%m-%dT%H:%M:%S"), SUBJECT_IDS=", ".join(subject_ids),
        SYSTEM_ID=target.system_id, RESOURCE_ID=target.resource_id, CATEGORY=decision.category or "unknown",
        REASON=reason, FACTS=_facts_block(item))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    opened: dict[str, str] = {}
    for turn in range(1, config.AGENT_MAX_ITERATIONS + 1):
        if budget[0] <= 0:
            stats.over_budget += 1
            out.log.append({"turn": turn, "event": "over_budget"})
            break
        result = client.structured("agent", case_id, messages, AgentAction,
                                   {"case_id": case_id, "evidence_text": dict(opened)}, PROMPT,
                                   schema_mode="json_object")
        stats.turns += 1
        if result.usage is not None:
            budget[0] -= result.usage.input_tokens + result.usage.output_tokens
        if result.value is None:
            stats.fallbacks[result.flag] += 1
            out.log.append({"turn": turn, "event": "fallback", "flag": result.flag, "error": result.error[:200]})
            break
        action: AgentAction = result.value
        messages.append({"role": "assistant", "content": action.model_dump_json(exclude_none=True)})
        if action.tool == "stop":
            stats.stopped += 1
            out.log.append({"turn": turn, "event": "stop"})
            break
        if action.tool == "submit_proposal":
            p = action.proposal
            stats.proposals += 1
            ok, why = accept(p, item_key=target.key, category=decision.category, keys=keys, opened=opened,
                             corpus=corpus, cutoff=cutoff, known_systems=known_systems, linked=linked)
            entry = {"turn": turn, "event": "proposal", "kind": p.kind, "resource_id": p.resource_id,
                     "proposed_state": p.proposed_state.value if p.proposed_state else None,
                     "evidence_ids": p.evidence_ids, "quotes": [q[:120] for q in p.quotes],
                     "accepted": ok, "reason": why}
            out.log.append(entry)
            if not ok:
                stats.rejected[why] += 1
                break
            stats.accepted += 1
            eid = p.evidence_ids[0]
            at = corpus.available[eid]
            if p.kind == "LINK":
                out.edges.append((p.system_id, p.resource_id, f"agent:{eid}", at))
            else:
                fields = state_fields(p.proposed_state, decision.category)
                out.observations.append(Observation(
                    obs_id=f"agent:{case_id}:{eid}:{p.resource_id}", file_id=eid, source_kind="agent",
                    family="agent", available_at=at, state_observed_at=at, system_id=p.system_id,
                    resource_id=p.resource_id, assertion=AGENT_READBACK, fields={"quotes": p.quotes},
                    detail="accepted agent proposal", **fields))
            break
        if action.tool == "search_evidence":
            payload = corpus.search_evidence(action.query, cutoff)
        elif action.tool == "query_facts":
            payload = corpus.query_facts(action.query, cutoff)
        else:
            payload = corpus.read_evidence(action.file_id, cutoff)
            if "error" not in payload:
                opened[action.file_id] = corpus.text.get(action.file_id, "")
        out.log.append({"turn": turn, "event": action.tool, "arg": action.query or action.file_id})
        left = config.AGENT_MAX_ITERATIONS - turn
        messages.append({"role": "user", "content": safety.wrap(f"tool_result:{action.tool}", json.dumps(
            payload, sort_keys=True, ensure_ascii=False)[:9000]) + f"\nTurns left: {left}."
            + (" Submit a proposal or stop now." if left == 1 else "")})
    return out
