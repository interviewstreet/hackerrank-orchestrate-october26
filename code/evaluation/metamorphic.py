"""Metamorphic checks: input changes with a known effect on the output.

1. ``shuffle_rows``      - shuffled request order (samples) and shuffled global tables (custom
                           cases merged): every row is unchanged.
2. ``email_case_space``  - request emails in upper case with surrounding spaces: unchanged.
3. ``older_contradiction`` - an older read-back with the opposite result for every record of the
                           key file: unchanged (the newest observation wins).
4. ``audit_before_key``  - ``audit_at`` one second before the key file: that file is never cited
                           and the row changes.
5. ``audit_at_key``      - ``audit_at`` exactly at the key file time: unchanged (inclusive cutoff).
"""

from __future__ import annotations

import copy
import csv
import json
import random
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import custom
from loaders import DATASET_DIR, load_requests

SEED = 20261024
FLIP = {"FOUND": "NOT_FOUND", "NOT_FOUND": "FOUND", "ACTIVE": "DISABLED", "DISABLED": "ACTIVE"}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ledger_cases(cases: list[dict]) -> list[dict]:
    """Cases whose first evidence file is a read-back ledger and that need no agent."""
    return [c for c in cases if c["evidence"] and isinstance(c["evidence"][0]["content"], dict)
            and "records" in c["evidence"][0]["content"] and not c.get("agent_replies")
            and c["expected"]["deletion_status"] != "NOT_APPLICABLE"]


def _sample_rows(requests_path: Path, ctx) -> dict:
    pipeline = custom.load_pipeline()
    results = pipeline.run_cases(load_requests(requests_path), ctx)
    return {r.case_id: (r.status, pipeline.serialize_steps(r.steps)) for r in results}


def _rewrite_requests(src: Path, dst: Path, change) -> None:
    with open(src, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows, header = [change(dict(r)) for r in reader], reader.fieldnames
    with open(dst, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def sample_checks(ctx=None) -> list[dict]:
    """Shuffle and email checks on the 32 public samples (deterministic pipeline)."""
    pipeline = custom.load_pipeline()
    ctx = ctx or pipeline.build_context()
    src = DATASET_DIR / "sample_deletion_requests.csv"
    base = _sample_rows(src, ctx)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        rng = random.Random(SEED)
        shuffled = Path(tmp) / "shuffled.csv"
        with open(src, encoding="utf-8-sig", newline="") as handle:
            lines = handle.read().splitlines(keepends=True)
        body = lines[1:]
        rng.shuffle(body)
        shuffled.write_text("".join([lines[0]] + body), encoding="utf-8")
        out.append(_result("shuffle_rows:samples", _sample_rows(shuffled, ctx) == base))
        spaced = Path(tmp) / "spaced.csv"
        _rewrite_requests(src, spaced, lambda r: dict(r, email=f"  {r['email'].upper()} "))
        out.append(_result("email_case_space:samples", _sample_rows(spaced, ctx) == base))
    return out


def _result(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def custom_checks(cases: list[dict] | None = None) -> list[dict]:
    cases = cases if cases is not None else custom.load_cases()
    plain = [c for c in cases if not c.get("agent_replies")]
    out = []
    base = custom.run_cases(plain).rows
    rng = random.Random(SEED)

    def shuffle(rows):
        rows = list(rows)
        rng.shuffle(rows)
        return rows

    out.append(_result("shuffle_rows:custom", custom.run_cases(plain, materialize={"order": shuffle}).rows == base))
    spaced = [copy.deepcopy(c) for c in plain]
    for c in spaced:
        c["request"]["email"] = f" {c['request']['email'].upper()}  "
    out.append(_result("email_case_space:custom", custom.run_cases(spaced).rows == base))

    for case in _ledger_cases(cases):
        out.extend(_time_checks(case))
    return out


def _time_checks(case: dict) -> list[dict]:
    cid, name = case["request"]["case_id"], case["name"]
    key = case["evidence"][0]
    base = custom.run_cases([case]).rows[cid]
    out = []

    older = copy.deepcopy(case)
    at = _iso(_ts(key["captured_at"]) - timedelta(days=1))
    content = copy.deepcopy(key["content"])
    content["exported_at"] = at
    for rec in content["records"]:
        rec["recorded_at"], rec["result"] = at, FLIP.get(rec["result"], rec["result"])
    older["evidence"].append({"file_id": key["file_id"] + "0", "path": key["path"].replace(".json", "_older.json"),
                              "origin": key["origin"], "captured_at": at, "content": content})
    got = custom.run_cases([older]).rows[cid]
    out.append(_result(f"older_contradiction:{name}", got == base, "" if got == base else json.dumps(got)[:200]))

    before = copy.deepcopy(case)
    before["request"]["audit_at"] = _iso(_ts(key["captured_at"]) - timedelta(seconds=1))
    status, steps = custom.run_cases([before]).rows[cid]
    cited = {s["evidence_id"] for s in steps}
    out.append(_result(f"audit_before_key:{name}", key["file_id"] not in cited and (status, steps) != base,
                       f"{status} cites {sorted(cited - {''})}"))

    exact = copy.deepcopy(case)
    exact["request"]["audit_at"] = key["captured_at"]
    got = custom.run_cases([exact]).rows[cid]
    out.append(_result(f"audit_at_key:{name}", got == base))
    return out


def all_checks(ctx=None) -> list[dict]:
    return sample_checks(ctx) + custom_checks()
