import csv
import io
import os
import tempfile
from pathlib import Path

import pytest

from code.load import load_dataset, _load_csv, REQUIRED_COLUMNS, REQUIRED_NONEMPTY


def test_load_dataset_success():
    """Load the real dataset – should succeed and return non‑empty tables."""
    data = load_dataset()
    # all logical tables should be present
    expected_keys = {
        "deletion_requests",
        "sample_deletion_requests",
        "user_identities",
        "user_audit_log",
        "system_activity",
        "deletion_rules",
        "evidence_files",
    }
    assert expected_keys.issubset(set(data.keys()))
    for key in expected_keys:
        assert isinstance(data[key], list)
        assert len(data[key]) > 0  # at least one row in each file


def _temp_csv(content: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(content)
    return Path(path)


def test_missing_column_raises():
    # Create a CSV for deletion_requests missing the 'case_id' column
    header = ",".join([c for c in REQUIRED_COLUMNS["deletion_requests"] if c != "case_id"])
    rows = "test@example.com,2026-01-01T00:00:00Z,COMPLETE,2026-01-02T00:00:00Z,2026-01-03T00:00:00Z,Sample text"
    csv_path = _temp_csv(f"{header}\n{rows}\n")
    with pytest.raises(ValueError) as exc:
        _load_csv("deletion_requests", csv_path)
    assert "Missing required column" in str(exc.value)
    csv_path.unlink()


def test_empty_required_field_raises():
    # Create a CSV for user_identities where the 'email' column is empty for a row
    header = ",".join(REQUIRED_COLUMNS["user_identities"])
    rows = "user_01,John Doe,,+1234567890,abcdef,2026-01-01T00:00:00Z"
    csv_path = _temp_csv(f"{header}\n{rows}\n")
    with pytest.raises(ValueError) as exc:
        _load_csv("user_identities", csv_path)
    assert "Empty required field 'email'" in str(exc.value)
    csv_path.unlink()
