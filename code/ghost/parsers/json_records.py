"""JSON evidence: service exports, snapshot bundles, ledgers and single-collection reports."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..errors import ParseError
from .base import (COLLECTION_CATEGORY, ParseResult, is_null, ledger_result, norm_subject,
                   state_for, system_for)

log = logging.getLogger(__name__)

# service_resource_export: service -> collection key -> category
_EXPORT_COLLECTIONS = {
    "profiles": "ANALYTICS_PROFILE",
    "restore_entries": "BACKUP_ARCHIVE",
    "exports": "USER_EXPORT",
    "connectors": "DATA_FLOW",
    "audit_records": "SECURITY_AUDIT_LOG",
    "tickets": "SUPPORT_MESSAGE",
}


def parse(path: Path, evidence_id: str, captured_at: str) -> ParseResult:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ParseError(evidence_id, f"invalid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ParseError(evidence_id, "top level is not an object")

    out = ParseResult()
    if "service_exports" in doc:
        _service_export(out, doc["service_exports"], evidence_id, captured_at)
    elif "snapshots" in doc:
        _snapshot_bundle(out, doc["snapshots"], evidence_id, captured_at)
    elif isinstance(doc.get("records"), list) and "collection" in doc:
        category = COLLECTION_CATEGORY.get(doc["collection"])
        if category is None:
            raise ParseError(evidence_id, f"unknown collection {doc['collection']!r}")
        at = doc.get("captured_at") or captured_at
        for rec in doc["records"]:
            _raw_record(out, rec, category, evidence_id, captured_at, at, doc["collection"])
    elif isinstance(doc.get("records"), list):
        for i, rec in enumerate(doc["records"]):
            _ledger_record(out, rec, evidence_id, captured_at, f"records[{i}]")
    else:
        raise ParseError(evidence_id, f"unrecognised JSON shape, keys={sorted(doc)}")
    return out


def _raw_record(out: ParseResult, rec: dict, category: str, evidence_id: str, captured_at: str,
                observed_at: str, ref: str) -> None:
    rid = rec.get("resource_id")
    if not rid:
        out.skipped += 1
        return
    result, subjects = state_for(category, rec)
    out.add(evidence_id=evidence_id, captured_at=captured_at,
            observed_at=rec.get("observed_at") or observed_at,
            system_id=system_for(rid), resource_id=rid, category=category, result=result,
            subjects=subjects,
            retention_until=rec.get("retention_until") or rec.get("retained_until"), raw_ref=ref)


def _ledger_record(out: ParseResult, rec: dict, evidence_id: str, captured_at: str, ref: str) -> None:
    rid, category = rec.get("resource_id"), rec.get("record_type")
    raw_subject = rec.get("subject_reference") or rec.get("lookup_value") or ""
    subject = norm_subject("subject", raw_subject) if raw_subject else None
    result = ledger_result(category or "", rec.get("result") or "", subject)
    if not rid or not category or result is None:
        log.debug("%s: %s unusable ledger row %s", evidence_id, ref, rec)
        out.skipped += 1
        return
    out.add(evidence_id=evidence_id, captured_at=captured_at,
            observed_at=rec.get("recorded_at") or captured_at,
            system_id=rec.get("system") or system_for(rid), resource_id=rid, category=category,
            result=result, subjects=(subject,) if subject else (), raw_ref=ref)


def _service_export(out: ParseResult, exports: dict, evidence_id: str, captured_at: str) -> None:
    for service, collections in sorted(exports.items()):
        out.scope.add((service, captured_at))
        for coll, records in sorted(collections.items()):
            ref = f"{service}.{coll}"
            for rec in records:
                rid = rec.get("resource_id")
                if not rid:
                    out.skipped += 1
                    continue
                at = rec.get("observed_at") or captured_at
                if coll == "profile_lookups":
                    profile = rec.get("profile")
                    if rec.get("status_code") == 404 or not profile:
                        result, subjects = "NOT_FOUND", ()
                    else:
                        result, subjects = state_for("USER_PROFILE", profile)
                    out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=at,
                            system_id=system_for(rid, service), resource_id=rid,
                            category="USER_PROFILE", result=result, subjects=subjects, raw_ref=ref)
                elif coll == "index_queries":
                    query = rec.get("query")
                    q = norm_subject("query", query) if query and not is_null(query) else None
                    hits = (rec.get("hits") or {})
                    docs = [d for d in hits.get("documents") or [] if d.get("resource_id") == rid]
                    if not hits.get("total") or not docs:
                        result, subjects = "NOT_FOUND", ()
                    else:
                        result, subjects = state_for("SEARCH_INDEX_ENTRY", docs[0])
                    subj = tuple(sorted(set(subjects) | ({q} if q else set())))
                    out.add(evidence_id=evidence_id, captured_at=captured_at, observed_at=at,
                            system_id=system_for(rid, service), resource_id=rid,
                            category="SEARCH_INDEX_ENTRY", result=result, subjects=subj, raw_ref=ref)
                elif coll in _EXPORT_COLLECTIONS:
                    _raw_record(out, rec, _EXPORT_COLLECTIONS[coll], evidence_id, captured_at, at, ref)
                else:
                    log.warning("%s: unknown export collection %s", evidence_id, ref)
                    out.skipped += 1


def _snapshot_bundle(out: ParseResult, snapshots: list, evidence_id: str, captured_at: str) -> None:
    for i, snap in enumerate(snapshots):
        coll, store = snap.get("collection"), snap.get("data_store")
        at = snap.get("captured_at") or captured_at
        ref = f"snapshots[{i}].{store}.{coll}"
        records = snap.get("records") or []
        if coll == "operational_record_history":  # ledger rows reported by another service
            for j, rec in enumerate(records):
                _ledger_record(out, rec, evidence_id, captured_at, f"{ref}[{j}]")
            continue
        category = COLLECTION_CATEGORY.get(coll or "")
        if category is None:
            log.warning("%s: unknown bundle collection %s", evidence_id, ref)
            out.skipped += len(records)
            continue
        out.scope.add((store, at))
        for rec in records:
            _raw_record(out, rec, category, evidence_id, captured_at, at, ref)
