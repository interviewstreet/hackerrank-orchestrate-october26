"""Unit tests (stdlib unittest): python3 -m unittest discover -s code/tests -t code"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ghostaudit import loaders
from ghostaudit.config import DEFAULT_DATASET_DIR as D
from ghostaudit.config import EXIT_BUDGET_EXCEEDED
from ghostaudit.engine.policy import Policy
from ghostaudit.engine.state import reconstruct
from ghostaudit.evidence import build_observation_store
from ghostaudit.evidence.logs import parse_line
from ghostaudit.identity import IdentityResolver
from ghostaudit.intent import DELETE, NON_DELETE, heuristic
from ghostaudit.llm.adapter import LLMAdapter
from ghostaudit.llm.backends import BackendResponse
from ghostaudit.llm.backends.anthropic_api import AnthropicBackend, content_blocks
from ghostaudit.llm.backends.claude_cli import parse_output
from ghostaudit.llm.budget import Budget, BudgetExceeded
from ghostaudit.llm.cache import LLMCache
from ghostaudit.llm.ledger import Ledger
from ghostaudit.models import Kind, Observation, Step
from ghostaudit.output import order_steps, steps_to_json, validate_row

logging.disable(logging.WARNING)
UTC = timezone.utc
_STORE = None


def store():
    global _STORE
    if _STORE is None:
        man = loaders.load_manifest(D / "evidence_files.csv", D)
        act = loaders.load_activity(D / "system_activity.csv")
        _STORE = build_observation_store(man, act, LLMAdapter(backend="replay"))
    return _STORE


class OutputTests(unittest.TestCase):
    def test_ordering_matches_sample_case_11(self):
        steps = [
            Step("VERIFICATION", "integration_service", "data_flow_9522", "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""),
            Step("REMEDIATION", "analytics_platform", "analytics_2034", "ANONYMIZE_RECORD", "ANONYMIZED", ""),
            Step("FINDING", "support_platform", "support_864", "REPORT_EXPOSED_PII", "PRESENT", "evidence_03"),
            Step("FINDING", "search_service", "search_052", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_03"),
            Step("FINDING", "analytics_platform", "analytics_2034", "REPORT_EXPOSED_PII", "PRESENT", "evidence_03"),
            Step("REMEDIATION", "integration_service", "data_flow_9522", "DISABLE_DATA_FLOW", "DISABLED", ""),
            Step("VERIFICATION", "security_service", "audit_record_9394", "VERIFY_RECORD_PRESENT", "PRESENT", ""),
            Step("VERIFICATION", "account_service", "account_4248", "VERIFY_RECORD_ABSENT", "ABSENT", ""),
        ]
        got = [(s.phase[0], s.resource_id) for s in order_steps(steps)]
        self.assertEqual(got, [("F", "search_052"), ("F", "analytics_2034"), ("F", "support_864"),
                               ("R", "data_flow_9522"), ("R", "analytics_2034"),
                               ("V", "account_4248"), ("V", "audit_record_9394"), ("V", "data_flow_9522")])

    def test_serialization_round_trips_sample_rows(self):
        import csv
        with open(D / "sample_output.csv", newline="", encoding="utf-8") as fh:
            for row in list(csv.DictReader(fh))[:3]:
                steps = [Step(s["phase"], s["system_id"], s["resource_id"], s["operation"], s["state"], s["evidence_id"])
                         for s in json.loads(row["steps_json"])]
                self.assertEqual(json.loads(steps_to_json(steps)), json.loads(row["steps_json"]))
                self.assertEqual(validate_row(row["case_id"], row["deletion_status"], row["steps_json"]), [])

    def test_validator_rejects_malformed(self):
        bad_state = json.dumps([{"step_no": 1, "phase": "VERIFICATION", "system_id": "a", "resource_id": "b",
                                 "operation": "VERIFY_RECORD_ABSENT", "state": "PRESENT", "evidence_id": "e"}])
        self.assertTrue(validate_row("c", "COMPLETE", bad_state))
        self.assertTrue(validate_row("c", "NOT_APPLICABLE", bad_state))
        cited_future = json.dumps([
            {"step_no": 1, "phase": "FINDING", "system_id": "a", "resource_id": "b", "operation": "REPORT_REMAINING_RECORD", "state": "PRESENT", "evidence_id": "e"},
            {"step_no": 2, "phase": "REMEDIATION", "system_id": "a", "resource_id": "b", "operation": "DELETE_RECORD", "state": "ABSENT", "evidence_id": "e"}])
        self.assertTrue(validate_row("c", "INCOMPLETE", cited_future))
        self.assertTrue(validate_row("c", "COMPLETE", "not json"))
        self.assertEqual(validate_row("c", "NOT_APPLICABLE", "[]"), [])


class LoaderTests(unittest.TestCase):
    def test_byte_order_mark_and_padded_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "req.csv"
            text = (D / "sample_deletion_requests.csv").read_text(encoding="utf-8").replace("case_id,", " case_id,", 1)
            path.write_text("\ufeff" + text, encoding="utf-8")
            self.assertEqual([c.case_id for c in loaders.load_cases(path)],
                             [c.case_id for c in loaders.load_cases(D / "sample_deletion_requests.csv")])

    def test_unreadable_visual_evidence_is_tracked(self):
        man = [e for e in loaders.load_manifest(D / "evidence_files.csv", D) if e.path.suffix == ".png"][:2]
        with mock.patch.dict(os.environ, {"GDA_VISION_OCR_FALLBACK": "0"}):
            st = build_observation_store(man, [], LLMAdapter(backend="offline"))
        self.assertEqual(sorted(f for f, _ in st.unreadable), sorted(e.file_id for e in man))
        self.assertEqual(st.observations, [])

    def test_ocr_fallback_reports_findings_only(self):
        """Without a vision result the committed OCR text is read, but the file stays 'unreadable' (no COMPLETE may
        rest on it) and no OCR record can assert an absent or clean state."""
        man = [e for e in loaders.load_manifest(D / "evidence_files.csv", D) if e.path.suffix == ".png"][:2]
        with mock.patch.dict(os.environ, {"GDA_VISION_OCR_FALLBACK": "1"}):
            st = build_observation_store(man, [], LLMAdapter(backend="offline"))
        self.assertEqual(sorted(f for f, _ in st.unreadable), sorted(e.file_id for e in man))
        self.assertTrue(st.observations)
        self.assertTrue({o.kind for o in st.observations} <= {Kind.PRESENT, Kind.FLOW_ACTIVE, Kind.RESTORE_ALLOWED,
                                                             Kind.RETAINED, Kind.LINK})

    def test_every_visual_file_has_committed_ocr_text(self):
        """The OCR cache is keyed by file sha256: a re-rendered edge PNG (e.g. after a Pillow upgrade) or a changed
        dataset image would silently lose its OCR text and its LLM transcription."""
        import hashlib
        from ghostaudit.evidence import ocr
        edge = Path(__file__).resolve().parents[1] / "evaluation" / "edge_dataset" / "main"
        for root in (D, edge):
            for ef in loaders.load_manifest(root / "evidence_files.csv", root):
                if ef.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
                    self.assertIsNotNone(ocr.cache().get(hashlib.sha256(ef.path.read_bytes()).hexdigest()), ef.path.name)

    def test_grounding_drops_ids_the_image_does_not_show(self):
        from ghostaudit.evidence import ocr
        from ghostaudit.evidence.records import RawRecord
        ef = loaders.load_manifest(D / "evidence_files.csv", D)[0]
        text = ("1] search 1874 - g.silva76,jr@gmail.com\n2] Баскир_9288 miller logistics@company.com\n"
                "3] search_428 Gabriel Silva")
        recs = [RawRecord(ef.file_id, ef.captured_at, rid, dict(f)) for rid, f in (
            ("search_1874", {"email": "g.silva76.jr@gmail.com"}),           # OCR lost "_" and read "." as ","
            ("backup_9288", {"email": "miller.logistics@company.com"}),     # Cyrillic look-alikes, lost "."
            ("export_001", {}),                                              # not in the image: invented
            ("search_428", {"email": "someone.else@example.com"}))]          # id shown, email not shown
        g = ocr.Grounding()
        kept = g.check(ef, recs, text)
        self.assertEqual([r.resource_id for r in kept], ["search_1874", "backup_9288", "search_428"])
        self.assertEqual(g.files[ef.file_id]["dropped"], ["export_001"])
        self.assertEqual(g.files[ef.file_id]["fields_removed"], ["search_428.email"])
        self.assertEqual(g.check(ef, recs[:1], None), recs[:1])  # no OCR text: nothing is dropped

    def test_output_rows_follow_the_request_file_order(self):
        ids = [c.case_id for c in loaders.load_cases(D / "deletion_requests.csv")]
        self.assertEqual(sorted(ids, key=loaders.natural_case_key), ids)
        self.assertEqual(sorted(["case_e02", "case_100", "case_e01a", "case_99", "case_e01"], key=loaders.natural_case_key),
                         ["case_99", "case_100", "case_e01", "case_e01a", "case_e02"])

    def test_unicode_equivalent_emails_normalize_alike(self):
        composed, decomposed = "josé.alvarez@example.test", "josé.alvarez@example.test"
        self.assertEqual(loaders.normalize_email(composed), loaders.normalize_email(decomposed.upper()))
        self.assertEqual(loaders.email_hash(composed), loaders.email_hash(decomposed))
        self.assertNotEqual(loaders.normalize_email(composed), loaders.normalize_email("jose.alvarez@example.test"))

    def test_manifest_paths_outside_the_dataset_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dataset"
            (root / "evidence").mkdir(parents=True)
            (root / "evidence" / "ok.log").write_text("", encoding="utf-8")
            man = root / "evidence_files.csv"
            man.write_text("file_id,file_path,origin,captured_at\n"
                           "evidence_01,evidence/ok.log,x,2026-01-01T00:00:00Z\n"
                           "evidence_02,../outside.log,x,2026-01-01T00:00:00Z\n"
                           "evidence_03,/etc/passwd,x,2026-01-01T00:00:00Z\n", encoding="utf-8")
            files = loaders.load_manifest(man, root)
            self.assertEqual([f.file_id for f in files], ["evidence_01"])


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.r = IdentityResolver(loaders.load_identities(D / "user_identities.csv"), loaders.load_audit_log(D / "user_audit_log.csv"))

    def test_historical_email_resolves_with_hash(self):
        s = self.r.resolve("minjun.kim@gmail.com")
        self.assertEqual(s.user_id, "user_12")
        self.assertIn(("email", "minjun.kim90@gmail.com"), s.identifiers)
        self.assertIn(("email_hash", loaders.email_hash("minjun.kim90@gmail.com")), s.identifiers)
        self.assertTrue(loaders.email_hash("minjun.kim90@gmail.com").startswith("44a651"))

    def test_case_insensitive_and_near_miss(self):
        self.assertEqual(self.r.resolve("SIPHO.MOKOENA@GMAIL.COM").user_id, "user_36")
        self.assertIsNone(self.r.resolve("g.silva76.jr@gmail.com"))

    def test_every_request_resolves(self):
        for f in ("deletion_requests.csv", "sample_deletion_requests.csv"):
            for c in loaders.load_cases(D / f):
                self.assertIsNotNone(self.r.resolve(c.email, c.requested_at), c.case_id)


class EvidenceTests(unittest.TestCase):
    def kinds(self, rid, eid):
        return {o.kind for o in store().by_resource(rid) if o.evidence_id == eid}

    def test_golden_facts(self):
        self.assertIn(Kind.PRESENT, self.kinds("account_005", "evidence_54"))           # failover replica drift
        self.assertIn(Kind.PRESENT, self.kinds("search_4262", "evidence_94"))           # readback hit
        obs = [o for o in store().by_resource("analytics_9914") if o.evidence_id == "evidence_01"]
        self.assertTrue(any(("email_hash", loaders.email_hash("minjun.kim90@gmail.com")) in o.identifiers for o in obs))
        self.assertEqual(obs[0].category, "MARKETING_PROFILE")
        self.assertIn(Kind.ABSENT, self.kinds("account_7566", "evidence_94"))
        self.assertIn(Kind.REDACTED, self.kinds("tombstone_440", "evidence_51"))
        self.assertIn(Kind.FLOW_ACTIVE, self.kinds("data_flow_9522", "evidence_03"))

    def test_visual_extraction_from_cache(self):
        recs = [o for o in store().by_resource("support_001") if o.evidence_id == "evidence_58"]
        self.assertTrue(recs and recs[0].category == "SUPPORT_ATTACHMENT")
        self.assertIn(("email", "priya.raman@gmail.com"), recs[0].identifiers)

    def test_no_structured_file_is_unparsed(self):
        for fid, rep in store().report.items():
            if fid.startswith("evidence_") and not rep["path"].endswith((".png", ".pdf")):
                self.assertGreater(rep.get("records", 0) + len(rep.get("coverage", [])), 0, rep)

    def test_log_formats(self):
        cloud = ('2026-06-08T09:52:27Z requestId=tr-1 level=DEBUG function=security_service message="instance=\\"s\\" '
                 'resource_id=\\"audit_record_1\\" event=\\"audit_record_read_completed\\" rows=\\"1\\""')
        f = parse_line(cloud)
        self.assertEqual((f["resource_id"], f["rows"], f["trace_id"], f["service"]), ("audit_record_1", "1", "tr-1", "security_service"))
        pipe = '2026-07-03T07:51:32Z | DEBUG | security_service | tr-5 | audit_record_read_completed | resource_id="audit_record_2" rows="1"'
        self.assertEqual(parse_line(pipe)["event"], "audit_record_read_completed")
        sysl = '2026-03-25T08:51:15Z <15>1 node-1 support_platform tr-7 - - level=DEBUG event="message_scan_started" subject_key="a@b.co"'
        self.assertEqual(parse_line(sysl)["subject_key"], "a@b.co")


class StateTests(unittest.TestCase):
    def obs(self, eid, t, kind, explicit=True):
        return Observation(eid, t, t, "search_service", "search_1", kind, None, frozenset(), "", {}, explicit)

    def test_future_observation_is_ignored(self):
        t0 = datetime(2026, 5, 1, tzinfo=UTC)
        o = [self.obs("e1", t0, Kind.ABSENT), self.obs("e2", t0 + timedelta(days=3), Kind.PRESENT)]
        st = reconstruct(o, t0 + timedelta(days=1))
        self.assertEqual((st.kind, st.evidence_id), (Kind.ABSENT, "e1"))

    def test_latest_wins_and_explicit_is_cited(self):
        t0 = datetime(2026, 5, 1, tzinfo=UTC)
        o = [self.obs("e1", t0, Kind.PRESENT), self.obs("e2", t0 + timedelta(days=1), Kind.ABSENT),
             self.obs("e3", t0 + timedelta(days=2), Kind.ABSENT, explicit=False)]
        st = reconstruct(o, t0 + timedelta(days=5))
        self.assertEqual((st.kind, st.evidence_id), (Kind.ABSENT, "e2"))

    def test_recreation_after_deletion(self):
        t0 = datetime(2026, 5, 1, tzinfo=UTC)
        o = [self.obs("e1", t0, Kind.ABSENT), self.obs("activity_9", t0 + timedelta(days=1), Kind.RECREATED)]
        self.assertEqual(reconstruct(o, t0 + timedelta(days=2)).kind, Kind.PRESENT)


class PolicyTests(unittest.TestCase):
    def test_retention(self):
        p = Policy(loaders.load_rules(D / "deletion_rules.csv"))
        at = datetime(2026, 9, 1, tzinfo=UTC)
        self.assertEqual(p.decide("security_service", "SECURITY_AUDIT_LOG", {"retention_until": "2031-01-01T00:00:00Z"}, at).treatment, "RETAIN")
        self.assertEqual(p.decide("security_service", "SECURITY_AUDIT_LOG", {"retention_until": "2026-01-01T00:00:00Z"}, at).treatment, "DELETE")
        self.assertEqual(p.decide("identity_service", None, {}, at).treatment, "REDACT")
        self.assertEqual(p.decide("analytics_platform", "MARKETING_PROFILE", {}, at).treatment, "DELETE")
        self.assertEqual(p.decide("backup_service", None, {}, at).treatment, "BLOCK_RESTORE")


class IntentTests(unittest.TestCase):
    def test_heuristic_on_eval_texts(self):
        cases = loaders.load_cases(D / "deletion_requests.csv") + loaders.load_cases(D / "sample_deletion_requests.csv")
        non = {c.case_id for c in cases if heuristic(c.request_text).label == NON_DELETE}
        self.assertEqual(non, {f"case_{i}" for i in range(533, 543)})

    def test_mixed_and_multilingual(self):
        self.assertEqual(heuristic("Please export my data and then delete my account.").label, DELETE)
        self.assertEqual(heuristic("이 이메일 주소에 연결된 계정의 영구 삭제를 요청합니다.").label, DELETE)
        self.assertEqual(heuristic("Please remove me from marketing lists only.").label, NON_DELETE)


class FakeBackend:
    provider = "fake"

    def __init__(self):
        self.calls = 0

    def call(self, prompt, images, model, max_tokens, json_mode=False):
        self.calls += 1
        return BackendResponse('{"ok": true}', 1000, 100, model, self.provider, cost_usd=0.01)


class LLMTests(unittest.TestCase):
    def adapter(self, tmp, limit, on_exceed="fallback", backend=None):
        ledger = Ledger(directory=Path(tmp) / "ledger")
        return LLMAdapter(backend="claude_cli", cache=LLMCache(Path(tmp) / "cache.jsonl"), ledger=ledger,
                          budget=Budget(ledger, limit_usd=limit, scope="run", on_exceed=on_exceed),
                          backend_impl=backend or FakeBackend())

    def test_budget_fallback_and_cache_is_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeBackend()
            a = self.adapter(tmp, 0.01, backend=fake)
            a.budget.estimate = lambda *args: 0.0
            self.assertIsNotNone(a.complete(task="t", prompt="one", json_schema={}))
            self.assertIsNone(a.complete(task="t", prompt="two", json_schema={}))   # spent 0.01 -> over budget
            hit = a.complete(task="t", prompt="one", json_schema={})                 # cache hit costs nothing
            self.assertTrue(hit.cached)
            self.assertEqual(fake.calls, 1)

    def test_budget_abort(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.adapter(tmp, 0.0, on_exceed="abort")
            with self.assertRaises(BudgetExceeded):
                a.complete(task="t", prompt="x", json_schema={})
            self.assertEqual(BudgetExceeded.exit_code, EXIT_BUDGET_EXCEEDED)

    def test_total_scope_sums_previous_ledgers(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "ledger"
            d.mkdir()
            (d / "old.jsonl").write_text(json.dumps({"cost_usd": 2.5, "cached": False}) + "\n")
            b = Budget(Ledger(directory=d), limit_usd=3.0, scope="total")
            self.assertAlmostEqual(b.spent(), 2.5)
            self.assertFalse(b.reserve(1.0))

    def test_claude_cli_output_parsing(self):
        out = json.dumps({"result": '{"a":1}', "total_cost_usd": 0.02, "usage": {"input_tokens": 5,
                          "cache_read_input_tokens": 10, "output_tokens": 7}, "modelUsage": {"claude-haiku-5-5": {}}})
        r = parse_output(out, "x", "p")
        self.assertEqual((r.tokens_in, r.tokens_out, r.model, r.cost_usd), (15, 7, "claude-haiku-5-5", 0.02))

    def test_anthropic_request_shape_with_mock(self):
        class Msg:
            content = [type("B", (), {"type": "text", "text": '{"x": 1}'})()]
            usage = type("U", (), {"input_tokens": 3, "output_tokens": 4})()

        class Client:
            def __init__(self):
                self.kw = None
                self.messages = self

            def create(self, **kw):
                self.kw = kw
                return Msg()

        c = Client()
        with tempfile.NamedTemporaryFile(suffix=".png") as img:
            img.write(b"\x89PNG")
            img.flush()
            r = AnthropicBackend(client=c).call("hi", [Path(img.name)], "claude-sonnet-5-5", 100)
        blocks = c.kw["messages"][0]["content"]
        self.assertEqual([b["type"] for b in blocks], ["image", "text"])
        self.assertNotIn("temperature", c.kw)
        self.assertEqual((r.tokens_in, r.tokens_out), (3, 4))
        self.assertEqual(content_blocks("p", [])[0]["type"], "text")

    def test_variant_backend_keeps_default_entries_and_replay_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = LLMCache(Path(tmp) / "cache.jsonl")
            ledger = Ledger(directory=Path(tmp) / "ledger")
            budget = Budget(ledger, limit_usd=1.0, scope="run")
            default = LLMAdapter(backend="claude_cli", cache=cache, ledger=ledger, budget=budget, backend_impl=FakeBackend())
            default.complete(task="t", prompt="seen", json_schema={})
            local = LLMAdapter(backend="ollama", cache=cache, ledger=ledger, budget=budget, backend_impl=FakeBackend())
            self.assertFalse(local.complete(task="t", prompt="seen", json_schema={}).cached)  # own key: a real call
            self.assertFalse(local.complete(task="t", prompt="new", json_schema={}).cached)
            replay = LLMAdapter(backend="replay", cache=cache, ledger=ledger, budget=budget)
            self.assertEqual(replay.complete(task="t", prompt="seen", json_schema={}).provider, "fake")
            self.assertIsNotNone(replay.complete(task="t", prompt="new", json_schema={}))   # variant via base key
            self.assertEqual(len(cache._data), 3)

    def test_ollama_unreachable_is_unavailable(self):
        from ghostaudit.llm.backends import BackendUnavailable
        from ghostaudit.llm.backends.ollama import OllamaBackend
        with self.assertRaises(BackendUnavailable):
            OllamaBackend(host="http://127.0.0.1:9")

    def test_missing_key_is_clear(self):
        import os
        from ghostaudit.llm.backends import BackendUnavailable
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(BackendUnavailable):
                AnthropicBackend()
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved


if __name__ == "__main__":
    unittest.main()
