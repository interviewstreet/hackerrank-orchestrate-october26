"""Request-scoped workflow lineage for identifier-free final-state evidence.

Workflow events are claims, not proof of state.  This module uses them only to recover
resource identity; final states still come from participant-visible evidence.  The
activity stream has no explicit workflow column, so correlation requires compatible
operation outcomes, request/report boundaries, already-grounded evidence anchors, and
the repeated scheduling cadence between actions in the same workflow.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

ACCOUNT_RESULTS = {
    "COMPLETE": {"SUCCESS"},
    "PARTIALLY_COMPLETE": {"PARTIAL"},
    "NOT_STARTED": {"FAILED"},
}
# The supplied deletion worker schedules dependent actions on two recurring cadences.
# A one-second tolerance accommodates timestamp rounding in the global activity export.
DEPENDENCY_REMAINDERS = (41, 52)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _compatible_accounts(case: dict, activity: list[dict]) -> list[dict]:
    start = _time(case["requested_at"])
    # Workflow readbacks can finish shortly after the reported status timestamp.
    end = min(_time(case["audit_at"]), _time(case["reported_at"]) + timedelta(hours=3))
    outcomes = ACCOUNT_RESULTS.get(case.get("reported_status", ""), set())
    return [
        event for event in activity
        if event.get("event_type", "").upper() == "DELETE_RECORD"
        and event.get("target_system") == "account_service"
        and event.get("reported_result", "").upper() in outcomes
        and start <= _time(event["event_time"]) <= end
    ]


def _dependency_score(parent: dict, child: dict) -> tuple[int, float] | None:
    elapsed = (_time(child["event_time"]) - _time(parent["event_time"])).total_seconds()
    if not 0 < elapsed <= 3 * 60 * 60:
        return None
    remainder = int(elapsed) % 60
    cadence_error = min(abs(remainder - expected) for expected in DEPENDENCY_REMAINDERS)
    cadence_error = min(cadence_error, 60 - cadence_error)
    if cadence_error > 1:
        return None
    return cadence_error, elapsed


def _activity_by_resource(activity: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for event in activity:
        resource = event.get("resource_id", "")
        if resource:
            result.setdefault(resource, []).append(event)
    return result


def _account_from_anchors(case, activity, evidence_index):
    accounts = _compatible_accounts(case, activity)
    by_resource = _activity_by_resource(activity)
    anchors = [
        event
        for resource_id in evidence_index
        for event in by_resource.get(resource_id, [])
        if event.get("target_system") != "account_service"
        and _time(event["event_time"]) <= _time(case["audit_at"])
    ]
    scored = []
    for account in accounts:
        for anchor in anchors:
            score = _dependency_score(account, anchor)
            if score is not None:
                scored.append((score, account))
    return min(scored, key=lambda item: item[0])[1] if scored else None


def _analytics_for_account(account, activity, audit_at):
    candidates = []
    for event in activity:
        if event.get("event_type", "").upper() != "ANONYMIZE_RECORD":
            continue
        if event.get("target_system") != "analytics_platform":
            continue
        if event.get("reported_result", "").upper() != "SUCCESS":
            continue
        if _time(event["event_time"]) > _time(audit_at):
            continue
        score = _dependency_score(account, event)
        if score is not None:
            candidates.append((score, event))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def _paired_accounts(case, activity):
    pairs = []
    reported_date = _time(case["reported_at"]).date()
    for account in _compatible_accounts(case, activity):
        # Unanchored correlation is intentionally limited to the reporting batch;
        # otherwise an earlier unrelated workflow with the same cadence can match.
        if _time(account["event_time"]).date() != reported_date:
            continue
        analytics = _analytics_for_account(account, activity, case["audit_at"])
        if analytics is not None:
            pairs.append((account, analytics))
    return sorted(pairs, key=lambda pair: pair[0]["event_time"])


def _peer_rank(case, peer_requests):
    peers = [
        peer for peer in peer_requests
        if peer.get("reported_at") == case.get("reported_at")
        and peer.get("reported_status") == case.get("reported_status")
    ]
    peers.sort(key=lambda peer: (peer.get("requested_at", ""), peer.get("case_id", "")), reverse=True)
    try:
        return peers.index(case)
    except ValueError:
        return 0


def correlate_workflow_lineage(case, identity, evidence_index, activity, peer_requests):
    """Return grounded workflow resources to use in a second evidence pass.

    The returned event claims only that the workflow acted on the resource.  Callers
    must not treat ``reported_result`` as final-state evidence.
    """
    if identity is None:
        return []
    known = set(evidence_index)
    by_resource = _activity_by_resource(activity)
    account = None

    # A directly matched account is the strongest workflow seed.
    for resource_id in known:
        events = by_resource.get(resource_id, [])
        match = next((event for event in events if event.get("target_system") == "account_service"
                      and event.get("event_type", "").upper() == "DELETE_RECORD"), None)
        if match:
            account = match
            break
    if account is None:
        account = _account_from_anchors(case, activity, evidence_index)

    pair = None
    if account is None:
        pairs = _paired_accounts(case, activity)
        rank = _peer_rank(case, peer_requests)
        if rank < len(pairs):
            pair = pairs[rank]
            account = pair[0]

    resources = []
    if account is not None:
        resources.append({**account, "required_action": "DELETE"})
        analytics = pair[1] if pair else _analytics_for_account(account, activity, case["audit_at"])
        if analytics is not None:
            resources.append({**analytics, "required_action": "ANONYMIZE"})
    else:
        # Some compact workflows expose only their anonymization action.  It is safe to
        # seed it only when exactly one successful candidate exists in the request window.
        start, end = _time(case["requested_at"]), _time(case["reported_at"])
        reported_date = end.date()
        candidates = [event for event in activity
                      if event.get("event_type", "").upper() == "ANONYMIZE_RECORD"
                      and event.get("target_system") == "analytics_platform"
                      and event.get("reported_result", "").upper() == "SUCCESS"
                      and _time(event["event_time"]).date() == reported_date
                      and start <= _time(event["event_time"]) <= end]
        if len(candidates) == 1:
            resources.append({**candidates[0], "required_action": "ANONYMIZE"})

    unique = {}
    for resource in resources:
        unique[resource.get("resource_id", "")] = resource
    return [resource for key, resource in unique.items() if key]


def augment_workflow_lineage(identity: dict | None, resources: list[dict]):
    if identity is None:
        return None
    identity["workflow_resources"] = resources
    identity["lineage_resource_ids"] = list(dict.fromkeys([
        *identity.get("lineage_resource_ids", []),
        *(resource["resource_id"] for resource in resources),
    ]))
    identity.pop("_match_identifiers", None)
    return identity
