"""JSON evidence (snapshot bundles, service exports, connector/export/security ledgers) -> RawRecords.

Every dict carrying a `resource_id` is one record. Nested dicts without their own resource_id (a search
document, a profile) are merged into the parent; a nested dict for the *same* resource is merged as well.
Collection / data-store names are inherited from the enclosing objects.
"""
from __future__ import annotations

import json

from ..loaders import parse_ts
from ..models import EvidenceFile
from .records import NAME_FIELDS, RawRecord, is_null, system_for

SERVICE_KEYS = {
    "account_service", "search_service", "support_platform", "analytics_platform", "export_service",
    "integration_service", "backup_service", "security_service", "identity_service", "legal_service",
    "marketing_platform",
}
GENERIC_LIST_KEYS = {"records", "snapshots", "documents", "hits", "items", "entries"}


def _merge_children(node: dict) -> dict:
    flat: dict = {}
    for k, v in node.items():
        if isinstance(v, dict):
            if "resource_id" in v and v.get("resource_id") != node.get("resource_id"):
                continue
            if k.lower() in NAME_FIELDS:
                # a structured name ({"first": .., "last": ..}) is one direct identifier
                parts = [str(x) for x in v.values() if not isinstance(x, (dict, list)) and not is_null(x)]
                flat.setdefault(k, " ".join(parts) or None)
                continue
            for ck, cv in _merge_children(v).items():
                flat.setdefault(ck, cv)
            if not v:
                flat[k] = None
        elif isinstance(v, list):
            same = [x for x in v if isinstance(x, dict) and x.get("resource_id") == node.get("resource_id")]
            for x in same:
                for ck, cv in _merge_children(x).items():
                    flat.setdefault(ck, cv)
            if not any(isinstance(x, dict) for x in v):
                flat[k] = json.dumps(v, sort_keys=True)
        else:
            flat[k] = v
    if "profile" in node and node["profile"] is None:
        flat["profile"] = None
    return flat


def extract(ef: EvidenceFile) -> tuple[list[RawRecord], set[tuple[str, str]]]:
    data = json.loads(ef.path.read_text(encoding="utf-8"))
    records: list[RawRecord] = []
    coverage: set[tuple[str, str]] = set()

    def walk(node, ctx: dict):
        if isinstance(node, dict):
            ctx = dict(ctx)
            if node.get("data_store"):
                ctx["system"] = node["data_store"]
            if node.get("collection"):
                ctx["collection"] = node["collection"]
            if node.get("captured_at"):
                ctx["captured"] = node["captured_at"]
            # a snapshot block with an explicit records list is a full capture of that data store
            if "records" in node and isinstance(node["records"], list) and node.get("data_store"):
                coverage.add((node["data_store"], ctx.get("collection", "*")))
            rid = node.get("resource_id")
            if isinstance(rid, str) and rid:
                f = _merge_children(node)
                records.append(RawRecord(
                    evidence_id=ef.file_id,
                    captured_at=ef.captured_at,
                    resource_id=rid,
                    fields=f,
                    observed_at=parse_ts(str(f.get("observed_at") or f.get("recorded_at") or ctx.get("captured") or "")),
                    system_hint=f.get("system") or ctx.get("system") or system_for(rid),
                    location=ctx.get("system_location", ""),
                    collection=ctx.get("collection", ""),
                    source_format="json",
                ))
            for k, v in node.items():
                if not isinstance(v, (dict, list)):
                    continue
                if rid and isinstance(v, dict) and v.get("resource_id") in (None, rid):
                    continue  # already merged into the parent record
                child = dict(ctx)
                if k in SERVICE_KEYS:
                    child["system"] = k
                if isinstance(v, list) and k not in GENERIC_LIST_KEYS and not node.get("collection"):
                    child["collection"] = k
                walk(v, child)
        elif isinstance(node, list):
            for item in node:
                walk(item, ctx)

    walk(data, {})
    return records, coverage
