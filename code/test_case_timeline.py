"""
test_case_timeline.py — tests for the derived time-travel timeline.

Run from the repo root with:
    python3 code/test_case_timeline.py
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent))

from case_timeline import build_timeline
from models import IdentityChange

UTC = timezone.utc
CASE = {"case_id": "c1", "requested_at": "2026-09-06T12:00:00Z",
        "audit_at": "2026-10-01T12:00:00Z"}


def dt(*a):
    return datetime(*a, tzinfo=UTC)


def rec(eid, sid, rid, presence, captured, observed=None, claim=False):
    return NS(evidence_id=eid, system_id=sid, resource_id=rid, presence=presence,
              captured_at=captured, observed_at=observed or captured, claim_only=claim,
              replica_or_table=None)


IDENTITY = NS(history=[IdentityChange("audit_1", "email", "a@x.co", "b@x.co",
                                      "2026-02-03T06:23:48Z")])
EDGES = [{"activity_id": "activity_9", "event_time": "2026-09-09T11:02:59Z",
          "event_type": "DELETE_RECORD", "target_system": "account_service",
          "target_resource_id": "account_1", "reported_result": "SUCCESS"}]


class TestBuildTimeline(unittest.TestCase):

    def events(self, **kw):
        args = dict(identity=IDENTITY, evidence={"records": [], "absence_proofs": {}},
                    lineage_edges=EDGES)
        args.update(kw)
        return build_timeline(CASE, **args)

    def test_order_and_kinds(self):
        ev = {"records": [rec("evidence_3", "search_service", "search_1", "PRESENT",
                              dt(2026, 10, 1, 12), claim=True)],
              "absence_proofs": {}}
        got = [(e["event"], e["evidence_id"]) for e in self.events(evidence=ev)]
        self.assertEqual(got, [("IDENTITY_CHANGE", "audit_1"), ("DELETION_REQUESTED", ""),
                               ("DELETE_RECORD", "activity_9"), ("EVIDENCE_CLAIM", "evidence_3"),
                               ("AUDIT", "")])

    def test_columns_match_timeline_table(self):
        for e in self.events():
            self.assertEqual(set(e), {"time", "system_id", "resource_id", "event",
                                      "state_after", "evidence_id"})

    def test_activity_row_keeps_reported_result(self):
        act = [e for e in self.events() if e["event"] == "DELETE_RECORD"][0]
        self.assertEqual((act["system_id"], act["resource_id"], act["state_after"]),
                         ("account_service", "account_1", "SUCCESS"))

    def test_direct_evidence_is_proof_and_same_file_ordered_by_observed_at(self):
        cap = dt(2026, 4, 9, 12)
        ev = {"records": [rec("evidence_36", "account_service", "account_7", "ABSENT", cap,
                              observed=dt(2026, 4, 9, 12)),
                          rec("evidence_36", "account_service", "account_7", "PRESENT", cap,
                              observed=dt(2026, 4, 3, 12))],
              "absence_proofs": {}}
        proof = [e["state_after"] for e in self.events(evidence=ev) if e["event"] == "EVIDENCE_PROOF"]
        self.assertEqual(proof, ["PRESENT", "ABSENT"])   # the later observation wins

    def test_absence_proofs_and_contradicted_ones(self):
        ok = NS(evidence_id="evidence_5", captured_at=dt(2026, 9, 20), contradicted_by=())
        bad = NS(evidence_id="evidence_6", captured_at=dt(2026, 9, 21),
                 contradicted_by=("evidence_7",))
        ev = {"records": [], "absence_proofs": {("search_service", "search_1"): [ok, bad, ok]}}
        absent = [e for e in self.events(evidence=ev) if e["event"] == "ABSENCE_PROOF"]
        self.assertEqual([(e["evidence_id"], e["state_after"]) for e in absent],
                         [("evidence_5", "ABSENT")])          # deduplicated, contradicted skipped

    def test_nothing_after_audit_at(self):
        late = [{"activity_id": "activity_10", "event_time": "2026-10-01T12:00:01Z",
                 "event_type": "SYNC_RECORD", "target_system": "s", "target_resource_id": "r",
                 "reported_result": "SUCCESS"}]
        ev = {"records": [rec("evidence_9", "s", "r", "PRESENT", dt(2026, 10, 2))],
              "absence_proofs": {}}
        got = self.events(lineage_edges=EDGES + late, evidence=ev)
        self.assertNotIn("activity_10", [e["evidence_id"] for e in got])
        self.assertNotIn("evidence_9", [e["evidence_id"] for e in got])
        self.assertEqual(got[-1]["time"], "2026-10-01T12:00:00Z")

    def test_no_evidence_search_gives_empty(self):
        self.assertEqual(build_timeline(CASE, IDENTITY, None, EDGES), [])
        self.assertEqual(build_timeline(dict(CASE, audit_at=""), IDENTITY,
                                        {"records": []}, EDGES), [])

    def test_timeline_has_no_personal_values(self):
        """Identity changes carry the audit_id and field name, never the email."""
        text = repr(self.events())
        self.assertNotIn("a@x.co", text)
        self.assertNotIn("b@x.co", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
