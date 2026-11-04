"""
test_identity_resolver.py — unit tests for IdentityResolver.

Run from the repo root with:
    python3 -m pytest code/test_identity_resolver.py -v
or:
    python3 code/test_identity_resolver.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import sys
import os
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Allow importing sibling modules when run directly
sys.path.insert(0, str(Path(__file__).parent))

from identity_resolver import IdentityResolver, _sha256
from models import IdentityBundle

# ---------------------------------------------------------------------------
# Helpers — build small in-memory CSV strings for unit tests
# ---------------------------------------------------------------------------

IDENTITIES_CSV = """\
user_id,name,email,phone,email_hash,updated_at
user_01,Alice Smith,alice@example.com,+1-555-0001,hash_alice_current,2026-01-01T00:00:00Z
user_02,Bob Jones,bob@example.com,+1-555-0002,hash_bob_current,2026-01-01T00:00:00Z
user_03,Carol Lee,carol@example.com,+1-555-0003,hash_carol_current,2026-01-01T00:00:00Z
"""

# user_01 changed email twice: old1 → old2 → alice@example.com (current)
# user_02 changed phone once
AUDIT_CSV = """\
audit_id,user_id,event_time,field_name,old_value,new_value
audit_01,user_01,2025-06-01T00:00:00Z,email,alice-old1@example.com,alice-old2@example.com
audit_02,user_01,2025-12-01T00:00:00Z,email,alice-old2@example.com,alice@example.com
audit_03,user_01,2025-12-01T00:00:00Z,email_hash,hash_alice_old2,hash_alice_current
audit_04,user_01,2025-06-01T00:00:00Z,email_hash,hash_alice_old1,hash_alice_old2
audit_05,user_02,2025-03-01T00:00:00Z,phone,+1-555-9999,+1-555-0002
"""


def _make_resolver(identities: str = IDENTITIES_CSV, audit: str = AUDIT_CSV) -> IdentityResolver:
    """Write temp CSV strings to temp files and build a resolver."""
    import tempfile, os

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f1:
        f1.write(identities)
        ids_path = f1.name

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f2:
        f2.write(audit)
        audit_path = f2.name

    try:
        resolver = IdentityResolver(ids_path, audit_path)
    finally:
        os.unlink(ids_path)
        os.unlink(audit_path)

    return resolver


# ---------------------------------------------------------------------------
# Tests — unit (synthetic data)
# ---------------------------------------------------------------------------

class TestCurrentEmailLookup(unittest.TestCase):
    """Email exactly matches the current snapshot."""

    def setUp(self):
        self.resolver = _make_resolver()

    def test_exact_match_returns_bundle(self):
        bundle = self.resolver.resolve("alice@example.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")

    def test_returns_identity_bundle_type(self):
        bundle = self.resolver.resolve("bob@example.com")
        self.assertIsInstance(bundle, IdentityBundle)

    def test_current_fields_populated(self):
        bundle = self.resolver.resolve("alice@example.com")
        self.assertEqual(bundle.current_name, "Alice Smith")
        self.assertEqual(bundle.current_phone, "+1-555-0001")
        self.assertEqual(bundle.current_email_hash, "hash_alice_current")

    def test_unknown_email_returns_none(self):
        bundle = self.resolver.resolve("nobody@example.com")
        self.assertIsNone(bundle)


class TestCaseNormalisation(unittest.TestCase):
    """Emails supplied in upper/mixed case must still resolve."""

    def setUp(self):
        self.resolver = _make_resolver()

    def test_uppercase_current_email(self):
        bundle = self.resolver.resolve("ALICE@EXAMPLE.COM")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")

    def test_mixed_case_current_email(self):
        bundle = self.resolver.resolve("Bob@Example.Com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_02")

    def test_uppercase_historical_email(self):
        bundle = self.resolver.resolve("ALICE-OLD1@EXAMPLE.COM")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")

    def test_request_email_preserved_as_supplied(self):
        """The original (un-normalised) email is stored verbatim."""
        raw = "ALICE@EXAMPLE.COM"
        bundle = self.resolver.resolve(raw)
        self.assertEqual(bundle.request_email, raw)


class TestHistoricalEmailLookup(unittest.TestCase):
    """Email matches a historical old_value in the audit log."""

    def setUp(self):
        self.resolver = _make_resolver()

    def test_first_historical_email_resolves(self):
        bundle = self.resolver.resolve("alice-old1@example.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")

    def test_intermediate_historical_email_resolves(self):
        bundle = self.resolver.resolve("alice-old2@example.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")

    def test_historical_resolve_returns_current_identifiers(self):
        """Even when resolved via old email, current fields come from snapshot."""
        bundle = self.resolver.resolve("alice-old1@example.com")
        self.assertEqual(bundle.current_email, "alice@example.com")
        self.assertEqual(bundle.current_name, "Alice Smith")

    def test_historical_emails_collected(self):
        bundle = self.resolver.resolve("alice@example.com")
        self.assertIn("alice-old1@example.com", bundle.historical_emails)
        self.assertIn("alice-old2@example.com", bundle.historical_emails)

    def test_historical_hashes_collected(self):
        bundle = self.resolver.resolve("alice@example.com")
        self.assertIn("hash_alice_old1", bundle.historical_email_hashes)
        self.assertIn("hash_alice_old2", bundle.historical_email_hashes)

    def test_no_history_user_has_empty_lists(self):
        bundle = self.resolver.resolve("carol@example.com")
        self.assertEqual(bundle.historical_emails, [])
        self.assertEqual(bundle.historical_phones, [])
        self.assertEqual(bundle.historical_email_hashes, [])

    def test_historical_phone_collected(self):
        bundle = self.resolver.resolve("bob@example.com")
        self.assertIn("+1-555-9999", bundle.historical_phones)


class TestAllEmails(unittest.TestCase):
    """all_emails() returns current + historical, deduped, lowercased."""

    def setUp(self):
        self.resolver = _make_resolver()

    def test_all_emails_includes_current(self):
        bundle = self.resolver.resolve("alice@example.com")
        self.assertIn("alice@example.com", bundle.all_emails())

    def test_all_emails_includes_historical(self):
        bundle = self.resolver.resolve("alice@example.com")
        emails = bundle.all_emails()
        self.assertIn("alice-old1@example.com", emails)
        self.assertIn("alice-old2@example.com", emails)

    def test_all_emails_no_duplicates(self):
        bundle = self.resolver.resolve("alice@example.com")
        emails = bundle.all_emails()
        self.assertEqual(len(emails), len(set(emails)))

    def test_no_history_all_emails_has_one_entry(self):
        bundle = self.resolver.resolve("carol@example.com")
        self.assertEqual(bundle.all_emails(), ["carol@example.com"])

class TestAuditAtFiltering(unittest.TestCase):
    """
    When audit_at is supplied, entries after that timestamp must NOT appear
    in the returned identifier bundle.  The user must still be resolved
    (the lookup tables use the full history regardless).
    """

    # user_01 changed email at 2025-06-01 and 2025-12-01.
    # If audit_at = 2025-09-01, only the 2025-06-01 entry should be visible.
    EARLY_AUDIT_AT = datetime(2025, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    LATE_AUDIT_AT  = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.resolver = _make_resolver()

    def test_entries_after_audit_at_excluded_from_bundle(self):
        """With early audit_at, the second email change is hidden."""
        bundle = self.resolver.resolve("alice@example.com", audit_at=self.EARLY_AUDIT_AT)
        self.assertIsNotNone(bundle)
        # 2025-12-01 change (alice-old2 -> alice) is after 2025-09-01 → excluded
        self.assertNotIn("alice-old2@example.com", bundle.historical_emails)
        # 2025-06-01 change (alice-old1 -> alice-old2) is before → included
        self.assertIn("alice-old1@example.com", bundle.historical_emails)

    def test_entries_before_audit_at_included_in_bundle(self):
        """With late audit_at, all historical entries are included."""
        bundle = self.resolver.resolve("alice@example.com", audit_at=self.LATE_AUDIT_AT)
        self.assertIsNotNone(bundle)
        self.assertIn("alice-old1@example.com", bundle.historical_emails)
        self.assertIn("alice-old2@example.com", bundle.historical_emails)

    def test_user_still_resolved_via_historical_email_regardless_of_audit_at(self):
        """
        Even if the email-change that maps old1→old2 happened BEFORE audit_at,
        the lookup tables are built from the full history, so alice-old1 still
        resolves to user_01 (the user identity doesn't change).
        """
        # With a very early audit_at that excludes the 2025-06-01 entry from the
        # identifier bundle, the resolver must still find the user.
        very_early = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bundle = self.resolver.resolve("alice-old1@example.com", audit_at=very_early)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_01")


class TestFutureIdentifiersExcluded(unittest.TestCase):
    """
    If the snapshot's current email/phone only became current after audit_at,
    the bundle must report the value held at audit_at instead, and the
    future value must not appear anywhere in the bundle.
    """

    # alice: old2 -> alice@example.com at 2025-12-01 (hash row too)
    # bob:   +1-555-9999 -> +1-555-0002 at 2025-03-01
    BEFORE_ALICE_CHANGE = datetime(2025, 9, 1, tzinfo=timezone.utc)
    BEFORE_BOB_CHANGE = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def setUp(self):
        self.resolver = _make_resolver()

    def test_future_email_not_current(self):
        b = self.resolver.resolve("alice@example.com", audit_at=self.BEFORE_ALICE_CHANGE)
        self.assertEqual(b.current_email, "alice-old2@example.com")
        self.assertNotIn("alice@example.com", b.all_emails())
        self.assertIn("alice-old1@example.com", b.all_emails())

    def test_future_email_hash_not_current(self):
        b = self.resolver.resolve("alice@example.com", audit_at=self.BEFORE_ALICE_CHANGE)
        self.assertEqual(b.current_email_hash, "hash_alice_old2")
        self.assertNotIn("hash_alice_current", b.all_email_hashes())

    def test_future_phone_not_current(self):
        b = self.resolver.resolve("bob@example.com", audit_at=self.BEFORE_BOB_CHANGE)
        self.assertEqual(b.current_phone, "+1-555-9999")
        self.assertNotIn("+1-555-0002", b.all_phones())

    def test_hash_recomputed_when_no_hash_row(self):
        audit = AUDIT_CSV + (
            "audit_06,user_03,2026-01-15T00:00:00Z,email,carol-old@example.com,carol@example.com\n"
        )
        r = _make_resolver(audit=audit)
        b = r.resolve("carol@example.com", audit_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(b.current_email, "carol-old@example.com")
        self.assertEqual(b.current_email_hash, _sha256("carol-old@example.com"))

    def test_no_audit_at_keeps_snapshot(self):
        b = self.resolver.resolve("alice@example.com")
        self.assertEqual(b.current_email, "alice@example.com")
        self.assertEqual(b.current_email_hash, "hash_alice_current")


class TestComputedEmailHashes(unittest.TestCase):
    """
    SHA-256 of each historical email is added to the bundle so that
    all_email_hashes() covers every address the subject ever used.
    """

    def setUp(self):
        self.resolver = _make_resolver()

    def test_sha256_of_historical_email_in_bundle(self):
        """even when no email_hash audit row exists, the computed hash is present."""
        # In our synthetic audit CSV, audit_01 records old email alice-old1 but
        # there is no matching email_hash row for alice-old1.
        bundle = self.resolver.resolve("alice@example.com")
        expected_hash = _sha256("alice-old1@example.com")
        self.assertIn(expected_hash, bundle.historical_email_hashes)

    def test_stored_and_computed_hashes_no_duplicates(self):
        """No hash appears twice even when both stored and computed."""
        bundle = self.resolver.resolve("alice@example.com")
        hashes = bundle.all_email_hashes()
        self.assertEqual(len(hashes), len(set(hashes)))



DATASET_DIR = Path(__file__).parent.parent / "dataset"
IDS_PATH    = DATASET_DIR / "user_identities.csv"
AUDIT_PATH  = DATASET_DIR / "user_audit_log.csv"
REQ_PATH    = DATASET_DIR / "deletion_requests.csv"


@unittest.skipUnless(IDS_PATH.exists(), "Real dataset not present")
class TestRealDataset(unittest.TestCase):
    """Integration tests against the actual participant dataset."""

    @classmethod
    def setUpClass(cls):
        cls.resolver = IdentityResolver(IDS_PATH, AUDIT_PATH)
        cls.requests = list(csv.DictReader(open(REQ_PATH, encoding="utf-8")))

    def test_all_518_cases_attempted(self):
        results = self.resolver.resolve_all(self.requests)
        self.assertEqual(len(results), 518)

    def test_resolution_rate(self):
        """Expect a high resolution rate; none should be zero."""
        results = self.resolver.resolve_all(self.requests)
        resolved = sum(1 for _, b in results if b is not None)
        rate = resolved / len(results)
        print(f"\n  Resolution rate: {resolved}/{len(results)} = {rate:.1%}")
        self.assertGreater(rate, 0.80, "Resolution rate below 80% — investigate")

    def test_known_current_email(self):
        """case_45: oliver-bennett@gmail.com is a current email."""
        bundle = self.resolver.resolve("oliver-bennett@gmail.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.current_email, "oliver-bennett@gmail.com")

    def test_historical_email_javier(self):
        """case_43: javier.r940897@outlook.com is a historical email of user_41."""
        bundle = self.resolver.resolve("javier.r940897@outlook.com")
        self.assertIsNotNone(bundle, "Should resolve via historical audit log")
        self.assertEqual(bundle.user_id, "user_41")
        self.assertEqual(bundle.current_email, "javier.r9408@outlook.com")

    def test_all_caps_email(self):
        """case_38: SIPHO.MOKOENA@GMAIL.COM should resolve despite being uppercase."""
        bundle = self.resolver.resolve("SIPHO.MOKOENA@GMAIL.COM")
        self.assertIsNotNone(bundle, "ALL-CAPS email should resolve")
        self.assertEqual(bundle.user_id, "user_36")

    def test_all_caps_historical_email(self):
        """case_40: CHOI.JIHOON94@GMAIL.COM — historical email, uppercase."""
        bundle = self.resolver.resolve("CHOI.JIHOON94@GMAIL.COM")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_38")

    def test_historical_email_abena(self):
        """case_37: abena.o189491@zoho.com — historical email that changed twice."""
        bundle = self.resolver.resolve("abena.o189491@zoho.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_35")

    def test_historical_email_lucas_souza(self):
        """case_41: lucas-souza95@gmail.com — old email, now lucas-souza@gmail.com."""
        bundle = self.resolver.resolve("lucas-souza95@gmail.com")
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle.user_id, "user_39")

    def test_unresolvable_returns_none(self):
        bundle = self.resolver.resolve("definitely.not.a.real.user@nowhere.invalid")
        self.assertIsNone(bundle)

    def test_resolved_bundles_have_user_id(self):
        results = self.resolver.resolve_all(self.requests)
        for req, bundle in results:
            if bundle is not None:
                self.assertTrue(bundle.user_id.startswith("user_"),
                                f"{req['case_id']}: user_id looks wrong: {bundle.user_id!r}")

    def test_all_emails_always_includes_current(self):
        results = self.resolver.resolve_all(self.requests)
        for req, bundle in results:
            if bundle is not None:
                self.assertIn(bundle.current_email.lower(), bundle.all_emails(),
                              f"{req['case_id']}: current email missing from all_emails()")


if __name__ == "__main__":
    unittest.main(verbosity=2)
