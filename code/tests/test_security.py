import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from code import cache
from code.evidence import _safe_evidence_path, parse_sql_evidence
from code.main import _write_output_atomic


class SecurityHardeningTests(unittest.TestCase):
    def test_manifest_path_cannot_escape_dataset(self):
        with self.assertRaisesRegex(ValueError, "escapes dataset"):
            _safe_evidence_path(Path("dataset"), "../AGENTS.md")

    def test_sql_snapshot_cannot_attach_another_database(self):
        path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sql", dir=".", delete=False, encoding="utf-8"
            ) as handle:
                handle.write("ATTACH DATABASE ':memory:' AS escaped;")
                path = Path(handle.name)
            identity = {
                "user_id": "user_test", "all_emails": [],
                "all_phones": [], "all_email_hashes": [],
            }
            with self.assertRaises(sqlite3.DatabaseError):
                parse_sql_evidence(path, identity)
        finally:
            if path:
                path.unlink(missing_ok=True)

    def test_non_object_cache_is_treated_as_empty(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "cache.json"
            path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
            with patch.object(cache, "CACHE_PATH", path):
                self.assertIsNone(cache.get("key"))
                cache.set("key", "value")
                self.assertEqual(cache.get("key"), "value")

    def test_atomic_output_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "output.csv"
            rows = [{"case_id": "case_1", "deletion_status": "NOT_APPLICABLE", "steps_json": "[]"}]
            _write_output_atomic(path, rows)
            self.assertTrue(path.is_file())
            self.assertFalse(path.with_suffix(".csv.tmp").exists())
