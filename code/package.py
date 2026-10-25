"""Build ``code.zip`` for submission (AGENTS.md 6.9).

Contents: ``code/`` (pipeline, prompts, ``README.md``, ``requirements.txt``, ``llm_snapshot.py``,
``ocr_snapshot.json``, ``evaluation/`` with both reports), the repo-root ``.env.example``, and
copies of ``code/README.md`` and the two reports at the archive root (``README.md``,
``evaluation/*.md``: the paths AGENTS.md 6.8 names). The copies come from the same files at
build time, so they cannot drift.

Never: ``.env`` or any secret file, ``dataset/``, ``output.csv``, caches, virtual environments,
nested archives. ``check()`` refuses a forbidden path, so a ``.env`` can never enter the archive
even if it is copied into ``code/``. ``scan_secrets()`` reads every packaged file and refuses
key-shaped content and the configured ``ZENMUX_API_KEY`` value (environment or ``.env``;
compared, never printed).

Usage: python code/package.py [--out code.zip]
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INCLUDE_DIRS = ("code",)
ROOT_FILES = (".env.example",)
# archive name -> repo-relative source (root copies of files under code/)
COPIES = {"README.md": "code/README.md",
          "evaluation/evaluation_report.md": "code/evaluation/evaluation_report.md",
          "evaluation/usage_report.md": "code/evaluation/usage_report.md"}
FORBIDDEN_PARTS = {"dataset", ".cache", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
                   ".ruff_cache", ".git", "node_modules"}
FORBIDDEN_NAMES = (".env", ".env.*", "*.zip", "*.pem", "*.key", "id_rsa*", "*.sqlite", "*.db", "output.csv",
                   "*_failures.csv", "*.pyc")
ALLOWED_NAMES = (".env.example",)
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "api key assignment": re.compile(r"(?im)^[ \t]*[A-Z_]*API_KEY[ \t]*=[ \t]*['\"]?[A-Za-z0-9_\-]{8,}"),
    "sk- token": re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    "bearer token": re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    "aws key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


class PackagingError(RuntimeError):
    pass


def forbidden(rel: Path) -> str:
    """Reason a repo-relative path must not be packaged, or ``""``."""
    if FORBIDDEN_PARTS & set(rel.parts):
        return "forbidden directory"
    name = rel.name
    if name in ALLOWED_NAMES:
        return ""
    for pattern in FORBIDDEN_NAMES:
        if fnmatch.fnmatch(name, pattern):
            return f"forbidden file {pattern}"
    return ""


def package_files(root: Path = REPO_ROOT) -> list[Path]:
    files = []
    for top in INCLUDE_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and not forbidden(rel):
                files.append(rel)
    files += [Path(name) for name in ROOT_FILES if (root / name).is_file()]
    return files


def check(files: list[Path]) -> None:
    bad = [(f, forbidden(f)) for f in files if forbidden(f)]
    if bad:
        raise PackagingError("; ".join(f"{f}: {why}" for f, why in bad))


def scan_secrets(files: list[Path], root: Path = REPO_ROOT) -> list[str]:
    """Findings as ``path: kind`` (never the matched text)."""
    import config  # code/ is on sys.path when this file runs or is imported

    key = config.api_key().strip()
    findings = []
    for rel in files:
        text = (root / rel).read_bytes().decode("utf-8", errors="replace")
        for kind, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{rel.as_posix()}: {kind}")
        if len(key) >= 8 and key in text:
            findings.append(f"{rel.as_posix()}: ZENMUX_API_KEY value")
    return findings


def build(out: Path, root: Path = REPO_ROOT) -> int:
    files = package_files(root)
    check(files)
    missing = [src for src in COPIES.values() if not (root / src).is_file()]
    if missing:
        raise PackagingError(f"missing required files: {missing}")
    secrets = scan_secrets(files, root)
    if secrets:
        raise PackagingError("secret scan: " + "; ".join(secrets))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in files:
            archive.write(root / rel, rel.as_posix())
        for name, src in COPIES.items():
            archive.write(root / src, name)
    return len(files) + len(COPIES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "code.zip"))
    args = parser.parse_args(argv)
    try:
        count = build(Path(args.out))
    except PackagingError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {count} files -> {args.out} (secret scan clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
