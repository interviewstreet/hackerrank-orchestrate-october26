"""Build ``code.zip`` for submission (AGENTS.md 6.9).

Contents: ``code/`` and ``evaluation/`` (reports). Never: ``.env`` or any secret file, ``dataset/``,
caches, virtual environments, nested archives. ``check()`` refuses a forbidden path, so a
``.env`` can never enter the archive even if it is copied into ``code/``.

Usage: python code/package.py [--out code.zip]
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INCLUDE_DIRS = ("code", "evaluation")
FORBIDDEN_PARTS = {"dataset", ".cache", "__pycache__", ".venv", "venv", ".pytest_cache", ".git", "node_modules"}
FORBIDDEN_NAMES = (".env", ".env.*", "*.zip", "*.pem", "*.key", "id_rsa*", "*.sqlite", "*.db")
ALLOWED_NAMES = (".env.example",)


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
    return files


def check(files: list[Path]) -> None:
    bad = [(f, forbidden(f)) for f in files if forbidden(f)]
    if bad:
        raise PackagingError("; ".join(f"{f}: {why}" for f, why in bad))


def build(out: Path, root: Path = REPO_ROOT) -> int:
    files = package_files(root)
    check(files)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in files:
            archive.write(root / rel, rel.as_posix())
    return len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "code.zip"))
    args = parser.parse_args(argv)
    print(f"wrote {build(Path(args.out))} files -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
