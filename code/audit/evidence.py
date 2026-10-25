"""Parse every evidence file into a flat list of observations.

An observation says: at time `observed_at`, file `file_id` saw resource
`resource_id` in system `system_id`, in state `state`, carrying the
identifiers in `idents`. All later reasoning (identity linking, state at
audit time, policy) works on these observations only, so each evidence
format needs exactly one parser here.

States:
    PRESENT     record exists and still carries direct identifiers
    ABSENT      record lookup returned nothing
    RETAINED    record exists and is a retained record (audit log, legal hold)
    REDACTED    record exists, direct identifiers removed
    ANONYMIZED  record exists, unlinked from the subject
    ACTIVE      data flow enabled
    DISABLED    data flow disabled
    RESTORABLE  backup can still restore the subject's data
    BLOCKED     backup restore blocked for the subject
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
USER_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"\b[0-9a-f]{64}\b")
RESOURCE_RE = re.compile(
    r"\b(account|search|support|analytics|export|data_flow|backup|audit_record|"
    r"tombstone|legal_hold|cache|marketing|email_delivery|object|telemetry)_\d+\b"
)

PREFIX_SYSTEM = {
    "account": "account_service",
    "search": "search_service",
    "support": "support_platform",
    "analytics": "analytics_platform",
    "export": "export_service",
    "data_flow": "integration_service",
    "backup": "backup_service",
    "audit_record": "security_service",
    "tombstone": "identity_service",
    "legal_hold": "legal_service",
    "cache": "cache_service",
    "marketing": "marketing_platform",
    "email_delivery": "email_delivery_service",
    "object": "object_storage",
    "telemetry": "telemetry_service",
}

PREFIX_CATEGORY = {
    "account": "USER_PROFILE",
    "search": "SEARCH_INDEX_ENTRY",
    "support": "SUPPORT_MESSAGE",
    "analytics": "ANALYTICS_PROFILE",
    "export": "USER_EXPORT",
    "data_flow": "DATA_FLOW",
    "backup": "BACKUP_ARCHIVE",
    "audit_record": "SECURITY_AUDIT_LOG",
    "tombstone": "ACCOUNT_TOMBSTONE",
    "legal_hold": "LEGAL_HOLD_RECORD",
    "cache": "CACHE_ENTRY",
    "marketing": "MARKETING_PROFILE",
    "email_delivery": "EMAIL_DELIVERY_LOG",
    "object": "SUPPORT_ATTACHMENT",
    "telemetry": "PRODUCT_TELEMETRY",
}

RETAINED_CATEGORIES = {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"}

# result values of the flat "record_type / result" evidence formats
FLAT_RESULT_STATE = {
    "FOUND": "PRESENT",
    "NOT_FOUND": "ABSENT",
    "IDENTIFIABLE": "PRESENT",
    "ANONYMIZED": "ANONYMIZED",
    "REDACTED": "REDACTED",
    "ACTIVE": "ACTIVE",
    "DISABLED": "DISABLED",
    "BLOCKED": "BLOCKED",
}


@dataclass
class Observation:
    file_id: str
    available_at: str  # manifest capture time: the file cannot be used before it
    observed_at: str  # when the record itself was observed
    system_id: str
    resource_id: str
    category: str
    state: str
    idents: set = field(default_factory=set)
    note: str = ""

    def key(self):
        return (self.system_id, self.resource_id)


def prefix_of(resource_id: str) -> str:
    m = RESOURCE_RE.match(resource_id)
    return m.group(1) if m else resource_id.rsplit("_", 1)[0]


def system_of(resource_id: str) -> str:
    return PREFIX_SYSTEM.get(prefix_of(resource_id), "unknown_service")


def category_of(resource_id: str) -> str:
    return PREFIX_CATEGORY.get(prefix_of(resource_id), "UNKNOWN")


def norm_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return "tel:" + digits if len(digits) >= 7 else ""


def extract_idents(*values) -> set:
    """Pull every identifier-like token (email, user id, hash, phone) out of values."""
    out = set()
    stack = list(values)
    while stack:
        v = stack.pop()
        if v is None:
            continue
        if isinstance(v, dict):
            stack.extend(v.values())
            continue
        if isinstance(v, (list, tuple, set)):
            stack.extend(v)
            continue
        s = str(v)
        for e in EMAIL_RE.findall(s):
            out.add(e.lower())
        for u in USER_RE.findall(s):
            out.add(u)
        for h in HASH_RE.findall(s.lower()):
            out.add(h)
        if re.fullmatch(r"\+?[\d\s()./-]{7,}", s.strip()):
            p = norm_phone(s)
            if p:
                out.add(p)
    return out


def _has_direct(*values) -> bool:
    return any(v not in (None, "", "null", "[REDACTED]") for v in values)


def _bool(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "allow")


# ---------------------------------------------------------------- generic records


def record_state(resource_id: str, rec: dict, collection: str = "") -> tuple[str, str]:
    """Infer (category, state) for a full record dict found in a snapshot or table."""
    cat = category_of(resource_id)
    p = prefix_of(resource_id)
    if p == "account":
        status = str(rec.get("account_status") or "").upper()
        if status == "DELETED" and not _has_direct(rec.get("email"), rec.get("full_name"), rec.get("phone")):
            return cat, "ABSENT"
        return cat, "PRESENT"
    if p == "analytics":
        direct = _has_direct(rec.get("user_id"), rec.get("customer_reference"), rec.get("email"),
                             rec.get("phone"), rec.get("email_hash"))
        return cat, "PRESENT" if direct else "ANONYMIZED"
    if p == "support":
        if collection == "ticket_attachments" or rec.get("file_name") or rec.get("storage_class") == "ticket_attachment":
            return "SUPPORT_ATTACHMENT", "PRESENT"
        text = rec.get("message_text") if "message_text" in rec else None
        direct = _has_direct(rec.get("requester_name"), rec.get("requester_email"), rec.get("requester_phone"))
        if text is not None:
            direct = direct or bool(EMAIL_RE.search(text or "")) or (text not in ("[REDACTED]", "", None) and "[REDACTED]" not in text)
        return cat, "PRESENT" if direct else "REDACTED"
    if p == "tombstone":
        direct = _has_direct(rec.get("name"), rec.get("email"), rec.get("phone"), rec.get("email_hash"))
        return cat, "PRESENT" if direct else "REDACTED"
    if p == "data_flow":
        return cat, "ACTIVE" if _bool(rec.get("enabled")) else "DISABLED"
    if p == "backup":
        return cat, "RESTORABLE" if _bool(rec.get("restore_allowed")) else "BLOCKED"
    if p == "export":
        if "download_available" in rec and not _bool(rec.get("download_available")):
            return cat, "ABSENT"
        return cat, "PRESENT"
    if cat in RETAINED_CATEGORIES:
        return cat, "RETAINED"
    return cat, "PRESENT"


def _flat_obs(file_id, avail, rec, observed_at=None):
    """Records of the shape {system, resource_id, record_type, result, subject_reference|lookup_value}."""
    rid = rec["resource_id"]
    cat = rec.get("record_type") or category_of(rid)
    result = str(rec.get("result", "")).upper()
    state = FLAT_RESULT_STATE.get(result, "PRESENT")
    if cat == "BACKUP_ARCHIVE" and state == "ACTIVE":
        state = "RESTORABLE"
    if cat in RETAINED_CATEGORIES and state == "PRESENT":
        state = "RETAINED"
    if cat == "ACCOUNT_TOMBSTONE" and result == "FOUND":
        state = "PRESENT"
    ident_src = rec.get("subject_reference", rec.get("lookup_value"))
    return Observation(file_id, avail, observed_at or rec.get("recorded_at") or avail,
                       rec.get("system") or system_of(rid), rid, cat, state,
                       extract_idents(ident_src), note="flat")


# ---------------------------------------------------------------- JSON records


def parse_json(file_id, avail, path: Path):
    d = json.loads(path.read_text())
    obs = []
    if "snapshots" in d:  # records_assurance snapshot bundle
        for snap in d["snapshots"]:
            t = snap.get("captured_at") or avail
            if snap.get("data_store") in PREFIX_SYSTEM.values():
                # a full collection snapshot: records missing from it are absent at time t
                obs.append(Observation(file_id, avail, t, snap["data_store"], "*", "COVERAGE", "COVERAGE",
                                       note=snap.get("collection", "")))
            for rec in snap.get("records", []):
                if "record_type" in rec:
                    obs.append(_flat_obs(file_id, avail, rec))
                    continue
                rid = rec["resource_id"]
                cat, state = record_state(rid, rec, snap.get("collection", ""))
                obs.append(Observation(file_id, avail, t, system_of(rid), rid, cat, state,
                                       extract_idents(rec), note=snap.get("collection", "")))
        return obs
    if "service_exports" in d:  # records_assurance_gateway export
        for system, tables in d["service_exports"].items():
            for table, rows in tables.items():
                for rec in rows:
                    obs.extend(_service_export_obs(file_id, avail, system, table, rec))
        return obs
    records = d.get("records", [])
    t_file = d.get("captured_at") or d.get("exported_at") or avail
    for rec in records:
        if "record_type" in rec:
            obs.append(_flat_obs(file_id, avail, rec))
            continue
        rid = rec["resource_id"]
        cat, state = record_state(rid, rec, d.get("collection", ""))
        obs.append(Observation(file_id, avail, t_file, system_of(rid), rid, cat, state,
                               extract_idents(rec), note=d.get("collection", "")))
    return obs


def _service_export_obs(file_id, avail, system, table, rec):
    rid = rec["resource_id"]
    t = rec.get("observed_at") or avail
    cat = category_of(rid)
    if table == "profile_lookups":
        prof = rec.get("profile")
        if rec.get("status_code") == 404 or not prof:
            return [Observation(file_id, avail, t, system, rid, cat, "ABSENT", set(), note=table)]
        return [Observation(file_id, avail, t, system, rid, cat, "PRESENT", extract_idents(prof), note=table)]
    if table == "index_queries":
        hits = (rec.get("hits") or {}).get("documents") or []
        found = [h for h in hits if h.get("resource_id") == rid]
        idents = extract_idents(rec.get("query")) if not found else extract_idents(found)
        state = "PRESENT" if found else "ABSENT"
        return [Observation(file_id, avail, t, system, rid, cat, state, idents, note=table)]
    if table == "tickets":
        direct = _has_direct(rec.get("requester_name"), rec.get("requester_email"), rec.get("requester_phone"))
        return [Observation(file_id, avail, t, system, rid, cat, "PRESENT" if direct else "REDACTED",
                            extract_idents(rec), note=table)]
    if table == "restore_entries":
        return [Observation(file_id, avail, t, system, rid, cat,
                            "RESTORABLE" if _bool(rec.get("restore_allowed")) else "BLOCKED",
                            extract_idents(rec), note=table)]
    if table == "connectors":
        return [Observation(file_id, avail, t, system, rid, cat,
                            "ACTIVE" if _bool(rec.get("enabled")) else "DISABLED",
                            extract_idents(rec), note=table)]
    cat2, state = record_state(rid, rec, table)
    return [Observation(file_id, avail, t, system, rid, cat2, state, extract_idents(rec), note=table)]


# ---------------------------------------------------------------- text handover


def parse_handover(file_id, avail, path: Path):
    obs = []
    for line in path.read_text().splitlines():
        parts = [p.strip() for p in line.lstrip("- ").split("|")]
        if len(parts) == 6 and RESOURCE_RE.match(parts[2]):
            t, system, rid, rtype, result, subject = parts
            obs.append(_flat_obs(file_id, avail, {
                "recorded_at": t, "system": system, "resource_id": rid,
                "record_type": rtype, "result": result, "subject_reference": subject,
            }))
    return obs


# ---------------------------------------------------------------- SQL snapshots


def parse_sql(file_id, avail, path: Path):
    con = sqlite3.connect(":memory:")
    con.executescript(path.read_text())
    tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    obs = []
    scope = {}
    if "snapshot_scope" in tables:
        scope = dict(con.execute("select origin_system, captured_at from snapshot_scope").fetchall())
    for system, t in scope.items():
        obs.append(Observation(file_id, avail, t, system, "*", "COVERAGE", "COVERAGE", note="snapshot_scope"))
    for table in tables:
        if table == "snapshot_scope":
            continue
        cur = con.execute(f'select * from "{table}"')
        cols = [c[0] for c in cur.description]
        for row in cur.fetchall():
            rec = dict(zip(cols, row))
            if "record_json" in rec:
                inner = json.loads(rec["record_json"])
                rid = rec["resource_id"]
                collection = rec.get("collection_name", "")
                if "document" in inner:  # search document nests its fields
                    inner = {**inner, **(inner.get("document") or {})}
                cat, state = record_state(rid, inner, collection)
                obs.append(Observation(file_id, avail, rec.get("updated_at") or avail, system_of(rid), rid,
                                       cat, state, extract_idents(inner), note=f"{table}:{collection}"))
                continue
            rid = rec["resource_id"]
            norm = dict(rec)
            if table == "support_records":
                norm["message_text"] = None
            if table == "customer_exports":
                norm.pop("object_key", None)
            cat, state = record_state(rid, norm, table)
            t = rec.get("updated_at") or rec.get("indexed_at") or avail
            obs.append(Observation(file_id, avail, t, system_of(rid), rid, cat, state,
                                   extract_idents({k: v for k, v in rec.items() if k != "resource_id"}),
                                   note=table))
    return obs


# ---------------------------------------------------------------- logs

KV_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("([^"]*)"|[^\s"|]+)')
TRACE_RE = re.compile(r"\b((?:tr|rb)-[A-Za-z0-9-]+)\b")
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
EVENT_NAME_RES = [
    re.compile(r"\]\s+([a-z_]+):"),  # [svc] [trace] event_name:
    re.compile(r"\|\s*([a-z_]+)\s*\|\s*instance"),  # | event | instance=
]
IDENT_KEYS = {
    "lookup_key", "match_key", "subject_key", "scan_key", "owner_key", "correlation_key",
    "matched_value", "subject_ref", "subject_reference", "customer_email", "customer_reference",
    "email", "requester_email", "owner_email", "lookup_value",
}


def parse_log_line(line: str) -> dict:
    line = line.replace('\\"', '"')
    out = {}
    m = TS_RE.match(line)
    out["_ts"] = m.group(1) if m else None
    brace = line.find("{")
    if brace >= 0 and line.rstrip().endswith("}"):
        try:
            out.update({k: str(v) for k, v in json.loads(line[brace:]).items()})
        except json.JSONDecodeError:
            pass
    for m in KV_RE.finditer(line):
        k = m.group(1)
        v = m.group(3) if m.group(3) is not None else m.group(2)
        if k == "message":
            continue
        out.setdefault(k, v)
    tm = TRACE_RE.search(line)
    if tm:
        out.setdefault("_trace", tm.group(1))
    if "trace_id" in out:
        out["_trace"] = out["trace_id"]
    if "event" not in out:
        for rx in EVENT_NAME_RES:
            em = rx.search(line)
            if em:
                out["event"] = em.group(1)
                break
    return out


def _log_state(rid: str, ev: dict) -> tuple[str, str] | None:
    """(category, state) from the merged key/values of one trace about one resource."""
    p = prefix_of(rid)
    cat = category_of(rid)
    event = ev.get("event", "")
    if p == "account":
        if ev.get("http_status") == "404" or ev.get("rows") == "0":
            return cat, "ABSENT"
        if ev.get("rows") or ev.get("http_status"):
            return cat, "PRESENT"
        return None
    if p == "search":
        if ev.get("result") == "hit":
            return cat, "PRESENT"
        if ev.get("result") in ("miss", "none", "no_hit") or ev.get("rows") == "0":
            return cat, "ABSENT"
        return None
    if p == "analytics":
        if event == "contact_lookup_completed":
            return ("SECONDARY_IDENTIFIER", "PRESENT") if ev.get("rows") != "0" else (cat, "ABSENT")
        if ev.get("direct_identifiers") == "1" or ev.get("matched_value"):
            return cat, "PRESENT"
        if ev.get("direct_identifiers") == "0":
            return cat, "ANONYMIZED"
        if event == "analytics_profile_read_completed":
            direct = _has_direct(ev.get("customer_reference"), ev.get("email"), ev.get("phone"), ev.get("email_hash"))
            return cat, "PRESENT" if direct else "ANONYMIZED"
        return None
    if p == "support":
        if event == "attachment_pii_scan":
            return "SUPPORT_ATTACHMENT", "PRESENT"
        if event == "message_pii_scan":
            return cat, "PRESENT"
        if event == "deletion_marker_check" and ev.get("marker_found") == "false":
            return "SECONDARY_IDENTIFIER", "PRESENT"
        if event in ("contact_query_completed",):
            return ("SECONDARY_IDENTIFIER", "PRESENT") if ev.get("rows") != "0" else (cat, "ABSENT")
        if event == "message_read":
            text = ev.get("message_text", "")
            return cat, "REDACTED" if text in ("[REDACTED]", "", "null") else "PRESENT"
        if event == "support_ticket_read_completed":
            direct = _has_direct(ev.get("requester_name"), ev.get("requester_email"), ev.get("requester_phone"))
            return cat, "PRESENT" if direct else "REDACTED"
        return None
    if p == "data_flow":
        if "enabled" in ev:
            return cat, "ACTIVE" if _bool(ev["enabled"]) else "DISABLED"
        if "scheduler_registered" in ev:
            return cat, "ACTIVE" if _bool(ev["scheduler_registered"]) else "DISABLED"
        return None
    if p == "backup":
        if "restore_allowed" in ev:
            return cat, "RESTORABLE" if _bool(ev["restore_allowed"]) else "BLOCKED"
        if "eligible" in ev:
            open_ = _bool(ev["eligible"]) and not _bool(ev.get("deletion_block", "false"))
            return cat, "RESTORABLE" if open_ else "BLOCKED"
        if "decision" in ev:
            return cat, "RESTORABLE" if ev["decision"].lower() == "allow" else "BLOCKED"
        return None
    if p == "export":
        if "available" in ev:
            return cat, "PRESENT" if _bool(ev["available"]) else "ABSENT"
        return None
    if p == "audit_record":
        if ev.get("rows") == "0":
            return cat, "ABSENT"
        return cat, "RETAINED"
    return None


def parse_log(file_id, avail, path: Path):
    lines = [parse_log_line(l) for l in path.read_text().splitlines() if l.strip()]
    obs = []
    # flat record_lookup lines (notification delivery, search diagnostics)
    for ev in lines:
        if ev.get("event") == "record_lookup" and "record_type" in ev:
            obs.append(_flat_obs(file_id, avail, {
                "recorded_at": ev["_ts"], "system": ev.get("system"), "resource_id": ev["resource_id"],
                "record_type": ev["record_type"], "result": ev.get("result"),
                "subject_reference": ev.get("subject_reference"),
            }))
    # traces: merge all lines that share a trace id
    groups: dict[str, list[dict]] = {}
    order = []
    for i, ev in enumerate(lines):
        if ev.get("event") == "record_lookup":
            continue
        key = ev.get("_trace") or f"_line{i}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(ev)
    for key in order:
        evs = groups[key]
        rids = []
        for ev in evs:
            rid = ev.get("resource_id")
            if rid and RESOURCE_RE.fullmatch(rid) and rid not in rids:
                rids.append(rid)
        if not rids:
            continue
        idents = set()
        for ev in evs:
            for k, v in ev.items():
                if k in IDENT_KEYS and v not in (None, "", "null"):
                    idents |= extract_idents(v)
        for rid in rids:
            merged = {}
            st = None
            ts_ = None
            for ev in evs:
                if ev.get("resource_id") not in (None, rid):
                    continue
                merged.update({k: v for k, v in ev.items() if k != "event"})
                if ev.get("resource_id") == rid and ev.get("event"):
                    merged["event"] = ev["event"]
                    got = _log_state(rid, merged)
                    if got is not None:
                        st, ts_ = got, ev.get("_ts")
            if st is None:
                continue
            cat, state = st
            obs.append(Observation(file_id, avail, ts_ or avail, system_of(rid), rid, cat, state,
                                   set(idents), note=f"log:{merged.get('event', '')}"))
    return obs


# ---------------------------------------------------------------- PDFs


def pdf_text(path: Path) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:  # pragma: no cover - fall back to pypdf
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)


# ---------------------------------------------------------------- driver


def load_manifest(dataset: Path):
    with open(dataset / "evidence_files.csv", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_all(dataset: Path, visual_facts: dict | None = None):
    """Parse every manifest file. Images and PDFs are handled by `visual_facts`,
    a {file_id: [observation dicts]} mapping produced by the multimodal extractor."""
    obs: list[Observation] = []
    unparsed = []
    for row in load_manifest(dataset):
        fid, rel, avail = row["file_id"], row["file_path"], row["captured_at"]
        path = dataset / rel
        suffix = path.suffix.lower()
        if suffix == ".json":
            obs.extend(parse_json(fid, avail, path))
        elif suffix == ".sql":
            obs.extend(parse_sql(fid, avail, path))
        elif suffix == ".log":
            obs.extend(parse_log(fid, avail, path))
        elif suffix == ".txt":
            obs.extend(parse_handover(fid, avail, path))
        elif suffix in (".png", ".jpg", ".jpeg", ".pdf"):
            facts = (visual_facts or {}).get(fid)
            if facts is None:
                unparsed.append(fid)
                continue
            for f in facts:
                rid = f["resource_id"]
                obs.append(Observation(fid, avail, f.get("observed_at") or avail,
                                       f.get("system_id") or system_of(rid), rid,
                                       f.get("category") or category_of(rid), f["state"],
                                       extract_idents(f.get("identifiers", [])), note="visual"))
        else:
            unparsed.append(fid)
    return obs, unparsed
