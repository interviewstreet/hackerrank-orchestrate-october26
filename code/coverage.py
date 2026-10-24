"""Per-file parse accounting.

Every manifest file gets one ``FileCoverage`` row: format, family, rows parsed, rows
skipped (with reasons) and any shape error. Formats that an extractor owns must parse
with no error; ``check()`` raises ``CoverageError`` otherwise.

Usage: python code/coverage.py   (prints the report; exit 1 on unknown shapes)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field

PARSED, DEFERRED, ERROR = "parsed", "deferred", "error"
# Formats parsed in this phase. Logs, PNG and PDF come in later phases.
OWNED_FORMATS = ("sql", "json", "txt", "csv")


class CoverageError(RuntimeError):
    pass


@dataclass
class FileCoverage:
    file_id: str
    path: str
    fmt: str
    status: str
    family: str = ""
    rows_parsed: int = 0
    scopes: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    error: str = ""


@dataclass
class CoverageReport:
    files: list[FileCoverage] = field(default_factory=list)

    def add(self, item: FileCoverage) -> None:
        self.files.append(item)

    def errors(self, formats=OWNED_FORMATS) -> list[FileCoverage]:
        return [f for f in self.files if f.status == ERROR and f.fmt in formats]

    def check(self, formats=OWNED_FORMATS) -> None:
        bad = self.errors(formats)
        if bad:
            raise CoverageError("; ".join(f"{f.file_id} ({f.path}): {f.error}" for f in bad))

    def summary(self) -> list[dict]:
        groups: dict[str, dict] = defaultdict(lambda: {"files": 0, "parsed": 0, "deferred": 0, "error": 0,
                                                       "rows": 0, "scopes": 0, "skipped": 0})
        for f in self.files:
            g = groups[f.fmt]
            g["files"] += 1
            g[f.status] += 1
            g["rows"] += f.rows_parsed
            g["scopes"] += f.scopes
            g["skipped"] += sum(f.skipped.values())
        return [{"format": fmt, **vals} for fmt, vals in sorted(groups.items())]

    def render(self) -> str:
        lines = ["| Format | Files | Parsed | Deferred | Errors | Rows | Scopes | Skipped |",
                 "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for g in self.summary():
            lines.append(f"| {g['format']} | {g['files']} | {g['parsed']} | {g['deferred']} | {g['error']} | "
                         f"{g['rows']} | {g['scopes']} | {g['skipped']} |")
        reasons: dict[str, int] = defaultdict(int)
        for f in self.files:
            for reason, n in f.skipped.items():
                reasons[f"{f.fmt}: {reason}"] += n
        for reason, n in sorted(reasons.items()):
            lines.append(f"- skipped {n}: {reason}")
        for f in self.files:
            if f.status == ERROR:
                lines.append(f"- ERROR {f.file_id} {f.path}: {f.error}")
        return "\n".join(lines)


def main() -> int:
    from facts import FactStore
    from loaders import load_dataset

    store = FactStore.build(load_dataset())
    print(store.coverage.render())
    try:
        store.coverage.check()
    except CoverageError as exc:
        print(f"COVERAGE FAILED: {exc}")
        return 1
    print("COVERAGE OK: no unknown shapes in " + ", ".join(OWNED_FORMATS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
