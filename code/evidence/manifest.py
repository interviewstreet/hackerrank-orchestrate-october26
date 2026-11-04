"""Loader for ``dataset/evidence_files.csv``."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .models import EvidenceFile
from .normalize import parse_ts

MANIFEST_NAME = "evidence_files.csv"
REQUIRED_COLUMNS = ("file_id", "file_path", "origin", "captured_at")
SUPPORTED_EXTENSIONS = ("json", "sql", "log", "pdf", "png", "txt")


class ManifestError(ValueError):
    pass


@dataclass
class ManifestReport:
    files: list[EvidenceFile] = field(default_factory=list)
    missing_on_disk: list[str] = field(default_factory=list)  # file_ids
    unlisted_on_disk: list[str] = field(default_factory=list)  # relative paths
    unsupported: list[str] = field(default_factory=list)  # file_ids
    duplicate_ids: list[str] = field(default_factory=list)
    outside_evidence_dir: list[str] = field(default_factory=list)  # file_ids refused


def load_manifest(dataset_dir: Path | str) -> ManifestReport:
    dataset_dir = Path(dataset_dir)
    path = dataset_dir / MANIFEST_NAME
    if not path.is_file():
        raise ManifestError(f"manifest not found: {path}")

    report = ManifestReport()
    seen: set[str] = set()
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing_cols:
            raise ManifestError(f"manifest missing columns: {missing_cols}")
        for lineno, row in enumerate(reader, start=2):
            file_id = (row["file_id"] or "").strip()
            rel = (row["file_path"] or "").strip()
            captured = parse_ts(row["captured_at"])
            if not file_id or not rel or captured is None:
                raise ManifestError(f"manifest line {lineno}: invalid row {row!r}")
            if file_id in seen:
                report.duplicate_ids.append(file_id)
                continue
            seen.add(file_id)
            # Manifest paths are POSIX; build a native path explicitly.
            abs_path = dataset_dir.joinpath(*PurePosixPath(rel).parts)
            # Only files under dataset/evidence/ may be read (no absolute paths or "..").
            try:
                abs_path.resolve().relative_to((dataset_dir / "evidence").resolve())
            except ValueError:
                report.outside_evidence_dir.append(file_id)
            ev = EvidenceFile(
                file_id=file_id,
                file_path=rel,
                origin=(row["origin"] or "").strip(),
                captured_at=captured,
                absolute_path=abs_path,
            )
            report.files.append(ev)
            if not abs_path.is_file():
                report.missing_on_disk.append(file_id)
            if ev.extension not in SUPPORTED_EXTENSIONS:
                report.unsupported.append(file_id)

    listed = {PurePosixPath(f.file_path).as_posix() for f in report.files}
    evidence_root = dataset_dir / "evidence"
    if evidence_root.is_dir():
        for p in sorted(evidence_root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(dataset_dir).as_posix()
                if rel not in listed:
                    report.unlisted_on_disk.append(rel)
    return report
