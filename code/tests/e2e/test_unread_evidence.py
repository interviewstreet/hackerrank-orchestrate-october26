"""Which COMPLETE verdicts an unread screenshot/PDF puts at risk (exit code 4 and `unverified_evidence`).

Finding (2026-10-25, owner's test): an invoice PDF naming only one person, registered in the manifest without a
vision transcription, flagged every COMPLETE request whose window contained its capture time, people it never
mentions included, so the run exited 4 for an unrelated request. Fixed: with OCR text, a file counts only for the
requests whose person (identifiers or resource ids) it shows; without OCR text it still counts for all of them.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .builder import MiniDataset
from .scenarios import AUD, EMAIL, REP, REQ, base, profile_lookup

MAIN = Path(__file__).resolve().parents[2] / "main.py"
OMAR = "omar.h@example.org"
INVOICE = b"%PDF-1.4 stand-in for an invoice the vision model never read"


def run(ocr_text: str | None, listed: str = "evidence/documents/invoice_for_client.pdf",
        present: bool = True) -> tuple[int, dict]:
    """Two COMPLETE requests in the same window and one unread file captured inside it (or, with present=False,
    listed in the manifest but missing). Returns (exit code, {case_id: unverified_evidence})."""
    ds = base().user("user_103", "Omar Haddad", OMAR, "+971 50 100 2000")
    ds.readback_log("2026-05-10T10:00:00Z", [profile_lookup("account_7001", EMAIL),
                                             profile_lookup("account_7301", OMAR, ts="2026-05-10T08:01:00Z")])
    ds.request("case_30", EMAIL, REQ, REP, AUD)
    ds.request("case_31", OMAR, REQ, REP, AUD)
    with tempfile.TemporaryDirectory(prefix="gda_unread_") as tmp:
        work = Path(tmp)
        root = ds.write(work / "dataset")
        pdf = root / listed
        if present:
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(INVOICE)
        with open(root / "evidence_files.csv", "a", encoding="utf-8") as fh:
            fh.write(f"evidence_02,{listed},billing_service,2026-05-08T09:00:00Z\n")
        cache = work / "ocr_cache.jsonl"
        if ocr_text is not None:
            cache.write_text(json.dumps({"sha256": hashlib.sha256(INVOICE).hexdigest(), "file": pdf.name,
                                         "engine": "test", "text": ocr_text}) + "\n", encoding="utf-8")
        env = dict(os.environ, GDA_LLM_BACKEND="offline", GDA_BUDGET_USD="0", GDA_OCR_CACHE=str(cache),
                   PATH="/nonexistent")  # no pdftotext / tesseract: the OCR text comes from the cache only
        proc = subprocess.run([sys.executable, str(MAIN), "--dataset-dir", str(root), "--out", str(work / "out.csv"),
                               "--trace-dir", str(work / "trace")], capture_output=True, text=True, env=env, cwd=work)
        flags = {c: json.loads((work / "trace" / f"{c}.json").read_text()).get("unverified_evidence")
                 for c in ("case_30", "case_31")}
        return proc.returncode, flags


class UnreadEvidenceScopeTests(unittest.TestCase):
    def test_unread_file_flags_only_the_people_it_names(self):
        code, flags = run("INVOICE\nEmail: LENA.NOVAK@EXAMPLE.ORG​\nInvoice: 100 USD\nPayment Date: 2026-05-07\n")
        self.assertEqual(flags, {"case_30": ["evidence_02"], "case_31": None})
        self.assertEqual(code, 4)

    def test_unread_file_naming_nobody_flags_nobody(self):
        code, flags = run("INVOICE\nEmail: someone.else@example.com\nInvoice: 100 USD\n")
        self.assertEqual(flags, {"case_30": None, "case_31": None})
        self.assertEqual(code, 0)

    def test_without_ocr_text_every_request_in_the_window_is_flagged(self):
        """Contents unknown: any COMPLETE request in the window may rest on it (the conservative default)."""
        code, flags = run(None)
        self.assertEqual(flags, {"case_30": ["evidence_02"], "case_31": ["evidence_02"]})
        self.assertEqual(code, 4)


class MissingEvidenceTests(unittest.TestCase):
    """Finding (2026-10-25, owner's removal test): a file listed in evidence_files.csv but missing on disk was
    skipped without a trace, so a request whose only finding was in it turned COMPLETE with exit 0. Its contents
    are unknown, exactly like an unreadable screenshot. Fixed: it now counts as unread for every request in its
    window."""

    def test_missing_listed_screenshot_counts_as_unread(self):
        code, flags = run(None, "evidence/images/connector_console_20260508.png", present=False)
        self.assertEqual(flags, {"case_30": ["evidence_02"], "case_31": ["evidence_02"]})
        self.assertEqual(code, 4)

    def test_missing_listed_snapshot_counts_as_unread(self):
        code, flags = run(None, "evidence/databases/customer_data_inventory_20260508.sql", present=False)
        self.assertEqual(flags, {"case_30": ["evidence_02"], "case_31": ["evidence_02"]})
        self.assertEqual(code, 4)


if __name__ == "__main__":
    unittest.main()
