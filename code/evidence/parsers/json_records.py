"""Parser for JSON evidence under ``evidence/records/``.

Shapes are detected from keys, not file names:

A. snapshot bundle     {exported_at, source, snapshots:[{captured_at, data_store, collection, records}]}
B. service export      {exported_at, region, source, service_exports:{svc:{coll:[...]}}}
C. lookup ledger       {exported_at, origin, record_count, records:[{recorded_at, system, resource_id, record_type, result, ...}]}
D. collection dump     {captured_at, source, collection, records:[...]}
"""

from __future__ import annotations

import json
from typing import Any

from ..models import ABSENT, COMPLETE, INCOMPLETE, PRESENT, EvidenceFile, ParseIssue, SnapshotScope
from ..normalize import (
    CANONICAL_SYSTEMS,
    category_for,
    norm_resource_id,
    parse_ts,
    system_for_resource,
)
from .common import ParseResult, ledger_presence, make_record

FMT = "json"


def is_ledger_record(r: Any) -> bool:
    return isinstance(r, dict) and {"system", "resource_id", "result"} <= set(r)


def ledger_record(ev: EvidenceFile, r: dict, locator: str, fallback_ts, res: ParseResult):
    observed = parse_ts(r.get("recorded_at")) or fallback_ts
    rec = make_record(
        ev,
        system_id=str(r["system"]),
        resource_id=str(r["resource_id"]),
        observed_at=observed,
        presence=ledger_presence(r.get("result")),
        payload=r,
        claim_only=True,
        source_format=ev.extension or FMT,
        locator=locator,
        data_category=r.get("record_type") or None,
        pii_override={},  # subject_reference/lookup_value are lookup keys
    )
    res.records.append(rec)
    res.bump("ledger_records")


def _system_for(store: str | None, rid: str) -> str:
    if store and store in CANONICAL_SYSTEMS:
        return store
    return system_for_resource(rid) or (store or "unknown_system")


def parse_json(ev: EvidenceFile) -> ParseResult:
    res = ParseResult()
    try:
        doc = json.loads(ev.absolute_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        res.issues.append(ParseIssue(ev.file_id, "error", f"invalid JSON: {exc}"))
        return res
    if not isinstance(doc, dict):
        res.issues.append(ParseIssue(ev.file_id, "unsupported", "top-level JSON is not an object"))
        return res

    if "snapshots" in doc:
        _parse_bundle(ev, doc, res)
    elif "service_exports" in doc:
        _parse_service_export(ev, doc, res)
    elif "records" in doc and "collection" in doc:
        _parse_collection_dump(ev, doc, res)
    elif "records" in doc and all(is_ledger_record(r) for r in doc.get("records") or []):
        fallback = parse_ts(doc.get("exported_at")) or ev.captured_at
        for i, r in enumerate(doc.get("records") or []):
            ledger_record(ev, r, f"records[{i}]", fallback, res)
    else:
        res.issues.append(ParseIssue(ev.file_id, "unsupported", f"unrecognised JSON shape: keys={sorted(doc)}"))
    return res


def _scope_and_records(ev, res, *, store, collection, captured, records, locator_prefix, scope_source):
    ids = []
    systems = set()
    skipped = 0
    for i, r in enumerate(records):
        loc = f"{locator_prefix}.records[{i}]"
        if is_ledger_record(r):
            ledger_record(ev, r, loc, captured, res)
            continue
        if not isinstance(r, dict) or not r.get("resource_id"):
            res.issues.append(ParseIssue(ev.file_id, "warning", f"{loc}: record without resource_id"))
            skipped += 1
            continue
        rid = str(r["resource_id"])
        system = _system_for(store, rid)
        systems.add(system)
        ids.append(norm_resource_id(rid))
        res.records.append(
            make_record(
                ev,
                system_id=system,
                resource_id=rid,
                observed_at=captured,
                presence=PRESENT,
                payload=r,
                claim_only=False,
                source_format=FMT,
                locator=loc,
                collection=collection,
                raw_extra={"data_store": store},
            )
        )
        res.bump("snapshot_records")
    # A snapshot of a collection (even an empty one) proves which resources it held.
    if records and all(is_ledger_record(r) for r in records):
        return
    scope_systems = systems or ({_system_for(store, "")} if store else set())
    for system in scope_systems:
        res.scopes.append(
            SnapshotScope(
                evidence_id=ev.file_id,
                system_id=system,
                data_category=category_for(collection, None),
                collection=collection,
                replica_or_table=None,
                captured_at=captured,
                resource_ids=frozenset(ids),
                scope_source=scope_source,
                completeness=INCOMPLETE if skipped else COMPLETE,
                limitations=(f"{skipped} snapshot record(s) had no resource_id and could not be listed",) if skipped else (),
            )
        )


def _parse_bundle(ev, doc, res):
    for si, snap in enumerate(doc.get("snapshots") or []):
        captured = parse_ts(snap.get("captured_at")) or parse_ts(doc.get("exported_at")) or ev.captured_at
        _scope_and_records(
            ev,
            res,
            store=snap.get("data_store"),
            collection=snap.get("collection"),
            captured=captured,
            records=snap.get("records") or [],
            locator_prefix=f"snapshots[{si}]",
            scope_source="collection_snapshot",
        )


def _parse_collection_dump(ev, doc, res):
    captured = parse_ts(doc.get("captured_at")) or ev.captured_at
    _scope_and_records(
        ev,
        res,
        store=None,
        collection=doc.get("collection"),
        captured=captured,
        records=doc.get("records") or [],
        locator_prefix="$",
        scope_source="collection_dump",
    )


def _parse_service_export(ev, doc, res):
    fallback = parse_ts(doc.get("exported_at")) or ev.captured_at
    exports = doc.get("service_exports") or {}
    for svc, colls in exports.items():
        if not isinstance(colls, dict):
            res.issues.append(ParseIssue(ev.file_id, "warning", f"service_exports.{svc} is not an object"))
            continue
        for coll, items in colls.items():
            for i, r in enumerate(items or []):
                loc = f"service_exports.{svc}.{coll}[{i}]"
                if is_ledger_record(r):
                    ledger_record(ev, r, loc, fallback, res)
                    continue
                if not isinstance(r, dict) or not r.get("resource_id"):
                    res.issues.append(ParseIssue(ev.file_id, "warning", f"{loc}: record without resource_id"))
                    continue
                observed = parse_ts(r.get("observed_at")) or fallback
                system = _system_for(svc, str(r["resource_id"]))
                common = dict(
                    observed_at=observed,
                    claim_only=False,
                    source_format=FMT,
                    collection=coll,
                    raw_extra={"region": doc.get("region")},
                )
                if "hits" in r:  # search index query
                    hits = r.get("hits") or {}
                    docs = hits.get("documents") or []
                    total = hits.get("total")
                    if not docs or total == 0:
                        res.records.append(make_record(
                            ev, system_id=system, resource_id=str(r["resource_id"]),
                            presence=ABSENT, payload={k: v for k, v in r.items() if k != "hits"} | {"hits_total": total},
                            locator=loc, **common))
                    for di, d in enumerate(docs):
                        rid = str(d.get("resource_id") or r["resource_id"])
                        payload = dict(d) | {"query": r.get("query"), "hits_total": total}
                        res.records.append(make_record(
                            ev, system_id=system, resource_id=rid, presence=PRESENT,
                            payload=payload, locator=f"{loc}.hits.documents[{di}]", **common))
                    res.bump("readback_records")
                    continue
                presence = PRESENT
                status = r.get("status_code")
                if status is not None:
                    try:
                        status = int(status)
                    except (TypeError, ValueError):
                        pass
                    if status == 404 or ("profile" in r and r.get("profile") is None and status != 200):
                        presence = ABSENT
                payload = {k: v for k, v in r.items() if k != "profile"}
                if isinstance(r.get("profile"), dict):
                    payload.update({f"{k}": v for k, v in r["profile"].items()})
                res.records.append(make_record(
                    ev, system_id=system, resource_id=str(r["resource_id"]), presence=presence,
                    payload=payload, locator=loc, **common))
                res.bump("readback_records")
