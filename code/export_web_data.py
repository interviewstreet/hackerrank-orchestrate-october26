"""
export_web_data.py — turn audit.db into static JSON for the website.

Run after main.py:
    python3 code/main.py
    python3 code/export_web_data.py            # writes web/data/

Writes:
    web/data/summary.json          status counts, reported vs ours
    web/data/cases.json            short list of every case
    web/data/cases/<case_id>.json  everything about one case

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
    }


def _language_counts(counts: Counter) -> dict[str, int]:
    """All 6 languages in a fixed order (0 if absent), then anything else."""
    out = {lang: counts.get(lang, 0) for lang in LANGUAGES}
    out.update({k: v for k, v in sorted(counts.items()) if k not in LANGUAGES})
    return out


def build_case_list(conn: sqlite3.Connection) -> list[dict]:
    rows = _rows(conn, "SELECT case_id, email, reported_status, our_status, "
                       "classification FROM cases")
    out = [dict(r, email=mask_email(r["email"])) for r in rows]
    return sorted(out, key=lambda r: _case_sort_key(r["case_id"]))


def build_case(conn: sqlite3.Connection, case_id: str) -> dict:
    case = _rows(conn, "SELECT * FROM cases WHERE case_id = ?", (case_id,))[0]
    ids = _rows(conn, "SELECT user_id, kind, value, is_historical, audit_id "
                      "FROM identities WHERE case_id = ? ORDER BY rowid", (case_id,))
    names = [i["value"] for i in ids if i["kind"] == "name"]
    phones = [i["value"] for i in ids if i["kind"] == "phone"]

    hits = _rows(conn, "SELECT file_id, system_id, resource_id, matched_identifier, "
                       "captured_at FROM evidence_hits WHERE case_id = ? "
                       "ORDER BY captured_at, file_id, matched_identifier", (case_id,))
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
             "is_historical": bool(i["is_historical"]), "audit_id": i["audit_id"]}
            for i in ids],
        "evidence_hits": [dict(h, matched_identifier=mask_identifier(h["matched_identifier"]))
                          for h in hits],
        "resources": resources,
        "flows": flows,
        "restore_risks": restore_risks,
        "timeline": timeline,
        "steps": steps,
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
