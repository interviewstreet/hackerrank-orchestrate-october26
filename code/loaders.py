"""Load participant-facing dataset files with normalized times and identifiers.

Every timestamp becomes a timezone-aware UTC ``datetime``. Emails are trimmed and
lower-cased. ``email_hash`` is SHA-256 of the normalized email (hex digest).
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"


# ---------------------------------------------------------------- normalizers

def parse_ts(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp to an aware UTC datetime. Naive input is UTC."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def require_ts(value: str | None) -> datetime:
    """``parse_ts`` for a required field: a missing value is a data error, not a silent None."""
    dt = parse_ts(value)
    if dt is None:
        raise ValueError("missing required timestamp")
    return dt


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def email_hash(value: str | None) -> str:
    """SHA-256 hex digest of the normalized email."""
    return hashlib.sha256(normalize_email(value).encode("utf-8")).hexdigest()


def normalize_phone(value: str | None) -> str:
    """Digits only, keeping a leading '+' so country codes stay distinct."""
    text = (value or "").strip()
    digits = re.sub(r"\D", "", text)
    return ("+" + digits) if text.startswith("+") and digits else digits


def case_number(case_id: str) -> int:
    """Integer suffix of a case id: 'case_100' -> 100. Used for numeric row order."""
    match = re.fullmatch(r"case_(\d+)", case_id.strip())
    if not match:
        raise ValueError(f"bad case_id: {case_id!r}")
    return int(match.group(1))


# ---------------------------------------------------------------- records

@dataclass(frozen=True)
class Request:
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime | None
    audit_at: datetime
    request_text: str


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


@dataclass(frozen=True)
class Rule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass(frozen=True)
class EvidenceFile:
    file_id: str
    file_path: str
    origin: str
    captured_at: datetime

    def abs_path(self, dataset_dir: Path = DATASET_DIR) -> Path:
        return dataset_dir / self.file_path


@dataclass
class Dataset:
    identities: list[Identity] = field(default_factory=list)
    audit_log: list[AuditEntry] = field(default_factory=list)
    activity: list[Activity] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    evidence_files: list[EvidenceFile] = field(default_factory=list)


# ---------------------------------------------------------------- readers

def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_requests(path: Path) -> list[Request]:
    out = []
    for row in read_csv(path):
        out.append(Request(
            case_id=row["case_id"].strip(),
            email=normalize_email(row["email"]),
            requested_at=require_ts(row["requested_at"]),
            reported_status=row["reported_status"].strip(),
            reported_at=parse_ts(row.get("reported_at")),
            audit_at=require_ts(row["audit_at"]),
            request_text=row["request_text"],
        ))
    return out


def load_identities(path: Path) -> list[Identity]:
    return [Identity(
        user_id=row["user_id"].strip(),
        name=row["name"].strip(),
        email=normalize_email(row["email"]),
        phone=row["phone"].strip(),
        email_hash=row["email_hash"].strip().lower(),
        updated_at=require_ts(row["updated_at"]),
    ) for row in read_csv(path)]


def load_audit_log(path: Path) -> list[AuditEntry]:
    out = []
    for row in read_csv(path):
        field_name = row["field_name"].strip()
        old, new = row["old_value"].strip(), row["new_value"].strip()
        if field_name == "email":
            old, new = normalize_email(old), normalize_email(new)
        elif field_name == "email_hash":
            old, new = old.lower(), new.lower()
        out.append(AuditEntry(row["audit_id"].strip(), row["user_id"].strip(),
                              require_ts(row["event_time"]), field_name, old, new))
    return out


def load_activity(path: Path) -> list[Activity]:
    return [Activity(
        activity_id=row["activity_id"].strip(),
        event_time=require_ts(row["event_time"]),
        event_type=row["event_type"].strip(),
        source_system=row["source_system"].strip(),
        target_system=row["target_system"].strip(),
        resource_id=row["resource_id"].strip(),
        reported_result=row["reported_result"].strip(),
        details=row["details"],
    ) for row in read_csv(path)]


def load_rules(path: Path) -> list[Rule]:
    return [Rule(row["rule_id"].strip(), row["data_category"].strip(),
                 row["condition"].strip(), row["required_action"].strip())
            for row in read_csv(path)]


def load_evidence_files(path: Path) -> list[EvidenceFile]:
    return [EvidenceFile(row["file_id"].strip(), row["file_path"].strip(),
                         row["origin"].strip(), require_ts(row["captured_at"]))
            for row in read_csv(path)]


def load_dataset(dataset_dir: Path = DATASET_DIR) -> Dataset:
    """Load every global (non-request) dataset file."""
    return Dataset(
        identities=load_identities(dataset_dir / "user_identities.csv"),
        audit_log=load_audit_log(dataset_dir / "user_audit_log.csv"),
        activity=load_activity(dataset_dir / "system_activity.csv"),
        rules=load_rules(dataset_dir / "deletion_rules.csv"),
        evidence_files=load_evidence_files(dataset_dir / "evidence_files.csv"),
    )


def email_hash_match_report(data: Dataset) -> dict[str, tuple[int, int]]:
    """Check email_hash == SHA-256(normalized email) for the snapshot and audit pairs.

    Audit pairs join an ``email`` row and an ``email_hash`` row of the same user at
    the same ``event_time``. Returns ``{source: (matched, total)}``.
    """
    current = sum(email_hash(i.email) == i.email_hash for i in data.identities)
    by_key: dict[tuple[str, datetime], dict[str, AuditEntry]] = {}
    for entry in data.audit_log:
        if entry.field_name in ("email", "email_hash"):
            by_key.setdefault((entry.user_id, entry.event_time), {})[entry.field_name] = entry
    matched = total = 0
    for pair in by_key.values():
        if "email" not in pair or "email_hash" not in pair:
            total += 1  # unpaired change counts as a miss
            continue
        for side in ("old_value", "new_value"):
            total += 1
            matched += email_hash(getattr(pair["email"], side)) == getattr(pair["email_hash"], side)
    return {"current": (current, len(data.identities)), "audit_pairs": (matched, total)}
