"""
rules.py — load and evaluate dataset/deletion_rules.csv (owner: Person 3).

The rule book is read from the CSV at run time; nothing about which category
gets which action is hard-coded here. What *is* code is the meaning of each
condition sentence: every condition in the CSV is matched to a predicate by
its wording (see _CONDITION_KINDS). An unrecognised condition raises, so a
changed CSV can never be silently mis-applied.

Each predicate answers "does the rule's condition hold for this record?".
When it holds, the rule's required_action applies. When it does not hold the
outcome depends on what kind of condition it is:

* TRIGGER conditions describe when a record still needs work
  ("Record is still attributable to a user", "Log contains a user email
  address"). Not holding means the record is already in its required state.
* EXCEPTION conditions describe when a record may be kept
  ("within the supplied retention period", "legal hold is active",
  "shared ... context that must be retained", "Restore access can be
  blocked", tombstone conditions). Not holding means the exception does not
  apply, so the record falls back to deletion.
* SCOPE conditions limit an action to records of the subject only
  ("Attachment belongs only to the deletion subject"). Not holding means the
  record is shared, so only the subject's identifiers are removed (REDACT).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

DELETE = "DELETE"
REDACT = "REDACT"
ANONYMIZE = "ANONYMIZE"
RETAIN = "RETAIN"
ACTIONS = (DELETE, REDACT, ANONYMIZE, RETAIN)

ALWAYS = "ALWAYS"
TRIGGER = "TRIGGER"
EXCEPTION = "EXCEPTION"
SCOPE = "SCOPE"


@dataclass(frozen=True)
class RecordFacts:
    """Facts about one record copy that rule conditions are evaluated on.

    Built by policy_engine from P2 observations; every field is a fact read
    from evidence (or None when the evidence does not say).
    """
    category: str
    has_direct_identifiers: bool = False      # name / email / phone / hash still stored
    has_email: bool = False                   # an email address is still stored
    attributable: bool = False                # still linked to the user (PII or user reference)
    shared_context: Optional[bool] = None     # support conversation with other parties / orders
    subject_only: Optional[bool] = None       # attachment belongs only to the subject
    retention_active: Optional[bool] = None   # retention_until after audit_at
    legal_hold_active: Optional[bool] = None  # hold still in force at audit_at
    restore_blockable: Optional[bool] = True  # backup restore access can be blocked
    account_deleted: Optional[bool] = None    # tombstone: the account itself is deleted


# --------------------------------------------------------------------------
# condition sentence -> (kind, predicate)
# --------------------------------------------------------------------------
def _p_always(f: RecordFacts) -> bool:
    return True


def _p_attributable(f: RecordFacts) -> bool:
    return f.attributable


def _p_contains_email(f: RecordFacts) -> bool:
    return f.has_email


def _p_shared_context(f: RecordFacts) -> bool:
    return bool(f.shared_context)


def _p_subject_only(f: RecordFacts) -> bool:
    # Unknown ownership: the attachment was found through the subject's own
    # identifiers and nothing links it to anyone else, so treat it as theirs.
    return f.subject_only is not False


def _p_retention(f: RecordFacts) -> bool:
    # A security record with no stated retention end is taken to be within
    # the supplied retention period (the policy says retain; no expiry seen).
    return f.retention_active is not False


def _p_legal_hold(f: RecordFacts) -> bool:
    return f.legal_hold_active is not False


def _p_restore_blockable(f: RecordFacts) -> bool:
    return f.restore_blockable is not False


def _p_tombstone(f: RecordFacts) -> bool:
    return f.account_deleted is not False


# Ordered: the first pattern that matches the (lower-cased) condition wins.
_CONDITION_KINDS: list[tuple[re.Pattern, str, Callable[[RecordFacts], bool]]] = [
    (re.compile(r"^\s*always\s*$"), ALWAYS, _p_always),
    (re.compile(r"still attributable"), TRIGGER, _p_attributable),
    (re.compile(r"contains (a )?user email"), TRIGGER, _p_contains_email),
    (re.compile(r"shared .*context"), EXCEPTION, _p_shared_context),
    (re.compile(r"belongs only to the deletion subject"), SCOPE, _p_subject_only),
    (re.compile(r"retention period"), EXCEPTION, _p_retention),
    (re.compile(r"legal hold is active"), EXCEPTION, _p_legal_hold),
    (re.compile(r"restore access can be blocked"), EXCEPTION, _p_restore_blockable),
    (re.compile(r"account is deleted.*stable internal user_id"), EXCEPTION, _p_tombstone),
]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str
    kind: str
    predicate: Callable[[RecordFacts], bool]


@dataclass(frozen=True)
class RuleDecision:
    """Outcome of applying the rule book to one record."""
    rule_id: str
    action: str            # DELETE | REDACT | ANONYMIZE | RETAIN | NONE (already compliant)
    condition_met: bool
    reason: str


NONE = "NONE"  # TRIGGER rule whose condition does not hold: nothing left to do


def _classify_condition(text: str) -> tuple[str, Callable[[RecordFacts], bool]]:
    low = text.strip().lower()
    for pat, kind, pred in _CONDITION_KINDS:
        if pat.search(low):
            return kind, pred
    raise ValueError(f"unrecognised deletion-rule condition: {text!r}")


class RuleBook:
    """The deletion policy, loaded from deletion_rules.csv."""

    def __init__(self, rules: list[Rule]):
        self.rules = rules
        self._by_category: dict[str, Rule] = {}
        for r in rules:
            if r.data_category in self._by_category:
                raise ValueError(f"two rules for category {r.data_category}")
            self._by_category[r.data_category] = r

    @classmethod
    def load(cls, path: str | Path) -> "RuleBook":
        rules = []
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                action = row["required_action"].strip().upper()
                if action not in ACTIONS:
                    raise ValueError(f"{row['rule_id']}: unknown action {action!r}")
                kind, pred = _classify_condition(row["condition"])
                rules.append(Rule(
                    rule_id=row["rule_id"].strip(),
                    data_category=row["data_category"].strip().upper(),
                    condition=row["condition"].strip(),
                    required_action=action,
                    kind=kind,
                    predicate=pred,
                ))
        return cls(rules)

    def categories(self) -> list[str]:
        return list(self._by_category)

    def rule_for(self, category: Optional[str]) -> Optional[Rule]:
        return self._by_category.get((category or "").upper())

    def apply(self, facts: RecordFacts) -> Optional[RuleDecision]:
        """Required treatment for a record that is still present, or None
        when no rule covers its category."""
        rule = self.rule_for(facts.category)
        if rule is None:
            return None
        met = rule.predicate(facts)
        if met:
            return RuleDecision(rule.rule_id, rule.required_action, True,
                                f"{rule.rule_id}: {rule.condition}")
        if rule.kind == TRIGGER:
            return RuleDecision(rule.rule_id, NONE, False,
                                f"{rule.rule_id}: condition not met ({rule.condition})")
        if rule.kind == SCOPE:
            return RuleDecision(rule.rule_id, REDACT, False,
                                f"{rule.rule_id}: shared record, remove only the subject's identifiers")
        # EXCEPTION (or ALWAYS, which cannot fail): the permission to keep the
        # record does not apply, so it must be deleted.
        return RuleDecision(rule.rule_id, DELETE, False,
                            f"{rule.rule_id}: exception does not apply ({rule.condition})")
