"""CSV ingestion for participant-facing data."""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_evidence_index(repo_root: str | Path) -> dict[str, dict[str, str]]:
    rows = _rows(Path(repo_root).resolve() / "dataset" / "evidence_files.csv")
    return {row["file_id"]: row for row in rows}


def load_all(repo_root: str | Path) -> dict:
    dataset = Path(repo_root).resolve() / "dataset"
    requests = _rows(dataset / "deletion_requests.csv")
    samples = _rows(dataset / "sample_deletion_requests.csv")
    sample_output_rows = _rows(dataset / "sample_output.csv")
    identities = _rows(dataset / "user_identities.csv")
    audits = _rows(dataset / "user_audit_log.csv")
    activity = sorted(_rows(dataset / "system_activity.csv"), key=lambda r: r["event_time"])
    rules = _rows(dataset / "deletion_rules.csv")
    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in audits:
        by_user[row["user_id"]].append(row)
    for events in by_user.values():
        events.sort(key=lambda r: r["event_time"])
    by_resource: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in activity:
        by_resource[row["resource_id"]].append(row)
    by_id = {row["user_id"]: row for row in identities}
    by_email = {row["email"].casefold(): row for row in identities if row.get("email")}
    return {
        "deletion_requests": requests,
        "sample_requests": samples,
        "sample_output": {r["case_id"]: r for r in sample_output_rows},
        "user_identities": by_id,
        "user_identities_by_email": by_email,
        "user_audit_log": dict(by_user),
        "system_activity": activity,
        "system_activity_by_resource": dict(by_resource),
        "deletion_rules": {r["data_category"]: r for r in rules},
        "evidence_manifest": load_evidence_index(repo_root),
    }
