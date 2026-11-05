"""
test_export_web_data.py — tests for export_web_data.py (masking + JSON files).

Run from the repo root with:
    python3 code/test_export_web_data.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import audit_db
import export_web_data as ex
from models import ClassificationResult
from test_audit_db import CASE, DECISION, EVIDENCE, STEPS, make_classifier, make_identity

REPO_ROOT = Path(__file__).parent.parent
REAL_EXPORT = REPO_ROOT / "web" / "public" / "data"


class TestMasking(unittest.TestCase):

    def test_mask_email(self):
        self.assertEqual(ex.mask_email("javier.r940897@outlook.com"), "ja****@outlook.com")
        self.assertEqual(ex.mask_email("ab@x.io"), "a****@x.io")
        self.assertEqual(ex.mask_email("a@x.io"), "a****@x.io")
        self.assertEqual(ex.mask_email(""), "")
        self.assertEqual(ex.mask_email("not-an-email"), "****")

    def test_mask_phone_keeps_last_two_digits(self):
        self.assertEqual(ex.mask_phone("+33 6 24 34 80 16"), "+** * ** ** ** 16")
        self.assertEqual(ex.mask_phone(""), "")

    def test_mask_name(self):
        self.assertEqual(ex.mask_name("Ana  Lima"), "A. L.")
        self.assertEqual(ex.mask_name(""), "")

    def test_mask_hash(self):
        self.assertEqual(ex.mask_hash("0123456789abcdef" * 4), "01234567…")
        self.assertEqual(ex.mask_hash("h_short"), "****")
        self.assertEqual(ex.mask_hash(""), "")

    def test_mask_identifier(self):
        self.assertEqual(ex.mask_identifier("email:ana.l@x.com"), "email:an****@x.com")
        self.assertEqual(ex.mask_identifier("phone:+1 555 0100"), "phone:+* *** **00")
        self.assertEqual(ex.mask_identifier("user_id:user_9"), "user_id:user_9")
        self.assertEqual(ex.mask_identifier("secret"), "****")
        self.assertEqual(ex.mask_identifier("weird:value"), "weird:****")

    def test_mask_text(self):
        text = "I am Ana Lima, mail ana.l@x.com or call +55 11 91234 5678."
        got = ex.mask_text(text, names=["Ana Lima"], phones=["+55 11 91234 5678"])
        self.assertEqual(got, "I am A. L., mail an****@x.com or call +** ** ***** **78.")


class TestExport(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db_path, self.out = root / "audit.db", root / "data"
        conn = audit_db.connect(self.db_path)
        text_case = dict(CASE, request_text="I am Ana Lima (old.mail@example.com). Delete it.")
        audit_db.save_case(conn, text_case, our_status="INCOMPLETE",
                           classification="IS_DELETION", classifier=self.leaky_classifier(),
                           identity=make_identity(),
                           evidence=EVIDENCE, decision=DECISION, steps=STEPS)
        audit_db.save_case(conn, dict(CASE, case_id="case_t10", email="zoe@ex.org",
                                      reported_status="NOT_STARTED"),
                           our_status="NOT_APPLICABLE", classification="NOT_APPLICABLE",
                           classifier=ClassificationResult(
                               "NOT_APPLICABLE", "HIGH", [], language="fr",
                               signals=["opt_out: publicité"],
                               reason="Not a deletion request: the person asks to stop "
                                      "marketing messages (“publicité”)."))
        audit_db.save_case(conn, dict(CASE, case_id="case_t2", email="bo@ex.org"),
                           our_status="COMPLETE", classification="IS_DELETION")
        conn.close()
        self.summary = ex.export(self.db_path, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def leaky_classifier():
        """A reason that quotes the person's name and email must still be masked."""
        c = make_classifier()
        c.signals = ["deletion: delete", "keep: Ana Lima"]
        c.reason = "Deletion request from Ana Lima (old.mail@example.com)."
        return c

    def load(self, rel):
        return json.loads((self.out / rel).read_text(encoding="utf-8"))

    def all_text(self):
        return "".join(p.read_text(encoding="utf-8") for p in self.out.rglob("*.json"))

    def test_files_written(self):
        names = sorted(p.relative_to(self.out).as_posix() for p in self.out.rglob("*.json"))
        self.assertEqual(names, ["cases.json", "cases/case_t1.json", "cases/case_t10.json",
                                 "cases/case_t2.json", "summary.json"])

    def test_summary(self):
        s = self.load("summary.json")
        self.assertEqual(s, self.summary)
        self.assertEqual(s["total_cases"], 3)
        self.assertEqual(s["status_counts"],
                         {"COMPLETE": 1, "INCOMPLETE": 1, "NOT_APPLICABLE": 1})
        self.assertEqual(s["reported_status_counts"],
                         {"COMPLETE": 2, "PARTIALLY_COMPLETE": 0, "NOT_STARTED": 1})
        self.assertEqual(s["reported_vs_ours"]["COMPLETE"],
                         {"COMPLETE": 1, "INCOMPLETE": 1, "NOT_APPLICABLE": 0})
        self.assertEqual(s["reported_vs_ours"]["NOT_STARTED"]["NOT_APPLICABLE"], 1)
        self.assertEqual(s["reported_complete_but_not_complete"], 1)
        # case_t2 was saved without a classifier result -> "unknown"
        self.assertEqual(s["language_counts"], {"en": 1, "es": 0, "pt": 0, "fr": 1,
                                                "ja": 0, "ko": 0, "unknown": 1})

    def test_case_list_sorted_numerically_and_masked(self):
        lst = self.load("cases.json")
        self.assertEqual([c["case_id"] for c in lst], ["case_t1", "case_t2", "case_t10"])
        self.assertEqual(lst[0], {"case_id": "case_t1", "email": "ol****@example.com",
                                  "reported_status": "COMPLETE", "our_status": "INCOMPLETE",
                                  "classification": "IS_DELETION"})

    def test_case_detail(self):
        c = self.load("cases/case_t1.json")
        self.assertEqual(c["request_text"], "I am A. L. (ol****@example.com). Delete it.")
        self.assertEqual((c["language"], c["confidence"]), ("en", "HIGH"))
        self.assertEqual(c["matched_signals"], ["deletion: delete", "keep: A. L."])
        self.assertEqual(c["reason"], "Deletion request from A. L. (ol****@example.com).")
        self.assertEqual(c["user_id"], "user_9")
        self.assertEqual(c["identities"][0], {"kind": "email", "value": "ne****@example.com",
                                              "is_historical": False, "audit_id": "audit_7"})
        self.assertIn({"kind": "phone", "value": "+** ** ***** **78", "is_historical": False,
                       "audit_id": ""}, c["identities"])
        self.assertEqual({h["matched_identifier"] for h in c["evidence_hits"]},
                         {"email:ne****@example.com", "name:a. l."})
        self.assertEqual(c["resources"][0]["satisfied"], False)
        self.assertEqual(c["resources"][0]["evidence_ids"], ["evidence_1"])
        self.assertIs(c["flows"][0]["active_at_audit"], True)
        self.assertEqual([t["event"] for t in c["timeline"]], ["DELETE", "SYNC"])
        self.assertEqual([s["step_no"] for s in c["steps"]], [1, 2])
        self.assertEqual(set(c["steps"][0]), {"step_no", "phase", "system_id", "resource_id",
                                              "operation", "state", "evidence_id"})

    def test_case_without_results_has_empty_lists(self):
        c = self.load("cases/case_t10.json")
        self.assertIsNone(c["user_id"])
        self.assertEqual((c["language"], c["matched_signals"]), ("fr", ["opt_out: publicité"]))
        for k in ("identities", "evidence_hits", "resources", "flows", "timeline", "steps"):
            self.assertEqual(c[k], [])

    def test_no_raw_identifier_anywhere(self):
        text = self.all_text().lower()
        for raw in ("old.mail@example.com", "new.mail@example.com", "ana lima",
                    "91234 5678", "zoe@ex.org", "bo@ex.org", "h_new", "h_old"):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, text)

    def test_rerun_is_identical_and_removes_stale_files(self):
        before = {p: p.read_bytes() for p in self.out.rglob("*.json")}
        (self.out / "cases" / "case_gone.json").write_text("{}")
        ex.export(self.db_path, self.out)
        after = {p: p.read_bytes() for p in self.out.rglob("*.json")}
        self.assertEqual(after, before)

    def test_missing_db_gives_clear_error(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            ex.export(Path(self.tmp.name) / "nope.db", self.out)
        self.assertIn("run python3 code/main.py first", str(ctx.exception))

    def test_export_does_not_modify_db(self):
        before = self.db_path.read_bytes()
        ex.export(self.db_path, self.out)
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_unsafe_case_id_rejected(self):
        with self.assertRaises(ValueError):
            ex._safe_filename("../../etc/passwd")


@unittest.skipUnless((REAL_EXPORT / "summary.json").exists(),
                     "real export not present (run main.py and export_web_data.py)")
class TestRealExportIsMasked(unittest.TestCase):
    """The public files must not contain any email or phone from the dataset."""

    def test_no_dataset_email_or_phone_in_export(self):
        ids = REPO_ROOT / "dataset" / "user_identities.csv"
        audit = REPO_ROOT / "dataset" / "user_audit_log.csv"
        secrets: set[str] = set()
        with open(ids, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                secrets.update(v.lower() for k, v in r.items()
                               if k in ("email", "phone") and v)
        with open(audit, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["field_name"] in ("email", "phone"):
                    secrets.update(v.lower() for v in (r["old_value"], r["new_value"]) if v)
        text = "".join(p.read_text(encoding="utf-8").lower()
                       for p in REAL_EXPORT.rglob("*.json"))
        leaked = sorted(s for s in secrets if s in text)
        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
