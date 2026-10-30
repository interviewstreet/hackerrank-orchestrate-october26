"""CSV loaders and normalization helpers for the participant dataset."""
from __future__ import annotations

import csv
import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .models import Activity, AuditEntry, Case, EvidenceFile, Identity, Rule

# Unicode-aware: internationalised addresses (e.g. Cyrillic local part and IDN domain) are emails too
EMAIL_RE = re.compile(r"[\w.%+\-]+@[\w\-]+(?:\.[\w\-]+)*\.[^\W\d_]{2,}")
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
USER_RE = re.compile(r"\buser_\d+\b")
log = logging.getLogger(__name__)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    if not v or v.lower() in {"null", "none"}:
        return None
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ts(value: str | None, where: str) -> datetime | None:
    """parse_ts that reports a value which is present but not a real instant (e.g. 2026-02-29)."""
    dt = parse_ts(value)
    if dt is None and value and value.strip().lower() not in {"null", "none"}:
        log.warning("unreadable timestamp %r in %s", value, where)
    return dt


def normalize_text(value: str) -> str:
    """Canonical form for matching: NFKC (composed é == e + combining accent, full-width == ASCII) + casefold."""
    return unicodedata.normalize("NFKC", value or "").strip().casefold()


def normalize_email(value: str) -> str:
    return normalize_text(value)


def normalize_phone(value: str) -> str:
    v = (value or "").strip()
    digits = re.sub(r"\D", "", v)
    return ("+" + digits) if v.startswith("+") else digits


def email_hash(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def _rows(path: Path) -> list[dict]:
    # utf-8-sig: a CSV re-saved by a spreadsheet tool starts with a byte-order mark that would rename column 1
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    # tolerate padded header names (" case_id")
    return [{(k or "").strip(): v for k, v in r.items()} for r in rows]


def load_cases(path: Path) -> list[Case]:
    """An unreadable requested_at/reported_at falls back to the other one; an unreadable audit_at stays None
    and is resolved by the pipeline (no cutoff)."""
    cases = []
    for r in _rows(path):
        cid = r["case_id"].strip()
        requested = _ts(r["requested_at"], f"{cid}.requested_at")
        reported = _ts(r["reported_at"], f"{cid}.reported_at")
        cases.append(Case(
            case_id=cid,
            email=r["email"],
            requested_at=requested or reported,
            reported_status=r["reported_status"].strip(),
            reported_at=reported or requested,
            audit_at=_ts(r["audit_at"], f"{cid}.audit_at"),
            request_text=r["request_text"],
        ))
    return cases


def load_rules(path: Path) -> list[Rule]:
    return [Rule(r["rule_id"], r["data_category"], r["condition"], r["required_action"]) for r in _rows(path)]


def load_manifest(path: Path, dataset_root: Path) -> list[EvidenceFile]:
    """A file whose capture time cannot be read cannot be placed before any cutoff, so it is skipped."""
    out = []
    root = dataset_root.resolve()
    for r in _rows(path):
        captured = _ts(r["captured_at"], f"evidence_files.csv {r['file_id']}")
        if captured is None:
            continue
        file_path = (root / r["file_path"]).resolve()
        if not file_path.is_relative_to(root):
            # an absolute path or "../" must not make the agent read outside the dataset
            log.warning("evidence_files.csv %s points outside the dataset (%s); skipped", r["file_id"], r["file_path"])
            continue
        out.append(EvidenceFile(r["file_id"], file_path, r["origin"], captured))
    return out


def load_identities(path: Path) -> list[Identity]:
    return [
        Identity(r["user_id"], r["name"], r["email"], r["phone"], r["email_hash"], parse_ts(r["updated_at"]))
        for r in _rows(path)
    ]


def load_audit_log(path: Path) -> list[AuditEntry]:
    return [
        AuditEntry(r["audit_id"], r["user_id"], _ts(r["event_time"], f"user_audit_log.csv {r['audit_id']}"),
                   r["field_name"], r["old_value"], r["new_value"])
        for r in _rows(path)
    ]


def load_activity(path: Path) -> list[Activity]:
    """An event whose time cannot be read cannot be placed before any cutoff, so it is skipped."""
    out = []
    for r in _rows(path):
        t = _ts(r["event_time"], f"system_activity.csv {r['activity_id']}")
        if t is not None:
            out.append(Activity(r["activity_id"], t, r["event_type"], r["source_system"],
                                r["target_system"], r["resource_id"], r["reported_result"], r["details"]))
    return out


def natural_case_key(case_id: str) -> tuple:
    """Natural order: digit runs compare as numbers (case_99 < case_100, case_e01a right after case_e01). On the
    dataset this is exactly the order of deletion_requests.csv."""
    return tuple((0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", case_id)) + ((-1, 0, case_id),)


def case_sort_key(case_id: str):
    m = re.search(r"(\d+)$", case_id)
    return (case_id.rstrip("0123456789"), int(m.group(1)) if m else -1, case_id)
