#!/usr/bin/env python3
"""Build code.zip at the repository root: README.md + code/ (with the committed LLM cache and the
evaluation reports), excluding the dataset, caches of Python, run ledgers, local env files and archives."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"__pycache__", ".runs", ".venv", "venv", "node_modules", ".git", ".pytest_cache", "ledger"}
EXCLUDE_SUFFIXES = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".pyc"}
EXCLUDE_NAMES = {".env", ".DS_Store", "sample_predictions.csv"}
ROOT_REPORTS = ("evaluation_report.md", "usage_report.md")


def included(path: Path) -> bool:
    rel = path.relative_to(REPO)
    return not (set(rel.parts) & EXCLUDE_DIRS or path.suffix in EXCLUDE_SUFFIXES or path.name in EXCLUDE_NAMES)


def main() -> int:
    target = REPO / "code.zip"
    files = [REPO / "README.md"] + sorted(p for p in (REPO / "code").rglob("*") if p.is_file() and included(p))
    for required in ("code/evaluation/evaluation_report.md", "code/evaluation/usage_report.md", "code/main.py"):
        if not (REPO / required).exists():
            print(f"missing {required}", file=sys.stderr)
            return 1
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(REPO).as_posix())
        # the problem statement names evaluation/ at the archive root; the organizer README names code/evaluation/.
        # Ship the two required reports at both paths so either reading finds them.
        for name in ROOT_REPORTS:
            zf.write(REPO / "code" / "evaluation" / name, f"evaluation/{name}")
    print(f"wrote {target} ({len(files) + len(ROOT_REPORTS)} files, {target.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
