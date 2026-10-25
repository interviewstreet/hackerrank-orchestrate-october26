"""Self-supervised lineage examples from participant-visible identity edges.

This module intentionally does not read public expected output. It emits only in-memory
examples and aggregate reports; exact user/resource pairs are never persisted as a
runtime mapping. Stage 3 may train aggregate numeric weights from these examples.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from code.evidence import _contains

RESOURCE_RE = re.compile(
    r"\b(?:account|search|support|analytics|export|backup|data_flow|audit_record|"
    r"tombstone|cache|marketing|email_delivery|object|telemetry|legal)_[A-Za-z0-9.-]+\b",
    re.IGNORECASE,
)
TRACE_RE = re.compile(r"\btrace_id[=:]\s*\"?([^\s\",;]+)", re.IGNORECASE)

FEATURES = (
    "direct_identifier_match",
    "stable_reference_match",
    "catalog_link",
    "same_trace",
    "workflow_dependency",
    "same_artifact",
    "same_system",
    "competing_subject",
)


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _identity_tokens(dataset: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for row in _csv_rows(dataset / "user_identities.csv"):
        user_id = row["user_id"]
        result[user_id].append(user_id)
        for key in ("email", "phone", "email_hash"):
            if row.get(key):
                result[user_id].append(row[key])
    for row in _csv_rows(dataset / "user_audit_log.csv"):
        if row.get("field_name") not in {"email", "phone", "email_hash"}:
            continue
        for key in ("old_value", "new_value"):
            if row.get(key):
                result[row["user_id"]].append(row[key])
    return {user: list(dict.fromkeys(values)) for user, values in result.items()}


def _system(resource_id: str) -> str:
    prefix = resource_id.casefold()
    for value, system in (
        ("account_", "account_service"), ("search_", "search_service"),
        ("support_", "support_platform"), ("analytics_", "analytics_platform"),
        ("export_", "export_service"), ("backup_", "backup_service"),
        ("data_flow_", "integration_service"), ("audit_record_", "security_service"),
        ("tombstone_", "identity_service"), ("cache_", "cache_service"),
        ("marketing_", "marketing_platform"),
        ("email_delivery_", "email_delivery_service"),
        ("telemetry_", "telemetry_service"), ("legal_", "legal_service"),
        ("object_", "object_storage"),
    ):
        if prefix.startswith(value):
            return system
    return "unknown"


def _resources(text: str) -> list[str]:
    # Supplied resource IDs contain a numeric component. Requiring one prevents
    # service names (account_service) and event names (audit_record_read_completed)
    # from becoming mislabeled resources merely because they share a prefix.
    values = [match.group(0) for match in RESOURCE_RE.finditer(text)]
    return list(dict.fromkeys(value for value in values if any(ch.isdigit() for ch in value)))


def _context(source_id: str, available_at: str, text: str, *, source_kind: str,
             catalog_link: bool = False, same_trace: bool = False) -> dict:
    return {
        "source_id": source_id,
        "available_at": available_at,
        "text": text,
        "source_kind": source_kind,
        "catalog_link": int(catalog_link),
        "same_trace": int(same_trace),
        "resources": _resources(text),
    }


def _json_contexts(value, source_id: str, available_at: str, path=""):
    if isinstance(value, dict):
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        direct = str(value.get("resource_id") or value.get("id") or "")
        if direct and RESOURCE_RE.fullmatch(direct):
            yield _context(source_id, available_at, serialized, source_kind="evidence_json")
        for key, child in value.items():
            yield from _json_contexts(child, source_id, available_at, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _json_contexts(child, source_id, available_at, f"{path}/{index}")


def _text_contexts(text: str, source_id: str, available_at: str, source_kind: str):
    groups: dict[str, list[str]] = defaultdict(list)
    lines = text.splitlines()
    for line in lines:
        trace = TRACE_RE.search(line)
        if trace:
            groups[trace.group(1)].append(line)
        elif _resources(line):
            yield _context(source_id, available_at, line, source_kind=source_kind)
    for grouped in groups.values():
        joined = " ".join(grouped)
        if _resources(joined):
            yield _context(
                source_id, available_at, joined, source_kind=source_kind,
                same_trace=len(grouped) > 1,
            )


def _read_evidence(path: Path) -> str:
    try:
        if path.suffix.casefold() == ".pdf":
            from code.evidence import _extract_pdf_text
            return _extract_pdf_text(str(path.resolve()))
        if path.suffix.casefold() == ".png":
            from code.evidence import _extract_image_text
            return _extract_image_text(str(path.resolve()))
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ImportError, RuntimeError):
        return ""


def _contexts(dataset: Path) -> list[dict]:
    result = []
    for row in _csv_rows(dataset / "system_activity.csv"):
        text = " ".join(str(row.get(key, "")) for key in (
            "resource_id", "details", "source_system", "target_system"
        ))
        result.append(_context(
            row["activity_id"], row["event_time"], text, source_kind="activity",
            catalog_link=row.get("event_type", "").upper() == "LINK_RESOURCE_IDENTITY",
        ))
    for item in _csv_rows(dataset / "evidence_files.csv"):
        path = dataset / item["file_path"]
        text = _read_evidence(path)
        if path.suffix.casefold() == ".json":
            try:
                result.extend(_json_contexts(
                    json.loads(text), item["file_id"], item["captured_at"]
                ))
            except json.JSONDecodeError:
                pass
        else:
            result.extend(_text_contexts(
                text, item["file_id"], item["captured_at"],
                f"evidence_{path.suffix.casefold().lstrip('.')}",
            ))
    return [item for item in result if item["resources"]]


def _matched_users(text: str, tokens: dict[str, list[str]]) -> dict[str, list[str]]:
    result = {}
    for user_id, values in tokens.items():
        found = [value for value in values if _contains(text, value)]
        if found:
            result[user_id] = found
    return result


def _split(user_id: str) -> str:
    bucket = int.from_bytes(hashlib.sha256(user_id.encode("utf-8")).digest()[:2], "big") % 5
    return "validation" if bucket == 0 else "train"


def _blank_features() -> dict[str, int]:
    return {feature: 0 for feature in FEATURES}


def _positive_example(positives, user_id, resource_id):
    return positives.setdefault((user_id, resource_id), {
        "user_id": user_id, "resource_id": resource_id, "label": 1,
        "split": _split(user_id), "features": _blank_features(),
        "source_kinds": set(), "source_ids": set(), "available_ats": set(),
    })


def _add_workflow_edges(dataset: Path, tokens, positives, activity):
    """Add only request-scoped workflow edges connected to grounded resources."""
    from code.workflow import (
        _analytics_for_account, _compatible_accounts, _dependency_score,
    )

    email_users: dict[str, set[str]] = defaultdict(set)
    for user_id, values in tokens.items():
        for value in values:
            if "@" in value:
                email_users[value.casefold()].add(user_id)
    requests = []
    for name in ("sample_deletion_requests.csv", "deletion_requests.csv"):
        path = dataset / name
        if path.is_file():
            requests.extend(_csv_rows(path))

    added = 0
    for case in requests:
        users = email_users.get(case.get("email", "").casefold(), set())
        if len(users) != 1:
            continue
        user_id = next(iter(users))
        audit_at = case["audit_at"]
        grounded = {
            resource_id for (edge_user, resource_id), example in positives.items()
            if edge_user == user_id
            and any(available_at <= audit_at for available_at in example["available_ats"])
        }
        anchors = [
            event for event in activity
            if event.get("resource_id") in grounded
            and event.get("target_system") != "account_service"
            and event.get("event_time", "") <= audit_at
        ]
        scored = []
        for account in _compatible_accounts(case, activity):
            for anchor in anchors:
                score = _dependency_score(account, anchor)
                if score is not None:
                    scored.append((score, account, anchor))
        if not scored:
            continue
        candidate_accounts = {
            item[1].get("resource_id", ""): item[1] for item in scored
        }
        if len(candidate_accounts) != 1:
            # Training labels must not choose a neighboring user's account by score.
            continue
        account = next(iter(candidate_accounts.values()))
        account_edges = [item for item in scored if item[1] is account]
        _, _account, anchor = min(
            account_edges, key=lambda item: (item[0], item[2].get("activity_id", ""))
        )
        edges = [(account, "DELETE")]
        analytics = _analytics_for_account(account, activity, audit_at)
        if analytics is not None:
            edges.append((analytics, "ANONYMIZE"))
        for event, _action in edges:
            resource_id = event.get("resource_id", "")
            if not resource_id:
                continue
            was_new = (user_id, resource_id) not in positives
            example = _positive_example(positives, user_id, resource_id)
            example["features"]["workflow_dependency"] = 1
            example["features"]["same_system"] = 1
            example["source_kinds"].add("workflow_dependency")
            example["source_ids"].update(filter(None, [
                event.get("activity_id"), anchor.get("activity_id")
            ]))
            example["available_ats"].add(event.get("event_time", ""))
            added += int(was_new)
    return added


def build_training_examples(repo_root: str | Path) -> tuple[list[dict], dict]:
    """Build user-disjoint positive and hard-negative lineage examples in memory."""
    dataset = Path(repo_root).resolve() / "dataset"
    tokens = _identity_tokens(dataset)
    contexts = _contexts(dataset)
    positives: dict[tuple[str, str], dict] = {}
    source_edges: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    ambiguous_contexts = 0

    for item in contexts:
        users = _matched_users(item["text"], tokens)
        if len(users) != 1:
            ambiguous_contexts += int(len(users) > 1)
            continue
        user_id, matched = next(iter(users.items()))
        for resource_id in item["resources"]:
            key = (user_id, resource_id)
            example = _positive_example(positives, user_id, resource_id)
            features = example["features"]
            features["direct_identifier_match"] = 1
            features["stable_reference_match"] |= int(user_id in matched)
            features["catalog_link"] |= item["catalog_link"]
            features["same_trace"] |= item["same_trace"]
            features["same_artifact"] = 1
            features["same_system"] = 1
            example["source_kinds"].add(item["source_kind"])
            example["source_ids"].add(item["source_id"])
            example["available_ats"].add(item["available_at"])
            source_edges[(item["source_id"], _system(resource_id))].add(key)

    activity = _csv_rows(dataset / "system_activity.csv")
    workflow_edges = _add_workflow_edges(
        dataset, tokens, positives, activity
    )
    # Workflow-derived edges participate in hard-negative pools by system, but not in
    # same-artifact pools unless their activity source was already a direct context.

    negatives: dict[tuple[str, str], dict] = {}
    global_by_system: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in positives:
        global_by_system[_system(edge[1])].append(edge)

    for (user_id, resource_id), positive in sorted(positives.items()):
        alternatives = []
        for source_id in sorted(positive["source_ids"]):
            alternatives.extend(
                edge for edge in sorted(source_edges[(source_id, _system(resource_id))])
                if edge[0] != user_id and edge[1] != resource_id
            )
        if not alternatives:
            alternatives.extend(
                edge for edge in sorted(global_by_system[_system(resource_id)])
                if edge[0] != user_id and edge[1] != resource_id
            )
        for other_user, candidate in list(dict.fromkeys(alternatives))[:3]:
            key = (user_id, candidate)
            if key in positives or key in negatives:
                continue
            same_artifact = any(
                (other_user, candidate) in source_edges[(source_id, _system(resource_id))]
                for source_id in positive["source_ids"]
            )
            features = _blank_features()
            features.update({
                "same_artifact": int(same_artifact),
                "same_system": 1,
                "competing_subject": 1,
            })
            negatives[key] = {
                "user_id": user_id, "resource_id": candidate, "label": 0,
                "split": _split(user_id), "features": features,
                "source_kinds": {"hard_negative"}, "source_ids": set(),
            }

    examples = []
    for example in [*positives.values(), *negatives.values()]:
        examples.append({
            **example,
            "source_kinds": sorted(example["source_kinds"]),
            "source_ids": sorted(example["source_ids"]),
            "available_ats": sorted(example.get("available_ats", [])),
        })
    examples.sort(key=lambda row: (row["split"], row["user_id"], -row["label"], row["resource_id"]))
    summary = {
        "examples": len(examples),
        "positives": len(positives),
        "hard_negatives": len(negatives),
        "users": len({row["user_id"] for row in examples}),
        "train_examples": sum(row["split"] == "train" for row in examples),
        "validation_examples": sum(row["split"] == "validation" for row in examples),
        "train_users": len({row["user_id"] for row in examples if row["split"] == "train"}),
        "validation_users": len({row["user_id"] for row in examples if row["split"] == "validation"}),
        "ambiguous_contexts_excluded": ambiguous_contexts,
        "workflow_edges_added": workflow_edges,
        "positive_sources": dict(sorted(Counter(
            kind for row in positives.values() for kind in row["source_kinds"]
        ).items())),
    }
    return examples, summary


def render_training_report(summary: dict) -> str:
    lines = [
        "# Self-Supervised Lineage Training-Set Report", "",
        "No canonical output, case labels, organizer truth, or post-audit mappings are",
        "used. Exact edge rows remain in memory and are not persisted.", "",
        "## Dataset Summary", "",
        f"- Examples: **{summary['examples']:,}**",
        f"- Positive grounded edges: **{summary['positives']:,}**",
        f"- Hard negatives: **{summary['hard_negatives']:,}**",
        f"- Subjects represented: **{summary['users']:,}**",
        f"- Excluded ambiguous contexts: **{summary['ambiguous_contexts_excluded']:,}**",
        f"- Grounded workflow edges added: **{summary['workflow_edges_added']:,}**",
        "", "## User-Disjoint Split", "",
        "| Split | Users | Examples |", "|---|---:|---:|",
        f"| Train | {summary['train_users']:,} | {summary['train_examples']:,} |",
        f"| Validation | {summary['validation_users']:,} | {summary['validation_examples']:,} |",
        "", "No user ID occurs in both splits.", "", "## Positive Source Coverage", "",
        "| Source | Edge observations |", "|---|---:|",
    ]
    for source, count in summary["positive_sources"].items():
        lines.append(f"| `{source}` | {count:,} |")
    lines.extend([
        "", "## Stage 2 Gate", "",
        "The examples are suitable for deterministic Stage 3 weight training only.",
        "Candidate generation remains bounded by the separate observability gate;",
        "training cannot recover canonical IDs absent before their audit cutoffs.", "",
    ])
    return "\n".join(lines)
