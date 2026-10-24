"""Frozen custom evaluation cases (``custom_cases/*.json``).

Each case is a self-contained mini dataset: one request, its identities, audit log,
activity rows and evidence files, and the expected output row. The expected row was
written from the rules (AGENTS.md section 6, ``deletion_rules.csv``), not from pipeline
output, and the cases were frozen before Phase 5 tuning.

``materialize`` writes a case (or several, merged) as a ``dataset/`` directory; the policy
file is copied from the real dataset. ``run`` executes the normal pipeline on it. A case
with ``agent_replies`` runs the investigator with a scripted fake model (no network), so
the code acceptance check is exercised end to end.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from llm_cache import LLMCache  # noqa: E402
from llm_client import LIVE, FakeTransport, LLMClient  # noqa: E402
from loaders import DATASET_DIR, email_hash, load_requests  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "custom_cases"
REQUEST_HEADER = ("case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text")
IDENTITY_HEADER = ("user_id", "name", "email", "phone", "email_hash", "updated_at")
AUDIT_HEADER = ("audit_id", "user_id", "event_time", "field_name", "old_value", "new_value")
ACTIVITY_HEADER = ("activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id",
                   "reported_result", "details")
EVIDENCE_HEADER = ("file_id", "file_path", "origin", "captured_at")


def load_pipeline():
    """``code/main.py`` under a private name (``evaluation/main.py`` shadows ``main``)."""
    if "audit_pipeline" in sys.modules:
        return sys.modules["audit_pipeline"]
    spec = importlib.util.spec_from_file_location("audit_pipeline", CODE_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up here
    spec.loader.exec_module(module)
    return module


def load_cases(cases_dir: Path = CASES_DIR) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(cases_dir.glob("*.json"))]


def _write_csv(path: Path, header: tuple[str, ...], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def materialize(cases: list[dict], root: Path, order=None) -> Path:
    """Write ``cases`` merged into one dataset directory under ``root``.

    ``order(rows)`` may reorder every global table (metamorphic shuffle test)."""
    order = order or (lambda rows: rows)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DATASET_DIR / "deletion_rules.csv", root / "deletion_rules.csv")
    identities = [dict(i, email_hash=email_hash(i["email"])) for c in cases for i in c["identities"]]
    evidence = []
    for case in cases:
        for ev in case["evidence"]:
            path = root / ev["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ev["content"]
            path.write_text(content if isinstance(content, str) else json.dumps(content, indent=2),
                            encoding="utf-8")
            evidence.append({"file_id": ev["file_id"], "file_path": ev["path"], "origin": ev["origin"],
                             "captured_at": ev["captured_at"]})
    _write_csv(root / "deletion_requests.csv", REQUEST_HEADER, order([c["request"] for c in cases]))
    _write_csv(root / "user_identities.csv", IDENTITY_HEADER, order(identities))
    _write_csv(root / "user_audit_log.csv", AUDIT_HEADER, order([a for c in cases for a in c["audit_log"]]))
    _write_csv(root / "system_activity.csv", ACTIVITY_HEADER, order([a for c in cases for a in c["activity"]]))
    _write_csv(root / "evidence_files.csv", EVIDENCE_HEADER, order(evidence))
    return root


@dataclass
class CaseRun:
    rows: dict[str, tuple[str, list[dict]]]
    agent: dict = field(default_factory=dict)


def run(dataset_dir: Path, agent_replies: list | None = None) -> CaseRun:
    """Run the pipeline on a materialized dataset. With replies, the agent uses a fake model."""
    pipeline = load_pipeline()
    client = None
    if agent_replies:
        client = LLMClient(transport=FakeTransport(agent_replies), cache=LLMCache(cache_dir=None, snapshot={}),
                           mode=LIVE)
    ctx = pipeline.build_context(dataset_dir, client=client, vision=False, agent=client is not None)
    results = pipeline.run_cases(load_requests(dataset_dir / "deletion_requests.csv"), ctx)
    rows = {r.case_id: (r.status, json.loads(pipeline.serialize_steps(r.steps))) for r in results}
    s = ctx.agent_stats
    return CaseRun(rows, {"runs": s.runs, "proposals": s.proposals, "accepted": s.accepted,
                          "rejected": dict(s.rejected)})


def run_cases(cases: list[dict], **kwargs) -> CaseRun:
    with tempfile.TemporaryDirectory() as tmp:
        return run(materialize(cases, Path(tmp) / "dataset", **kwargs.pop("materialize", {})), **kwargs)


def check(case: dict) -> dict:
    """Run one case alone and compare with its expected row (and agent counts when given)."""
    got = run_cases([case], agent_replies=case.get("agent_replies") or None)
    status, steps = got.rows[case["request"]["case_id"]]
    want = case["expected"]
    problems = []
    if status != want["deletion_status"]:
        problems.append(f"status {status} != {want['deletion_status']}")
    if steps != want["steps"]:
        problems.append("steps differ")
    for key, value in (case.get("expected_agent") or {}).items():
        if got.agent.get(key) != value:
            problems.append(f"agent {key} {got.agent.get(key)} != {value}")
    return {"name": case["name"], "passed": not problems, "problems": problems, "status": status,
            "steps": steps, "agent": got.agent}
