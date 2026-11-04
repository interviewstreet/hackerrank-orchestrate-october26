"""Evidence loader: parse every manifest file once and expose indexed observations/coverage."""
from __future__ import annotations

import collections
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List

from .contracts import Coverage, Observation
from .dataset_loader import DatasetContext
from .util import category_for_resource, extract_identifiers
from .parsers.document_parser import parse_pdf
from .parsers.image_parser import parse_image
from .parsers.json_parser import parse_json
from .parsers.log_parser import parse_log
from .parsers.record_parser import parse_txt
from .parsers.sql_parser import parse_sql

PARSERS = {".sql": parse_sql, ".json": parse_json, ".log": parse_log, ".txt": parse_txt,
           ".pdf": parse_pdf, ".png": parse_image, ".jpg": parse_image, ".jpeg": parse_image}


@dataclass
class EvidenceStore:
    observations: List[Observation] = field(default_factory=list)
    coverage: List[Coverage] = field(default_factory=list)
    status: Dict[str, str] = field(default_factory=dict)             # evidence_id -> PROCESSED | FAILED:<reason>
    by_resource: Dict[str, List[Observation]] = field(default_factory=dict)
    by_email: Dict[str, List[Observation]] = field(default_factory=dict)
    by_user_ref: Dict[str, List[Observation]] = field(default_factory=dict)
    by_hash: Dict[str, List[Observation]] = field(default_factory=dict)
    by_system: Dict[str, List[Observation]] = field(default_factory=dict)
    coverage_by_system: Dict[str, List[Coverage]] = field(default_factory=dict)

    def index(self) -> None:
        for o in self.observations:
            self.by_resource.setdefault(o.resource_id, []).append(o)
            self.by_system.setdefault(o.system_id, []).append(o)
            for e in o.emails:
                self.by_email.setdefault(e, []).append(o)
            for u in o.user_refs:
                self.by_user_ref.setdefault(u, []).append(o)
            for h in o.hashes:
                self.by_hash.setdefault(h, []).append(o)
        for c in self.coverage:
            self.coverage_by_system.setdefault(c.system_id, []).append(c)



LINK_LAG = timedelta(minutes=7, seconds=1)   # data-catalog link events are written 7m01s after the artifact is captured


def _ts(v: str) -> datetime:
    return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")


def _link_observations(ctx: DatasetContext, store: "EvidenceStore") -> None:
    """Tie PDF/screenshot artifacts to resources using data-catalog LINK_RESOURCE_IDENTITY events.

    The artifact is the PDF/PNG whose manifest capture time is exactly LINK_LAG before the event. The link event
    supplies the resource id and the subject identifiers; the artifact supplies the evidence id. OCR-only facts keep
    lower confidence."""
    by_time = collections.defaultdict(list)
    for fid, row in ctx.manifest.items():
        if row["abs_path"].lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
            by_time[row["captured_at"]].append(fid)
    for act in ctx.activities:
        if act["event_type"] != "LINK_RESOURCE_IDENTITY":
            continue
        want = (_ts(act["event_time"]) - LINK_LAG).strftime("%Y-%m-%dT%H:%M:%SZ")
        for fid in by_time.get(want, []):
            ids = extract_identifiers(act["details"])
            rid = act["resource_id"]
            system, cat = category_for_resource(rid)
            if act["target_system"] == "object_storage":
                cat = "SUPPORT_ATTACHMENT"
            store.observations.append(Observation(
                evidence_id=fid, captured_at=ctx.manifest[fid]["captured_at"], system_id=system or act["target_system"],
                resource_id=rid, data_category=cat or "", state="PRESENT",
                observed_at=ctx.manifest[fid]["captured_at"], emails=ids["emails"], user_refs=ids["user_refs"],
                hashes=[], phones=[], names=[],
                attrs={"link_activity_id": act["activity_id"], "details": act["details"]},
                source_format="link", locator=act["activity_id"], confidence=0.9))


def load_evidence(ctx: DatasetContext) -> EvidenceStore:
    store = EvidenceStore()
    for fid in sorted(ctx.manifest, key=lambda f: int(f.split("_")[1])):
        row = ctx.manifest[fid]
        ext = "." + row["abs_path"].rsplit(".", 1)[-1].lower()
        parser = PARSERS.get(ext)
        if not parser:
            store.status[fid] = f"FAILED:unsupported format {ext}"
            continue
        try:
            obs, cov = parser(fid, row["captured_at"], row["abs_path"])
            store.observations.extend(obs)
            store.coverage.extend(cov)
            store.status[fid] = "PROCESSED"
        except Exception as exc:  # keep going: one bad file must not stop the run
            store.status[fid] = f"FAILED:{type(exc).__name__}: {exc}"
    _link_observations(ctx, store)
    store.index()
    return store


if __name__ == "__main__":
    import sys
    from .dataset_loader import load_dataset
    ctx = load_dataset(sys.argv[1] if len(sys.argv) > 1 else "dataset")
    st = load_evidence(ctx)
    failed = {k: v for k, v in st.status.items() if v != "PROCESSED"}
    print(f"files={len(st.status)} failed={len(failed)} observations={len(st.observations)} coverage={len(st.coverage)}")
    for k, v in failed.items():
        print("  FAIL", k, v)
    by_fmt = collections.Counter(o.source_format for o in st.observations)
    print("by format:", dict(by_fmt))
    print("by category:", dict(collections.Counter(o.data_category for o in st.observations)))
    per_file = collections.Counter(o.evidence_id for o in st.observations)
    empty = [f for f in st.status if per_file.get(f, 0) == 0]
    print("files yielding 0 observations:", empty)
