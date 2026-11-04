"""
test_utils.py — tests for the shared timestamp parser.

Run from the repo root with:
    python3 code/test_utils.py
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_ts, to_utc

UTC = timezone.utc


class TestParseTs(unittest.TestCase):

    def test_z_suffix(self):
        self.assertEqual(parse_ts("2026-09-26T11:00:00Z"),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_lowercase_z(self):
        self.assertEqual(parse_ts("2026-09-26T11:00:00z"),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_missing_timezone_means_utc(self):
        self.assertEqual(parse_ts("2026-09-26T11:00:00"),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_space_separator(self):
        self.assertEqual(parse_ts("2026-09-26 11:00:00"),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_date_only_is_midnight_utc(self):
        self.assertEqual(parse_ts("2026-09-26"), datetime(2026, 9, 26, tzinfo=UTC))

    def test_fractional_seconds(self):
        self.assertEqual(parse_ts("2026-09-26T11:00:00.123Z").microsecond, 123000)

    def test_other_offset_converted_to_utc(self):
        self.assertEqual(parse_ts("2026-09-26T13:00:00+02:00"),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_surrounding_spaces(self):
        self.assertEqual(parse_ts("  2026-09-26T11:00:00Z "),
                         datetime(2026, 9, 26, 11, tzinfo=UTC))

    def test_result_always_comparable(self):
        """The bug from the review: naive vs aware comparison crashed."""
        a = parse_ts("2026-09-26 11:00:00")
        b = parse_ts("2026-01-01T00:00:00Z")
        self.assertTrue(a > b)

    def test_empty_returns_none_with_warning(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertIsNone(parse_ts(value, context="case_99 audit_at"))
                self.assertIn("empty timestamp", err.getvalue())
                self.assertIn("case_99 audit_at", err.getvalue())

    def test_garbage_raises_clear_error(self):
        with self.assertRaises(ValueError) as ctx:
            parse_ts("next tuesday", context="case_99 audit_at")
        self.assertIn("next tuesday", str(ctx.exception))
        self.assertIn("case_99 audit_at", str(ctx.exception))


class TestToUtc(unittest.TestCase):

    def test_naive_becomes_utc(self):
        self.assertEqual(to_utc(datetime(2026, 1, 1)).tzinfo, UTC)

    def test_aware_converted(self):
        tz = timezone(timedelta(hours=9))
        self.assertEqual(to_utc(datetime(2026, 1, 1, 9, tzinfo=tz)),
                         datetime(2026, 1, 1, 0, tzinfo=UTC))


if __name__ == "__main__":
    unittest.main(verbosity=2)
