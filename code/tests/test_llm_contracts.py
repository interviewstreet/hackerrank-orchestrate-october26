"""LLM contracts (schema.py), the client (fake transport), cache and snapshot replay. No network."""

import importlib.util
import json
import tempfile
import unittest
from datetime import UTC
from pathlib import Path
from typing import ClassVar

from pydantic import ValidationError

import helpers  # noqa: F401
from llm_cache import LLMCache
from llm_client import LIVE, REPLAY, FakeTransport, LLMClient, TransportError
from schema import AgentProposal, IntentBatch, IntentItem, LLMUsage, VisionExtraction, VisionRow

ROW = {"system_id": "account_service", "resource_id": "account_901", "category": None, "observed_state": "FOUND",
       "identifier": "ana.test@example.org", "observed_at": None, "source_text": "account_901 ana.test@example.org"}
VCTX = {"known_systems": {"account_service"}, "known_categories": {"USER_PROFILE"}, "file_id": "evidence_99"}
TEXT = "Please delete my account and all my data."
TID = "0123456789ab"


def proposal(**over):
    p = {"kind": "STATE", "case_id": "case_1", "system_id": "account_service", "resource_id": "account_901",
         "user_identifier": None, "proposed_state": "ABSENT", "evidence_ids": ["evidence_99"],
         "quotes": ["account_901 NOT_FOUND"], "reason": "row says not found"}
    p.update(over)
    return p


ACTX = {"case_id": "case_1", "evidence_text": {"evidence_99": "x | account_901 NOT_FOUND | y"}}


def fake_client(replies, cache=None, mode=LIVE):
    return LLMClient(transport=FakeTransport(replies), cache=cache or LLMCache(cache_dir=None, snapshot={}), mode=mode)


class ContractTest(unittest.TestCase):
    def test_valid_vision_row(self):
        row = VisionRow.model_validate(ROW, context=VCTX)
        self.assertEqual(row.observed_state, "FOUND")

    def test_extra_field_rejected(self):
        for model, data, ctx in ((VisionRow, dict(ROW, deletion_status="COMPLETE"), VCTX),
                                 (VisionExtraction, {"file_id": "evidence_99", "rows": [], "steps": []}, VCTX),
                                 (AgentProposal, proposal(status="COMPLETE"), ACTX),
                                 (IntentBatch, {"items": [], "status": "x"}, {"texts": {}})):
            with self.subTest(model.__name__), self.assertRaises(ValidationError):
                model.model_validate(data, context=ctx)

    def test_unknown_system_rejected(self):
        with self.assertRaises(ValidationError):
            VisionRow.model_validate(dict(ROW, system_id="payroll_service"), context=VCTX)

    def test_unknown_category_and_bad_resource_id_rejected(self):
        for bad in ({"category": "PAYROLL"}, {"resource_id": "ORD-2026-1"}, {"resource_id": "user 17"}):
            with self.subTest(bad), self.assertRaises(ValidationError):
                VisionRow.model_validate(dict(ROW, **bad), context=VCTX)

    def test_validation_needs_context(self):
        with self.assertRaises(ValidationError):
            VisionRow.model_validate(ROW)

    def test_vision_file_id_must_match(self):
        with self.assertRaises(ValidationError):
            VisionExtraction.model_validate({"file_id": "evidence_01", "rows": []}, context=VCTX)

    def test_intent_quote_must_be_substring(self):
        ok = {"text_id": TID, "label": "DELETE", "confidence": "high", "quote": "delete my account"}
        IntentItem.model_validate(ok, context={"texts": {TID: TEXT}})
        with self.assertRaises(ValidationError):
            IntentItem.model_validate(dict(ok, quote="erase everything"), context={"texts": {TID: TEXT}})

    def test_intent_label_enum(self):
        with self.assertRaises(ValidationError):
            IntentItem.model_validate({"text_id": TID, "label": "COMPLETE", "confidence": "high", "quote": "delete"},
                                      context={"texts": {TID: TEXT}})

    def test_intent_batch_must_cover_text_ids(self):
        texts = {TID: TEXT, "ba9876543210": "Delete my data please."}
        item = {"text_id": TID, "label": "DELETE", "confidence": "high", "quote": "delete my account"}
        with self.assertRaises(ValidationError):
            IntentBatch.model_validate({"items": [item]}, context={"texts": texts})
        with self.assertRaises(ValidationError):   # duplicate
            IntentBatch.model_validate({"items": [item, item]}, context={"texts": {TID: TEXT}})

    def test_agent_quote_must_be_substring_of_cited_row(self):
        AgentProposal.model_validate(proposal(), context=ACTX)
        with self.assertRaises(ValidationError):
            AgentProposal.model_validate(proposal(quotes=["account_901 deleted"]), context=ACTX)
        with self.assertRaises(ValidationError):   # quote from a file that was not cited / opened
            AgentProposal.model_validate(proposal(evidence_ids=["evidence_98"]), context=ACTX)

    def test_agent_typed_fields(self):
        with self.assertRaises(ValidationError):
            AgentProposal.model_validate(proposal(kind="LINK", user_identifier=None), context=ACTX)
        with self.assertRaises(ValidationError):
            AgentProposal.model_validate(proposal(proposed_state=None), context=ACTX)
        with self.assertRaises(ValidationError):
            AgentProposal.model_validate(proposal(evidence_ids=[]), context=ACTX)

    def test_usage_record(self):
        use = LLMUsage(purpose="vision", ref_id="evidence_04", model="m", input_tokens=1, output_tokens=2,
                       latency_ms=3, retries=0, cache_hit=False)
        self.assertEqual(use.purpose, "vision")
        with self.assertRaises(ValidationError):
            LLMUsage(purpose="status", ref_id="x", model="m", input_tokens=1, output_tokens=1, latency_ms=1,
                     retries=0, cache_hit=False)


class ClientTest(unittest.TestCase):
    MESSAGES: ClassVar[list[dict]] = [{"role": "user", "content": "x"}]
    GOOD: ClassVar[dict] = {"file_id": "evidence_99", "rows": [ROW]}

    def call(self, client):
        return client.structured("vision", "evidence_99", self.MESSAGES, VisionExtraction, VCTX, "v1")

    def test_retry_includes_validation_error(self):
        client = fake_client(["not json", self.GOOD])
        result = self.call(client)
        self.assertIsNotNone(result.value)
        self.assertEqual(result.usage.retries, 1)
        retry_messages = client.transport.bodies[1]["messages"]
        self.assertIn("failed validation", retry_messages[-1]["content"])

    def test_second_failure_falls_back(self):
        client = fake_client(["{}", {"file_id": "evidence_99", "rows": [dict(ROW, system_id="nope")]}])
        result = self.call(client)
        self.assertIsNone(result.value)
        self.assertEqual(result.flag, "schema_fallback")

    def test_transport_error_falls_back(self):
        result = self.call(fake_client([TransportError("HTTP 503")]))
        self.assertEqual((result.value, result.flag), (None, "transport_fallback"))

    def test_prose_around_json_is_discarded(self):
        result = self.call(fake_client(["Here you go: " + json.dumps(self.GOOD) + " done."]))
        self.assertEqual(len(result.value.rows), 1)

    def test_cache_hit_and_snapshot_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = LLMCache(cache_dir=Path(tmp), snapshot={})
            first = self.call(fake_client([self.GOOD], cache))
            second = self.call(fake_client([], cache))
            self.assertFalse(first.usage.cache_hit)
            self.assertTrue(second.usage.cache_hit)
            snap = Path(tmp) / "snap.py"
            self.assertEqual(cache.export_snapshot(snap), 1)
            spec = importlib.util.spec_from_file_location("snap", snap)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            replay = fake_client([], LLMCache(cache_dir=None, snapshot=module.SNAPSHOT), mode=REPLAY)
            replayed = self.call(replay)
            self.assertEqual(replayed.value, first.value)
            self.assertEqual(replay.transport.bodies, [])   # replay never calls the network
            # A hit reports the original call's usage; only live calls count as spent now.
            for hit in (second, replayed):
                self.assertEqual((hit.usage.input_tokens, hit.usage.output_tokens), (100, 20))
                self.assertEqual(hit.usage.latency_ms, first.usage.latency_ms)
            totals = replay.totals()["vision"]
            self.assertEqual((totals["input_tokens"], totals["live_input_tokens"], totals["cache_hits"]), (100, 0, 1))

    def test_snapshot_miss_is_flagged(self):
        result = self.call(fake_client([], mode=REPLAY))
        self.assertEqual((result.value, result.flag), (None, "snapshot_miss"))


class ModelPathTest(unittest.TestCase):
    def test_intent_high_label_is_used_low_is_not(self):
        import intent_model
        texts = ["Could you look at my account data?", "Maybe remove my profile?"]
        ids = [intent_model.text_id(t) for t in texts]
        reply = {"items": [{"text_id": ids[0], "label": "NOT_DELETION", "confidence": "high", "quote": "look at"},
                           {"text_id": ids[1], "label": "DELETE", "confidence": "low", "quote": "remove my profile"}]}
        labels = intent_model.label_texts(texts, fake_client([reply]))
        self.assertEqual((labels[ids[0]].label, labels[ids[0]].flag), ("NOT_DELETION", "model_high"))
        self.assertEqual((labels[ids[1]].label, labels[ids[1]].flag), (None, "model_low"))

    def test_agent_state_accepted_from_quoted_raw_text(self):
        from datetime import datetime
        from types import SimpleNamespace

        from agent.loop import accept
        from evidence.common import Identifiers
        p = AgentProposal.model_validate(proposal(), context=ACTX)
        corpus = SimpleNamespace(visible=lambda e, c: True, store=SimpleNamespace(for_resource=lambda r, c: []))
        ok, why = accept(p, item_key=("account_service", "account_901"), category="USER_PROFILE",
                         keys=Identifiers(), opened=dict(ACTX["evidence_text"]), corpus=corpus,
                         cutoff=datetime(2026, 1, 1, tzinfo=UTC), known_systems={"account_service"})
        self.assertEqual((ok, why), (True, ""))
        wrong = AgentProposal.model_validate(proposal(proposed_state="FOUND"), context=ACTX)
        ok, why = accept(wrong, item_key=("account_service", "account_901"), category="USER_PROFILE",
                         keys=Identifiers(), opened=dict(ACTX["evidence_text"]), corpus=corpus,
                         cutoff=datetime(2026, 1, 1, tzinfo=UTC), known_systems={"account_service"})
        self.assertEqual((ok, why), (False, "state_mismatch"))   # "NOT_FOUND" is not FOUND


if __name__ == "__main__":
    unittest.main()
