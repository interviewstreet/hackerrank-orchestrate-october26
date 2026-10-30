"""Plain-text handover records: `- ts | system | resource | CATEGORY | RESULT | subject_ref`."""
from __future__ import annotations

import re

from ..loaders import parse_ts
from ..models import EvidenceFile
from .records import RawRecord

LINE_RE = re.compile(
    r"^\s*-?\s*(?P<ts>\S+)\s*\|\s*(?P<system>[\w-]+)\s*\|\s*(?P<rid>[\w-]+)\s*\|\s*(?P<cat>[A-Z_]+)\s*\|\s*(?P<result>[A-Z_]+)\s*\|\s*(?P<ref>.*?)\s*$"
)


def extract(ef: EvidenceFile) -> tuple[list[RawRecord], set[tuple[str, str]]]:
    records: list[RawRecord] = []
    for line in ef.path.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        f = {
            "system": m["system"],
            "resource_id": m["rid"],
            "record_type": m["cat"],
            "result": m["result"],
            "subject_reference": m["ref"],
        }
        records.append(RawRecord(
            evidence_id=ef.file_id,
            captured_at=ef.captured_at,
            resource_id=m["rid"],
            fields=f,
            observed_at=parse_ts(m["ts"]),
            system_hint=m["system"],
            location="handover",
            collection="handover",
            source_format="txt",
        ))
    return records, set()
