"""Step 5: deletion_rules.csv applied to each resource's observed state.

Produces, per resource, the steps the contract requires:
  compliant  -> one VERIFICATION citing the evidence
  violation  -> FINDING (cites evidence) + REMEDIATION + VERIFICATION of the end state
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import RULES_CSV
from ..dataset_io import read_csv
from ..errors import DatasetError

log = logging.getLogger(__name__)

# Rule action -> how each observed result is treated.
# Value: (finding operation or None, remediation or None, verification operation)
_DELETE = {
    "NOT_FOUND": (None, None, "VERIFY_RECORD_ABSENT"),
    "*": ("REPORT_REMAINING_RECORD", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
}
_REDACT = {
    "NOT_FOUND": (None, None, "VERIFY_RECORD_ABSENT"),
    "IDENTIFIABLE": ("REPORT_EXPOSED_PII", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
    "*": (None, None, "VERIFY_RECORD_REDACTED"),
}
_ANONYMIZE = {
    "NOT_FOUND": (None, None, "VERIFY_RECORD_ABSENT"),
    "IDENTIFIABLE": ("REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
    "REFERENCED": ("REPORT_EXPOSED_PII", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
    "*": (None, None, "VERIFY_RECORD_ANONYMIZED"),
}
_RETAIN = {
    "NOT_FOUND": (None, None, None),  # a missing retained record cannot be remediated; flagged
    "*": (None, None, "VERIFY_RECORD_PRESENT"),
}
_BACKUP = {
    "RESTORE_ALLOWED": ("REPORT_RESTORE_RISK", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"),
    "RESTORE_BLOCKED": (None, None, "VERIFY_RESTORE_BLOCKED"),
    "NOT_FOUND": (None, None, None),
    "*": (None, None, "VERIFY_RESTORE_BLOCKED"),
}
_DATA_FLOW = {
    "ACTIVE": ("REPORT_ACTIVE_DATA_FLOW", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"),
    "DISABLED": (None, None, "VERIFY_DATA_FLOW_DISABLED"),
    "*": (None, None, None),
}
_TABLES = {"DELETE": _DELETE, "REDACT": _REDACT, "ANONYMIZE": _ANONYMIZE, "RETAIN": _RETAIN}


@dataclass(frozen=True)
class Treatment:
    finding: str | None
    remediation: str | None
    verification: str | None

    @property
    def violation(self) -> bool:
        return self.finding is not None


class Policy:
    def __init__(self, actions: dict[str, str]) -> None:
        self.actions = actions

    @classmethod
    def load(cls) -> "Policy":
        rows = read_csv(RULES_CSV, ("data_category", "required_action"))
        actions: dict[str, str] = {}
        for r in rows:
            cat, act = r["data_category"].strip(), r["required_action"].strip().upper()
            if act not in _TABLES:
                raise DatasetError(f"deletion_rules.csv: unknown action {act!r} for {cat}")
            actions[cat] = act
        log.info("policy: %d categories", len(actions))
        return cls(actions)

    def treat(self, category: str, result: str, retention_expired: bool = False) -> Treatment | None:
        """None when the category is unknown to the rules (caller flags it for review)."""
        if category == "DATA_FLOW":
            table = _DATA_FLOW
        elif category == "BACKUP_ARCHIVE":
            table = _BACKUP
        else:
            action = self.actions.get(category)
            if action is None:
                return None
            if action == "RETAIN" and retention_expired:
                action = "DELETE"  # retention period over: the record must go
            table = _TABLES[action]
        f, r, v = table.get(result, table["*"])
        return Treatment(f, r, v)
