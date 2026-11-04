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

A case that raises an error is written as INCOMPLETE with [] and reported,
so output.csv is always written with one row per request.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evidence_search import find_records
from identity_resolver import IdentityResolver
from models import EVIDENCE_KEYS, ClassificationResult
from policy_engine import decide
from request_classifier import classify_request
from step_builder import build_steps
from utils import parse_ts, warn

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
OUTPUT_PATH = REPO_ROOT / "output.csv"

VALID_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def _case_sort_key(case_id: str) -> tuple:
    """case_2 < case_10 (numeric), falling back to text for odd IDs."""
    m = re.fullmatch(r"(.*?)(\d+)", case_id)
    return (m.group(1), int(m.group(2))) if m else (case_id, -1)


def _check_evidence(evidence, case_id: str) -> None:
    """Enforce the P2 -> P3 contract (CONTRACTS.md, section 1)."""
    if not isinstance(evidence, dict):
        raise TypeError(f"find_records() must return a dict, got {type(evidence).__name__}")
    missing = [k for k in EVIDENCE_KEYS if k not in evidence]
    if missing:
        raise KeyError(f"find_records() result is missing key(s): {', '.join(missing)}")
    extra = sorted(set(evidence) - set(EVIDENCE_KEYS))
    if extra:
        warn(f"{case_id}: find_records() returned extra key(s) {', '.join(extra)}; "
             "add them to CONTRACTS.md if P3 should use them")


def process_case(case: dict, resolver: IdentityResolver) -> tuple[str, list, str]:
    """
    Return (deletion_status, steps, classifier_label) for one request row.
    May raise; run_case() catches errors.
    """
    case_id = case["case_id"]

    cls = classify_request(case["request_text"])
    if cls.label == ClassificationResult.NOT_APPLICABLE:
        return "NOT_APPLICABLE", [], cls.label
    if cls.label == ClassificationResult.UNCERTAIN:
        warn(f"{case_id}: classifier UNCERTAIN ({cls.note}); treating as deletion")

    audit_at = parse_ts(case.get("audit_at"), context=f"{case_id} audit_at")
    if audit_at is None:
        warn(f"{case_id}: no audit_at, so identifiers are not time-filtered")

    # Empty requested_at -> warning; the resolver then looks up the owner at audit_at
    requested_at = parse_ts(case.get("requested_at"), context=f"{case_id} requested_at")

    identity = resolver.resolve(case["email"], audit_at=audit_at,
                                requested_at=requested_at, case_id=case_id)
    if identity is None:
        warn(f"{case_id}: email could not be resolved to a user; output INCOMPLETE []")
        return "INCOMPLETE", [], cls.label

    evidence = find_records(identity, case)
    _check_evidence(evidence, case_id)

    decision = decide(identity, evidence, case)
    if not isinstance(decision, dict):
        raise TypeError(f"decide() must return a dict, got {type(decision).__name__}")
    status = decision.get("deletion_status")
    if status not in ("COMPLETE", "INCOMPLETE"):
        warn(f"{case_id}: decide() returned status {status!r}; using INCOMPLETE")
        status = "INCOMPLETE"

    steps = build_steps(decision)
    if not isinstance(steps, list):
        raise TypeError(f"build_steps() must return a list, got {type(steps).__name__}")
    return status, steps, cls.label


def run_case(case: dict, resolver: IdentityResolver) -> tuple[str, str, str, bool]:
    """
    Run one case safely. Returns (deletion_status, steps_json, classifier_label,
    failed). Any error becomes INCOMPLETE with [] and a warning.
    """
    case_id = case.get("case_id", "?")
    try:
        status, steps, label = process_case(case, resolver)
        # Deterministic, compact JSON; keep non-ASCII as-is
        steps_json = json.dumps(steps, ensure_ascii=False, separators=(",", ":"))
        return status, steps_json, label, False
    except Exception as exc:  # noqa: BLE001 — one bad case must not stop the run
        warn(f"{case_id}: {type(exc).__name__}: {exc}; output INCOMPLETE []")
        return "INCOMPLETE", "[]", "", True


def main() -> int:
    with open(DATASET_DIR / "deletion_requests.csv", newline="", encoding="utf-8") as fh:
        cases = list(csv.DictReader(fh))

    resolver = IdentityResolver(
        DATASET_DIR / "user_identities.csv",
        DATASET_DIR / "user_audit_log.csv",
    )

    rows: list[tuple[str, str, str]] = []
    uncertain: list[str] = []
    failed: list[str] = []
    for case in cases:
        status, steps_json, label, err = run_case(case, resolver)
        assert status in VALID_STATUSES, f"{case['case_id']}: bad status {status!r}"
        rows.append((case["case_id"], status, steps_json))
        if label == ClassificationResult.UNCERTAIN:
            uncertain.append(case["case_id"])
        if err:
            failed.append(case["case_id"])

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
    sort = lambda ids: sorted(ids, key=_case_sort_key)  # noqa: E731
    print(f"UNCERTAIN (treated as deletion, review by hand): {len(uncertain)}"
          + (f" -> {', '.join(sort(uncertain))}" if uncertain else ""))
    print(f"Cases that raised an error (written INCOMPLETE []): {len(failed)}"
          + (f" -> {', '.join(sort(failed))}" if failed else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
