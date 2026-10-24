"""Deletion policy as data (plan 9.5) plus the safety invariants (decision 5).

``evaluate(state, cutoff)`` maps one resolved resource to a ``Decision``:
the category, the rule, the outcome (compliant / violation / unknown / missing retained
record / not a target) and the finding, remediation and verification operations.
Branches that no sample exercises carry ``hypothesis=True`` and go to the trace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from evidence.common import (
    ABSENT,
    ACTIVE,
    ANONYMIZED,
    BLOCKED,
    DISABLED,
    IDENTIFIABLE,
    OPEN,
    OPERATION_CLAIM,
    PRESENT,
    REDACTED,
    Identifiers,
)
from loaders import parse_ts
from resolver import CONFLICT, UNKNOWN, ResourceState, exists_rollup
from schema import Operation as Op

COMPLIANT, VIOLATION, UNPROVEN, MISSING_RETAINED, NOT_TARGET = (
    "compliant", "violation", "unproven", "missing_retained", "not_target")

# Categories that the request must never delete or anonymize (safety invariant 1).
RETAINED = frozenset({"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE", "ACCOUNT_TOMBSTONE",
                      "SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG"})

# Category -> (rule_id, check, finding, remediation, verification).
#   check: "exists"  - violation while any copy is PRESENT
#          "direct"  - violation while a present copy exposes direct identifiers
#          "linked"  - violation while a present copy is attributable (any identifier, user_id too)
#          "retain"  - the record must stay PRESENT
#          "flow"    - violation while the flow is ACTIVE
#          "restore" - violation while restore is OPEN
RULES: dict[str, tuple[str, str, Op | None, Op | None, Op]] = {
    "USER_PROFILE": ("rule_01", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "SECONDARY_IDENTIFIER": ("rule_02", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD,
                             Op.VERIFY_RECORD_ABSENT),
    "SEARCH_INDEX_ENTRY": ("rule_03", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "CACHE_ENTRY": ("rule_04", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "SUPPORT_MESSAGE": ("rule_05", "direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "SUPPORT_ATTACHMENT": ("rule_06", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "ANALYTICS_PROFILE": ("rule_07", "linked", Op.REPORT_EXPOSED_PII, Op.ANONYMIZE_RECORD, Op.VERIFY_RECORD_ANONYMIZED),
    "PRODUCT_TELEMETRY": ("rule_08", "linked", Op.REPORT_EXPOSED_PII, Op.ANONYMIZE_RECORD, Op.VERIFY_RECORD_ANONYMIZED),
    "USER_EXPORT": ("rule_09", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "MARKETING_PROFILE": ("rule_10", "exists", Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD, Op.VERIFY_RECORD_ABSENT),
    "EMAIL_DELIVERY_LOG": ("rule_11", "direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "SECURITY_AUDIT_LOG": ("rule_12", "retain", None, None, Op.VERIFY_RECORD_PRESENT),
    "LEGAL_HOLD_RECORD": ("rule_13", "retain", None, None, Op.VERIFY_RECORD_PRESENT),
    "BACKUP_ARCHIVE": ("rule_14", "restore", Op.REPORT_RESTORE_RISK, Op.BLOCK_RESTORE, Op.VERIFY_RESTORE_BLOCKED),
    "ACCOUNT_TOMBSTONE": ("rule_15", "direct", Op.REPORT_EXPOSED_PII, Op.REDACT_RECORD, Op.VERIFY_RECORD_REDACTED),
    "DATA_FLOW": ("flow", "flow", Op.REPORT_ACTIVE_DATA_FLOW, Op.DISABLE_DATA_FLOW, Op.VERIFY_DATA_FLOW_DISABLED),
}

# Fallback category when the record states none: (system_id, collection) then system_id.
COLLECTION_CATEGORY = {
    ("support_platform", "ticket_attachments"): "SUPPORT_ATTACHMENT",
}
SYSTEM_CATEGORY = {
    "account_service": "USER_PROFILE",
    "search_service": "SEARCH_INDEX_ENTRY",
    "analytics_platform": "ANALYTICS_PROFILE",
    "support_platform": "SUPPORT_MESSAGE",
    "export_service": "USER_EXPORT",
    "integration_service": "DATA_FLOW",
    "backup_service": "BACKUP_ARCHIVE",
    "security_service": "SECURITY_AUDIT_LOG",
    "legal_service": "LEGAL_HOLD_RECORD",
    "identity_service": "ACCOUNT_TOMBSTONE",
    "cache_service": "CACHE_ENTRY",
    "email_delivery_service": "EMAIL_DELIVERY_LOG",
    "marketing_platform": "MARKETING_PROFILE",
}
# Category from the words that describe a record (D10), for records that state none: catalog
# link text such as "Attachment catalog confirmed ...". Ids, file names and emails are removed
# first, so only descriptive words count. Two different categories give none (UNPROVEN).
CONTENT_CATEGORY: tuple[tuple[re.Pattern, str], ...] = tuple((re.compile(p, re.I), c) for p, c in (
    (r"\battachments?\b", "SUPPORT_ATTACHMENT"),
    (r"\bsearch[- ]?index\b|\bsearch documents?\b", "SEARCH_INDEX_ENTRY"),
    (r"\bcache\b", "CACHE_ENTRY"),
    (r"\btelemetry\b", "PRODUCT_TELEMETRY"),
    (r"\bmarketing\b|\bnewsletter\b", "MARKETING_PROFILE"),
    (r"\banalytics\b", "ANALYTICS_PROFILE"),
    (r"\bdata exports?\b|\bexport (?:job|archive|file)s?\b", "USER_EXPORT"),
    (r"\bbackups?\b", "BACKUP_ARCHIVE"),
    (r"\btombstones?\b", "ACCOUNT_TOMBSTONE"),
    (r"\blegal hold\b", "LEGAL_HOLD_RECORD"),
    (r"\bsecurity audit\b|\baudit log\b", "SECURITY_AUDIT_LOG"),
    (r"\bemail delivery\b|\bdelivery log\b", "EMAIL_DELIVERY_LOG"),
    (r"\bsupport (?:ticket|conversation|message)s?\b", "SUPPORT_MESSAGE"),
    (r"\bconnector\b|\bdata flow\b", "DATA_FLOW"),
))
AMBIGUOUS_CATEGORY = "?ambiguous"   # category_of: the catalog words name two or more categories
NOT_WORDS = re.compile(r"\S+@\S+|\S*\d\S*|\([^)]*\)")
RETENTION_KEYS = ("retention_until", "retain_until", "retained_until", "retention_expires_at")
# rule_13 retains a legal hold record only while "a supplied legal hold is active". The hold
# status is an explicit status field, else the hold's retention end date (``retained_until``).
HOLD_STATUS_KEYS = ("hold_status", "legal_hold_status", "status")
HOLD_RELEASED = frozenset({"INACTIVE", "RELEASED"})


@dataclass
class Decision:
    category: str
    rule_id: str
    outcome: str
    finding: Op | None = None
    remediation: Op | None = None
    verification: Op | None = None
    check: str = ""                # effective rule check (see RULES)
    copy: str = ""                 # the copy that violates (citation) or proves compliance
    bad_copies: list[str] = field(default_factory=list)   # every copy in the violating state
    attribute: str = ""            # the resolved attribute the outcome rests on
    hypothesis: list[str] = field(default_factory=list)
    reason: str = ""


def category_of(state: ResourceState) -> str:
    for cs in state.copies.values():
        for st in cs.statements:
            if st.obs is None:
                continue
            for value in (st.obs.record_type, st.obs.fields.get("record_type"), st.obs.fields.get("data_category")):
                if isinstance(value, str) and value in RULES:
                    return value
    if state.record_type in RULES:
        return state.record_type
    system = state.target.system_id
    if (system, state.collection) in COLLECTION_CATEGORY:
        return COLLECTION_CATEGORY[(system, state.collection)]
    named = content_categories(state.target.descriptions)
    if len(named) > 1:   # the words name two categories: no category, the record stays unproven
        return AMBIGUOUS_CATEGORY
    return named.pop() if named else SYSTEM_CATEGORY.get(system, "")


def content_categories(texts) -> set[str]:
    """Every category named by the descriptive words of a record's catalog text."""
    return {category for text in texts for pattern, category in CONTENT_CATEGORY
            if pattern.search(NOT_WORDS.sub(" ", text))}


def content_category(texts) -> str:
    """The one category the catalog text names, or ``""`` when it names none or several."""
    named = content_categories(texts)
    return named.pop() if len(named) == 1 else ""


def _present_copies(state: ResourceState) -> list:
    return [cs for _, cs in sorted(state.copies.items()) if cs.get("exists") == PRESENT]


def _exposure(cs, check: str) -> str:
    """IDENTIFIABLE / clean / UNKNOWN for one present copy."""
    treatment = cs.get("treatment")
    if treatment in (IDENTIFIABLE,):
        return IDENTIFIABLE
    if treatment in (ANONYMIZED, REDACTED):
        return "clean"
    ids = cs.get("exposed_ids")
    if isinstance(ids, Identifiers):
        hit = ids.direct() if check == "direct" else ids.any()
        return IDENTIFIABLE if hit else "clean"
    return UNKNOWN


def _retention_expired(state: ResourceState, cutoff) -> bool | None:
    for cs in state.copies.values():
        for st in cs.statements:
            if st.obs is None:
                continue
            for key in RETENTION_KEYS:
                if st.obs.fields.get(key):
                    until = parse_ts(str(st.obs.fields[key]))
                    if until is not None:
                        return until <= cutoff
    return None


def _hold_status(state: ResourceState) -> str:
    """Explicit status of a legal hold (newest statement first), upper case, or ``""``.
    A workflow operation claim is not a status."""
    stated = [st for cs in state.copies.values() for st in cs.statements
              if st.obs is not None and st.obs.assertion != OPERATION_CLAIM]
    for st in sorted(stated, key=lambda s: (s.obs.state_observed_at, s.obs.obs_id), reverse=True):
        for key in HOLD_STATUS_KEYS:
            value = st.obs.fields.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    return ""


def _exposure_decision(d: Decision, state: ResourceState, check: str, exists: str) -> Decision:
    """REDACT / ANONYMIZE rules: the record stays; the exposure of each present copy decides."""
    if exists == ABSENT:
        # The record is gone although policy keeps it redacted/anonymized (H).
        d.hypothesis.append("redact_target_absent")
        d.outcome, d.attribute, d.verification = COMPLIANT, "exists", Op.VERIFY_RECORD_ABSENT
        d.finding = d.remediation = None
        return d
    present = _present_copies(state)
    exposures = [(cs, _exposure(cs, check)) for cs in present]
    bad = [cs for cs, e in exposures if e == IDENTIFIABLE]
    if bad:
        d.outcome, d.copy, d.attribute = VIOLATION, bad[0].copy, "exposure"
        d.bad_copies = [cs.copy for cs in bad]
    elif present and all(e == "clean" for _, e in exposures):
        d.outcome, d.copy, d.attribute = COMPLIANT, present[0].copy, "exposure"
    if d.category == "SUPPORT_MESSAGE":
        d.hypothesis.append("support_shared_context_assumed")
    return d


def _process_decision(d: Decision, state: ResourceState, check: str) -> Decision:
    """Data flows and backups: any ACTIVE / OPEN copy is a violation; all known DISABLED / BLOCKED is compliant."""
    attr, bad_value, good_value = (("flow_state", ACTIVE, DISABLED) if check == "flow"
                                   else ("restore_state", OPEN, BLOCKED))
    values = {name: cs.get(attr) for name, cs in sorted(state.copies.items())}
    bad = [name for name, v in values.items() if v == bad_value]
    if bad:
        d.outcome, d.copy, d.attribute = VIOLATION, bad[0], attr
        d.bad_copies = bad
    elif values and all(v == good_value for v in values.values() if v not in (UNKNOWN,)) \
            and any(v == good_value for v in values.values()):
        d.outcome, d.copy, d.attribute = COMPLIANT, next(n for n, v in values.items() if v == good_value), attr
    elif any(v == CONFLICT for v in values.values()):
        d.reason = "conflict"
    return d


def evaluate(state: ResourceState, cutoff) -> Decision:
    category = category_of(state)
    if category == AMBIGUOUS_CATEGORY:   # no rule applies with proof: unproven, never the first match
        return Decision("", "", UNPROVEN, reason="ambiguous category")
    if category not in RULES:
        return Decision(category, "", NOT_TARGET, reason="out of rules")
    rule_id, check, finding, remediation, verify = RULES[category]
    d = Decision(category, rule_id, UNPROVEN, finding, remediation, verify, check=check)
    exists = exists_rollup(state)

    if check == "retain":
        expired = _retention_expired(state, cutoff)
        if category == "LEGAL_HOLD_RECORD":
            status = _hold_status(state)
            if status in HOLD_RELEASED:   # an explicit released hold is not retained
                expired = True
                d.hypothesis.append(f"legal_hold_{status.lower()}")
            elif not status and expired is None:   # no status and no end date: active is not proven
                d.finding = d.remediation = None
                d.reason = "legal hold status missing"
                return d
        if expired:
            d.hypothesis.append("retention_expired_delete")
            d.finding, d.remediation, d.verification = (Op.REPORT_REMAINING_RECORD, Op.DELETE_RECORD,
                                                        Op.VERIFY_RECORD_ABSENT)
            check = d.check = "exists"
        else:
            if expired is None:
                d.hypothesis.append("retention_unknown_retain")
            d.finding = d.remediation = None
            if exists == PRESENT:
                d.outcome, d.copy, d.attribute = COMPLIANT, _present_copies(state)[0].copy, "exists"
            elif exists == ABSENT:
                d.outcome, d.attribute = MISSING_RETAINED, "exists"
                d.hypothesis.append("retained_record_missing")
            return d

    if check == "exists":
        if exists == PRESENT:
            d.outcome, d.copy, d.attribute = VIOLATION, _present_copies(state)[0].copy, "exists"
            d.bad_copies = [cs.copy for cs in _present_copies(state)]
        elif exists == ABSENT:
            d.outcome, d.attribute = COMPLIANT, "exists"
        return d

    if check in ("direct", "linked"):
        return _exposure_decision(d, state, check, exists)
    return _process_decision(d, state, check)


# ------------------------------------------------------------------ safety invariants

class SafetyViolation(AssertionError):
    pass


def check_safety(decision: Decision, *, foreign_only: bool, proof_assertions: list[str]) -> None:
    """Raise when a planned step breaks a decision-5 invariant.

    A retained category may be deleted only when its retention is proven expired.
    """
    category, remediation = decision.category, decision.remediation
    retained = category in RETAINED and "retention_expired_delete" not in decision.hypothesis
    if remediation in (Op.DELETE_RECORD, Op.ANONYMIZE_RECORD) and retained:
        raise SafetyViolation(f"{remediation} on retained category {category}")
    if remediation is not None and foreign_only:
        raise SafetyViolation("action on a record linked only to another user")
    if "operation_claim" in proof_assertions:
        raise SafetyViolation("operation claim used as proof")
