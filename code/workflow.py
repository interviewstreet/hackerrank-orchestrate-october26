"""Request-scoped workflow lineage for identifier-free final-state evidence.

Workflow events are claims, not proof of state.  This module uses them only to recover
resource identity; final states still come from participant-visible evidence.  The
activity stream has no explicit workflow column, so correlation requires compatible
operation outcomes, request/report boundaries, already-grounded evidence anchors, and
the repeated scheduling cadence between actions in the same workflow.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# The supplied activity export lacks workflow IDs. Cadence is accepted only as a
# secondary signal connected to an evidence-grounded resource; it is never sufficient
# for unanchored or peer-rank correlation.
# The supplied deletion worker schedules dependent actions on two recurring cadences.
# A one-second tolerance accommodates timestamp rounding in the global activity export.
DEPENDENCY_REMAINDERS = (41, 52)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _compatible_accounts(case: dict, activity: list[dict]) -> list[dict]:
    start = _time(case["requested_at"])
    # Workflow readbacks can finish shortly after the reported status timestamp.
    end = min(_time(case["audit_at"]), _time(case["reported_at"]) + timedelta(hours=3))
    return [
        event for event in activity
        if event.get("event_type", "").upper() == "DELETE_RECORD"
        and event.get("target_system") == "account_service"
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
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1].get("activity_id", "")))
    best_score = scored[0][0]
    best = {item[1].get("resource_id", ""): item[1]
            for item in scored if item[0] == best_score}
    return next(iter(best.values())) if len(best) == 1 else None


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


def _unique_report_anchor(case, activity):
    """Return one destructive worker action temporally tied to the case report.

    This is an identity link only.  The action's reported result is deliberately ignored;
    participant-visible evidence must still prove the resulting state.
    """
    start = _time(case["requested_at"])
    end = _time(case["audit_at"])
    reported = _time(case["reported_at"])
    actions = {
        "DELETE_RECORD": "DELETE",
        "ANONYMIZE_RECORD": "ANONYMIZE",
        "REDACT_RECORD": "REDACT",
        "DISABLE_CONNECTOR": "DISABLE",
    }
    candidates = [
        event for event in activity
        if event.get("source_system") == "deletion_worker"
        and event.get("event_type", "").upper() in actions
        and start <= _time(event["event_time"]) <= end
        and abs((_time(event["event_time"]) - reported).total_seconds()) <= 15 * 60
    ]
    if len(candidates) != 1:
        return None
    event = candidates[0]
    return {**event, "required_action": actions[event["event_type"].upper()]}


def correlate_workflow_lineage(case, identity, evidence_index, activity, peer_requests):
    """Return grounded workflow resources to use in a second evidence pass.

    The returned event claims only that the workflow acted on the resource.  Callers
    must not treat ``reported_result`` as final-state evidence.
    """
    del peer_requests
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
    report_anchor = _unique_report_anchor(case, activity)
    if account is None and report_anchor is not None:
        if report_anchor.get("target_system") == "account_service":
            account = report_anchor
        else:
            # The unique near-report action can seed cadence correlation, while its
            # claimed result remains ineligible as proof of final state.
            account = _account_from_anchors(
                case, activity, {report_anchor.get("resource_id", ""): []}
            )

    # Never pair an unanchored workflow by reported result or peer/case rank.
    resources = []
    if report_anchor is not None:
        resources.append(report_anchor)
    if account is not None:
        resources.append({**account, "required_action": "DELETE"})
        analytics = _analytics_for_account(account, activity, case["audit_at"])
        if analytics is not None:
            resources.append({**analytics, "required_action": "ANONYMIZE"})

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
