"""Phase 3: log shapes and typing, PDF facts, OCR grounding, stale links (synthetic + dataset)."""

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import helpers  # noqa: F401
import main as pipeline
from evidence import extract_log
from evidence.common import ABSENT, OPERATION_CLAIM, PRESENT, STATE_READBACK, ShapeError
from evidence.log_lines import parse_line
from loaders import DATASET_DIR, EvidenceFile, load_requests

AT = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

SHAPES = {
    "bracket": '2026-03-01T10:00:00Z [INFO] [account_service] [tr-1] profile_lookup_completed: '
               'resource_id="account_901" rows="1" http_status="200"',
    "pipe": '2026-03-01T10:00:00Z | INFO | account_service | tr-1 | profile_lookup_completed | '
            'resource_id="account_901" rows="1"',
    "syslog": '2026-03-01T10:00:00Z <14>1 node-1 account_service tr-1 - - level=INFO '
              'resource_id="account_901" event="profile_lookup_completed" rows="1"',
    "kv": '2026-03-01T10:00:00Z INFO service=account_service event=profile_lookup_completed '
          'resource_id="account_901" rows="1"',
    "json": '2026-03-01T10:00:00Z {"severity":"INFO","service":"account_service","trace_id":"tr-1",'
            '"event":"profile_lookup_completed","resource_id":"account_901","rows":1}',
    "cloud": '2026-03-01T10:00:00Z requestId=tr-1 level=INFO function=account_service '
             'message="resource_id=\\"account_901\\" event=\\"profile_lookup_completed\\" rows=\\"1\\""',
}


def _extract(lines):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "x.log"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return extract_log.extract(EvidenceFile("ev_t", "logs/x.log", "account_service", AT), path)


class LogLineTest(unittest.TestCase):
    def test_every_shape_parses_to_the_same_event(self):
        for shape, line in SHAPES.items():
            with self.subTest(shape):
                ll = parse_line(line)
                self.assertEqual(ll.shape, shape)
                self.assertEqual((ll.service, ll.event, ll.fields["resource_id"]),
                                 ("account_service", "profile_lookup_completed", "account_901"))
                self.assertEqual(ll.at, AT)

    def test_unknown_shape_raises(self):
        for line in ("no timestamp here", "2026-03-01T10:00:00Z free text without pairs",
                     "2026-03-01T10:00:00Z | INFO | only | three"):
            with self.subTest(line), self.assertRaises(ShapeError):
                parse_line(line)

    def test_unknown_event_is_a_coverage_error(self):
        with self.assertRaises(ShapeError):
            _extract(['2026-03-01T10:00:00Z INFO service=account_service event=profile_teleported '
                      'resource_id="account_901"'])


class LogTypingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = _extract([
            '2026-03-01T10:00:00Z | INFO | account_service | tr-9 | profile_lookup_started | '
            'lookup_key="Ana.Test@example.org"',
            '2026-03-01T10:00:01Z | INFO | account_service | tr-9 | connection_acquired | '
            'pool="account_service_failover"',
            '2026-03-01T10:00:02Z | INFO | account_service | tr-9 | profile_lookup_completed | '
            'resource_id="account_901" rows="0" http_status="404"',
            '2026-03-01T10:00:03Z | INFO | account_service | tr-8 | delete_completed | '
            'resource_id="account_902" lookup_key="user_77"',
            '2026-03-01T10:00:04Z | INFO | account_service | tr-7 | cache_lookup | key="k"',
        ])
        cls.obs = {o.resource_id: o for o in cls.out.observations}

    def test_trace_start_key_links_the_read_back(self):
        obs = self.obs["account_901"]
        self.assertEqual(obs.assertion, STATE_READBACK)
        self.assertIn("ana.test@example.org", obs.link_ids.emails)
        self.assertEqual(obs.state_observed_at.second, 2)
        self.assertEqual(obs.available_at, AT)

    def test_pool_names_the_physical_copy(self):
        self.assertEqual(self.obs["account_901"].physical_copy, "failover")

    def test_404_is_absent_without_exposure(self):
        obs = self.obs["account_901"]
        self.assertEqual(obs.exists, ABSENT)
        self.assertIsNone(obs.exposed_ids)

    def test_success_line_is_only_a_claim(self):
        obs = self.obs["account_902"]
        self.assertEqual(obs.assertion, OPERATION_CLAIM)
        self.assertIsNone(obs.exists)

    def test_noise_is_counted_not_dropped(self):
        self.assertEqual(self.out.skipped.get("noise:connection_acquired"), 1)
        self.assertEqual(self.out.skipped.get("noise:cache_lookup"), 1)
        self.assertEqual(self.out.rows_parsed, 5)


class DatasetEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = pipeline.build_context()
        cls.store = cls.ctx.store
        cls.requests = {r.case_id: r for r in load_requests(DATASET_DIR / "sample_deletion_requests.csv")}

    def test_pdf_alias_names_the_resource(self):
        # evidence_18 prints a statement number; the catalog maps it to export_1842.
        obs = [o for o in self.store.for_resource("export_1842", datetime.max.replace(tzinfo=UTC))
               if o.file_id == "evidence_18"]
        self.assertEqual(len(obs), 1)
        self.assertEqual((obs[0].source_kind, obs[0].exists), ("pdf", PRESENT))

    def test_pdf_without_resource_id_is_counted(self):
        item = next(f for f in self.store.coverage.files if f.file_id == "evidence_27")
        self.assertEqual(item.skipped, {"document without a resource id": 1})

    def test_ocr_is_grounding_only(self):
        pngs = {f.file_id for f in self.store.coverage.files if f.fmt == "png"}
        self.assertEqual(len(pngs), 11)
        self.assertFalse(any(o.file_id in pngs for o in self.store.observations.values()))
        if not self.store.grounding:
            self.skipTest("Tesseract is not installed")
        self.assertEqual(set(self.store.grounding), pngs)

    def test_stale_link_gets_no_step(self):
        # tombstone_17 is linked only by a catalog row from before the request and no file states it.
        result = pipeline.run_case(self.requests["case_17"], self.ctx)
        self.assertIn("stale_link:tombstone_17", result.flags)
        self.assertNotIn("tombstone_17", {s["resource_id"] for s in result.steps})


if __name__ == "__main__":
    unittest.main()
