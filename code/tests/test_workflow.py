import unittest

from code.workflow import augment_workflow_lineage, correlate_workflow_lineage


class WorkflowLineageTests(unittest.TestCase):
    def case(self, status="COMPLETE"):
        return {
            "case_id": "case_x", "requested_at": "2026-09-01T08:00:00Z",
            "reported_at": "2026-09-01T12:00:00Z",
            "audit_at": "2026-09-02T12:00:00Z", "reported_status": status,
        }

    def test_evidence_anchor_recovers_account_and_anonymized_resource(self):
        activity = [
            {"event_time": "2026-09-01T09:00:00Z", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_1",
             "reported_result": "SUCCESS"},
            {"event_time": "2026-09-01T09:20:41Z", "event_type": "ANONYMIZE_RECORD",
             "target_system": "analytics_platform", "resource_id": "analytics_1",
             "reported_result": "SUCCESS"},
            {"event_time": "2026-09-01T10:00:52Z", "event_type": "REDACT_RECORD",
             "target_system": "support_platform", "resource_id": "support_1",
             "reported_result": "FAILED"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"support_1": [{}]}, activity,
            [self.case()],
        )
        self.assertEqual([item["resource_id"] for item in resources],
                         ["account_1", "analytics_1"])

    def test_claim_outcome_must_match_reported_status(self):
        activity = [
            {"event_time": "2026-09-01T09:00:00Z", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "wrong",
             "reported_result": "FAILED"},
            {"event_time": "2026-09-01T09:10:00Z", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_1",
             "reported_result": "SUCCESS"},
            {"event_time": "2026-09-01T10:10:52Z", "event_type": "REDACT_RECORD",
             "target_system": "support_platform", "resource_id": "support_1",
             "reported_result": "FAILED"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"support_1": [{}]}, activity,
            [self.case()],
        )
        self.assertEqual(resources[0]["resource_id"], "account_1")

    def test_augmentation_invalidates_identifier_cache(self):
        identity = {"lineage_resource_ids": ["search_1"], "_match_identifiers": ["old"]}
        augment_workflow_lineage(identity, [{"resource_id": "account_1"}])
        self.assertEqual(identity["lineage_resource_ids"], ["search_1", "account_1"])
        self.assertNotIn("_match_identifiers", identity)
