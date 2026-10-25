"""JSON evidence: service_resource_export, snapshot bundles, record ledgers,
and flat collection files. Inner timestamps win over the manifest time."""
import json

from ..config import COLLECTION_CATEGORY, PREFIX_MAP
from ..loaders import parse_ts


def _category(system, collection, record_type, resource_id):
    if record_type:
        return record_type
    if collection and collection in COLLECTION_CATEGORY:
        return COLLECTION_CATEGORY[collection]
    prefix = str(resource_id).rsplit("_", 1)[0] if False else None
    for p in sorted(PREFIX_MAP, key=len, reverse=True):
        if str(resource_id).startswith(p + "_"):
            return PREFIX_MAP[p][1]
    return ""


def _system(collection_system, record):
    return (record.get("system") or record.get("data_store")
            or collection_system or "")


def _parse_generic_record(store, source_id, observed, system, collection,
                          record_type, record):
    """One snapshot-bundle style record (presence = PRESENT)."""
    resource_id = record.get("resource_id")
    if not resource_id:
        return
    # Search documents nest identifiers under "document".
    category = _category(system, collection, record_type, resource_id)
    enabled = record.get("enabled")
    restore = record.get("restore_allowed")
    if record.get("download_available") is not None and category == "USER_EXPORT":
        presence = "PRESENT"
    else:
        presence = "PRESENT"
    store.add(source_id, "evidence", observed,
              system or PREFIX_MAP.get(str(resource_id).split("_")[0], ("", ""))[0],
              resource_id, category, presence, record=record,
              enabled=enabled, restore_allowed=restore,
              retention_until=parse_ts(record.get("retention_until")
                                       or record.get("retained_until")))


def parse_json_text(text, source_id, store, manifest_ts):
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return 0
    before = len(store.facts)
    if not isinstance(data, dict):
        return 0
    exported = parse_ts(data.get("exported_at") or data.get("captured_at")) or manifest_ts

    # Shape 1: service_exports
    if isinstance(data.get("service_exports"), dict):
        for system, sections in data["service_exports"].items():
            if not isinstance(sections, dict):
                continue
            for section, records in sections.items():
                if not isinstance(records, list):
                    continue
                for rec in records:
                    _parse_service_export(store, source_id, system, rec, section)

    # Shape 2: snapshot bundles
    if isinstance(data.get("snapshots"), list):
        for snap in data["snapshots"]:
            observed = parse_ts(snap.get("captured_at")) or exported
            system = snap.get("data_store", "")
            collection = snap.get("collection", "")
            for rec in snap.get("records", []):
                if rec.get("record_type") and rec.get("result"):
                    _parse_lookup_record(store, source_id, rec,
                                         parse_ts(rec.get("recorded_at")) or observed)
                else:
                    _parse_generic_record(store, source_id, observed, system,
                                          collection, None, rec)

    # Shape 3: generic records[] ledgers (FOUND / NOT_FOUND and friends)
    if isinstance(data.get("records"), list) and "service_exports" not in data:
        collection = data.get("collection", "")
        system_hint = ""
        if "analytics" in collection:
            system_hint = "analytics_platform"
        elif "export" in collection:
            system_hint = "export_service"
        for rec in data["records"]:
            if rec.get("record_type") and rec.get("result"):
                _parse_lookup_record(store, source_id, rec,
                                     parse_ts(rec.get("recorded_at")) or exported)
            else:
                _parse_generic_record(store, source_id, exported, system_hint,
                                      collection, None, rec)
    return len(store.facts) - before


def _parse_lookup_record(store, source_id, rec, observed):
    resource_id = rec.get("resource_id")
    if not resource_id:
        return
    result = str(rec.get("result", "")).upper()
    system = rec.get("system", "")
    category = _category(system, None, rec.get("record_type"), resource_id)
    subject = rec.get("subject_reference") or rec.get("lookup_value") or ""
    extra = {"subject_reference": subject} if subject else {}
    merged = dict(rec)
    merged.update(extra)
    if result in ("NOT_FOUND",):
        presence = "ABSENT"
    elif result in ("FOUND", "IDENTIFIABLE", "ACTIVE"):
        presence = "PRESENT"
    elif result in ("ANONYMIZED", "REDACTED"):
        presence = "PRESENT"
        merged = {k: v for k, v in merged.items()
                  if k not in ("subject_reference", "lookup_value")}
    else:
        presence = "PRESENT"
    enabled = None
    restore = None
    if category == "DATA_FLOW":
        enabled = (result == "ACTIVE") if result in ("ACTIVE", "DISABLED") else None
    if category == "BACKUP_ARCHIVE":
        restore = (result == "ACTIVE") if result in ("ACTIVE", "BLOCKED") else None
    store.add(source_id, "evidence", observed, system, resource_id, category,
              presence, record=merged if presence == "PRESENT" else None,
              emails={subject} if "@" in str(subject) else None,
              user_ids={subject} if str(subject).startswith("user_") else None,
              enabled=enabled, restore_allowed=restore,
              exposed=(result == "IDENTIFIABLE"),
              attributable=(result == "IDENTIFIABLE"))


def _parse_service_export(store, source_id, system, rec, section=""):
    resource_id = rec.get("resource_id")
    if not resource_id:
        return
    observed = parse_ts(rec.get("observed_at"))
    # account profile lookups: 404 / null profile => ABSENT
    if section == "profile_lookups" or "status_code" in rec:
        if rec.get("status_code") == 404 or rec.get("profile") is None:
            store.add(source_id, "evidence", observed, system, resource_id,
                      "USER_PROFILE", "ABSENT")
        else:
            store.add(source_id, "evidence", observed, system, resource_id,
                      "USER_PROFILE", "PRESENT", record=rec.get("profile") or rec)
        return
    # search index queries: documents live under hits
    if "hits" in rec:
        hits = rec.get("hits") or {}
        docs = hits.get("documents") or []
        total = hits.get("total", len(docs))
        query = rec.get("query")
        if not docs or total == 0:
            store.add(source_id, "evidence", observed, system, resource_id,
                      "SEARCH_INDEX_ENTRY", "ABSENT",
                      emails={query} if query and "@" in str(query) else None)
        for doc in docs:
            store.add(source_id, "evidence", observed, system,
                      doc.get("resource_id", resource_id),
                      "SEARCH_INDEX_ENTRY", "PRESENT", record=doc,
                      emails={query} if query and "@" in str(query) else None)
        return
    category = _category(system, None, None, resource_id)
    store.add(source_id, "evidence", observed, system, resource_id, category,
              "PRESENT", record=rec, enabled=rec.get("enabled"),
              restore_allowed=rec.get("restore_allowed"),
              retention_until=parse_ts(rec.get("retention_until")))
