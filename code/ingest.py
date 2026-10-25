"""Validated CSV ingestion for participant-facing data."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

SCHEMAS = {
    "deletion_requests.csv": ("case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"),
    "sample_deletion_requests.csv": ("case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text"),
    "sample_output.csv": ("case_id", "deletion_status", "steps_json"),
    "user_identities.csv": ("user_id", "name", "email", "phone", "email_hash", "updated_at"),
    "user_audit_log.csv": ("audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"),
    "system_activity.csv": ("activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id", "reported_result", "details"),
    "deletion_rules.csv": ("rule_id", "data_category", "condition", "required_action"),
    "evidence_files.csv": ("file_id", "file_path", "origin", "captured_at"),
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = SCHEMAS.get(path.name)
        if expected and tuple(reader.fieldnames or ()) != expected:
            raise ValueError(
                f"{path.name} columns do not match contract: "
                f"expected {expected}, got {tuple(reader.fieldnames or ())}"
            )
        return list(reader)


def _index_unique(rows, key, source):
    result = {}
    for row in rows:
        value = row.get(key, "")
        if not value:
            raise ValueError(f"{source} contains a blank {key}")
        if value in result:
            raise ValueError(f"{source} contains duplicate {key}: {value}")
        result[value] = row
    return result


def load_evidence_index(repo_root: str | Path) -> dict[str, dict[str, str]]:
    rows = _rows(Path(repo_root).resolve() / "dataset" / "evidence_files.csv")
    return _index_unique(rows, "file_id", "evidence_files.csv")


def load_all(repo_root: str | Path, include_sample_output=True) -> dict:
    dataset = Path(repo_root).resolve() / "dataset"
    requests = _rows(dataset / "deletion_requests.csv")
    samples = _rows(dataset / "sample_deletion_requests.csv")
    sample_output_rows = (
        _rows(dataset / "sample_output.csv") if include_sample_output else []
    )
    identities = _rows(dataset / "user_identities.csv")
    audits = _rows(dataset / "user_audit_log.csv")
    activity = sorted(_rows(dataset / "system_activity.csv"), key=lambda row: row["event_time"])
    rules = _rows(dataset / "deletion_rules.csv")

    requests_by_id = _index_unique(requests, "case_id", "deletion_requests.csv")
    samples_by_id = _index_unique(samples, "case_id", "sample_deletion_requests.csv")
    sample_output = _index_unique(sample_output_rows, "case_id", "sample_output.csv")
    by_id = _index_unique(identities, "user_id", "user_identities.csv")
    rules_by_category = _index_unique(rules, "data_category", "deletion_rules.csv")
    _index_unique(activity, "activity_id", "system_activity.csv")
    _index_unique(audits, "audit_id", "user_audit_log.csv")

    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in audits:
        by_user[row["user_id"]].append(row)
    for events in by_user.values():
        events.sort(key=lambda row: row["event_time"])

    by_resource: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in activity:
        by_resource[row["resource_id"]].append(row)

    by_email = {}
    for row in identities:
        email = row.get("email", "").casefold()
        if email in by_email:
            raise ValueError(f"user_identities.csv contains duplicate current email: {email}")
        if email:
            by_email[email] = row

    return {
        "deletion_requests": list(requests_by_id.values()),
        "sample_requests": list(samples_by_id.values()),
        "sample_output": sample_output,
        "user_identities": by_id,
        "user_identities_by_email": by_email,
        "user_audit_log": dict(by_user),
        "system_activity": activity,
        "system_activity_by_resource": dict(by_resource),
        "deletion_rules": rules_by_category,
        "evidence_manifest": load_evidence_index(repo_root),
    }
