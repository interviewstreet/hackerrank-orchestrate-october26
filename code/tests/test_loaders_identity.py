import hashlib
import unittest
from datetime import timezone

import helpers  # noqa: F401  (sets sys.path)
from identity import FutureDataError, IdentityIndex
from loaders import (AuditEntry, Dataset, Identity, email_hash, email_hash_match_report, load_dataset,
                     load_requests, DATASET_DIR, normalize_email, normalize_phone, parse_ts)


class EmailHashTest(unittest.TestCase):
    def test_hash_is_sha256_of_normalized_email(self):
        expected = hashlib.sha256(b"amina.elmasri@gmail.com").hexdigest()
        self.assertEqual(email_hash("  Amina.ElMasri@GMAIL.com \n"), expected)
        # Value recorded for user_01 in dataset/user_identities.csv.
        self.assertEqual(expected, "d4e1f59abcf9a1e0cfdc7c27ad6c07ed4ff88b326a16ed5eed5ec6bc31618c93")

    def test_dataset_hashes_all_match(self):
        report = email_hash_match_report(load_dataset())
        for source, (matched, total) in report.items():
            self.assertGreater(total, 0, source)
            self.assertEqual(matched, total, source)

    def test_normalizers(self):
        self.assertEqual(normalize_email(" A@B.COM "), "a@b.com")
        self.assertEqual(normalize_phone("+44 7700 900-880"), "+447700900880")


class TimeTest(unittest.TestCase):
    def test_parse_ts_is_aware_utc(self):
        dt = parse_ts("2026-09-03T11:30:00Z")
        self.assertIs(dt.tzinfo, timezone.utc)
        self.assertEqual(parse_ts("2026-09-03T13:30:00+02:00"), dt)
        self.assertEqual(parse_ts("2026-09-03T11:30:00"), dt)  # naive input is UTC
        self.assertIsNone(parse_ts(""))


def _ts(text):
    return parse_ts(text)


def _dataset():
    """user_a: email old@x -> mid@x (2026-03) -> new@x (2026-06); phone change 2026-08."""
    ident = Identity("user_a", "Ana Test", "new@x.com", "+1 555 0002", email_hash("new@x.com"),
                     _ts("2026-08-01T00:00:00Z"))
    other = Identity("user_b", "Bo Test", "b@x.com", "+1 555 0100", email_hash("b@x.com"),
                     _ts("2026-01-01T00:00:00Z"))
    log = [
        AuditEntry("audit_1", "user_a", _ts("2026-03-01T00:00:00Z"), "email", "old@x.com", "mid@x.com"),
        AuditEntry("audit_2", "user_a", _ts("2026-03-01T00:00:00Z"), "email_hash",
                   email_hash("old@x.com"), email_hash("mid@x.com")),
        AuditEntry("audit_3", "user_a", _ts("2026-06-01T00:00:00Z"), "email", "mid@x.com", "new@x.com"),
        AuditEntry("audit_4", "user_a", _ts("2026-06-01T00:00:00Z"), "email_hash",
                   email_hash("mid@x.com"), email_hash("new@x.com")),
        AuditEntry("audit_5", "user_a", _ts("2026-08-01T00:00:00Z"), "phone", "+1 555 0001", "+1 555 0002"),
    ]
    return Dataset(identities=[ident, other], audit_log=log)


class AsOfIdentityTest(unittest.TestCase):
    def setUp(self):
        self.idx = IdentityIndex(_dataset())

    def test_history_change_as_of_after_all_changes(self):
        s = self.idx.resolve("OLD@x.com", _ts("2026-09-01T00:00:00Z"))
        self.assertEqual(s.user_id, "user_a")
        self.assertEqual(s.matched_via, "historical")
        self.assertEqual(s.current_email, "new@x.com")
        self.assertEqual(s.emails, ["new@x.com", "mid@x.com", "old@x.com"])  # 2-step chain
        self.assertEqual(s.phones, ["+1 555 0002", "+1 555 0001"])
        self.assertEqual(set(s.email_hashes), {email_hash(e) for e in s.emails})
        self.assertEqual(s.audit_ids, ["audit_1", "audit_2", "audit_3", "audit_4", "audit_5"])

    def test_as_of_before_later_change_ignores_future_values(self):
        as_of = _ts("2026-04-01T00:00:00Z")
        s = self.idx.resolve("mid@x.com", as_of)
        self.assertEqual(s.current_email, "mid@x.com")
        self.assertEqual(s.matched_via, "current")
        self.assertNotIn("new@x.com", s.emails)
        self.assertNotIn(email_hash("new@x.com"), s.email_hashes)
        self.assertEqual(s.current_phone, "+1 555 0001")
        self.assertNotIn("+1 555 0002", s.phones)
        self.assertTrue(all(a in ("audit_1", "audit_2") for a in s.audit_ids))
        self.assertIn("future_changes_ignored", s.flags)
        # A value that only appears after as_of cannot resolve.
        self.assertIsNone(self.idx.resolve("new@x.com", as_of))

    def test_cutoff_is_inclusive(self):
        s = self.idx.resolve("new@x.com", _ts("2026-06-01T00:00:00Z"))
        self.assertEqual(s.current_email, "new@x.com")

    def test_guard_rejects_future_audit_rows(self):
        idx = IdentityIndex(_dataset())
        as_of = _ts("2026-04-01T00:00:00Z")
        original = idx._field_view

        def leaky(user_id, field_name, when):
            view = original(user_id, field_name, when)
            view.used = list(idx.changes[user_id])  # simulate a bug that leaks later rows
            return view

        idx._field_view = leaky
        with self.assertRaises(FutureDataError):
            idx.subject("user_a", as_of)

    def test_unknown_email(self):
        self.assertIsNone(self.idx.resolve("nobody@x.com", _ts("2026-09-01T00:00:00Z")))


class DatasetIdentityTest(unittest.TestCase):
    def test_all_requests_resolve_to_one_user(self):
        idx = IdentityIndex(load_dataset())
        for name in ("deletion_requests.csv", "sample_deletion_requests.csv"):
            for req in load_requests(DATASET_DIR / name):
                s = idx.resolve(req.email, req.audit_at)
                self.assertIsNotNone(s, req.case_id)
                self.assertFalse([f for f in s.flags if f.startswith("ambiguous")], req.case_id)


if __name__ == "__main__":
    unittest.main()
