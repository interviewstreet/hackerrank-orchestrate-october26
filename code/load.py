"""
Dataset loader and input validator for Ghost Data Still Exists.

Exposes a single public function:
    load_dataset(root) -> dict[str, list[dict]]

Each value is a list of row-dicts (DictReader style).
Raises ValueError with a clear message on any schema or data problem.
Does NOT modify any source file.
"""

import csv
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Schema contract: required columns per file
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "deletion_requests": [
        "case_id", "email", "requested_at", "reported_status",
        "reported_at", "audit_at", "request_text",
    ],
    "sample_deletion_requests": [
        "case_id", "email", "requested_at", "reported_status",
        "reported_at", "audit_at", "request_text",
    ],
    "user_identities": [
        "user_id", "name", "email", "phone", "email_hash", "updated_at",
    ],
    "user_audit_log": [
        "audit_id", "user_id", "event_time", "field_name", "old_value", "new_value",
    ],
    "system_activity": [
        "activity_id", "event_time", "event_type", "source_system",
        "target_system", "resource_id", "reported_result", "details",
    ],
    "deletion_rules": [
        "rule_id", "data_category", "condition", "required_action",
    ],
    "evidence_files": [
        "file_id", "file_path", "origin", "captured_at",
    ],
}

# Columns that must not be blank in any row (row-level identifier checks)
REQUIRED_NONEMPTY: Dict[str, List[str]] = {
    "deletion_requests":        ["case_id", "email", "audit_at"],
    "sample_deletion_requests": ["case_id", "email", "audit_at"],
    "user_identities":          ["user_id", "email"],
    "user_audit_log":           ["audit_id", "user_id"],
    "system_activity":          ["activity_id"],
    "deletion_rules":           ["rule_id", "required_action"],
    "evidence_files":           ["file_id", "file_path"],
}

# File paths relative to the dataset directory
FILE_NAMES: Dict[str, str] = {
    "deletion_requests":        "deletion_requests.csv",
    "sample_deletion_requests": "sample_deletion_requests.csv",
    "user_identities":          "user_identities.csv",
    "user_audit_log":           "user_audit_log.csv",
    "system_activity":          "system_activity.csv",
    "deletion_rules":           "deletion_rules.csv",
    "evidence_files":           "evidence_files.csv",
}


def _load_csv(logical_name: str, path: Path) -> List[Dict[str, str]]:
    """Load a single CSV file, validate columns and required-nonempty fields.

    Returns a list of row-dicts (all values are strings, as read).
    Raises ValueError with a precise, actionable message on any problem.
    """
    if not path.exists():
        raise ValueError(f"Required file not found: {path}")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        actual_cols = reader.fieldnames or []

        # 1. Column presence check
        required = REQUIRED_COLUMNS[logical_name]
        missing = [c for c in required if c not in actual_cols]
        if missing:
            raise ValueError(
                f"[{logical_name}] Missing required column(s): {missing} "
                f"(found: {list(actual_cols)}) in file: {path.name}"
            )

        # 2. Row-level checks
        nonempty_cols = REQUIRED_NONEMPTY.get(logical_name, [])
        rows = []
        for row_num, row in enumerate(reader, start=2):  # row 1 is header
            for col in nonempty_cols:
                if not row.get(col, "").strip():
                    raise ValueError(
                        f"[{logical_name}] Empty required field '{col}' "
                        f"at row {row_num} in file: {path.name}"
                    )
            rows.append(dict(row))

    return rows


def load_dataset(root: Path | None = None) -> Dict[str, List[Dict[str, str]]]:
    """Load and validate all required datasets.

    Args:
        root: Repository root. Defaults to the parent of this file's directory
            (i.e. the repo root when code/ is a sub-directory).

    Returns:
        dict keyed by logical name -> list of row dicts.

    Raises:
        ValueError: On missing files, schema violations, or empty required fields.
    """
    if root is None:
        root = Path(__file__).resolve().parent.parent

    dataset_dir = root / "dataset"

    result: Dict[str, List[Dict[str, str]]] = {}
    for logical_name, filename in FILE_NAMES.items():
        path = dataset_dir / filename
        result[logical_name] = _load_csv(logical_name, path)

    # ---------------------------------------------------------------------------
    # Cross-file consistency check: every deletion_request case_id must be
    # resolvable to at least one known email in user_identities or user_audit_log.
    # We collect all known emails once for efficiency.
    # ---------------------------------------------------------------------------
    known_emails = {
        row["email"].strip().lower()
        for row in result["user_identities"]
        if row.get("email", "").strip()
    }
    historical_emails = {
        row["new_value"].strip().lower()
        for row in result["user_audit_log"]
        if row.get("field_name", "").strip() == "email" and row.get("new_value", "").strip()
    } | {
        row["old_value"].strip().lower()
        for row in result["user_audit_log"]
        if row.get("field_name", "").strip() == "email" and row.get("old_value", "").strip()
    }
    all_known_emails = known_emails | historical_emails

    unresolvable = []
    for row in result["deletion_requests"]:
        email = row.get("email", "").strip().lower()
        if email and email not in all_known_emails:
            unresolvable.append((row["case_id"], row["email"]))

    if unresolvable:
        # Report but do NOT raise — these may be intentional edge-cases in the
        # challenge (e.g. requests with no matching account). Surface as a
        # warning so the caller can decide.
        result["__warnings__"] = [  # type: ignore[assignment]
            {
                "type": "UNRESOLVABLE_EMAIL",
                "case_id": cid,
                "email": em,
                "message": (
                    f"case_id={cid}: email '{em}' not found in "
                    "user_identities or user_audit_log"
                ),
            }
            for cid, em in unresolvable
        ]

    return result
