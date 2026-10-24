"""Shared types for evidence extraction.

An ``Observation`` is one statement a file makes about one resource. A ``Scope`` says
that a file lists *every* record of a system copy at a time, so a known resource that
is missing from it is ABSENT there. Extractors never decide ownership or policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from loaders import normalize_email, normalize_phone

# exists
PRESENT, ABSENT = "PRESENT", "ABSENT"
# treatment of identifiers inside a present record
IDENTIFIABLE, ANONYMIZED, REDACTED = "IDENTIFIABLE", "ANONYMIZED", "REDACTED"
# flows and restores
ACTIVE, DISABLED, OPEN, BLOCKED = "ACTIVE", "DISABLED", "OPEN", "BLOCKED"

# assertion types, strongest first (see resolver.py)
SNAPSHOT_ROW = "snapshot_row"        # a row inside a full or subject-scoped snapshot
STATE_READBACK = "state_readback"    # an explicit FOUND / NOT_FOUND / ACTIVE ... read-back
ACTIVITY_READBACK = "activity_readback"
OWNERSHIP_LINK = "ownership_link"    # links a resource to identifiers, says nothing about state
OPERATION_CLAIM = "operation_claim"  # "worker reported success": never proof of state
VISION_ROW = "vision_row"            # a model-read screenshot row, grounded in the file's OCR text
AGENT_READBACK = "agent_readback"    # an accepted investigator STATE proposal (quoted raw text)

PRIMARY = "primary"

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_USER_ID = re.compile(r"\buser_\d+\b")
RE_HASH = re.compile(r"^[0-9a-f]{64}$", re.I)
RE_RESOURCE_ID = re.compile(r"^[a-z]+(?:_[a-z]+)*_\d+$")
NAME_KEYS = frozenset({"full_name", "display_name", "requester_name", "name"})
PHONE_KEY = re.compile(r"phone", re.I)
# Fields that name another resource (an edge), not an identifier of a person.
REF_KEYS = frozenset({"source_resource_id"})


class ShapeError(ValueError):
    """A file or row has a shape no extractor knows. Coverage reports it loudly."""


@dataclass
class Identifiers:
    emails: set[str] = field(default_factory=set)
    user_ids: set[str] = field(default_factory=set)
    phones: set[str] = field(default_factory=set)      # normalized digits
    hashes: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)

    def direct(self) -> bool:
        """True when a direct identifier (not the stable user_id) is present."""
        return bool(self.emails or self.phones or self.hashes or self.names)

    def any(self) -> bool:
        return self.direct() or bool(self.user_ids)

    def update(self, other: Identifiers) -> None:
        for name in ("emails", "user_ids", "phones", "hashes", "names"):
            getattr(self, name).update(getattr(other, name))

    def as_dict(self) -> dict[str, list[str]]:
        return {k: sorted(v) for k, v in vars(self).items() if v}


def scan_identifiers(obj, key: str = "") -> Identifiers:
    """Collect identifiers from a JSON-like value. Emails/user ids are found in free text too."""
    found = Identifiers()
    if obj is None or isinstance(obj, bool):
        return found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in REF_KEYS:
                continue
            found.update(scan_identifiers(v, k))
        return found
    if isinstance(obj, (list, tuple)):
        for v in obj:
            found.update(scan_identifiers(v, key))
        return found
    text = str(obj).strip()
    if not text:
        return found
    if PHONE_KEY.search(key):
        found.phones.add(normalize_phone(text))
        return found
    if key in NAME_KEYS:
        found.names.add(text)
        return found
    if RE_HASH.fullmatch(text):
        found.hashes.add(text.lower())
        return found
    found.emails.update(normalize_email(e) for e in RE_EMAIL.findall(text))
    found.user_ids.update(RE_USER_ID.findall(text))
    return found


def lookup_identifiers(value) -> Identifiers:
    """Identifiers from a lookup key / subject reference (an email or a user_id)."""
    return scan_identifiers(value, "subject_reference")


@dataclass
class Observation:
    obs_id: str
    file_id: str                 # evidence file_id, or activity_id for activity rows
    source_kind: str             # sql | json | txt | activity
    family: str                  # file family, e.g. sql_replica_pair
    available_at: datetime       # manifest captured_at (or activity event_time): cutoff field
    state_observed_at: datetime  # when the state was inspected
    system_id: str
    resource_id: str
    assertion: str
    physical_copy: str = PRIMARY
    collection: str = ""
    record_type: str = ""        # explicit record_type when the file states it
    record_updated_at: datetime | None = None
    exists: str | None = None    # PRESENT | ABSENT | None (no statement)
    treatment: str | None = None # IDENTIFIABLE | ANONYMIZED | REDACTED | None (derive from ids)
    flow_state: str | None = None
    restore_state: str | None = None
    link_ids: Identifiers = field(default_factory=Identifiers)     # usable to link a subject
    exposed_ids: Identifiers | None = None  # identifiers stored in the record (None: unknown)
    fields: dict = field(default_factory=dict)
    refs: tuple[str, ...] = ()   # other resource ids this record derives from
    detail: str = ""


@dataclass
class Scope:
    """A file lists every record of ``system_id``/``physical_copy`` at ``observed_at``.

    ``subjects`` is None for a full snapshot. Otherwise the listing is complete only for
    those subjects: the identifiers found in this system's (and collection's) own rows of the
    file, never those of a sibling system in the same file.
    """
    file_id: str
    family: str
    system_id: str
    physical_copy: str
    available_at: datetime
    observed_at: datetime
    collection: str = ""
    subjects: Identifiers | None = None


@dataclass
class Extraction:
    observations: list[Observation] = field(default_factory=list)
    scopes: list[Scope] = field(default_factory=list)
    family: str = ""
    rows_parsed: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str, n: int = 1) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + n


# Explicit result words used by read-back rows.
RESULT_STATES = {
    "FOUND": dict(exists=PRESENT),
    "NOT_FOUND": dict(exists=ABSENT),
    "IDENTIFIABLE": dict(exists=PRESENT, treatment=IDENTIFIABLE),
    "ANONYMIZED": dict(exists=PRESENT, treatment=ANONYMIZED),
    "REDACTED": dict(exists=PRESENT, treatment=REDACTED),
    "DISABLED": dict(exists=PRESENT, flow_state=DISABLED),
    "BLOCKED": dict(exists=PRESENT, restore_state=BLOCKED),
}


def result_state(result: str, record_type: str) -> dict:
    """Map a read-back result word to state fields. ACTIVE depends on the record type."""
    word = result.strip().upper()
    if word == "ACTIVE":
        if record_type == "DATA_FLOW":
            return dict(exists=PRESENT, flow_state=ACTIVE)
        if record_type == "BACKUP_ARCHIVE":
            return dict(exists=PRESENT, restore_state=OPEN)
        raise ShapeError(f"ACTIVE result for record type {record_type!r}")
    if word not in RESULT_STATES:
        raise ShapeError(f"unknown result {result!r}")
    return dict(RESULT_STATES[word])


def record_state(system_id: str, record: dict) -> dict:
    """State fields carried by a snapshot row's own columns."""
    state: dict = {"exists": PRESENT}
    for key in ("enabled",):
        if key in record and record[key] is not None:
            state["flow_state"] = ACTIVE if record[key] in (True, 1, "1", "true", "TRUE") else DISABLED
    if "restore_allowed" in record and record["restore_allowed"] is not None:
        state["restore_state"] = OPEN if record["restore_allowed"] in (True, 1, "1", "true", "TRUE") else BLOCKED
    return state


def resource_refs(record: dict) -> tuple[str, ...]:
    refs = []
    for key in REF_KEYS:
        value = record.get(key)
        if isinstance(value, str) and RE_RESOURCE_ID.fullmatch(value):
            refs.append(value)
    return tuple(refs)
