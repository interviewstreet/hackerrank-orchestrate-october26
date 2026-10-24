"""JSON evidence -> observations and scopes. Four shapes are known:

* snapshot bundle  ``{exported_at, source, snapshots:[{captured_at, data_store, collection, records}]}``
  Each snapshot lists every record of its store for the subjects in the bundle (an empty
  snapshot proves absence for them). ``operational_record_history`` snapshots hold read-backs
  about other systems instead.
* service export   ``{exported_at, region, source, service_exports:{system:{collection:[rows]}}}``
  Per-row ``observed_at`` read-backs; ``status_code`` 404 means not found.
* record ledger    ``{exported_at, origin, record_count, records:[{recorded_at, system, resource_id,
  record_type, result, subject_reference}]}``: explicit read-backs.
* collection dump  ``{captured_at, source, collection, records}``: rows of one collection.

Any other shape raises ``ShapeError``.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from evidence.common import (
    ABSENT,
    PRESENT,
    PRIMARY,
    SNAPSHOT_ROW,
    STATE_READBACK,
    Extraction,
    Identifiers,
    Observation,
    Scope,
    ShapeError,
    lookup_identifiers,
    record_state,
    resource_refs,
    result_state,
    scan_identifiers,
)
from loaders import EvidenceFile, parse_ts, require_ts

# Collection name -> logical system, for dumps that do not name the system.
COLLECTION_SYSTEMS = {
    "customer_profiles": "account_service",
    "customer_analytics_reports": "analytics_platform",
    "customer_export_jobs": "export_service",
    "customer_search_documents": "search_service",
    "support_conversations": "support_platform",
    "ticket_attachments": "support_platform",
    "connector_configurations": "integration_service",
    "backup_catalog": "backup_service",
    "security_audit_events": "security_service",
    "retained_order_records": "legal_service",
    "deleted_customer_references": "identity_service",
}
READBACK_KEYS = {"recorded_at", "system", "resource_id", "record_type", "result"}


def extract(ev: EvidenceFile, path: Path) -> Extraction:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ShapeError(f"{ev.file_id}: top level is not an object")
    if "snapshots" in data:
        return _bundle(ev, data)
    if "service_exports" in data:
        return _service_export(ev, data)
    if "records" in data and "record_count" in data:
        return _ledger(ev, data)
    if "records" in data and "collection" in data and "captured_at" in data:
        return _collection(ev, data)
    raise ShapeError(f"{ev.file_id}: unknown JSON shape with keys {sorted(data)}")


class _Builder:
    def __init__(self, ev: EvidenceFile, family: str):
        self.ev, self.out, self.n = ev, Extraction(family=family), 0

    def add(self, *, system, resource_id, observed_at, assertion, collection="", record=None,
            link_ids=None, exposed_ids=None, detail="", record_type="", **state) -> Observation:
        if not resource_id:
            raise ShapeError(f"{self.ev.file_id}: row without resource_id at {detail}")
        self.n += 1
        record = record or {}
        updated = record.get("updated_at")
        obs = Observation(
            obs_id=f"{self.ev.file_id}#{self.n}", file_id=self.ev.file_id, source_kind="json",
            family=self.out.family, available_at=self.ev.captured_at,
            state_observed_at=(parse_ts(observed_at) if isinstance(observed_at, str) else observed_at)
            or self.ev.captured_at,
            system_id=system, resource_id=resource_id, assertion=assertion, collection=collection,
            record_type=record_type, record_updated_at=parse_ts(updated) if updated else None,
            link_ids=link_ids if link_ids is not None else Identifiers(),
            exposed_ids=exposed_ids, fields=record, refs=resource_refs(record), detail=detail, **state)
        self.out.observations.append(obs)
        self.out.rows_parsed += 1
        return obs

    def row(self, system, record, observed_at, collection, detail) -> Observation:
        ids = scan_identifiers(record)
        return self.add(system=system, resource_id=record.get("resource_id"), observed_at=observed_at,
                        assertion=SNAPSHOT_ROW, collection=collection, record=record, link_ids=ids,
                        exposed_ids=ids, detail=detail, **record_state(system, record))

    def readback(self, record, observed_at, lookup, detail) -> Observation:
        missing = READBACK_KEYS - set(record) - {"recorded_at"}
        if missing:
            raise ShapeError(f"{self.ev.file_id}: read-back row lacks {sorted(missing)} at {detail}")
        return self.add(system=record["system"], resource_id=record["resource_id"], observed_at=observed_at,
                        assertion=STATE_READBACK, record=record, record_type=record["record_type"],
                        link_ids=lookup_identifiers(lookup), detail=detail,
                        **result_state(record["result"], record["record_type"]))


def _bundle(ev, data) -> Extraction:
    b = _Builder(ev, "json_snapshot_bundle")
    stores: list[tuple[str, str, datetime]] = []
    for i, snap in enumerate(data["snapshots"]):
        for key in ("captured_at", "data_store", "collection", "records"):
            if key not in snap:
                raise ShapeError(f"{ev.file_id}: snapshot {i} lacks {key}")
        at = require_ts(snap["captured_at"])
        if snap["collection"] == "operational_record_history":
            for j, rec in enumerate(snap["records"]):
                b.readback(rec, rec.get("recorded_at") or snap["captured_at"], rec.get("lookup_value"),
                           f"snapshots[{i}].records[{j}]")
            continue
        system = snap["data_store"]
        stores.append((system, snap["collection"], at))
        for j, rec in enumerate(snap["records"]):
            b.row(system, rec, at, snap["collection"], f"snapshots[{i}].records[{j}]")
    # Each snapshot is complete only for the subjects it lists itself, not those of a sibling
    # snapshot in the same bundle.
    subjects: dict[tuple[str, str], Identifiers] = {}
    for obs in b.out.observations:
        subjects.setdefault((obs.system_id, obs.collection), Identifiers()).update(obs.link_ids)
    for system, collection, at in stores:
        b.out.scopes.append(Scope(ev.file_id, b.out.family, system, PRIMARY, ev.captured_at, at,
                                  collection=collection,
                                  subjects=subjects.get((system, collection), Identifiers())))
    return b.out


def _service_export(ev, data) -> Extraction:
    b = _Builder(ev, "json_service_export")
    for system, collections in data["service_exports"].items():
        if not isinstance(collections, dict):
            raise ShapeError(f"{ev.file_id}: service_exports.{system} is not an object")
        for collection, rows in collections.items():
            for j, rec in enumerate(rows):
                where = f"service_exports.{system}.{collection}[{j}]"
                if "observed_at" not in rec:
                    raise ShapeError(f"{ev.file_id}: {where} lacks observed_at")
                if "status_code" in rec:
                    _profile_lookup(b, system, collection, rec, where)
                elif "hits" in rec:
                    _index_query(b, system, collection, rec, where)
                else:
                    ids = scan_identifiers(rec)
                    b.add(system=system, resource_id=rec.get("resource_id"), observed_at=rec["observed_at"],
                          assertion=STATE_READBACK, collection=collection, record=rec, link_ids=ids,
                          exposed_ids=ids, detail=where, **record_state(system, rec))
    return b.out


def _profile_lookup(b, system, collection, rec, where) -> None:
    code = rec["status_code"]
    profile = rec.get("profile") or {}
    ids = scan_identifiers(profile)
    if code == 200:
        state = dict(exists=PRESENT)
    elif code == 404:
        state = dict(exists=ABSENT)
    else:
        raise ShapeError(f"{b.ev.file_id}: {where} has status_code {code!r}")
    b.add(system=system, resource_id=rec.get("resource_id"), observed_at=rec["observed_at"],
          assertion=STATE_READBACK, collection=collection, record=rec, link_ids=ids,
          exposed_ids=ids if code == 200 else None, detail=where, **state)


def _index_query(b, system, collection, rec, where) -> None:
    docs = rec["hits"].get("documents") or []
    if not docs:
        b.out.skip("index query with no hits")
        return
    query_ids = lookup_identifiers(rec.get("query"))
    for k, doc in enumerate(docs):
        ids = scan_identifiers(doc)
        # The query only links a hit that carries no identifier of its own.
        link = ids if ids.any() else query_ids
        b.add(system=system, resource_id=doc.get("resource_id"), observed_at=rec["observed_at"],
              assertion=STATE_READBACK, collection=collection, record=doc, link_ids=link,
              exposed_ids=ids, detail=f"{where}.hits.documents[{k}]", exists=PRESENT)


def _ledger(ev, data) -> Extraction:
    b = _Builder(ev, "json_record_ledger")
    if data["record_count"] != len(data["records"]):
        raise ShapeError(f"{ev.file_id}: record_count {data['record_count']} != {len(data['records'])} rows")
    for j, rec in enumerate(data["records"]):
        b.readback(rec, rec.get("recorded_at") or data.get("exported_at"), rec.get("subject_reference"),
                   f"records[{j}]")
    return b.out


def _collection(ev, data) -> Extraction:
    b = _Builder(ev, "json_collection_dump")
    collection = data["collection"]
    if collection not in COLLECTION_SYSTEMS:
        raise ShapeError(f"{ev.file_id}: unknown collection {collection!r}")
    system, at = COLLECTION_SYSTEMS[collection], require_ts(data["captured_at"])
    for j, rec in enumerate(data["records"]):
        b.row(system, rec, at, collection, f"records[{j}]")
    subjects = Identifiers()
    for obs in b.out.observations:
        subjects.update(obs.link_ids)
    b.out.scopes.append(Scope(ev.file_id, b.out.family, system, PRIMARY, ev.captured_at, at,
                              collection=collection, subjects=subjects))
    return b.out
