"""End-to-end pipeline used by main.py and the evaluation harness."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from . import loaders
from .config import DatasetPaths
from .engine.auditor import AuditContext, audit_case
from .engine.linking import Linker
from .engine.policy import Policy
from .evidence import build_observation_store, multimodal
from .identity import IdentityResolver
from .intent import DELETE, IntentClassifier, heuristic
from .llm.adapter import LLMAdapter
from .models import Case, CaseResult
from .output import write_output

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    results: list[CaseResult]
    errors: list[str]
    llm: LLMAdapter | None
    intent: IntentClassifier
    context: AuditContext


def complete_times(cases: list[Case], horizon: datetime) -> list[Case]:
    """Fill timestamps the loader could not read: a missing audit_at means no cutoff (the latest instant in the
    dataset); a request with no readable time at all is placed at that cutoff."""
    out = []
    for c in cases:
        if c.audit_at is None or c.requested_at is None:
            audit = c.audit_at or horizon
            log.warning("%s: unreadable request timestamps; auditing with cutoff %s", c.case_id, audit.isoformat())
            c = replace(c, audit_at=audit, requested_at=c.requested_at or audit, reported_at=c.reported_at or audit)
        out.append(c)
    return out


def guarded_audit(case: Case, ctx: AuditContext) -> CaseResult:
    """One failing case yields a valid NOT_APPLICABLE row with the error in its trace, never a lost run."""
    try:
        return audit_case(case, ctx)
    except Exception as exc:  # noqa: BLE001 - the remaining cases must still be written
        log.exception("audit failed for %s", case.case_id)
        return CaseResult(case.case_id, "NOT_APPLICABLE", [], {"case_id": case.case_id, "error": repr(exc)})


def run(paths: DatasetPaths, out: Path, trace_dir: Path | None = None, backend: str | None = None,
        ledger_dir: Path | None = None, workflow_model: Path | None = None, save_model: Path | None = None) -> RunResult:
    from .llm.ledger import Ledger

    llm = LLMAdapter(backend=backend, ledger=Ledger(directory=ledger_dir) if ledger_dir else None)
    manifest = loaders.load_manifest(paths.manifest, paths.root)
    activities = loaders.load_activity(paths.activity)
    instants = [e.captured_at for e in manifest] + [a.event_time for a in activities]
    horizon = max(instants) if instants else datetime.now().astimezone()
    cases = complete_times(loaders.load_cases(paths.requests), horizon)
    resolver = IdentityResolver(loaders.load_identities(paths.identities), loaders.load_audit_log(paths.audit_log))
    policy = Policy(loaders.load_rules(paths.rules))

    multimodal.prefetch(manifest, llm)
    store = build_observation_store(manifest, activities, llm)

    # every request the dataset knows about takes part in the workflow assignment (one workflow per request)
    known = {c.case_id: c for c in cases}
    for extra in (paths.sample_requests, paths.eval_requests):
        if extra.exists() and extra.resolve() != paths.requests.resolve():
            for c in complete_times(loaders.load_cases(extra), horizon):
                known.setdefault(c.case_id, c)
    intent = IntentClassifier(llm)
    intents = intent.classify_all([c.request_text for c in cases])

    model = json.loads(workflow_model.read_text(encoding="utf-8")) if workflow_model and workflow_model.exists() else None
    linker = Linker(store, resolver, activities, model=model)
    ctx = AuditContext(store, resolver, policy, linker, intents)
    # requests that do not authorize deletion never started a deletion workflow, so they do not compete for one
    competing = [c for c in known.values()
                 if (intents.get(c.request_text) or heuristic(c.request_text)).label == DELETE]
    ctx.prepare(sorted(competing, key=lambda c: loaders.case_sort_key(c.case_id)))

    if model is None:
        from .engine.linking import learn_lead_range
        linker.lead_range = learn_lead_range(linker, ctx._items)
        if save_model is not None:
            save_model.parent.mkdir(parents=True, exist_ok=True)
            save_model.write_text(json.dumps(linker.export_model(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results = [guarded_audit(c, ctx) for c in cases]
    errors = write_output(results, out, [c.case_id for c in cases])
    if trace_dir is not None:
        trace_dir.mkdir(parents=True, exist_ok=True)
        for r in results:
            (trace_dir / f"{r.case_id}.json").write_text(
                json.dumps(r.trace, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return RunResult(results, errors, llm, intent, ctx)
