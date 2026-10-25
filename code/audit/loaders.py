"""CSV loading, timestamp parsing (timezone-aware UTC) and id helpers."""
import csv
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_ts(value):
    """Parse an ISO-8601 timestamp to an aware UTC datetime (or None)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("null", "none", "nan"):
        return None
    # Dates like "2033-12-31T23:59:59Z" and plain dates are both supported.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fmt_ts(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


_CASE_NUM = re.compile(r"(\d+)\s*$")


def case_sort_key(case_id):
    """Natural order for case ids: case_33 < case_100 (not string order)."""
    m = _CASE_NUM.search(str(case_id))
    return (int(m.group(1)) if m else 0, str(case_id))


def load_dataset(dataset_dir, requests_file="deletion_requests.csv"):
    dataset_dir = Path(dataset_dir)
    return {
        "requests": load_csv(dataset_dir / requests_file),
        "identities": load_csv(dataset_dir / "user_identities.csv"),
        "audit_log": load_csv(dataset_dir / "user_audit_log.csv"),
        "activity": load_csv(dataset_dir / "system_activity.csv"),
        "rules": load_csv(dataset_dir / "deletion_rules.csv"),
        "evidence_files": load_csv(dataset_dir / "evidence_files.csv"),
    }
