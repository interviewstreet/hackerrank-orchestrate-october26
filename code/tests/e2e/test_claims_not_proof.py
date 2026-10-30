"""A deletion workflow's own result is a claim, never proof of absence (contract §6.6).

Finding (2026-10-25, owner's removal test): with no observable record of the person, the no-footprint fallback
verified `account_8819` ABSENT citing `activity_3114`, a `DELETE_RECORD ... FAILED` event. Verification steps of
a COMPLETE case must cite evidence that establishes the state; no sample ever cites an activity for it.
Fixed: with nothing observable the case is COMPLETE without steps; the workflow is only noted in the trace.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .scenarios import AUD, EMAIL, REP, REQ, base
from .test_scenarios import run_scenario

OMAR = "omar.h@example.org"


def deletion_claims_only():
    ds = base().user("user_103", "Omar Haddad", OMAR, "+971 50 100 2000")
    ds.act("2026-05-03T08:00:00Z", "DELETE_RECORD", "deletion_worker", "account_service", "account_7001", "FAILED",
           "Deletion worker submitted primary profile account_7001 to account_service.")
    ds.act("2026-05-03T08:05:00Z", "DELETE_RECORD", "deletion_worker", "account_service", "account_7301", "SUCCESS",
           "Deletion worker submitted primary profile account_7301 to account_service.")
    ds.request("case_32", EMAIL, REQ, REP, AUD)
    ds.request("case_33", OMAR, REQ, REP, AUD)
    return ds, {}


class ClaimsAreNotProofTests(unittest.TestCase):
    def test_deletion_claim_is_never_cited_as_proof_of_absence(self):
        with tempfile.TemporaryDirectory(prefix="gda_claims_") as tmp:
            _, got, log = run_scenario(deletion_claims_only, Path(tmp))
        for cid in ("case_32", "case_33"):
            status, steps = got[cid]
            cited = [s for s in steps if s[5].startswith("activity_")]
            self.assertEqual(cited, [], f"{cid} cites a workflow claim as proof: {cited}\n{log}")


if __name__ == "__main__":
    unittest.main()
