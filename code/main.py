"""
main.py — entry point for the Ghost Data Still Exists deletion-audit pipeline.

Run from anywhere:
    python3 code/main.py

Reads dataset/ and writes output.csv at the repository root.

Pipeline per case:
    0. classify_request()         request_classifier.py   (Person 1)
    1. IdentityResolver.resolve() identity_resolver.py    (Person 1)
    2. find_records()             evidence_search.py      (Person 2)
    3. decide()                   policy_engine.py        (Person 3)
    4. build_steps()              step_builder.py         (Person 4)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evidence_search import find_records
from identity_resolver import IdentityResolver
from models import ClassificationResult
from policy_engine import decide
from request_classifier import classify_request
from step_builder import build_steps

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
OUTPUT_PATH = REPO_ROOT / "output.csv"

VALID_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def _parse_dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _case_sort_key(case_id: str) -> tuple:
    """case_2 < case_10 (numeric), falling back to text for odd IDs."""
    m = re.fullmatch(r"(.*?)(\d+)", case_id)
    return (m.group(1), int(m.group(2))) if m else (case_id, -1)


def _warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def process_case(case: dict, resolver: IdentityResolver) -> tuple[str, list[dict]]:
    """Return (deletion_status, steps) for one request row."""
    case_id = case["case_id"]

    cls = classify_request(case["request_text"])
    if cls.label == ClassificationResult.NOT_APPLICABLE:
        return "NOT_APPLICABLE", []
    if cls.label == ClassificationResult.UNCERTAIN:
        _warn(f"{case_id}: classifier UNCERTAIN ({cls.note}); treating as deletion")

    identity = resolver.resolve(case["email"], audit_at=_parse_dt(case["audit_at"]))
    if identity is None:
        _warn(f"{case_id}: email could not be resolved to a user; output INCOMPLETE []")
        return "INCOMPLETE", []

    records = find_records(identity, case)
    decision = decide(identity, records, case)
    status = decision.get("deletion_status")
    if status not in ("COMPLETE", "INCOMPLETE"):
        _warn(f"{case_id}: decide() returned status {status!r}; using INCOMPLETE")
        status = "INCOMPLETE"
    steps = build_steps(decision)
    return status, steps


def main() -> int:
    with open(DATASET_DIR / "deletion_requests.csv", newline="", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))

    resolver = IdentityResolver(
        DATASET_DIR / "user_identities.csv",
        DATASET_DIR / "user_audit_log.csv",
    )

    rows: list[tuple[str, str, str]] = []
    for case in cases:
        status, steps = process_case(case, resolver)
        assert status in VALID_STATUSES, f"{case['case_id']}: bad status {status!r}"
        # Deterministic, compact JSON; keep non-ASCII as-is
        steps_json = json.dumps(steps, ensure_ascii=False, separators=(",", ":"))
        rows.append((case["case_id"], status, steps_json))

    rows.sort(key=lambda r: _case_sort_key(r[0]))

    ids = [r[0] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("ERROR: duplicate case_id in output")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        writer.writerows(rows)

    counts = Counter(r[1] for r in rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    for status in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"):
        print(f"  {status:<15} {counts.get(status, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
