"""Ghost Data Still Exists - deletion-audit pipeline entry point.

Usage:
    python code/main.py [--requests PATH] [--out PATH] [--trace PATH]

Defaults: dataset/deletion_requests.csv -> ./output.csv (repository root).

Per case: intent -> identity -> ownership links -> per-copy state at audit_at ->
policy -> citation -> planner. Non-deletion requests get ``NOT_APPLICABLE,[]``.
One failing case never stops the run: it is logged and still gets a row.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import intent
import planner
import audit_trace
from facts import FactStore
from identity import IdentityIndex, SubjectIdentity
from links import LinkIndex, subject_keys
from loaders import DATASET_DIR, REPO_ROOT, Dataset, Request, case_number, load_dataset, load_requests
from policy import evaluate
from resolver import resolve
from schema import HEADER, OutputRow, Status

REQUEST_FILES = ("deletion_requests.csv", "sample_deletion_requests.csv")


@dataclass
class Context:
    data: Dataset
    identities: IdentityIndex
    store: FactStore
    links: LinkIndex
    all_requests: list[Request]   # every request file: job-burst uniqueness must not depend on the run


@dataclass
class CaseResult:
    case_id: str
    status: str
    steps: list[dict] = field(default_factory=list)
    intent: str = ""
    subject: SubjectIdentity | None = None
    flags: list[str] = field(default_factory=list)
    error: str = ""
    items: list = field(default_factory=list)


def build_context(dataset_dir: Path = DATASET_DIR) -> Context:
    data = load_dataset(dataset_dir)
    identities = IdentityIndex(data)
    store = FactStore.build(data, dataset_dir)
    store.coverage.check()
    requests = [r for name in REQUEST_FILES if (dataset_dir / name).exists()
                for r in load_requests(dataset_dir / name)]
    return Context(data, identities, store, LinkIndex(store, data, identities), requests)


def run_case(req: Request, ctx: Context) -> CaseResult:
    decision = intent.classify(req.request_text)
    result = CaseResult(req.case_id, Status.INCOMPLETE.value, intent=decision.label)
    if decision.flagged:
        result.flags.append("intent_ambiguous")
    if "instruction_pattern" in decision.reasons:
        result.flags.append("instruction_pattern")
    if not intent.treat_as_deletion(decision):
        result.status = Status.NOT_APPLICABLE.value
        return result

    subject = result.subject = ctx.identities.resolve(req.email, req.audit_at)
    if subject is None:
        result.flags.append("identity_unresolved")
        return result
    result.flags.extend(subject.flags)

    keys = subject_keys(subject)
    targets = ctx.links.targets(subject, req, ctx.all_requests, result.flags)
    for _, target in sorted(targets.items()):
        state = resolve(ctx.store, target, keys, req.audit_at)
        decision = evaluate(state, req.audit_at)
        result.items.append(planner.build_item(target, state, decision))
        result.flags.extend(f"H:{h}:{target.resource_id}" for h in decision.hypothesis)
    result.status, result.steps = planner.plan(result.items)
    return result


def run_cases(requests: list[Request], ctx: Context, tracer: audit_trace.TraceWriter | None = None) -> list[CaseResult]:
    results = []
    for req in sorted(requests, key=lambda r: case_number(r.case_id)):
        try:
            result = run_case(req, ctx)
            # Contract guard: a row that breaks schema.OutputRow is never written.
            OutputRow(case_id=result.case_id, deletion_status=result.status, steps=result.steps)
            results.append(result)
        except Exception as exc:  # per-case isolation: never lose a row
            print(f"[error] {req.case_id}: {exc!r}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # Safe fallback: never claim COMPLETE for a case we could not process.
            results.append(CaseResult(req.case_id, Status.INCOMPLETE.value, error=repr(exc), flags=["case_error"]))
        if tracer is not None:
            tracer.write(audit_trace.case_record(results[-1], results[-1].items))
    return results


def serialize_steps(steps: list[dict]) -> str:
    return json.dumps(steps, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_output(results: list[CaseResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for res in results:
            writer.writerow([res.case_id, res.status, serialize_steps(res.steps)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    parser.add_argument("--requests", default=str(DATASET_DIR / "deletion_requests.csv"))
    parser.add_argument("--out", default=str(REPO_ROOT / "output.csv"))
    parser.add_argument("--trace", default=None, help="write a per-case JSONL trace to this path")
    args = parser.parse_args(argv)

    ctx = build_context()
    requests = load_requests(Path(args.requests))
    tracer = audit_trace.TraceWriter(Path(args.trace) if args.trace else None)
    try:
        results = run_cases(requests, ctx, tracer)
    finally:
        tracer.close()
    write_output(results, Path(args.out))

    statuses = Counter(r.status for r in results)
    intents = Counter(r.intent for r in results if r.intent)
    errors = sum(1 for r in results if r.error)
    print(f"wrote {len(results)} rows -> {args.out}")
    print("status:", dict(sorted(statuses.items())))
    print("intent:", dict(sorted(intents.items())))
    print(f"errors: {errors}, ambiguous intent: {sum('intent_ambiguous' in r.flags for r in results)}, "
          f"unresolved identity: {sum('identity_unresolved' in r.flags for r in results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
