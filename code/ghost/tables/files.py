"""Evidence manifest: evidence_id -> path, kind, capture time, content hash."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from ..config import DATASET_DIR, EVIDENCE_MANIFEST_CSV
from ..dataset_io import read_csv

log = logging.getLogger(__name__)

_KIND_BY_SUFFIX = {".sql": "sql", ".json": "json", ".txt": "txt", ".log": "log",
                   ".png": "png", ".jpg": "png", ".jpeg": "png", ".pdf": "pdf"}


@dataclass(frozen=True)
class EvidenceFile:
    evidence_id: str
    path: str          # relative to dataset/
    kind: str
    origin: str
    captured_at: str
    sha256: str


def build_files() -> list[EvidenceFile]:
    rows = read_csv(EVIDENCE_MANIFEST_CSV, ("file_id", "file_path", "origin", "captured_at"))
    files: list[EvidenceFile] = []
    for r in rows:
        full = DATASET_DIR / r["file_path"]
        if not full.is_file():
            log.error("%s: listed in manifest but missing on disk: %s", r["file_id"], r["file_path"])
            continue
        kind = _KIND_BY_SUFFIX.get(full.suffix.lower(), "unknown")
        if kind == "unknown":
            log.warning("%s: unknown file type %s", r["file_id"], full.suffix)
        files.append(EvidenceFile(r["file_id"], r["file_path"], kind, r["origin"], r["captured_at"],
                                  hashlib.sha256(full.read_bytes()).hexdigest()))
    files.sort(key=lambda f: f.evidence_id)
    log.info("files: %d evidence files (%s)", len(files),
             ", ".join(f"{k}={sum(f.kind == k for f in files)}" for k in sorted({f.kind for f in files})))
    return files
