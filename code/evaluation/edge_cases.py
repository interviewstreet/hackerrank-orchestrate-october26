"""Edge-case evaluation dataset: build it, run the pipeline on it and score the result.

    python3 code/evaluation/edge_cases.py build          # writes code/evaluation/edge_dataset/
    python3 code/evaluation/edge_cases.py run            # runs main.py on it (replay: committed cache only) and scores
    python3 code/evaluation/edge_cases.py run --backend claude_cli   # reads uncached PNG evidence live (paid)

Two participant-shaped datasets are written: `main/` (one shared world, every case in its own 5-day window so a
full snapshot of one case never asserts absence for another) and `feb29/` (malformed 2026-02-29 timestamps,
kept separate because one bad date must not take the other cases down with it).

Expected answers are written by hand from the public contract, in the same conventions as the e2e scenarios
(see tests/e2e/scenarios.py). `label` says how far each answer is trusted:
  gate              - follows directly from the rules; a mismatch is a defect
  needs-vision      - only decidable after the PNG evidence is read (offline runs skip images)
  off-distribution  - format/category absent from the real dataset; informative only
  ambiguous         - the rules do not settle it; the literal reading is recorded, never gated
  known-limitation  - a documented miss the system does not handle yet (see docs/VISION_SPEC.md §9)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from tests.e2e.builder import MiniDataset, sha  # noqa: E402
from tests.e2e.scenarios import ACC, F, R, V  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "edge_dataset"
DELETE_TEXTS = [
    "Please permanently delete the account associated with this email address.",
    "I want my account closed and all personal data erased, including any copies.",
    "Please remove my profile and everything linked to this email.",
]


class EdgeDataset(MiniDataset):
    """MiniDataset plus binary evidence (PNG) and unique evidence paths for a shared world."""

    def image(self, relpath: str, captured: str, data: bytes, origin: str) -> str:
        fid = f"evidence_{len(self.files) + 1:02d}"
        self.files.append((fid, relpath, origin, captured, data))
        return fid

    def last_activity(self) -> str:
        return self.activity[-1][0]

    def write(self, root: Path) -> Path:
        seen: dict[str, int] = {}
        files = []
        for fid, rel, origin, cap, content in self.files:
            seen[rel] = seen.get(rel, 0) + 1
            if seen[rel] > 1:
                stem, dot, ext = rel.rpartition(".")
                rel = f"{stem}_{seen[rel]}.{ext}"
            files.append((fid, rel, origin, cap, content))
        binary = [(rel, c) for _, rel, _, _, c in files if isinstance(c, bytes)]
        self.files = [(f, r, o, c, x if isinstance(x, str) else "") for f, r, o, c, x in files]
        super().write(root)
        for rel, data in binary:
            (root / rel).write_bytes(data)
        return root


@dataclass
class Case:
    cid: str
    title: str
    setup: str
    trap: str
    label: str
    expected: tuple


# ---------------------------------------------------------------------------------------------------------------
# helpers

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class Window:
    """A 5-day slot: request day 0, report day 2, evidence day 3, audit day 4 at noon."""

    def __init__(self, k: int, start: datetime = datetime(2026, 3, 3, tzinfo=timezone.utc)):
        self.d0 = start + timedelta(days=5 * k)

    def at(self, day: int, hh: int = 0, mm: int = 0, ss: int = 0) -> str:
        return iso(self.d0 + timedelta(days=day, hours=hh, minutes=mm, seconds=ss))

    @property
    def req(self):
        return self.at(0, 9)

    @property
    def rep(self):
        return self.at(2, 9)

    @property
    def aud(self):
        return self.at(4, 12)


@dataclass
class Subject:
    n: int
    uid: str
    name: str
    email: str
    phone: str

    def rid(self, prefix: str, k: int = 1) -> str:
        return f"{prefix}_8{self.n:02d}{k}"

    @property
    def acc(self):
        return self.rid("account")


def subject(ds: EdgeDataset, n: int, name: str, email: str, phone: str) -> Subject:
    s = Subject(n, f"user_2{n:02d}", name, email, phone)
    ds.user(s.uid, name, email, phone, "2026-01-15T00:00:00Z")
    return s


def lookup(ts, rid, key, kv=ACC):
    return (ts, "account_service", "profile_lookup", rid, key, kv)


def search(ts, rid, key, hit=True):
    kv = (f"result=hit total_hits=1 index=customer_directory_v3 email={key} customer_reference=null" if hit
          else "result=miss total_hits=0 index=customer_directory_v3")
    return (ts, "search_service", "index_query", rid, key, kv)


def console_png(title: str, captured: str, header: list[str], rows: list[list[str]]) -> bytes:
    """A plain admin-console screenshot (deterministic: default bitmap font, fixed layout)."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default()
    widths = [max(len(h), *(len(r[i]) for r in rows)) * 7 + 24 for i, h in enumerate(header)]
    w, h = max(sum(widths) + 40, 520), 120 + 26 * len(rows)
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 34], fill=(32, 54, 92))
    d.text((14, 11), title, fill="white", font=font)
    d.text((14, 46), f"Snapshot taken {captured}", fill=(90, 90, 90), font=font)
    y, x = 74, 20
    for i, col in enumerate(header):
        d.text((x, y), col, fill=(20, 20, 20), font=font)
        x += widths[i]
    d.line([20, y + 16, w - 20, y + 16], fill=(180, 180, 180))
    for r in rows:
        y += 26
        x = 20
        for i, cell in enumerate(r):
            d.text((x, y), cell, fill=(40, 40, 40), font=font)
            x += widths[i]
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def deleted_profile(ds, s: Subject, w: Window, day: int = 3):
    """Read-back log proving the subject's primary profile is gone (evidence id returned)."""
    return ds.readback_log(w.at(day, 10), [lookup(w.at(day, 8), s.acc, s.email)])


# ---------------------------------------------------------------------------------------------------------------
# main dataset cases. Each takes (ds, window index) and returns a list of Case.

def e01_repeat_request(ds, k):
    s = subject(ds, 1, "Ingrid Solberg", "ingrid.solberg@example.net", "+47 412 50 101")
    a, b = Window(k), Window(k + 1)
    ev1 = ds.readback_log(a.at(3, 10), [lookup(a.at(3, 8), s.acc, s.email), search(a.at(3, 8, 5), s.rid("search"), s.email)])
    ev2 = ds.readback_log(b.at(3, 10), [lookup(b.at(3, 8), s.acc, s.email),
                                        search(b.at(3, 8, 5), s.rid("search"), s.email, hit=False)])
    ds.request("case_e01a", s.email, a.req, a.rep, a.aud, DELETE_TEXTS[0])
    ds.request("case_e01b", s.email, b.req, b.rep, b.aud, DELETE_TEXTS[1])
    setup = "Same email files two requests. The search entry is present at the first audit and gone by the second."
    return [
        Case("case_e01a", "Repeat request (first)", setup, "Same evidence, different cutoff", "gate", ("INCOMPLETE", [
            F("search_service", s.rid("search"), "REPORT_REMAINING_RECORD", ev1),
            R("search_service", s.rid("search"), "DELETE_RECORD"),
            V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
            V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT")])),
        Case("case_e01b", "Repeat request (second)", setup, "Later cutoff sees the clean state", "gate", ("COMPLETE", [
            V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev2),
            V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT", ev2)])),
    ]


def e02_restore_recreates(ds, k):
    s = subject(ds, 2, "Tomasz Wrona", "t.wrona@example.net", "+48 501 220 302")
    w = Window(k)
    ds.readback_log(w.at(1, 10), [lookup(w.at(1, 8), s.acc, s.email), search(w.at(1, 8, 5), s.rid("search"), s.email, hit=False)])
    ds.act(w.at(2, 6), "RESTORE_BACKUP", "backup_service", "search_service", s.rid("backup"), "SUCCESS",
           f"Restore job repopulated downstream resource {s.rid('search')}.")
    act = ds.last_activity()
    ds.request("case_e02", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e02", "Restore job brings data back",
                 "Profile and search entry confirmed gone, then a RESTORE_BACKUP job refills the search entry before the audit.",
                 "Recreation through a backup restore", "gate", ("INCOMPLETE", [
                     F("search_service", s.rid("search"), "REPORT_REMAINING_RECORD", act),
                     F("backup_service", s.rid("backup"), "REPORT_RESTORE_RISK", act),
                     R("backup_service", s.rid("backup"), "BLOCK_RESTORE"),
                     R("search_service", s.rid("search"), "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT"),
                     V("backup_service", s.rid("backup"), "VERIFY_RESTORE_BLOCKED")]))]


def e03_old_phone_only(ds, k):
    old_phone = "+34 611 480 903"
    s = subject(ds, 3, "Nuria Castells", "nuria.castells@example.net", "+34 622 117 903")
    w = Window(k)
    ds.change(s.uid, "phone", old_phone, s.phone, "2026-02-10T10:00:00Z")
    ev = ds.inventory_sql(w.at(3, 9), ["account_service"], [
        f"INSERT INTO customer_profiles VALUES ('{s.acc}', NULL, NULL, NULL, '{old_phone}', NULL, 'ACTIVE', '{w.at(3, 8)}')"],
        name="regional_replica")
    ds.request("case_e03", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e03", "Old phone number only",
                 "A regional replica keeps a profile row whose only identifier is the subject's previous phone number.",
                 "Identity from phone history", "gate", ("INCOMPLETE", [
                     F("account_service", s.acc, "REPORT_REMAINING_RECORD", ev),
                     R("account_service", s.acc, "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT")]))]


def e04_old_email_hash(ds, k):
    old = "akosua.mensah@oldmail.example"
    s = subject(ds, 4, "Akosua Mensah", "akosua.mensah@example.net", "+233 24 410 0904")
    w = Window(k)
    ds.change(s.uid, "email", old, s.email, "2026-02-12T10:00:00Z")
    ds.change(s.uid, "email_hash", sha(old), sha(s.email), "2026-02-12T10:00:00Z")
    deleted_profile(ds, s, w)
    ev = ds.evidence(f"evidence/logs/service_events_{w.at(3)[:10].replace('-', '')}.log", w.at(3, 11),
                     f"{w.at(3, 10, 58)} level=DEBUG service=analytics_platform instance=analytics-2 trace_id=tr-8040401 "
                     f"resource_id={s.rid('analytics')} event=contact_lookup_completed rows=1 email_opt_in=true "
                     f"correlation_key=\"{sha(old)}\"\n", "central_observability_export")
    ds.request("case_e04", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e04", "Hash of the old email",
                 "A marketing contact is keyed only by sha256 of the subject's previous email.",
                 "Hash linking with a historical identifier", "gate", ("INCOMPLETE", [
                     F("analytics_platform", s.rid("analytics"), "REPORT_REMAINING_RECORD", ev),
                     R("analytics_platform", s.rid("analytics"), "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("analytics_platform", s.rid("analytics"), "VERIFY_RECORD_ABSENT")]))]


def e05_partial_tombstone(ds, k):
    s = subject(ds, 5, "Rafael Duarte", "rafael.duarte@example.net", "+351 912 300 905")
    w = Window(k)
    ds.act(w.at(1, 8), "DELETE_RECORD", "deletion_worker", "account_service", s.acc, "SUCCESS",
           f"Deletion worker submitted primary profile {s.acc} to account_service.")
    ev = ds.bundle_json(w.at(3, 9), [
        ("account_service", "customer_profiles", []),
        ("identity_service", "deleted_customer_references", [
            {"resource_id": s.rid("tombstone"), "subject_reference": s.uid, "name": None, "email": None,
             "phone": None, "email_hash": sha(s.email), "account_status": "DELETED"}])])
    ds.request("case_e05", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e05", "Partly cleaned tombstone",
                 "Tombstone has name, email and phone removed but still carries the email hash.",
                 "Any leftover direct identifier is exposure", "gate", ("INCOMPLETE", [
                     F("identity_service", s.rid("tombstone"), "REPORT_EXPOSED_PII", ev),
                     R("identity_service", s.rid("tombstone"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("identity_service", s.rid("tombstone"), "VERIFY_RECORD_REDACTED")]))]


def e06_flow_already_stopped(ds, k):
    s = subject(ds, 6, "Keiko Tanabe", "keiko.tanabe@example.net", "+81 90 4410 0906")
    w = Window(k)
    flow, srch = s.rid("data_flow"), s.rid("search")
    ds.act(w.at(1, 6), "SYNC_RECORD", "integration_service", "search_service", flow, "SUCCESS",
           f"Active connector repopulated downstream resource {srch}.")
    ds.act(w.at(1, 8), "DISABLE_DATA_FLOW", "deletion_worker", "integration_service", flow, "SUCCESS",
           f"Policy action completed for {flow}.")
    ds.act(w.at(1, 9), "CHECK_DATA_FLOW", "deletion_worker", "integration_service", flow, "SUCCESS",
           f"Connector status check confirmed that data flow {flow} is disabled.")
    ev1 = ds.readback_log(w.at(3, 10), [lookup(w.at(3, 8), s.acc, s.email), search(w.at(3, 8, 5), srch, s.email, hit=False)])
    ev2 = ds.inventory_sql(w.at(3, 11), ["integration_service"], [
        f"INSERT INTO connector_subscriptions VALUES ('{flow}', NULL, '{s.email}', 'customer_events_connector', 0, 'stopped', '{w.at(3, 10, 30)}')"])
    ds.request("case_e06", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e06", "Data flow already stopped",
                 "A connector copied data, was disabled and checked before the audit; the search entry is gone afterwards.",
                 "A past flow is not an active risk", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev1),
                     V("search_service", srch, "VERIFY_RECORD_ABSENT", ev1),
                     V("integration_service", flow, "VERIFY_DATA_FLOW_DISABLED", ev2)]))]


def e07_restore_already_blocked(ds, k):
    s = subject(ds, 7, "Mehmet Aydın", "mehmet.aydin@example.net", "+90 532 410 0907")
    w = Window(k)
    bk = s.rid("backup")
    ds.act(w.at(1, 6), "CHECK_RESTORE_ACCESS", "deletion_worker", "backup_service", bk, "SUCCESS",
           f"Restore-access check confirmed that archive {bk} can still be restored.")
    ds.act(w.at(1, 8), "BLOCK_RESTORE", "deletion_worker", "backup_service", bk, "SUCCESS", f"Policy action completed for {bk}.")
    ev1 = deleted_profile(ds, s, w)
    ev2 = ds.inventory_sql(w.at(3, 11), ["backup_service"], [
        f"INSERT INTO backup_restore_entries VALUES ('{bk}', NULL, '{s.email}', 'archive/customer-data/{bk}.tar.zst', 0, '{w.at(3, 10, 30)}')"])
    ds.request("case_e07", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e07", "Restore already blocked",
                 "An access check said the archive was restorable, then BLOCK_RESTORE ran and the inventory shows restore_allowed=0.",
                 "The latest state wins", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev1),
                     V("backup_service", bk, "VERIFY_RESTORE_BLOCKED", ev2)]))]


def e08_ordering_stress(ds, k):
    s = subject(ds, 8, "Chiara Lombardi", "chiara.lombardi@example.net", "+39 347 410 0908")
    w = Window(k)
    acc, srch, exp, flow, bk = s.acc, s.rid("search"), s.rid("export"), s.rid("data_flow"), s.rid("backup")
    t = w.at(3, 8)
    ev = ds.inventory_sql(w.at(3, 9), ["account_service", "search_service", "export_service", "integration_service", "backup_service"], [
        f"INSERT INTO customer_profiles VALUES ('{acc}', '{s.uid}', '{s.name}', '{s.email}', '{s.phone}', '{sha(s.email)}', 'ACTIVE', '{t}')",
        f"INSERT INTO customer_search_documents VALUES ('{srch}', '{s.uid}', '{s.name}', '{s.email}', NULL, NULL, 'customer_directory_v3', '{t}')",
        f"INSERT INTO customer_exports VALUES ('{exp}', '{s.uid}', '{s.email}', NULL, 'exports/{exp}.zip', '{t}')",
        f"INSERT INTO connector_subscriptions VALUES ('{flow}', '{s.uid}', '{s.email}', 'customer_events_connector', 1, 'delivered', '{t}')",
        f"INSERT INTO backup_restore_entries VALUES ('{bk}', '{s.uid}', '{s.email}', 'archive/customer-data/{bk}.tar.zst', 1, '{t}')"])
    ds.request("case_e08", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e08", "Ordering stress",
                 "Profile, search document, export, an enabled connector and a restorable backup all still exist.",
                 "Phase order, disable/block before deletes, contract-table then system/resource order", "gate", ("INCOMPLETE", [
                     F("account_service", acc, "REPORT_REMAINING_RECORD", ev),
                     F("export_service", exp, "REPORT_REMAINING_RECORD", ev),
                     F("search_service", srch, "REPORT_REMAINING_RECORD", ev),
                     F("integration_service", flow, "REPORT_ACTIVE_DATA_FLOW", ev),
                     F("backup_service", bk, "REPORT_RESTORE_RISK", ev),
                     R("integration_service", flow, "DISABLE_DATA_FLOW"),
                     R("backup_service", bk, "BLOCK_RESTORE"),
                     R("account_service", acc, "DELETE_RECORD"),
                     R("export_service", exp, "DELETE_RECORD"),
                     R("search_service", srch, "DELETE_RECORD"),
                     V("account_service", acc, "VERIFY_RECORD_ABSENT"),
                     V("export_service", exp, "VERIFY_RECORD_ABSENT"),
                     V("search_service", srch, "VERIFY_RECORD_ABSENT"),
                     V("integration_service", flow, "VERIFY_DATA_FLOW_DISABLED"),
                     V("backup_service", bk, "VERIFY_RESTORE_BLOCKED")]))]


def e09_evidence_at_cutoff(ds, k):
    s = subject(ds, 9, "Owen Gallagher", "owen.gallagher@example.net", "+353 87 410 0909")
    w = Window(k)
    ev = ds.readback_log(w.aud, [lookup(w.at(4, 11), s.acc, s.email), search(w.at(4, 11, 5), s.rid("search"), s.email)])
    ds.request("case_e09", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e09", "Evidence exactly at the cutoff",
                 "The read-back showing the search entry is captured at audit_at to the second.",
                 "The cutoff is inclusive", "gate", ("INCOMPLETE", [
                     F("search_service", s.rid("search"), "REPORT_REMAINING_RECORD", ev),
                     R("search_service", s.rid("search"), "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT")]))]


def e10_sync_after_cutoff(ds, k):
    s = subject(ds, 10, "Priya Venkatesh", "priya.venkatesh@example.net", "+91 98450 10910")
    w = Window(k)
    ev = ds.readback_log(w.at(3, 10), [lookup(w.at(3, 8), s.acc, s.email), search(w.at(3, 8, 5), s.rid("search"), s.email, hit=False)])
    ds.act(w.at(4, 13), "SYNC_RECORD", "integration_service", "search_service", s.rid("data_flow"), "SUCCESS",
           f"Active connector repopulated downstream resource {s.rid('search')}.")
    ds.request("case_e10", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e10", "Sync after the cutoff",
                 "Everything is clean at the audit; a connector refills the search entry one hour later.",
                 "Later activity is ignored", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev),
                     V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT", ev)]))]


def e11_not_started_but_done(ds, k):
    s = subject(ds, 11, "Lucas Ferreira", "lucas.ferreira@example.net", "+55 11 98410 0911")
    w = Window(k)
    ev = deleted_profile(ds, s, w)
    ds.request("case_e11", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2], status="NOT_STARTED")
    return [Case("case_e11", "NOT_STARTED, but done",
                 "Workflow reports NOT_STARTED while the read-back proves the profile is gone.",
                 "Reported status is a claim", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)]))]


def e12_email_delivery_log(ds, k):
    s = subject(ds, 12, "Hannah Becker", "hannah.becker@example.net", "+49 151 410 0912")
    w = Window(k)
    ev = ds.readback_log(w.at(3, 10), [
        lookup(w.at(3, 8), s.acc, s.email),
        (w.at(3, 8, 10), "email_delivery_service", "delivery_log_read", s.rid("email_delivery"), s.email,
         f"rows=1 recipient_email={s.email} template=order_shipped")])
    ds.request("case_e12", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e12", "Email delivery log",
                 "A mail delivery log still shows the subject's address as recipient.",
                 "This category is redacted, not deleted", "off-distribution", ("INCOMPLETE", [
                     F("email_delivery_service", s.rid("email_delivery"), "REPORT_EXPOSED_PII", ev),
                     R("email_delivery_service", s.rid("email_delivery"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("email_delivery_service", s.rid("email_delivery"), "VERIFY_RECORD_REDACTED")]))]


def e13_pseudonymous_analytics(ds, k):
    s = subject(ds, 13, "Sven Lindqvist", "sven.lindqvist@example.net", "+46 70 410 0913")
    w = Window(k)
    ev = ds.readback_log(w.at(3, 10), [
        lookup(w.at(3, 8), s.acc, s.email),
        (w.at(3, 8, 20), "analytics_platform", "analytics_profile_read", s.rid("analytics"), s.uid,
         f"customer_reference={s.uid} email=null phone=null email_hash=null audience_cohort=general_shopper")])
    ds.request("case_e13", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e13", "Analytics keyed only by user_id",
                 "Analytics profile has every direct identifier removed but still carries customer_reference=user_id.",
                 "Is a stable user_id still 'attributable'?", "ambiguous", ("INCOMPLETE", [
                     F("analytics_platform", s.rid("analytics"), "REPORT_EXPOSED_PII", ev),
                     R("analytics_platform", s.rid("analytics"), "ANONYMIZE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("analytics_platform", s.rid("analytics"), "VERIFY_RECORD_ANONYMIZED")]))]


def e14_screenshot_only_evidence(ds, k):
    s = subject(ds, 14, "Amara Okafor", "amara.okafor@example.net", "+234 803 410 0914")
    w = Window(k)
    ds.act(w.at(1, 7), "CREATE_EXPORT", "export_service", "object_store", s.rid("export"), "SUCCESS",
           f"Scheduled account export processed {s.rid('export')}.")
    deleted_profile(ds, s, w)
    cap = w.at(3, 12)
    ev = ds.image(f"evidence/images/customer_export_console_{cap[:10].replace('-', '')}.png", cap, console_png(
        "Customer Export Console  -  export_service", cap, ["Export ID", "Owner", "Status", "Created (UTC)"],
        [[s.rid("export"), s.email, "Available", w.at(1, 7)]]), "export_service")
    ds.request("case_e14", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e14", "Screenshot is the only evidence",
                 "An export console screenshot is the only artifact showing the subject's export is still available.",
                 "The image path decides the case", "needs-vision", ("INCOMPLETE", [
                     F("export_service", s.rid("export"), "REPORT_REMAINING_RECORD", ev),
                     R("export_service", s.rid("export"), "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("export_service", s.rid("export"), "VERIFY_RECORD_ABSENT")]))]


def e15_file_listing_link(ds, k):
    s = subject(ds, 15, "Zainab Rahimi", "zainab.rahimi@example.net", "+44 7700 410915")
    w = Window(k)
    obj, fname = s.rid("object"), f"account_export_{s.n:02d}.zip"
    ds.act(w.at(1, 6), "LINK_RESOURCE_IDENTITY", "data_catalog", "object_storage", obj, "SUCCESS",
           f"Data catalog linked {obj} ({fname}) to {s.email} and {s.uid}.")
    deleted_profile(ds, s, w)
    cap = w.at(3, 12)
    ev = ds.image(f"evidence/images/object_storage_browser_{cap[:10].replace('-', '')}.png", cap, console_png(
        "Object Storage Browser  -  bucket: customer-exports", cap, ["Name", "Size", "Last modified (UTC)"],
        [[fname, "2.4 MB", w.at(1, 5)], ["quarterly_catalog.csv", "88 KB", w.at(0, 4)]]), "object_storage")
    ds.request("case_e15", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e15", "File listed by name only",
                 "A storage-browser screenshot lists a file by name; a data-catalog activity maps that name to object_N.",
                 "Name-to-resource resolution (the Sonnet file-listing pass, or the OCR fallback when a local VLM's "
                 "invented ids are dropped by the grounding guard)", "needs-vision", ("INCOMPLETE", [
                     F("object_storage", obj, "REPORT_REMAINING_RECORD", ev),
                     R("object_storage", obj, "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("object_storage", obj, "VERIFY_RECORD_ABSENT")]))]


def e16_screenshot_after_cutoff(ds, k):
    s = subject(ds, 16, "Mateusz Kowal", "mateusz.kowal@example.net", "+48 602 410 916")
    w = Window(k)
    ev = deleted_profile(ds, s, w)
    cap = w.at(4, 14)
    ds.image(f"evidence/images/customer_export_console_{cap[:10].replace('-', '')}.png", cap, console_png(
        "Customer Export Console  -  export_service", cap, ["Export ID", "Owner", "Status", "Created (UTC)"],
        [[s.rid("export"), s.email, "Available", w.at(4, 13)]]), "export_service")
    ds.request("case_e16", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e16", "Screenshot after the cutoff",
                 "A screenshot taken two hours after audit_at shows an export for the subject.",
                 "The cutoff also applies to images", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)]))]


def e17_legal_hold_expired(ds, k):
    s = subject(ds, 17, "Élodie Marchand", "elodie.marchand@example.net", "+33 6 41 00 09 17")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = ds.bundle_json(w.at(3, 11), [("legal_service", "retained_order_records", [
        {"resource_id": s.rid("legal_hold"), "subject_reference": s.uid, "order_reference": "ORD-81701",
         "retention_reason": "payment_dispute", "retained_until": w.at(1, 0), "hold_status": "RELEASED"}])])
    ds.request("case_e17", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e17", "Legal hold expired",
                 "The legal-hold record's retained_until passed before the audit and it is marked RELEASED.",
                 "RETAIN only while a hold is active", "ambiguous", ("INCOMPLETE", [
                     F("legal_service", s.rid("legal_hold"), "REPORT_REMAINING_RECORD", ev),
                     R("legal_service", s.rid("legal_hold"), "DELETE_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("legal_service", s.rid("legal_hold"), "VERIFY_RECORD_ABSENT")]))]


def e18_shared_attachment(ds, k):
    s = subject(ds, 18, "Daniel Mwangi", "daniel.mwangi@example.net", "+254 712 410 918")
    other = subject(ds, 19, "Grace Wanjiru", "grace.wanjiru@example.net", "+254 712 410 919")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = ds.bundle_json(w.at(3, 11), [("support_platform", "ticket_attachments", [
        {"resource_id": s.rid("support"), "ticket_id": "CS-81801", "file_name": "joint_delivery_claim.pdf",
         "uploaded_by": s.email, "shared_with": other.email, "storage_class": "ticket_attachment"}])])
    ds.request("case_e18", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e18", "Attachment shared with another customer",
                 "A ticket attachment uploaded by the subject is shared with a second customer.",
                 "DELETE rule's 'belongs only to the subject' condition fails", "ambiguous", ("INCOMPLETE", [
                     F("support_platform", s.rid("support"), "REPORT_EXPOSED_PII", ev),
                     R("support_platform", s.rid("support"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("support_platform", s.rid("support"), "VERIFY_RECORD_REDACTED")]))]


def e21_month_end(ds, _k):
    s = subject(ds, 21, "Agnieszka Lis", "agnieszka.lis@example.net", "+48 603 410 921")
    ds.readback_log("2026-02-27T10:00:00Z", [lookup("2026-02-27T08:00:00Z", s.acc, s.email, f"rows=1 http_status=200 email={s.email}"),
                                             search("2026-02-27T08:05:00Z", s.rid("search"), s.email)])
    ev = ds.readback_log("2026-03-01T00:10:00Z", [lookup("2026-03-01T00:08:00Z", s.acc, s.email),
                                                  search("2026-03-01T00:09:00Z", s.rid("search"), s.email, hit=False)])
    ds.request("case_e21", s.email, "2026-02-28T23:30:00Z", "2026-03-01T00:05:00Z", "2026-03-01T12:00:00Z", DELETE_TEXTS[1])
    return [Case("case_e21", "Month end without a 29th",
                 "Request at 2026-02-28 23:30, clean read-back at 2026-03-01 00:10, audit at noon.",
                 "Date ordering across the missing 29 Feb", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev),
                     V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT", ev)]))]


def e22_cyrillic_name(ds, k):
    s = subject(ds, 22, "Ольга Петрова", "olga.petrova@example.net", "+7 916 410 09 22")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = ds.inventory_sql(w.at(3, 11), ["support_platform"], [
        f"INSERT INTO support_records VALUES ('{s.rid('support')}', '{s.uid}', 'Ольга Петрова', NULL, NULL, "
        f"'Клиентка просила изменить адрес доставки.', '{w.at(3, 10)}')"], name="support")
    ds.request("case_e22", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e22", "Cyrillic name left in a ticket",
                 "A support ticket still shows the subject's name in Cyrillic; email and phone are already removed.",
                 "Non-Latin direct identifier", "gate", ("INCOMPLETE", [
                     F("support_platform", s.rid("support"), "REPORT_EXPOSED_PII", ev),
                     R("support_platform", s.rid("support"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("support_platform", s.rid("support"), "VERIFY_RECORD_REDACTED")]))]


def e23_cyrillic_email(ds, k):
    s = subject(ds, 23, "Дмитрий Соколов", "дмитрий.соколов@почта.рф", "+7 925 410 09 23")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = ds.inventory_sql(w.at(3, 11), ["support_platform"], [
        f"INSERT INTO support_records VALUES ('{s.rid('support')}', NULL, NULL, '{s.email}', NULL, "
        f"'Клиент просил вернуть заказ.', '{w.at(3, 10)}')"], name="support")
    ds.request("case_e23", "Дмитрий.Соколов@ПОЧТА.РФ", w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e23", "Cyrillic (IDN) email, upper-case request",
                 "Subject's email is fully Cyrillic; the request spells it in mixed case; a ticket still holds it.",
                 "Non-ASCII email matching and case folding", "gate", ("INCOMPLETE", [
                     F("support_platform", s.rid("support"), "REPORT_EXPOSED_PII", ev),
                     R("support_platform", s.rid("support"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("support_platform", s.rid("support"), "VERIFY_RECORD_REDACTED")]))]


def e24_homoglyph_decoy(ds, k):
    s = subject(ds, 24, "Olga Ivanova", "olga.ivanova@example.net", "+7 903 410 09 24")
    decoy = subject(ds, 25, "Olga Ivanova", "оlga.ivanova@example.net", "+7 903 410 09 25")
    w = Window(k)
    ev = ds.readback_log(w.at(3, 10), [
        lookup(w.at(3, 8), s.acc, s.email),
        lookup(w.at(3, 8, 2), decoy.acc, decoy.email, f"rows=1 http_status=200 email={decoy.email}")])
    ds.request("case_e24", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e24", "Look-alike email decoy",
                 "Another customer with the same name has a live account under an email whose first 'o' is Cyrillic.",
                 "Homoglyph must not link", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)]))]


def _tombstone_export(ds, s, w, first, last):
    return ds.service_export_json(w.at(3, 11), {"identity_service": {"deleted_customer_references": [
        {"resource_id": s.rid("tombstone"), "subject_reference": s.uid, "first_name": first, "last_name": last,
         "email": None, "phone": None, "email_hash": None, "account_status": "DELETED", "observed_at": w.at(3, 10, 40)}]}})


def e25_first_last_exposed(ds, k):
    s = subject(ds, 26, "Yusuf Demir", "yusuf.demir@example.net", "+90 533 410 0926")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = _tombstone_export(ds, s, w, "Yusuf", "Demir")
    ds.request("case_e25", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e25", "first_name/last_name still on tombstone",
                 "service_resource_export tombstone uses first_name/last_name (not full_name); both still filled.",
                 "Split name fields are direct identifiers", "gate", ("INCOMPLETE", [
                     F("identity_service", s.rid("tombstone"), "REPORT_EXPOSED_PII", ev),
                     R("identity_service", s.rid("tombstone"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("identity_service", s.rid("tombstone"), "VERIFY_RECORD_REDACTED")]))]


def e26_first_last_clean(ds, k):
    s = subject(ds, 27, "Ana Popescu", "ana.popescu@example.net", "+40 721 410 927")
    w = Window(k)
    ev1 = deleted_profile(ds, s, w)
    ev2 = _tombstone_export(ds, s, w, None, None)
    ds.request("case_e26", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    return [Case("case_e26", "first_name/last_name cleaned",
                 "Same export layout with first_name/last_name null.",
                 "The split-name fix must not over-trigger", "gate", ("COMPLETE", [
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev1),
                     V("identity_service", s.rid("tombstone"), "VERIFY_RECORD_REDACTED", ev2)]))]


def e27_nested_name(ds, k):
    s = subject(ds, 28, "Jonas Petersen", "jonas.petersen@example.net", "+45 20 41 09 28")
    w = Window(k)
    deleted_profile(ds, s, w)
    ev = ds.service_export_json(w.at(3, 11), {"support_platform": {"tickets": [
        {"resource_id": s.rid("support"), "customer_reference": s.uid,
         "requester": {"name": {"first": "Jonas", "last": "Petersen"}, "email": None, "phone": None},
         "message_excerpt": "Customer asked support to correct delivery details.", "observed_at": w.at(3, 10, 40)}]}})
    ds.request("case_e27", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    return [Case("case_e27", "Nested name object in a ticket",
                 "Ticket stores the requester as {name: {first, last}} with email and phone null.",
                 "Unfamiliar layout still exposes a name", "gate", ("INCOMPLETE", [
                     F("support_platform", s.rid("support"), "REPORT_EXPOSED_PII", ev),
                     R("support_platform", s.rid("support"), "REDACT_RECORD"),
                     V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                     V("support_platform", s.rid("support"), "VERIFY_RECORD_REDACTED")]))]


def _intent_case(ds, k, n, name, email, cid, title, text, trap, label, expected, present=True):
    s = subject(ds, n, name, email, f"+1 415 410 09{n:02d}")
    w = Window(k)
    kv = f"rows=1 http_status=200 email={s.email}" if present else ACC
    ev = ds.readback_log(w.at(3, 10), [lookup(w.at(3, 8), s.acc, s.email, kv)])
    ds.request(cid, s.email, w.req, w.rep, w.aud, text, status="NOT_STARTED" if present else "COMPLETE")
    exp = expected(s, ev)
    return [Case(cid, title, f"Request text: “{text}”", trap, label, exp)]


def e28_withdrawn(ds, k):
    return _intent_case(ds, k, 30, "Megan Walsh", "megan.walsh@example.net", "case_e28", "Withdrawn deletion request",
                        "Last week I asked you to delete my account. Please cancel that request; I want to keep my account and my data.",
                        "Mentions deletion but withdraws it", "gate", lambda s, ev: ("NOT_APPLICABLE", []))


def e29_conditional(ds, k):
    return _intent_case(ds, k, 31, "Bruno Sousa", "bruno.sousa@example.net", "case_e29", "Conditional request",
                        "If you cannot fix the delivery address on order ORD-55120 by Friday, then delete my account.",
                        "Deletion only if a condition fails", "ambiguous", lambda s, ev: ("NOT_APPLICABLE", []))


def e30_on_behalf(ds, k):
    return _intent_case(ds, k, 32, "Margaret Hughes", "margaret.hughes@example.net", "case_e30", "On behalf of someone else",
                        "I am writing for my mother, who passed away in March. Please close and delete her account registered to this email.",
                        "Third party asks for deletion", "ambiguous",
                        lambda s, ev: ("COMPLETE", [V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)]), present=False)


def e31_no_footprint(ds, k):
    s = subject(ds, 33, "Hugo Lambert", "hugo.lambert@example.net", "+32 470 41 09 33")
    w = Window(k)
    ds.request("case_e31", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    return [Case("case_e31", "Authorized deletion, no footprint",
                 "Known subject asks for deletion; no evidence file or activity mentions any of their identifiers.",
                 "NOT_APPLICABLE is only for non-deletion requests", "gate", ("COMPLETE", []))]


MAIN_CASES = [e01_repeat_request, None, e02_restore_recreates, e03_old_phone_only, e04_old_email_hash,
              e05_partial_tombstone, e06_flow_already_stopped, e07_restore_already_blocked, e08_ordering_stress,
              e09_evidence_at_cutoff, e10_sync_after_cutoff, e11_not_started_but_done, e12_email_delivery_log,
              e13_pseudonymous_analytics, e14_screenshot_only_evidence, e15_file_listing_link,
              e16_screenshot_after_cutoff, e17_legal_hold_expired, e18_shared_attachment, e22_cyrillic_name,
              e23_cyrillic_email, e24_homoglyph_decoy, e25_first_last_exposed, e26_first_last_clean, e27_nested_name,
              e28_withdrawn, e29_conditional, e30_on_behalf, e31_no_footprint]


def build_main() -> tuple[EdgeDataset, list[Case]]:
    ds, cases = EdgeDataset(), []
    cases += e21_month_end(ds, 0)
    for k, fn in enumerate(MAIN_CASES):
        if fn is not None:  # the None slot is the second window of e01
            cases += fn(ds, k)
    return ds, cases


# ---------------------------------------------------------------------------------------------------------------
# feb29 dataset: 2026 has no 29 February. Expected answers follow the handling agreed in the brainstorm:
# unreadable activity rows and evidence files are skipped, audit-log identifiers are kept, an unreadable request
# timestamp falls back to the next valid one, and the run always writes one row per case.

def build_feb29() -> tuple[EdgeDataset, list[Case]]:
    ds, cases = EdgeDataset(), []
    bad = "2026-02-29T08:00:00Z"

    s = subject(ds, 40, "Farah Aziz", "farah.aziz@example.net", "+60 12 410 0940")
    w = Window(0)
    ds.act(bad, "SYNC_RECORD", "integration_service", "search_service", s.rid("data_flow"), "SUCCESS",
           f"Active connector repopulated downstream resource {s.rid('search')}.")
    ev = ds.readback_log(w.at(3, 10), [lookup(w.at(3, 8), s.acc, s.email), search(w.at(3, 8, 5), s.rid("search"), s.email, hit=False)])
    ds.request("case_f01", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[0])
    cases.append(Case("case_f01", "Invalid date in an activity row", f"SYNC_RECORD with event_time {bad}.",
                      "Skip the row, keep running", "gate", ("COMPLETE", [
                          V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev),
                          V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT", ev)])))

    old = "liam.oconnor@oldmail.example"
    s = subject(ds, 41, "Liam O'Connor", "liam.oconnor@example.net", "+353 86 410 0941")
    w = Window(1)
    ds.change(s.uid, "email", old, s.email, "2026-02-29T10:00:00Z")
    ev = ds.readback_log(w.at(3, 10), [lookup(w.at(3, 8), s.acc, s.email), search(w.at(3, 8, 5), s.rid("search"), old)])
    ds.request("case_f02", old, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    cases.append(Case("case_f02", "Invalid date in the audit log", "Email change logged at 2026-02-29; request uses the old email.",
                      "Keep the identifiers, ignore the time", "gate", ("INCOMPLETE", [
                          F("search_service", s.rid("search"), "REPORT_REMAINING_RECORD", ev),
                          R("search_service", s.rid("search"), "DELETE_RECORD"),
                          V("account_service", s.acc, "VERIFY_RECORD_ABSENT"),
                          V("search_service", s.rid("search"), "VERIFY_RECORD_ABSENT")])))

    s = subject(ds, 42, "Sara Haddad", "sara.haddad@example.net", "+961 3 410 942")
    w = Window(2)
    ds.readback_log("2026-02-29T10:00:00Z", [search("2026-02-28T08:05:00Z", s.rid("search"), s.email)])
    ev = deleted_profile(ds, s, w)
    ds.request("case_f03", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[2])
    cases.append(Case("case_f03", "Invalid capture time on an evidence file",
                      "A read-back showing the search entry has captured_at 2026-02-29.",
                      "Unprovable capture time cannot be cited", "gate", ("COMPLETE", [
                          V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)])))

    s = subject(ds, 43, "Kofi Boateng", "kofi.boateng@example.net", "+233 20 410 0943")
    w = Window(3)
    ev = deleted_profile(ds, s, w)
    ds.request("case_f04", s.email, "2026-02-29T09:00:00Z", w.rep, w.aud, DELETE_TEXTS[0])
    cases.append(Case("case_f04", "Invalid requested_at", "requested_at = 2026-02-29T09:00:00Z.",
                      "Fall back to the next valid timestamp", "gate", ("COMPLETE", [
                          V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)])))

    s = subject(ds, 44, "Ines Moreau", "ines.moreau@example.net", "+33 6 41 00 09 44")
    w = Window(4)
    ev = deleted_profile(ds, s, w)
    ds.request("case_f05", s.email, w.req, w.rep, w.aud, DELETE_TEXTS[1])
    cases.append(Case("case_f05", "Control case", "Ordinary clean deletion in the same dataset.",
                      "One bad date must not cost the other cases", "gate", ("COMPLETE", [
                          V("account_service", s.acc, "VERIFY_RECORD_ABSENT", ev)])))
    return ds, cases


DATASETS = {"main": build_main, "feb29": build_feb29}


# ---------------------------------------------------------------------------------------------------------------
# write / run / score

def steps_json(steps: list[tuple]) -> str:
    keys = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")
    return json.dumps([{"step_no": i, **dict(zip(keys, s))} for i, s in enumerate(steps, start=1)], ensure_ascii=False)


def build() -> dict[str, list[Case]]:
    out = {}
    for name, fn in DATASETS.items():
        ds, cases = fn()
        root = OUT_DIR / name
        ds.write(root)
        with open(root / "expected_output.csv", "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh, lineterminator="\n")
            wr.writerow(["case_id", "deletion_status", "steps_json"])
            for c in sorted(cases, key=lambda c: c.cid):
                wr.writerow([c.cid, c.expected[0], steps_json(c.expected[1])])
        out[name] = cases
    write_cases_md(out)
    return out


def write_cases_md(all_cases: dict[str, list[Case]]) -> None:
    lines = ["# Edge-case dataset", "",
             "Generated by `python3 code/evaluation/edge_cases.py build`; do not edit by hand. Run it with "
             "`python3 code/evaluation/edge_cases.py run`.", "",
             "Labels: **gate** = follows directly from the rules; **needs-vision** = decided by PNG evidence "
             "(offline runs skip images); **off-distribution** = format absent from the real dataset; "
             "**ambiguous** = rules do not settle it, literal reading recorded; **known-limitation** = documented miss "
             "(docs/VISION_SPEC.md §9).", ""]
    for name, cases in all_cases.items():
        lines += [f"## `{name}/`", "", "| case | title | setup | trap | label | expected |", "|---|---|---|---|---|---|"]
        for c in sorted(cases, key=lambda c: c.cid):
            ops = ", ".join(f"{s[3].split('_', 1)[1].lower()} {s[2]}" for s in c.expected[1]) or "no steps"
            lines.append(f"| {c.cid} | {c.title} | {c.setup} | {c.trap} | {c.label} | **{c.expected[0]}**: {ops} |")
        lines.append("")
    (OUT_DIR / "CASES.md").write_text("\n".join(lines), encoding="utf-8")


def read_output(path: Path) -> dict:
    got = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                steps = [tuple(s[k] for k in ("phase", "system_id", "resource_id", "operation", "state", "evidence_id"))
                         for s in json.loads(r["steps_json"])]
                got[r["case_id"]] = (r["deletion_status"], steps)
    return got


def run(backend: str) -> int:
    all_cases = build()
    lines = ["# Edge-case results", "", f"Backend: `{backend}`. Generated by `python3 code/evaluation/edge_cases.py run`.", ""]
    gate_fail = 0
    for name, cases in all_cases.items():
        root = OUT_DIR / name
        work = OUT_DIR / ".runs" / name
        work.mkdir(parents=True, exist_ok=True)
        out = work / "output.csv"
        out.unlink(missing_ok=True)
        env = dict(os.environ, GDA_LLM_BACKEND=backend)
        if backend in {"offline", "replay"}:
            env["GDA_BUDGET_USD"] = "0"
        proc = subprocess.run([sys.executable, str(CODE_DIR / "main.py"), "--dataset-dir", str(root), "--out", str(out),
                               "--trace-dir", str(work / "trace"), "--backend", backend],
                              capture_output=True, text=True, env=env)
        got = read_output(out)
        err = [ln for ln in proc.stderr.splitlines() if ln.strip()][-1:] if proc.returncode else []
        lines += [f"## `{name}/` (exit {proc.returncode}, {len(got)}/{len(cases)} rows)", ""]
        if err:
            lines += [f"Run failed: `{err[0]}`", ""]
        lines += ["| case | label | expected | got | steps | detail |", "|---|---|---|---|---|---|"]
        for c in sorted(cases, key=lambda c: c.cid):
            exp_status, exp_steps = c.expected
            g = got.get(c.cid)
            if g is None:
                verdict, detail, gs = "FAIL", "no output row", "–"
            else:
                gs = g[0]
                missing = [s for s in exp_steps if s not in g[1]]
                extra = [s for s in g[1] if s not in exp_steps]
                if g[0] == exp_status and g[1] == exp_steps:
                    verdict, detail = "PASS", ""
                else:
                    verdict = "FAIL"
                    parts = []
                    if missing:
                        parts.append("missing " + "; ".join(f"{s[3]} {s[2]}{(' @' + s[5]) if s[5] else ''}" for s in missing))
                    if extra:
                        parts.append("extra " + "; ".join(f"{s[3]} {s[2]}{(' @' + s[5]) if s[5] else ''}" for s in extra))
                    if not parts:
                        parts.append("same steps, different order")
                    detail = " / ".join(parts)
            if verdict == "FAIL" and c.label == "gate":
                gate_fail += 1
            lines.append(f"| {c.cid} | {c.label} | {exp_status} | {gs} | {verdict} | {detail} |")
        lines.append("")
    summary = f"Gate failures: {gate_fail}"
    lines.insert(3, summary + "\n")
    (OUT_DIR / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 1 if gate_fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "run"])
    ap.add_argument("--backend", default="replay", help="LLM backend for `run` (default replay)")
    a = ap.parse_args()
    if a.command == "build":
        cases = build()
        print(f"wrote {OUT_DIR} ({', '.join(f'{k}: {len(v)} cases' for k, v in cases.items())})")
        return 0
    return run(a.backend)


if __name__ == "__main__":
    sys.exit(main())
