"""
export_web_data.py — turn audit.db into static JSON for the website.

Run after main.py:
    python3 code/main.py
    python3 code/export_web_data.py            # writes web/data/

Writes:
    web/data/summary.json          status counts, reported vs ours
    web/data/cases.json            short list of every case
    web/data/cases/<case_id>.json  everything about one case
    web/data/lie_detector.json     per system: cases the shop reported COMPLETE
                                   that still had evidence of the person's data

web/data/ is outside web/public/, so the files are not served directly:
the website reads them only through its API routes (web/app/api/).

The site is public, so personal identifiers are masked:
    email       javier.r940897@outlook.com -> ja****@outlook.com
    phone       +33 6 24 34 80 16          -> +** * ** ** ** 16  (last 2 digits kept)
    name        Javier Ruiz                -> J. R.
    email_hash  9f86d081884c7d65...        -> 9f86d081…           (first 8 hex kept)
Emails, and the subject's known names and phones, are also masked inside
request_text, reason and matched_signals. user_id, file ids, system ids and resource ids are not
personal data and are kept.

Output is deterministic (sorted, no timestamps), so re-running gives
identical files. Old cases/*.json files are removed first.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import audit_db  # noqa: E402
import lineage  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "web" / "data"

STATUSES = ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE")
LANGUAGES = ("en", "es", "pt", "fr", "ja", "ko")
REPORTED_STATUSES = ("COMPLETE", "PARTIALLY_COMPLETE", "NOT_STARTED")

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# ---------------------------------------------------------------------------
# Masking
# ---------------------------------------------------------------------------

def mask_email(email: str) -> str:
    """ja****@outlook.com — first 2 characters of the local part (1 if it is short)."""
    email = (email or "").strip()
    if "@" not in email:
        return "****" if email else ""
    local, _, domain = email.rpartition("@")
    keep = 2 if len(local) > 2 else 1
    return f"{local[:keep]}****@{domain}"


def mask_phone(phone: str) -> str:
    """Every digit except the last 2 becomes '*'; spaces and '+' are kept."""
    phone = phone or ""
    total = sum(c.isdigit() for c in phone)
    out, seen = [], 0
    for c in phone:
        if c.isdigit():
            seen += 1
            out.append(c if seen > total - 2 else "*")
        else:
            out.append(c)
    return "".join(out)


def mask_name(name: str) -> str:
    """Javier Ruiz -> J. R."""
    return " ".join(f"{w[0]}." for w in (name or "").split())


def mask_hash(value: str) -> str:
    """First 8 characters of a real (64-hex) hash; short values are fully hidden."""
    value = value or ""
    if not value:
        return ""
    return f"{value[:8]}…" if len(value) > 16 else "****"


_MASKERS = {"email": mask_email, "phone": mask_phone, "name": mask_name,
            "email_hash": mask_hash}


def mask_value(kind: str, value: str) -> str:
    """Mask *value* by its identifier kind; unknown kinds are fully hidden."""
    if kind in ("user_id", "resource_id"):
        return value
    return _MASKERS.get(kind, lambda v: "****" if v else "")(value)


def mask_identifier(term: str) -> str:
    """P2's 'kind:value' (e.g. 'email:x@y.com') -> 'email:x****@y.com'."""
    kind, sep, value = (term or "").partition(":")
    if not sep:
        return mask_value("", term)
    return f"{kind}:{mask_value(kind, value)}"


def mask_text(text: str, names: list[str] = (), phones: list[str] = ()) -> str:
    """Mask every email in free text, plus the subject's known names and phones."""
    text = _EMAIL_RE.sub(lambda m: mask_email(m.group(0)), text or "")
    for value, fn in [(p, mask_phone) for p in phones] + [(n, mask_name) for n in names]:
        if value and value.strip():
            text = re.sub(re.escape(value), fn(value), text, flags=re.IGNORECASE)
    return text


# ---------------------------------------------------------------------------
# Build the JSON documents
# ---------------------------------------------------------------------------

def _rows(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _case_sort_key(case_id: str) -> tuple:
    m = re.fullmatch(r"(.*?)(\d+)", case_id)
    return (m.group(1), int(m.group(2))) if m else (case_id, -1)


def build_summary(conn: sqlite3.Connection) -> dict:
    cases = _rows(conn, "SELECT reported_status, our_status, classification, language "
                        "FROM cases")
    ours = Counter(c["our_status"] for c in cases)
    reported = Counter(c["reported_status"] for c in cases)
    pairs = Counter((c["reported_status"], c["our_status"]) for c in cases)
    rep_keys = list(REPORTED_STATUSES) + sorted(set(reported) - set(REPORTED_STATUSES))
    our_keys = list(STATUSES) + sorted(set(ours) - set(STATUSES))
    return {
        "total_cases": len(cases),
        "status_counts": {s: ours.get(s, 0) for s in our_keys},
        "reported_status_counts": {s: reported.get(s, 0) for s in rep_keys},
        # rows = what the workflow claimed, columns = what our audit found
        "reported_vs_ours": {r: {s: pairs.get((r, s), 0) for s in our_keys}
                             for r in rep_keys},
        "reported_complete_but_not_complete": sum(
            n for (r, s), n in pairs.items() if r == "COMPLETE" and s == "INCOMPLETE"),
        "classification_counts": dict(sorted(
            Counter(c["classification"] for c in cases).items())),
        "language_counts": _language_counts(Counter(c["language"] or "unknown"
                                                    for c in cases)),
        # False while P3's decide() / P4's build_steps() are placeholders: then
        # every deletion case is INCOMPLETE by default, not by evidence, and the
        # website labels the numbers as preliminary.
        "policy_engine_connected": _policy_engine_connected(conn),
    }


def _policy_engine_connected(conn: sqlite3.Connection) -> bool:
    return any(conn.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
               for t in ("resources", "flows", "restore_risks", "steps"))


def _language_counts(counts: Counter) -> dict[str, int]:
    """All 6 languages in a fixed order (0 if absent), then anything else."""
    out = {lang: counts.get(lang, 0) for lang in LANGUAGES}
    out.update({k: v for k, v in sorted(counts.items()) if k not in LANGUAGES})
    return out


def build_lie_detector(conn: sqlite3.Connection) -> dict:
    """
    For deletion requests the shop reported COMPLETE: per system, how many
    cases still had evidence of the person's data (presence PRESENT) in a
    file captured after requested_at.

      proof_cases       at least one direct observation (snapshot, SQL row,
                        read-back, document, screenshot)
      claim_only_cases  only second-hand lookup ledgers (P2 claim_only)

    This is not a verdict: some systems must keep data by policy (e.g. audit
    logs, legal holds). The final verdict comes from the policy engine.
    """
    from utils import parse_ts

    cases = {r["case_id"]: r for r in _rows(
        conn, "SELECT case_id, requested_at FROM cases "
              "WHERE reported_status = 'COMPLETE' AND classification = 'IS_DELETION'")}
    proof: dict[str, set] = {}
    claim: dict[str, set] = {}
    for h in _rows(conn, "SELECT case_id, system_id, captured_at, presence, claim_only "
                         "FROM evidence_hits WHERE presence = 'PRESENT'"):
        c = cases.get(h["case_id"])
        if not c:
            continue
        requested, captured = parse_ts(c["requested_at"]), parse_ts(h["captured_at"])
        if requested is None or captured is None or captured <= requested:
            continue
        (claim if h["claim_only"] else proof).setdefault(h["system_id"], set()).add(h["case_id"])
    systems = sorted(set(proof) | set(claim))
    total = len(cases)
    rows = [{"system_id": sid,
             "proof_cases": len(proof.get(sid, ())),
             "claim_only_cases": len(claim.get(sid, set()) - proof.get(sid, set())),
             "share_with_proof": round(len(proof.get(sid, ())) / total, 4) if total else 0.0}
            for sid in systems]
    rows.sort(key=lambda r: (-r["proof_cases"], -r["claim_only_cases"], r["system_id"]))
    return {
        "reported_complete_cases": total,
        "systems": rows,
        "basis": "evidence captured after the request, showing the person's data as present",
        "note": "Some of this data may be kept on purpose (for example audit logs or legal "
                "holds). The final verdict for each case comes from the policy engine.",
        "policy_engine_connected": _policy_engine_connected(conn),
    }


def build_case_list(conn: sqlite3.Connection) -> list[dict]:
    rows = _rows(conn, "SELECT case_id, email, reported_status, our_status, "
                       "classification, language FROM cases")
    out = [dict(r, email=mask_email(r["email"])) for r in rows]
    return sorted(out, key=lambda r: _case_sort_key(r["case_id"]))


def build_case(conn: sqlite3.Connection, case_id: str) -> dict:
    case = _rows(conn, "SELECT * FROM cases WHERE case_id = ?", (case_id,))[0]
    ids = _rows(conn, "SELECT user_id, kind, value, is_historical, audit_id, changed_at, "
                      "matches_request FROM identities WHERE case_id = ? ORDER BY rowid",
                (case_id,))
    names = [i["value"] for i in ids if i["kind"] == "name"]
    phones = [i["value"] for i in ids if i["kind"] == "phone"]

    hits = _rows(conn, "SELECT file_id, system_id, resource_id, matched_identifier, "
                       "captured_at, replica_or_table, origin FROM evidence_hits "
                       "WHERE case_id = ? ORDER BY captured_at, file_id, matched_identifier",
                 (case_id,))
    edges = _rows(conn, "SELECT activity_id, event_time, event_type, kind, label, "
                        "source_system, source_resource_id, target_system, "
                        "target_resource_id, reported_result, details FROM lineage_edges "
                        "WHERE case_id = ? ORDER BY event_time, activity_id", (case_id,))
    for e in edges:
        e["details"] = mask_text(e["details"], names, phones)
    resources = _rows(conn, "SELECT system_id, resource_id, category, required_treatment, "
                            "state_at_audit, satisfied, evidence_ids FROM resources "
                            "WHERE case_id = ? ORDER BY rowid", (case_id,))
    flows = _rows(conn, "SELECT system_id, resource_id, kind, active_at_audit, evidence_id "
                        "FROM flows WHERE case_id = ? ORDER BY rowid", (case_id,))
    restore_risks = _rows(conn, "SELECT system_id, resource_id, active_at_audit, evidence_id "
                                "FROM restore_risks WHERE case_id = ? ORDER BY rowid",
                          (case_id,))
    timeline = _rows(conn, "SELECT time, system_id, resource_id, event, state_after, "
                           "evidence_id FROM timeline WHERE case_id = ? ORDER BY seq",
                     (case_id,))
    steps = _rows(conn, "SELECT step_no, phase, system_id, resource_id, operation, state, "
                        "evidence_id FROM steps WHERE case_id = ? ORDER BY step_no",
                  (case_id,))
    for r in resources:
        r["satisfied"] = bool(r["satisfied"])
        r["evidence_ids"] = json.loads(r["evidence_ids"] or "[]")
    for f in flows + restore_risks:
        f["active_at_audit"] = bool(f["active_at_audit"])

    return {
        "case_id": case["case_id"],
        "email": mask_email(case["email"]),
        "request_text": mask_text(case["request_text"], names, phones),
        "reported_status": case["reported_status"],
        "our_status": case["our_status"],
        "classification": case["classification"],
        "language": case["language"],
        "confidence": case["confidence"],
        "matched_signals": [mask_text(x, names, phones)
                            for x in json.loads(case["matched_signals"] or "[]")],
        "reason": mask_text(case["reason"], names, phones),
        "requested_at": case["requested_at"],
        "audit_at": case["audit_at"],
        "user_id": ids[0]["user_id"] if ids else None,
        "identities": [
            {"kind": i["kind"], "value": mask_value(i["kind"], i["value"]),
             "is_historical": bool(i["is_historical"]), "audit_id": i["audit_id"],
             "changed_at": i["changed_at"], "matches_request": bool(i["matches_request"])}
            for i in ids],
        "identity_trail": build_identity_trail(ids),
        "evidence_hits": [dict(h, matched_identifier=mask_identifier(h["matched_identifier"]))
                          for h in hits],
        # Reported activity = claims (system_activity.csv); display only
        "lineage_edges": edges,
        "lineage": build_lineage(hits, edges, flows, restore_risks),
        "resources": resources,
        "flows": flows,
        "restore_risks": restore_risks,
        "timeline": timeline,
        "steps": steps,
    }


def build_identity_trail(ids: list[dict]) -> list[dict]:
    """
    The subject's emails, oldest first, each with the audit-log change that
    replaced it: old email -> (audit_293, 2026-05-28) -> current email.
    Values are masked.
    """
    emails = [i for i in ids if i["kind"] == "email"]
    older = sorted((i for i in emails if i["is_historical"]),
                   key=lambda i: (i["changed_at"] or "", i["audit_id"]))
    current = [i for i in emails if not i["is_historical"]]
    trail = []
    for i in older + current:
        trail.append({
            "value": mask_email(i["value"]),
            "is_current": not i["is_historical"],
            "is_request": bool(i["matches_request"]),
            # the change that moved this email to the next one (None for current)
            "replaced_by": ({"audit_id": i["audit_id"], "changed_at": i["changed_at"]}
                            if i["is_historical"] else None),
        })
    return trail


def _node_id(system_id: str, resource_id: str, replica: str = "") -> str:
    return f"{system_id}|{resource_id}|{replica or ''}"


def build_lineage(hits: list[dict], edges: list[dict], flows: list[dict],
                  restore_risks: list[dict]) -> dict:
    """
    Nodes (one per system / resource / replica copy, grouped into columns)
    and edges for the case page's lineage map.

      nodes from evidence hits          source = "evidence"
      nodes only named in activity rows source = "activity"
      movement edges                    reported activity (claims)
      control rows (flow / restore)     attached to their node as claims
      P3 flows / restore_risks          flags on their node (active_flow,
                                        restore_risk), drawn on top
    """
    nodes: dict[str, dict] = {}

    def node(system_id: str, resource_id: str, replica: str = "", source: str = "activity",
             origins: tuple = ()) -> dict:
        nid = _node_id(system_id, resource_id, replica)
        if nid not in nodes:
            nodes[nid] = {"id": nid, "system_id": system_id, "resource_id": resource_id,
                          "replica_or_table": replica, "source": source,
                          "group": lineage.node_group(system_id, origins, replica),
                          "file_ids": [], "origins": [], "matched_identifiers": [],
                          "first_captured_at": "", "last_captured_at": "",
                          "claims": [], "active_flow": None, "restore_risk": None}
        return nodes[nid]

    for h in hits:
        n = node(h["system_id"], h["resource_id"], h["replica_or_table"], "evidence",
                 (h["origin"],))
        for key, value in (("file_ids", h["file_id"]), ("origins", h["origin"]),
                           ("matched_identifiers", mask_identifier(h["matched_identifier"]))):
            if value and value not in n[key]:
                n[key].append(value)
        captured = h["captured_at"]
        if captured and (not n["first_captured_at"] or captured < n["first_captured_at"]):
            n["first_captured_at"] = captured
        if captured > n["last_captured_at"]:
            n["last_captured_at"] = captured
    # the group may depend on all origins seen for a node
    for n in nodes.values():
        n["group"] = lineage.node_group(n["system_id"], n["origins"], n["replica_or_table"])

    def find(system_id: str, resource_id: str) -> dict:
        """The primary copy of (system, resource) if seen in evidence, else a new node."""
        same = [n for n in nodes.values()
                if n["system_id"] == system_id and n["resource_id"].lower() == resource_id.lower()]
        same.sort(key=lambda n: (n["replica_or_table"] != "", n["replica_or_table"]))
        return same[0] if same else node(system_id, resource_id)

    out_edges = []
    for e in edges:
        claim = {k: e[k] for k in ("activity_id", "event_time", "label", "reported_result",
                                   "details")}
        if e["kind"] == "control":
            find(e["target_system"], e["target_resource_id"])["claims"].append(claim)
            continue
        if e["kind"] != "movement":
            continue   # delete / redact / ... claims: timeline only, not the map
        src = find(e["source_system"], e["source_resource_id"])
        dst = find(e["target_system"], e["target_resource_id"])
        out_edges.append(dict(claim, **{"from": src["id"], "to": dst["id"], "kind": "claim"}))

    for f in flows:
        find(f["system_id"], f["resource_id"])["active_flow"] = {
            "kind": f["kind"], "active_at_audit": f["active_at_audit"],
            "evidence_id": f["evidence_id"]}
    for r in restore_risks:
        find(r["system_id"], r["resource_id"])["restore_risk"] = {
            "active_at_audit": r["active_at_audit"], "evidence_id": r["evidence_id"]}

    ordered = sorted(nodes.values(), key=lambda n: (
        lineage.GROUP_ORDER.index(n["group"]), n["system_id"], n["resource_id"],
        n["replica_or_table"]))
    return {
        "groups": [{"id": g, "label": label} for g, label in (
            (lineage.PRIMARY, "Primary systems"), (lineage.COPY, "Copies"),
            (lineage.BACKUP, "Backups & archives"))],
        "nodes": ordered,
        "edges": out_edges,
        "edge_note": "reported activity (claims)",
    }


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_filename(case_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", case_id):
        raise ValueError(f"unsafe case_id for a file name: {case_id!r}")
    return f"{case_id}.json"


def export(db_path: Path | str = audit_db.DEFAULT_DB_PATH,
           out_dir: Path | str = DEFAULT_OUT_DIR) -> dict:
    """Write every JSON file. Returns the summary dict."""
    db_path, out_dir = Path(db_path), Path(out_dir)
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found; run python3 code/main.py first")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cases_dir = out_dir / "cases"
        cases_dir.mkdir(parents=True, exist_ok=True)
        for old in cases_dir.glob("*.json"):
            old.unlink()

        summary = build_summary(conn)
        case_list = build_case_list(conn)
        _write_json(out_dir / "summary.json", summary)
        _write_json(out_dir / "cases.json", case_list)
        _write_json(out_dir / "lie_detector.json", build_lie_detector(conn))
        for c in case_list:
            _write_json(cases_dir / _safe_filename(c["case_id"]),
                        build_case(conn, c["case_id"]))
    finally:
        conn.close()
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=str(audit_db.DEFAULT_DB_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args(argv)
    summary = export(args.db, args.out)
    print(f"Exported {summary['total_cases']} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
