"""JSON evidence: snapshot bundles, result ledgers/manifests, analytics/export reports, service resource exports."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from ..contracts import Coverage, Observation
from ..util import category_for_resource
from .common import COLLECTION_CATEGORY, RESULT_TO_STATE, make_obs

# service_resource_export: service -> list key -> (category)
EXPORT_LISTS = {
    "profile_lookups": "USER_PROFILE", "profiles": "ANALYTICS_PROFILE", "restore_entries": "BACKUP_ARCHIVE",
}


def _result_record(evidence_id, captured_at, rec, fmt="json", locator="") -> Observation | None:
    """Records shaped {recorded_at, system, resource_id, record_type, result, subject_reference|lookup_value}."""
    result = str(rec.get("result") or "").upper()
    state = RESULT_TO_STATE.get(result)
    if not state:
        return None
    r2 = {k: v for k, v in rec.items() if k not in ("result", "record_type", "system", "recorded_at")}
    system = rec.get("system") or ""
    return make_obs(evidence_id, captured_at, r2, system_id=system, category=rec.get("record_type") or "", state=state,
                    observed_at=rec.get("recorded_at") or captured_at, source_format=fmt, locator=locator,
                    extra_attrs={"result": result, "identifiable": result == "IDENTIFIABLE"})


def parse_json(evidence_id: str, captured_at: str, path: str) -> Tuple[List[Observation], List[Coverage]]:
    data = json.load(open(path, encoding="utf-8"))
    obs: List[Observation] = []
    cov: List[Coverage] = []

    if "snapshots" in data:                                   # snapshot bundle
        for i, snap in enumerate(data["snapshots"]):
            store, coll = snap["data_store"], snap["collection"]
            ts = snap.get("captured_at") or captured_at
            if coll == "operational_record_history":          # explicit per-resource lookup results
                for j, rec in enumerate(snap["records"]):
                    o = _result_record(evidence_id, captured_at, rec, "json", f"snapshots[{i}].records[{j}]")
                    if o:
                        obs.append(o)
                continue
            system, cat = COLLECTION_CATEGORY.get(coll, (store, ""))
            cov.append(Coverage(evidence_id, ts, store or system, coll, "json", f"snapshots[{i}]"))
            for j, rec in enumerate(snap["records"]):
                o = make_obs(evidence_id, ts, rec, system_id=store or system, category=cat, source_format="json",
                             locator=f"snapshots[{i}].records[{j}]", extra_attrs={"collection": coll})
                if o:
                    obs.append(o)
        return obs, cov

    if "service_exports" in data:                              # service_resource_export
        ts = data.get("exported_at") or captured_at
        for service, body in data["service_exports"].items():
            cov.append(Coverage(evidence_id, ts, service, "", "json_lookup", service))
            for list_key, items in body.items():
                if not isinstance(items, list):
                    continue
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue
                    rec = dict(item)
                    state = None
                    if "status_code" in rec:                   # 404 -> absent, 200 -> present
                        state = "ABSENT" if int(rec["status_code"]) == 404 else "PRESENT"
                    prof = rec.get("profile")
                    if isinstance(prof, dict):
                        rec.update({f"profile_{k}": v for k, v in prof.items()})
                        rec.pop("profile")
                    o = make_obs(evidence_id, ts, rec, system_id=service, source_format="json",
                                 observed_at=rec.get("observed_at") or ts, state=state or "",
                                 locator=f"service_exports.{service}.{list_key}[{j}]",
                                 extra_attrs={"list": list_key})
                    if o:
                        obs.append(o)
        return obs, cov

    records = data.get("records") or []
    if records and "result" in records[0]:                    # ledger / manifest / config-state exports
        ts = data.get("exported_at") or captured_at
        for j, rec in enumerate(records):
            o = _result_record(evidence_id, ts, rec, "json", f"records[{j}]")
            if o:
                obs.append(o)
        return obs, cov

    coll = data.get("collection", "")                          # analytics report / export jobs
    system, cat = COLLECTION_CATEGORY.get(coll, ("", ""))
    ts = data.get("captured_at") or captured_at
    if system:
        cov.append(Coverage(evidence_id, ts, system, coll, "json", coll))
    for j, rec in enumerate(records):
        o = make_obs(evidence_id, ts, rec, system_id=system, category=cat, source_format="json",
                     locator=f"records[{j}]", extra_attrs={"collection": coll})
        if o:
            obs.append(o)
    return obs, cov
