"""Dataset loader: reads participant-facing CSVs once and builds in-memory indexes.

Only files under dataset/ that the task lists as participant-facing are read. Organizer-only data is never touched.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@dataclass
class EmailSpan:
    """An email address held by a user during [valid_from, valid_to). Empty bound = open-ended."""
    email: str
    valid_from: str
    valid_to: str
    audit_id: str = ""


@dataclass
class DatasetContext:
    dataset_dir: Path
    requests: List[Dict[str, str]]
    sample_requests: List[Dict[str, str]]
    identities: Dict[str, Dict[str, str]]            # user_id -> current identity row
    audit_log: List[Dict[str, str]]
    activities: List[Dict[str, str]]
    rules: Dict[str, Dict[str, str]]                 # data_category -> rule row
    manifest: Dict[str, Dict[str, str]]              # file_id -> manifest row (with absolute path)

    # indexes ----------------------------------------------------------------
    current_email_index: Dict[str, List[str]] = field(default_factory=dict)      # email -> [user_id]
    historical_email_index: Dict[str, List[str]] = field(default_factory=dict)   # any past/present email -> [user_id]
    email_spans: Dict[str, List[EmailSpan]] = field(default_factory=dict)        # user_id -> spans
    hash_index: Dict[str, List[str]] = field(default_factory=dict)               # email_hash (any era) -> [user_id]
    phone_index: Dict[str, List[str]] = field(default_factory=dict)              # phone (any era) -> [user_id]
    audit_by_user: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    activity_by_id: Dict[str, Dict[str, str]] = field(default_factory=dict)
    activity_by_resource: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    audit_by_id: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def users_for_email(self, email: str) -> List[str]:
        return self.historical_email_index.get((email or "").strip().lower(), [])


def load_dataset(dataset_dir: str | Path) -> DatasetContext:
    d = Path(dataset_dir)
    requests = _read_csv(d / "deletion_requests.csv")
    samples = _read_csv(d / "sample_deletion_requests.csv")
    identities = {r["user_id"]: r for r in _read_csv(d / "user_identities.csv")}
    audit_log = _read_csv(d / "user_audit_log.csv")
    activities = _read_csv(d / "system_activity.csv")
    rules = {r["data_category"]: r for r in _read_csv(d / "deletion_rules.csv")}
    manifest = {}
    for r in _read_csv(d / "evidence_files.csv"):
        r = dict(r)
        r["abs_path"] = str(d / r["file_path"])
        manifest[r["file_id"]] = r

    ctx = DatasetContext(d, requests, samples, identities, audit_log, activities, rules, manifest)
    _build_indexes(ctx)
    return ctx


def _add(index: Dict[str, List[str]], key: str, user_id: str) -> None:
    if key:
        bucket = index.setdefault(key, [])
        if user_id not in bucket:
            bucket.append(user_id)


def _build_indexes(ctx: DatasetContext) -> None:
    for uid, row in ctx.identities.items():
        _add(ctx.current_email_index, row["email"].strip().lower(), uid)
        _add(ctx.hash_index, row["email_hash"].strip().lower(), uid)
        _add(ctx.phone_index, row["phone"].strip(), uid)

    ctx.audit_by_id = {a["audit_id"]: a for a in ctx.audit_log}
    for a in ctx.audit_log:
        ctx.audit_by_user.setdefault(a["user_id"], []).append(a)
    for rows in ctx.audit_by_user.values():
        rows.sort(key=lambda a: a["event_time"])

    # Email timeline per user: walk the audit trail forward; each 'email' change closes one span and opens the next.
    for uid, row in ctx.identities.items():
        changes = [a for a in ctx.audit_by_user.get(uid, []) if a["field_name"] == "email"]
        spans: List[EmailSpan] = []
        if not changes:
            spans.append(EmailSpan(row["email"].strip().lower(), "", ""))
        else:
            spans.append(EmailSpan(changes[0]["old_value"].strip().lower(), "", changes[0]["event_time"], changes[0]["audit_id"]))
            for i, c in enumerate(changes):
                end = changes[i + 1]["event_time"] if i + 1 < len(changes) else ""
                spans.append(EmailSpan(c["new_value"].strip().lower(), c["event_time"], end, c["audit_id"]))
        ctx.email_spans[uid] = spans
        for s in spans:
            _add(ctx.historical_email_index, s.email, uid)

    for a in ctx.audit_log:
        if a["field_name"] == "email_hash":
            _add(ctx.hash_index, a["old_value"].strip().lower(), a["user_id"])
            _add(ctx.hash_index, a["new_value"].strip().lower(), a["user_id"])
        elif a["field_name"] == "phone":
            _add(ctx.phone_index, a["old_value"].strip(), a["user_id"])
            _add(ctx.phone_index, a["new_value"].strip(), a["user_id"])

    for act in ctx.activities:
        ctx.activity_by_id[act["activity_id"]] = act
        ctx.activity_by_resource.setdefault(act["resource_id"], []).append(act)


if __name__ == "__main__":
    import sys
    c = load_dataset(sys.argv[1] if len(sys.argv) > 1 else "dataset")
    multi = {e: u for e, u in c.historical_email_index.items() if len(u) > 1}
    print(f"requests={len(c.requests)} samples={len(c.sample_requests)} users={len(c.identities)} audit={len(c.audit_log)} "
          f"activities={len(c.activities)} rules={len(c.rules)} evidence={len(c.manifest)}")
    print(f"emails: current={len(c.current_email_index)} historical(any era)={len(c.historical_email_index)} shared-by-multiple-users={len(multi)}")
    unresolved = [r["case_id"] for r in c.requests if not c.users_for_email(r["email"])]
    print(f"requests whose email matches no user (current or historical): {len(unresolved)} {unresolved[:10]}")
