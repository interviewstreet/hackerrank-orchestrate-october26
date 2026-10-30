"""Label-free checks on a full run (SPEC §13.4): contract, citation validity, time-travel, determinism,
identifier invariance and policy sanity."""
from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))

from ghostaudit import loaders  # noqa: E402
from ghostaudit.output import validate_csv_text  # noqa: E402

MAIN = CODE / "main.py"
MODEL = CODE / "cache" / "workflow_model.json"
RETAINED_SYSTEMS = {"security_service", "legal_service", "backup_service"}


def read_rows(path: Path) -> dict[str, tuple[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["case_id"]: (r["deletion_status"], r["steps_json"]) for r in csv.DictReader(fh)}


def run_main(dataset: Path, requests: Path, out: Path, backend: str = "replay") -> None:
    subprocess.run([sys.executable, str(MAIN), "--dataset-dir", str(dataset), "--requests", str(requests),
                    "--out", str(out), "--backend", backend, "--workflow-model", str(MODEL)],
                   check=False, capture_output=True, text=True)


def contract(output: Path, requests: Path) -> list[str]:
    ids = [c.case_id for c in loaders.load_cases(requests)]
    errors = validate_csv_text(output.read_text(encoding="utf-8"), ids)
    for cid, (status, sj) in read_rows(output).items():
        steps = json.loads(sj)
        if status == "COMPLETE" and not steps:
            # valid output (authorized deletion, no footprint), but on the real data it has meant a missed link
            errors.append(f"{cid}: COMPLETE without steps (no observable footprint) - check linking")
        if status == "INCOMPLETE":
            for f in (s for s in steps if s["phase"] == "FINDING"):
                key = (f["system_id"], f["resource_id"])
                if not any(s["phase"] == "REMEDIATION" and (s["system_id"], s["resource_id"]) == key for s in steps):
                    errors.append(f"{cid}: finding {key} has no remediation")
                if not any(s["phase"] == "VERIFICATION" and (s["system_id"], s["resource_id"]) == key for s in steps):
                    errors.append(f"{cid}: finding {key} has no verification")
    return errors


def citations(output: Path, dataset: Path, requests: Path) -> list[str]:
    stamps = {e.file_id: e.captured_at for e in loaders.load_manifest(dataset / "evidence_files.csv", dataset)}
    stamps.update({a.activity_id: a.event_time for a in loaders.load_activity(dataset / "system_activity.csv")})
    stamps.update({a.audit_id: a.event_time for a in loaders.load_audit_log(dataset / "user_audit_log.csv")})
    audit_at = {c.case_id: c.audit_at for c in loaders.load_cases(requests)}
    errors = []
    for cid, (_, sj) in read_rows(output).items():
        for s in json.loads(sj):
            ev = s["evidence_id"]
            if not ev:
                continue
            if ev not in stamps:
                errors.append(f"{cid}: cites unknown evidence {ev}")
            elif stamps[ev] > audit_at[cid]:
                errors.append(f"{cid}: cites {ev} captured after audit_at")
    return errors


def policy_sanity(output: Path) -> list[str]:
    errors = []
    for cid, (_, sj) in read_rows(output).items():
        for s in json.loads(sj):
            if s["operation"] == "DELETE_RECORD" and s["system_id"] in RETAINED_SYSTEMS:
                errors.append(f"{cid}: deletes retained record {s['resource_id']}")
            if s["system_id"] == "identity_service" and s["operation"] in {"DELETE_RECORD", "VERIFY_RECORD_ABSENT"}:
                errors.append(f"{cid}: tombstone {s['resource_id']} must be redacted, not deleted")
    return errors


def _filtered_dataset(src: Path, dst: Path, cutoff, keep_cases: list[str], requests: Path) -> Path:
    """Copy of the dataset with every evidence file and activity captured after `cutoff` physically removed."""
    dst.mkdir(parents=True)
    for name in ("user_identities.csv", "user_audit_log.csv", "deletion_rules.csv"):
        shutil.copy(src / name, dst / name)
    with open(src / "evidence_files.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    kept = [r for r in rows if loaders.parse_ts(r["captured_at"]) <= cutoff]
    with open(dst / "evidence_files.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
    for r in kept:
        (dst / r["file_path"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src / r["file_path"], dst / r["file_path"])
    with open(src / "system_activity.csv", newline="", encoding="utf-8") as fh:
        acts = list(csv.DictReader(fh))
    with open(dst / "system_activity.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(acts[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(a for a in acts if loaders.parse_ts(a["event_time"]) <= cutoff)
    # all requests stay (they compete for workflows); only the audited group is written to the request file
    for name in ("deletion_requests.csv", "sample_deletion_requests.csv"):
        if (src / name).exists():
            shutil.copy(src / name, dst / name)
    with open(requests, newline="", encoding="utf-8") as fh:
        reqs = list(csv.DictReader(fh))
    group = dst / "audited_group.csv"
    with open(group, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(reqs[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(r for r in reqs if r["case_id"] in keep_cases)
    return group


def _without_late_retained(full: tuple[str, str] | None, got: tuple[str, str] | None) -> bool:
    """True when `got` equals `full` except for uncited VERIFY_RECORD_PRESENT checks that `full` adds.

    A file exported after the audit can hold a snapshot taken at or before it; a retained record seen only there
    existed at the audit and adds a post-remediation check (never a finding, citation or status change)."""
    if full is None or got is None or full[0] != got[0]:
        return False
    keys = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")
    f = [tuple(s[k] for k in keys) for s in json.loads(full[1])]
    g = [tuple(s[k] for k in keys) for s in json.loads(got[1])]
    extra = [s for s in f if s not in g]
    return [s for s in f if s in g] == g and all(s[3] == "VERIFY_RECORD_PRESENT" and not s[5] for s in extra)


def time_travel(output: Path, dataset: Path, requests: Path, max_groups: int | None = 6) -> tuple[list[str], int]:
    """Re-run groups of cases with all later evidence removed; their rows must not change (except for the
    uncited retained-record checks described in _without_late_retained)."""
    full = read_rows(output)
    groups = defaultdict(list)
    for c in loaders.load_cases(requests):
        groups[c.audit_at].append(c.case_id)
    keys = sorted(groups)
    if max_groups and len(keys) > max_groups:
        step = len(keys) / max_groups
        keys = [keys[int(i * step)] for i in range(max_groups)]
    errors, checked = [], 0
    for cutoff in keys:
        with tempfile.TemporaryDirectory(prefix="gda_tt_") as tmp:
            ds = Path(tmp) / "ds"
            group = _filtered_dataset(dataset, ds, cutoff, groups[cutoff], requests)
            out = Path(tmp) / "out.csv"
            run_main(ds, group, out)
            got = read_rows(out) if out.exists() else {}
            for cid in groups[cutoff]:
                checked += 1
                if got.get(cid) != full.get(cid) and not _without_late_retained(full.get(cid), got.get(cid)):
                    errors.append(f"{cid}: row changes when evidence after {cutoff.isoformat()} is removed")
    return errors, checked


def determinism(dataset: Path, requests: Path, reference: Path) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="gda_det_") as tmp:
        out = Path(tmp) / "again.csv"
        run_main(dataset, requests, out)
        return [] if out.read_bytes() == reference.read_bytes() else ["second replay run is not byte-identical"]


def identifier_invariance(dataset: Path, requests: Path, reference: Path) -> list[str]:
    """Upper-casing and padding the request email must not change any row."""
    with tempfile.TemporaryDirectory(prefix="gda_id_") as tmp:
        with open(requests, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            r["email"] = "  " + r["email"].upper() + " "
        req = Path(tmp) / "requests_upper.csv"
        with open(req, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        out = Path(tmp) / "upper.csv"
        run_main(dataset, req, out)
        a, b = read_rows(reference), read_rows(out)
        return [f"{cid}: row changes with an upper-cased email" for cid in a if a[cid] != b.get(cid)]


EDGE_DATASET = Path(__file__).resolve().parent / "edge_dataset" / "main"


def visual_grounding(datasets: list[Path]) -> tuple[list[str], int]:
    """VISION_SPEC step 2: every vision-model record (replay cache) must be shown by the OCR text of its image,
    and every visual file must have OCR text. Returns (failures, records checked)."""
    from ghostaudit.evidence import build_observation_store, ocr
    from ghostaudit.llm.adapter import LLMAdapter

    fails: list[str] = []
    checked = 0
    for root in datasets:
        ocr.GROUNDING.files.clear()
        build_observation_store(loaders.load_manifest(root / "evidence_files.csv", root), [], LLMAdapter(backend="replay"))
        s = ocr.GROUNDING.summary()
        checked += s["records"]
        fails += [f"{root.name}/{fid}: no OCR text" for fid, st in sorted(ocr.GROUNDING.files.items()) if not st["ocr"]]
        fails += [f"{root.name}/{x}: not visible in OCR text" for x in s["dropped"] + s["fields_removed"]]
    return fails, checked


def run_all(output: Path, dataset: Path, requests: Path, full: bool = False) -> dict:
    res = {
        "contract": contract(output, requests),
        "citations": citations(output, dataset, requests),
        "policy_sanity": policy_sanity(output),
        "determinism": determinism(dataset, requests, output),
        "identifier_invariance": identifier_invariance(dataset, requests, output),
    }
    tt, checked = time_travel(output, dataset, requests, None if full else 6)
    res["time_travel"] = tt
    res["time_travel_cases_checked"] = checked
    vg, n = visual_grounding([dataset, EDGE_DATASET] if EDGE_DATASET.exists() else [dataset])
    res["visual_grounding"] = vg
    res["visual_grounding_records_checked"] = n
    return res


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=CODE.parent / "output.csv")
    ap.add_argument("--dataset-dir", type=Path, default=CODE.parent / "dataset")
    ap.add_argument("--requests", type=Path)
    ap.add_argument("--full", action="store_true", help="time-travel check on every audit_at group")
    a = ap.parse_args()
    reqs = a.requests or a.dataset_dir / "deletion_requests.csv"
    result = run_all(a.output, a.dataset_dir, reqs, a.full)
    print(json.dumps({k: (v if isinstance(v, int) else {"failures": len(v), "examples": v[:5]}) for k, v in result.items()}, indent=2))
    sys.exit(1 if any(isinstance(v, list) and v for v in result.values()) else 0)
