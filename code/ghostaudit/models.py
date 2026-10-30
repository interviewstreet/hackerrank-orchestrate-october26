"""Frozen data contracts shared by every module (SPEC §4)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Case:
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass(frozen=True)
class EvidenceFile:
    file_id: str
    path: Path
    origin: str
    captured_at: datetime


@dataclass(frozen=True)
class Identity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: datetime


@dataclass(frozen=True)
class AuditEntry:
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str
    old_value: str
    new_value: str


@dataclass(frozen=True)
class Activity:
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str


class Kind(str, Enum):
    """What one observation says about a resource."""
    PRESENT = "PRESENT"            # record exists and still exposes direct identifiers
    ABSENT = "ABSENT"              # lookup returned nothing / 404 / NOT_FOUND / missing from a full snapshot
    REDACTED = "REDACTED"          # record exists, direct identifiers removed
    ANONYMIZED = "ANONYMIZED"      # record exists, unlinked from any user
    RETAINED = "RETAINED"          # policy-retained record exists (audit log, legal hold)
    FLOW_ACTIVE = "FLOW_ACTIVE"
    FLOW_DISABLED = "FLOW_DISABLED"
    RESTORE_ALLOWED = "RESTORE_ALLOWED"
    RESTORE_BLOCKED = "RESTORE_BLOCKED"
    LINK = "LINK"                  # links a resource to identifiers without stating its state
    RECREATED = "RECREATED"        # sync/restore repopulated the resource
    CLAIM = "CLAIM"                # workflow outcome claim; never decides state


@dataclass(frozen=True)
class Observation:
    evidence_id: str               # file_id | activity_id | audit_id  (the id that may be cited)
    observed_at: datetime          # row/line timestamp if present, else the file's captured_at
    captured_at: datetime          # manifest captured_at (or event_time for activity): the <= audit_at filter
    system_id: str                 # canonical system (replicas collapse to their logical system)
    resource_id: str
    kind: Kind
    category: str | None           # DATA_CATEGORY if derivable
    identifiers: frozenset         # {("email", "x@y"), ("user_id", "user_12"), ("email_hash", ..), ("phone", ..)}
    location: str = ""             # e.g. "failover_replica", "primary", "log"
    attrs: Mapping[str, str] = field(default_factory=dict)
    explicit: bool = True          # False for absence inferred from a full snapshot that lacks the record


@dataclass(frozen=True)
class Step:
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str


@dataclass
class CaseResult:
    case_id: str
    deletion_status: str
    steps: list
    trace: dict = field(default_factory=dict)
