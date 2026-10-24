"""Submission preflight checks for data, output, reports, secrets, and code.zip."""
from __future__ import annotations

import argparse
import csv
import re
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from code.evidence import _safe_evidence_path
from code.ingest import load_all
from code.validate import validate_case_coverage, validate_output, validate_row_count

REPORT_SECTIONS = {
    "evaluation/evaluation_report.md": (
        "Case-Level Deletion-Status Accuracy",
        "Step-Level and Field-Level Accuracy",
        "Sequence Accuracy",
        "Additional Evaluation Cases",
        "Failures Found and Improvements Made",
    ),
    "evaluation/usage_report.md": (
        "Model Providers and Model Names",
        "Model Call Counts",
        "Input and Output Tokens",
        "Total and Average Tokens Per Request",
        "Estimated Total and Per-Request Cost",
        "Per-Model and Overall Totals",
    ),
}
FORBIDDEN_ARCHIVE_PARTS = {"dataset", "__pycache__", ".venv", "venv", "node_modules", ".git"}
SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(?i)(?:api[_-]?key|password|secret)\s*=\s*['\"][^'\"]+['\"]"),
)


def _check_output(root: Path, data: dict) -> list[str]:
    path = root / "output.csv"
    if not path.is_file():
        return ["output.csv is missing"]
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected_header = ["case_id", "deletion_status", "steps_json"]
        if reader.fieldnames != expected_header:
            return [f"output.csv header must be {expected_header}"]
        rows = list(reader)
    errors = validate_output(rows)
    errors.extend(validate_row_count(rows, expected=len(data["deletion_requests"])))
    errors.extend(validate_case_coverage(
        rows, (case["case_id"] for case in data["deletion_requests"])
    ))
    return errors


def _check_reports(root: Path) -> list[str]:
    errors = []
    for relative, sections in REPORT_SECTIONS.items():
        path = root / "code" / relative
        if not path.is_file():
            errors.append(f"missing report: code/{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for section in sections:
            if section not in text:
                errors.append(f"code/{relative} missing section: {section}")
    return errors


def _check_source_secrets(root: Path) -> list[str]:
    errors = []
    paths = [root / "README.md", *sorted((root / "code").rglob("*.py")),
             *sorted((root / "code").rglob("*.md")), *sorted((root / "code").rglob("*.sh"))]
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible hardcoded secret in {path.relative_to(root)}")
                break
    return errors


def _check_archive(root: Path, required: bool) -> list[str]:
    path = root / "code.zip"
    if not path.exists():
        return ["code.zip is missing"] if required else []
    errors = []
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"code.zip has a corrupt member: {bad}")
            names = archive.namelist()
    except zipfile.BadZipFile:
        return ["code.zip is not a valid ZIP archive"]
    for name in names:
        parts = set(Path(name).parts)
        if parts & FORBIDDEN_ARCHIVE_PARTS or name.endswith((".pyc", ".pyo")):
            errors.append(f"forbidden code.zip member: {name}")
        if name.endswith((".zip", ".tar", ".gz", ".tgz", ".7z", ".rar")):
            errors.append(f"nested archive in code.zip: {name}")
        if name == "code/cache.json":
            errors.append("generated model cache included in code.zip")
    required_members = {"README.md", "code/main.py", "code/requirements.txt",
                        "code/evaluation/evaluation_report.md", "code/evaluation/usage_report.md"}
    missing = sorted(required_members - set(names))
    if missing:
        errors.append(f"code.zip missing required members: {', '.join(missing)}")
    return errors


def run_preflight(root: str | Path, require_package=False) -> list[str]:
    root = Path(root).resolve()
    errors = []
    if sys.version_info < (3, 10):
        errors.append("Python 3.10 or newer is required (submission target is Python 3.12)")
    try:
        data = load_all(root)
    except (OSError, ValueError) as exc:
        return [f"dataset validation failed: {exc}"]
    expected_counts = {
        "deletion_requests": 518, "sample_requests": 32,
        "evidence_manifest": 94, "deletion_rules": 15,
    }
    for key, expected in expected_counts.items():
        if len(data[key]) != expected:
            errors.append(f"{key}: expected {expected}, got {len(data[key])}")
    for item in data["evidence_manifest"].values():
        try:
            _safe_evidence_path(root / "dataset", item["file_path"])
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    errors.extend(_check_output(root, data))
    errors.extend(_check_reports(root))
    errors.extend(_check_source_secrets(root))
    errors.extend(_check_archive(root, require_package))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-package", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    errors = run_preflight(root, args.require_package)
    for error in errors:
        print(f"PREFLIGHT ERROR: {error}")
    if errors:
        print(f"Preflight failed with {len(errors)} error(s).")
        return 1
    print("Preflight passed: dataset, output, reports, source, and package are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
