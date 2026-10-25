"""Evaluation-only audit of whether canonical public resources are observable.

This module may read ``sample_output.csv`` solely to measure candidate availability. It
is never imported by prediction or training code, and its results must not be used as
runtime lineage mappings.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from code.evidence import _contains, build_evidence_index
from code.identity import resolve_identity
from code.ingest import load_all
from code.temporal import filter_events

RETRIEVABLE = "PRE_AUDIT_RETRIEVABLE"
LINKED_UNRETRIEVED = "PRE_AUDIT_LINKED_UNRETRIEVED"
UNLINKED = "PRE_AUDIT_UNLINKED"
POST_AUDIT = "POST_AUDIT_ONLY"
ABSENT = "ABSENT_GLOBALLY"
PRE_AUDIT = {RETRIEVABLE, LINKED_UNRETRIEVED, UNLINKED}


def _expected_resources(path: Path) -> dict[str, list[str]]:
    result = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            resources = [step["resource_id"] for step in json.loads(row["steps_json"])]
            result[row["case_id"]] = list(dict.fromkeys(resources))
    return result


def _identifiers(identity: dict | None) -> list[str]:
    if not identity:
        return []
    values = [identity.get("user_id", "")]
    for key in ("all_emails", "all_phones", "all_email_hashes"):
        values.extend(identity.get(key, []))
    return [str(value) for value in values if value]


def _read_searchable(path: Path) -> str:
    suffix = path.suffix.casefold()
    try:
        if suffix == ".pdf":
            from code.evidence import _extract_pdf_text
            return _extract_pdf_text(str(path.resolve()))
        if suffix == ".png":
            # The observability audit never makes model calls. Local OCR is sufficient
            # for candidate discovery; catalog/activity links remain separate sources.
            from code.evidence import _extract_image_text
            return _extract_image_text(str(path.resolve()))
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ImportError, RuntimeError):
        return ""


def _evidence_corpus(root: Path, manifest: dict[str, dict]) -> list[dict]:
    dataset = root / "dataset"
    corpus = []
    for file_id, item in manifest.items():
        path = (dataset / item["file_path"]).resolve()
        corpus.append({
            "source_id": file_id,
            "available_at": item.get("captured_at", ""),
            "location": item["file_path"],
            "text": _read_searchable(path),
        })
    return corpus


def _activity_occurrences(resource_id: str, activity: list[dict]) -> list[dict]:
    occurrences = []
    for event in activity:
        blob = f"{event.get('resource_id', '')} {event.get('details', '')}"
        if event.get("resource_id") == resource_id or _contains(blob, resource_id):
            occurrences.append({
                "source_id": event.get("activity_id", ""),
                "available_at": event.get("event_time", ""),
                "location": "system_activity.csv",
                "text": blob,
            })
    return occurrences


def _evidence_occurrences(resource_id: str, corpus: list[dict]) -> list[dict]:
    return [item for item in corpus if _contains(item["text"], resource_id)]


def _context_linked(occurrences: list[dict], resource_id: str,
                    identifiers: list[str]) -> bool:
    for occurrence in occurrences:
        text = occurrence.get("text", "")
        folded = text.casefold()
        start = folded.find(resource_id.casefold())
        while start >= 0:
            # Limit co-occurrence to a resource-sized local context rather than treating
            # every subject in a multi-record artifact as linked to every resource.
            context = text[max(0, start - 600):start + len(resource_id) + 600]
            if any(_contains(context, identifier) for identifier in identifiers):
                return True
            start = folded.find(resource_id.casefold(), start + 1)
    return False


def _case_audit(case: dict, expected: list[str], data: dict,
                corpus: list[dict], root: Path) -> list[dict]:
    identity = resolve_identity(case["email"], case["audit_at"], data)
    identifiers = _identifiers(identity)
    audit_at = case["audit_at"]

    # Disable network-backed vision for this evaluation diagnostic. Candidate
    # observability must be reproducible from local participant artifacts.
    api_key = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        evidence = build_evidence_index(
            root, data["evidence_manifest"], identity, audit_at
        ) if identity else {}
    finally:
        if api_key is not None:
            os.environ["GOOGLE_API_KEY"] = api_key
    events = filter_events(data["system_activity"], identity, audit_at)
    directly_retrievable = set(evidence)
    for event in events:
        if event.get("resource_id"):
            directly_retrievable.add(event["resource_id"])

    rows = []
    for resource_id in expected:
        occurrences = [
            *_activity_occurrences(resource_id, data["system_activity"]),
            *_evidence_occurrences(resource_id, corpus),
        ]
        pre = [item for item in occurrences if item["available_at"] <= audit_at]
        post = [item for item in occurrences if item["available_at"] > audit_at]
        if resource_id in directly_retrievable:
            category = RETRIEVABLE
        elif pre and _context_linked(pre, resource_id, identifiers):
            category = LINKED_UNRETRIEVED
        elif pre:
            category = UNLINKED
        elif post:
            category = POST_AUDIT
        else:
            category = ABSENT
        ordered = sorted(occurrences, key=lambda item: (
            item.get("available_at", ""), item.get("source_id", "")
        ))
        earliest = ordered[0] if ordered else {}
        rows.append({
            "case_id": case["case_id"],
            "resource_id": resource_id,
            "audit_at": audit_at,
            "category": category,
            "earliest_at": earliest.get("available_at", ""),
            "earliest_source": earliest.get("source_id", ""),
            "earliest_location": earliest.get("location", ""),
            "identity_linked": category in {RETRIEVABLE, LINKED_UNRETRIEVED},
            "pre_audit_sources": [item["source_id"] for item in pre],
            "post_audit_sources": [item["source_id"] for item in post],
        })
    return rows


def audit_observability(repo_root: str | Path) -> dict:
    root = Path(repo_root).resolve()
    data = load_all(root)
    expected = _expected_resources(root / "dataset" / "sample_output.csv")
    corpus = _evidence_corpus(root, data["evidence_manifest"])
    requests = {case["case_id"]: case for case in data["sample_requests"]}
    rows = []
    for case_id in sorted(expected):
        rows.extend(_case_audit(
            requests[case_id], expected[case_id], data, corpus, root
        ))
    counts = Counter(row["category"] for row in rows)
    available = sum(counts[category] for category in PRE_AUDIT)
    blocked = [row for row in rows if row["category"] not in PRE_AUDIT]
    return {
        "resources": rows,
        "counts": dict(sorted(counts.items())),
        "total_case_resources": len(rows),
        "pre_audit_candidates": available,
        "candidate_recall": available / len(rows) if rows else 1.0,
        "gate_passed": not blocked,
        "blocked": blocked,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Candidate Observability Report",
        "",
        "This is an evaluation-only diagnostic. It may compare against public canonical",
        "output, but none of its expected-resource data may enter prediction or training.",
        "",
        "## Gate Result",
        "",
        f"- Pre-audit candidate recall: **{result['pre_audit_candidates']}/"
        f"{result['total_case_resources']} ({result['candidate_recall']:.1%})**",
        f"- 100% observability gate: **{'PASS' if result['gate_passed'] else 'FAIL'}**",
        "",
        "## Classification Counts",
        "",
        "| Classification | Case-resource pairs |",
        "|---|---:|",
    ]
    for category, count in result["counts"].items():
        lines.append(f"| `{category}` | {count} |")
    lines.extend(["", "## Blocked Canonical Resources", "",
                  "| Case | Resource | Audit cutoff | Classification | Later sources |",
                  "|---|---|---|---|---|"])
    for row in result["blocked"]:
        later = ", ".join(row["post_audit_sources"]) or "—"
        lines.append(
            f"| `{row['case_id']}` | `{row['resource_id']}` | "
            f"`{row['audit_at']}` | `{row['category']}` | {later} |"
        )
    lines.extend([
        "", "## All 111 Canonical Case-resource Pairs", "",
        "`Earliest at` is the earliest manifest capture time or activity event time in",
        "participant data. `Linked` means the production retriever found the resource or",
        "the same local pre-audit context contains a resolved subject identifier.", "",
        "| Case | Resource | Earliest at | Earliest source | Linked | Classification |",
        "|---|---|---|---|---|---|",
    ])
    for row in result.get("resources", []):
        earliest_at = f"`{row['earliest_at']}`" if row["earliest_at"] else "—"
        earliest_source = (f"`{row['earliest_source']}`"
                           if row["earliest_source"] else "—")
        lines.append(
            f"| `{row['case_id']}` | `{row['resource_id']}` | "
            f"{earliest_at} | {earliest_source} | "
            f"{'yes' if row['identity_linked'] else 'no'} | `{row['category']}` |"
        )
    lines.extend([
        "", "## Decision", "",
        "Training is blocked from claiming a lawful 100% result while this gate fails.",
        "Post-audit artifacts and absent resource IDs must not become runtime mappings.",
        "The remedy is pre-audit lineage in participant data or an evaluator correction.",
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output", default="code/evaluation/observability_report.md")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    result = audit_observability(root)
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(result), encoding="utf-8", newline="\n")
    print(f"Candidate recall: {result['pre_audit_candidates']}/"
          f"{result['total_case_resources']} ({result['candidate_recall']:.1%})")
    print(f"Observability gate: {'PASS' if result['gate_passed'] else 'FAIL'}")
    print(f"Report: {output}")
    return 0 if result["gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
