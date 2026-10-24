"""Ghost Data Still Exists - deletion-audit pipeline entry point.

Usage:
    python code/main.py [--requests PATH] [--out PATH] [--trace PATH] [--usage PATH]
                        [--offline] [--no-vision] [--no-agent] [--export-snapshot]

Defaults: dataset/deletion_requests.csv -> ./output.csv (repository root).

Per case: intent -> identity -> ownership links -> per-copy state at audit_at ->
policy -> citation -> planner. Non-deletion requests get ``NOT_APPLICABLE,[]``.
One failing case never stops the run: it is logged, gets a conservative row
(``fallback_result``) and is listed in ``<out>_failures.csv``. Every row is written; the
exit code is non-zero when any case failed or strict validation of the written file fails.

Model use (plan 7.3, 7.4): vision rows for PNG screenshots, labels for AMBIGUOUS request
texts, and the bounded investigator for UNPROVEN / CONFLICT items. With no key, or
``--offline`` / ``ZENMUX_OFFLINE=1``, every model result is replayed from ``llm_snapshot.py``.
The model never sets a status or a step.
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

import audit_trace
import config
import intent
import intent_model
import links
import planner
import validate
from agent.loop import AgentStats, investigate
from agent.tools import Corpus
from evidence import extract_text, extract_vision
from evidence.extract_text import pdf_text
from facts import FactStore, catalog_alias_rows
from identity import FutureDataError, IdentityIndex, SubjectIdentity
from links import LinkIndex, assign_windows, subject_keys
from llm_client import LLMClient
from loaders import DATASET_DIR, REPO_ROOT, Dataset, Request, case_number, load_dataset, load_requests
from policy import RULES, SYSTEM_CATEGORY, UNPROVEN, attachment_exclusive, content_categories, evaluate
from resolver import resolve
from schema import HEADER, OP_PHASE, OP_STATE, IntentLabel, OutputRow, Status, step_sort_key

REQUEST_FILES = ("deletion_requests.csv", "sample_deletion_requests.csv")


@dataclass
class Context:
    data: Dataset
    identities: IdentityIndex
    store: FactStore
    links: LinkIndex
    all_requests: list[Request]   # every request file: job-burst uniqueness must not depend on the run
    client: LLMClient | None = None
    corpus: Corpus | None = None
    agent_enabled: bool = False
    agent_stats: AgentStats = field(default_factory=AgentStats)
    known_systems: set[str] = field(default_factory=set)
    vision_reports: list = field(default_factory=list)
    intent_labels: dict = field(default_factory=dict)
    windows: dict = field(default_factory=dict)   # case_id -> worker claim (links.assign_windows)


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
    agent_log: list[dict] = field(default_factory=list)
    model_calls: list[dict] = field(default_factory=list)


def _raw_text(data: Dataset, store: FactStore, dataset_dir: Path) -> dict[str, str]:
    """Plain text of every evidence file: file text, PDF text layer, PNG OCR grounding text."""
    out = {}
    for ev in data.evidence_files:
        path = ev.abs_path(dataset_dir)
        if ev.file_path.endswith(".png"):
            out[ev.file_id] = store.grounding.get(ev.file_id, "")
        elif ev.file_path.endswith(".pdf"):
            out[ev.file_id] = pdf_text(path)
        else:
            out[ev.file_id] = path.read_text(encoding="utf-8", errors="replace")
    return out


def add_vision(ctx: Context, dataset_dir: Path) -> None:
    """Model-read PNG rows, grounded in OCR text, become ``vision_row`` observations."""
    aliases = [extract_vision.Alias(*row) for row in catalog_alias_rows(ctx.data)]
    for ev in ctx.data.evidence_files:
        if not ev.file_path.endswith(".png"):
            continue
        assert ctx.client is not None   # add_vision runs only with a client
        rows, report = extract_vision.extract(ev, ev.abs_path(dataset_dir), ctx.store.grounding.get(ev.file_id),
                                              ctx.client, ctx.known_systems, set(RULES), SYSTEM_CATEGORY,
                                              aliases, ctx.store.layout.get(ev.file_id))
        ctx.store.add(rows, [])
        ctx.vision_reports.append(report)
    ctx.store.db.commit()


def build_context(dataset_dir: Path = DATASET_DIR, client: LLMClient | None = None, vision: bool = False,
                  agent: bool = False) -> Context:
    data = load_dataset(dataset_dir)
    identities = IdentityIndex(data)
    store = FactStore.build(data, dataset_dir)
    store.coverage.check()
    requests = [r for name in REQUEST_FILES if (dataset_dir / name).exists()
                for r in load_requests(dataset_dir / name)]
    ctx = Context(data, identities, store, LinkIndex(store, data, identities), requests, client=client,
                  agent_enabled=agent and client is not None)
    ctx.known_systems = ({o.system_id for o in store.observations.values()}
                         | {a.target_system for a in data.activity}) - {""}
    if vision and client is not None:
        add_vision(ctx, dataset_dir)
    if links.WINDOW_ASSIGNMENT_ENABLED:
        ctx.windows = window_assignment(ctx)
    if ctx.agent_enabled:
        ctx.corpus = Corpus(data, store, _raw_text(data, store, dataset_dir))
    return ctx


def window_assignment(ctx: Context) -> dict:
    """Assign worker DELETE_RECORD claims to deletion requests whose subject has no account record,
    one-to-one over every known request (links.assign_windows). Experiment: medium edges only."""
    candidates, order = {}, {}
    for req in ctx.all_requests:
        if not intent.treat_as_deletion(intent.classify(req.request_text)):
            continue
        try:
            subject = ctx.identities.resolve(req.email, req.audit_at)
        except FutureDataError:   # reported by run_case for that case, not here
            continue
        if subject is None:
            continue
        found = ctx.links.targets(subject, req, ctx.all_requests, [])
        if any(sys_id == links.WINDOW_SYSTEM for sys_id, _ in found):
            continue
        cands = ctx.links.window_candidates(req, subject.user_id)
        if cands:
            candidates[req.case_id], order[req.case_id] = cands, case_number(req.case_id)
    return assign_windows(candidates, order)


def label_ambiguous(requests: list[Request], ctx: Context) -> None:
    """Send only the texts the clause rules leave AMBIGUOUS to the model (batched)."""
    if ctx.client is None:
        return
    texts = [r.request_text for r in requests if intent.classify(r.request_text).label == IntentLabel.AMBIGUOUS]
    if texts:
        ctx.intent_labels = intent_model.label_texts(texts, ctx.client)


def _items(ctx: Context, subject, req: Request, flags: list[str], edges=(), extra=()) -> list:
    keys = subject_keys(subject)
    items = []
    targets = ctx.links.targets(subject, req, ctx.all_requests, flags, extra_edges=list(edges),
                                window=ctx.windows.get(req.case_id))
    for _, target in sorted(targets.items()):
        state = resolve(ctx.store, target, keys, req.audit_at, extra=list(extra))
        decision = evaluate(state, req.audit_at)
        items.append(planner.build_item(target, state, decision))
    return items


def _undecided(item) -> bool:
    d = item.decision
    return not item.target.stale and (d.outcome == UNPROVEN or d.reason == "conflict")


def _run_agent(req: Request, ctx: Context, subject, result: CaseResult) -> None:
    keys = subject_keys(subject)
    ids = sorted(keys.emails | keys.user_ids | keys.phones)
    assert ctx.client is not None and ctx.corpus is not None   # the agent runs only with both
    budget = [config.AGENT_TOKEN_BUDGET]
    edges, extra = [], []
    for item in [i for i in result.items if _undecided(i)]:
        outcome = investigate(req.case_id, item, keys=keys, subject_ids=ids, cutoff=req.audit_at,
                              client=ctx.client, corpus=ctx.corpus, known_systems=ctx.known_systems,
                              stats=ctx.agent_stats, budget=budget,
                              linked={i.target.key for i in result.items})
        result.agent_log.append({"resource_id": item.target.resource_id, "turns": outcome.log})
        edges += outcome.edges
        extra += outcome.observations
    if edges or extra:
        result.flags.append(f"agent_accepted:{len(edges)}link:{len(extra)}state")
        result.items = _items(ctx, subject, req, [], edges, extra)


def run_case(req: Request, ctx: Context) -> CaseResult:
    decision = intent.classify(req.request_text)
    result = CaseResult(req.case_id, Status.INCOMPLETE.value, intent=decision.label)
    if decision.flagged:
        model = ctx.intent_labels.get(intent_model.text_id(req.request_text))
        if model is not None and model.label:
            result.intent = model.label
            result.flags.append(f"intent_model:{model.label}")
            decision = intent.IntentResult(model.label, model.label in intent.DELETION_CLASSES, False,
                                           [*decision.reasons, "model_label"], decision.clauses)
        else:
            result.flags.append("intent_ambiguous" + (f":{model.flag}" if model else ""))
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

    result.items = _items(ctx, subject, req, result.flags)
    if ctx.agent_enabled and any(_undecided(i) for i in result.items):
        _run_agent(req, ctx, subject, result)
    for item in result.items:
        result.flags.extend(f"H:{h}:{item.target.resource_id}" for h in item.decision.hypothesis)
    result.status, result.steps = planner.plan(result.items)
    return result


def fallback_result(req: Request, ctx: Context, exc: Exception) -> CaseResult:
    """Conservative row for a case that raised: INCOMPLETE plus a future verification step
    (evidence_id "") for every known, non-stale target, with the verification of its policy row.
    The category comes from the catalog words, else the system; a target with none, or with
    two named categories, or a non-exclusive attachment (rule_06), is skipped.
    With no step, or when this lookup fails too, the row is ``INCOMPLETE,[]`` (flag
    ``no_fallback_row``): strict validation rejects it and main exits non-zero, but the batch
    goes on and every other row is written."""
    result = CaseResult(req.case_id, Status.INCOMPLETE.value, [], error=repr(exc), flags=["case_error"])
    steps: list[dict] = []
    try:
        subject = result.subject = ctx.identities.resolve(req.email, req.audit_at)
        found = ctx.links.targets(subject, req, ctx.all_requests, []) if subject is not None else {}
        for (system_id, resource_id), target in sorted(found.items()):
            named = content_categories(target.descriptions)
            category = named.pop() if len(named) == 1 else "" if named else SYSTEM_CATEGORY.get(system_id, "")
            if target.stale or category not in RULES or (category == "SUPPORT_ATTACHMENT"
                                                         and not attachment_exclusive(target)):
                continue
            op = RULES[category][4]
            steps.append({"step_no": 0, "phase": str(OP_PHASE[op]), "system_id": system_id,
                          "resource_id": resource_id, "operation": op.value, "state": str(OP_STATE[op]),
                          "evidence_id": ""})
        steps.sort(key=step_sort_key)
        for n, step in enumerate(steps, start=1):
            step["step_no"] = n
        OutputRow.model_validate({"case_id": req.case_id, "deletion_status": result.status, "steps": steps})
    except Exception as inner:  # noqa: BLE001 - the row stays INCOMPLETE,[] and the failure is listed
        result.error += f" | fallback failed: {inner!r}"
        steps = []
    result.steps = steps
    result.flags.append("fallback_row" if steps else "no_fallback_row")
    return result


def run_cases(requests: list[Request], ctx: Context, tracer: audit_trace.TraceWriter | None = None) -> list[CaseResult]:
    label_ambiguous(requests, ctx)
    results = []
    for req in sorted(requests, key=lambda r: case_number(r.case_id)):
        calls_before = len(ctx.client.calls) if ctx.client else 0
        try:
            result = run_case(req, ctx)
            # Contract guard: a row that breaks schema.OutputRow is never written.
            OutputRow.model_validate({"case_id": result.case_id, "deletion_status": result.status,
                                      "steps": result.steps})
            results.append(result)
        except Exception as exc:  # noqa: BLE001 - per-case isolation: never lose a row
            print(f"[error] {req.case_id}: {exc!r}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results.append(fallback_result(req, ctx, exc))
        if ctx.client:
            results[-1].model_calls = ctx.client.calls[calls_before:]
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


def failures_path(out: Path) -> Path:
    """``output.csv`` -> ``output_failures.csv`` in the same directory."""
    return out.with_name(f"{out.stem}_failures.csv")


def write_failures(results: list[CaseResult], path: Path) -> int:
    """Write the cases that raised (case_id, the row written, the error). With none, remove a
    list left by an earlier run so it cannot be read as current. Returns the failure count."""
    failed = [r for r in results if r.error]
    if not failed:
        path.unlink(missing_ok=True)
        return 0
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "row", "error"])
        for res in failed:
            row = "fallback_row" if "fallback_row" in res.flags else "no_fallback_row"
            writer.writerow([res.case_id, row, res.error])
    return len(failed)


def usage_summary(ctx: Context, requests: int) -> dict:
    client = ctx.client
    totals = client.totals() if client else {}
    tin = sum(t["input_tokens"] for t in totals.values())
    tout = sum(t["output_tokens"] for t in totals.values())
    cost = config.cost_usd(client.model, tin, tout) if client else 0.0
    stats = ctx.agent_stats
    return {
        "mode": client.mode if client else "off", "model": client.model if client else "",
        "requests": requests, "per_purpose": totals,
        "per_purpose_cost_usd": {p: config.cost_usd(client.model, t["input_tokens"], t["output_tokens"])
                                 for p, t in totals.items()} if client else {},
        "input_tokens": tin, "output_tokens": tout, "total_tokens": tin + tout,
        "avg_tokens_per_request": round((tin + tout) / requests, 1) if requests else 0,
        "cost_usd": cost, "cost_per_request_usd": (cost / requests) if (cost is not None and requests) else None,
        "flags": dict(Counter(c["flag"] for c in client.calls if c["flag"])) if client else {},
        "agent": {"runs": stats.runs, "turns": stats.turns, "proposals": stats.proposals,
                  "accepted": stats.accepted, "rejected": dict(stats.rejected), "stopped": stats.stopped,
                  "fallbacks": dict(stats.fallbacks), "over_budget": stats.over_budget},
        "vision": [{"file_id": r.file_id, "status": r.status, "returned": r.returned, "grounded": r.grounded,
                    "dropped": r.dropped, "injection_suspected": r.injection_suspected,
                    "screen_hits": r.screen_hits} for r in ctx.vision_reports],
        "intent": {k: {"label": v.label, "flag": v.flag} for k, v in sorted(ctx.intent_labels.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists deletion-audit agent")
    parser.add_argument("--requests", default=str(DATASET_DIR / "deletion_requests.csv"))
    parser.add_argument("--out", default=str(REPO_ROOT / "output.csv"))
    parser.add_argument("--trace", default=None, help="write a per-case JSONL trace to this path")
    parser.add_argument("--usage", default=None, help="write the model-usage summary (JSON) to this path")
    parser.add_argument("--offline", action="store_true", help="replay llm_snapshot.py (same as ZENMUX_OFFLINE=1)")
    parser.add_argument("--no-llm", action="store_true", help="deterministic only: no model results at all")
    parser.add_argument("--no-vision", action="store_true")
    parser.add_argument("--no-agent", action="store_true")
    parser.add_argument("--export-snapshot", action="store_true",
                        help="write every validated model result of this run to code/llm_snapshot.py "
                             "and every OCR reading to code/ocr_snapshot.json")
    args = parser.parse_args(argv)

    client = None if args.no_llm else LLMClient.from_config(offline=args.offline or None)
    ctx = build_context(client=client, vision=not args.no_vision, agent=not args.no_agent)
    requests = load_requests(Path(args.requests))
    tracer = audit_trace.TraceWriter(Path(args.trace) if args.trace else None)
    try:
        results = run_cases(requests, ctx, tracer)
    finally:
        tracer.close()
    write_output(results, Path(args.out))
    code = 0
    failures = write_failures(results, failures_path(Path(args.out)))
    if failures:
        print(f"FAILED: {failures} cases raised; list -> {failures_path(Path(args.out))}", file=sys.stderr)
        code = 1
    invalid = validate.validate_file(Path(args.out), Path(args.requests))
    if invalid:
        for line in invalid[:20]:
            print(f"[invalid] {line}", file=sys.stderr)
        print(f"FAILED: {len(invalid)} contract errors in {args.out}", file=sys.stderr)
        code = 1

    statuses = Counter(r.status for r in results)
    intents = Counter(r.intent for r in results if r.intent)
    errors = sum(1 for r in results if r.error)
    print(f"wrote {len(results)} rows -> {args.out}")
    print("status:", dict(sorted(statuses.items())))
    print("intent:", dict(sorted(intents.items())))
    ambiguous = sum(any(f.startswith("intent_ambiguous") for f in r.flags) for r in results)
    print(f"errors: {errors}, ambiguous intent: {ambiguous}, "
          f"unresolved identity: {sum('identity_unresolved' in r.flags for r in results)}")
    for bad in ctx.store.coverage.errors(formats=("png",)):   # owned formats already stopped the build
        print(f"[coverage] {bad.file_id} ({bad.path}) skipped: {bad.error}", file=sys.stderr)
    if client is not None:
        summary = usage_summary(ctx, len(results))
        calls = sum(t["calls"] for t in summary["per_purpose"].values())
        print(f"model: {summary['mode']} {summary['model']} calls={calls} "
              f"tokens in/out={summary['input_tokens']}/{summary['output_tokens']} flags={summary['flags']}")
        if args.usage:
            Path(args.usage).write_text(json.dumps(summary, indent=1, sort_keys=True, default=str), encoding="utf-8")
        if args.export_snapshot:
            print(f"snapshot: {client.cache.export_snapshot()} validated results -> {config.SNAPSHOT_FILE}")
    if args.export_snapshot:
        print(f"ocr snapshot: {extract_text.export_ocr_snapshot()} readings -> {config.OCR_SNAPSHOT_FILE}")
    return code


if __name__ == "__main__":
    sys.exit(main())
