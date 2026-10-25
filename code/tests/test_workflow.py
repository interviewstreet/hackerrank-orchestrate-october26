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

    def test_equal_analytics_candidates_fail_closed(self):
        activity = [
            {"event_time": "2026-09-01T09:00:00Z", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_1"},
            {"event_time": "2026-09-01T09:20:41Z", "event_type": "ANONYMIZE_RECORD",
             "target_system": "analytics_platform", "resource_id": "analytics_1"},
            {"event_time": "2026-09-01T09:20:41Z", "event_type": "ANONYMIZE_RECORD",
             "target_system": "analytics_platform", "resource_id": "analytics_2"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"account_1": [{}]}, activity,
            [self.case()],
        )
        self.assertEqual([item["resource_id"] for item in resources], ["account_1"])

    def test_reported_outcomes_do_not_break_ambiguous_lineage(self):
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
        self.assertEqual(resources, [])

    def test_unique_near_report_action_is_identity_anchor_not_state_proof(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T11:55:00Z",
             "event_type": "ANONYMIZE_RECORD", "source_system": "deletion_worker",
             "target_system": "analytics_platform", "resource_id": "analytics_1",
             "reported_result": "FAILED"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {}, activity, [self.case()]
        )
        self.assertEqual(resources[0]["resource_id"], "analytics_1")
        self.assertEqual(resources[0]["required_action"], "ANONYMIZE")

    def test_causal_chain_requires_two_independent_evidence_anchors(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T10:00:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "account_service", "resource_id": "account_1"},
            {"activity_id": "a2", "event_time": "2026-09-01T10:20:41Z",
             "event_type": "ANONYMIZE_RECORD", "source_system": "deletion_worker",
             "target_system": "analytics_platform", "resource_id": "analytics_1"},
            {"activity_id": "a3", "event_time": "2026-09-01T10:28:10Z",
             "event_type": "REDACT_RECORD", "source_system": "deletion_worker",
             "target_system": "support_platform", "resource_id": "support_1"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"support_1": [{}]}, activity,
            [self.case()],
        )
        self.assertEqual(resources, [])
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"},
            {"analytics_1": [{}], "support_1": [{}]}, activity, [self.case()],
        )
        self.assertEqual(
            [item["resource_id"] for item in resources],
            ["account_1", "analytics_1"],
        )

    def test_two_evidenced_cadence_events_link_account(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T09:00:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "account_service", "resource_id": "account_1"},
            {"activity_id": "a2", "event_time": "2026-09-01T10:20:41Z",
             "event_type": "DISABLE_DATA_FLOW", "source_system": "deletion_worker",
             "target_system": "integration_service", "resource_id": "flow_1"},
            {"activity_id": "a3", "event_time": "2026-09-01T10:39:11Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "search_service", "resource_id": "search_1"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"},
            {"flow_1": [{}], "search_1": [{}]}, activity, [self.case()],
        )
        self.assertEqual([item["resource_id"] for item in resources], ["account_1"])

    def test_unique_report_batch_links_account_to_evidenced_resource(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T11:54:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "account_service", "resource_id": "account_1",
             "reported_result": "FAILED"},
            {"activity_id": "a2", "event_time": "2026-09-01T12:04:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "search_service", "resource_id": "search_1",
             "reported_result": "SUCCESS"},
        ]
        resources = correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"search_1": [{}]}, activity,
            [self.case()],
        )
        self.assertEqual([item["resource_id"] for item in resources], ["account_1"])

    def test_report_batch_without_evidence_anchor_is_rejected(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T11:54:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "account_service", "resource_id": "account_1",
             "reported_result": "SUCCESS"},
            {"activity_id": "a2", "event_time": "2026-09-01T12:04:00Z",
             "event_type": "DELETE_RECORD", "source_system": "deletion_worker",
             "target_system": "search_service", "resource_id": "search_2",
             "reported_result": "SUCCESS"},
        ]
        self.assertEqual(correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {"search_1": [{}]}, activity,
            [self.case()],
        ), [])

    def test_one_report_event_shared_by_overlapping_requests_is_rejected(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T11:55:00Z",
             "event_type": "ANONYMIZE_RECORD", "source_system": "deletion_worker",
             "target_system": "analytics_platform", "resource_id": "analytics_1",
             "reported_result": "SUCCESS"},
        ]
        peer = {**self.case(), "case_id": "case_y"}
        self.assertEqual(correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {}, activity, [self.case(), peer]
        ), [])

    def test_ambiguous_unanchored_batch_is_rejected(self):
        activity = [
            {"activity_id": "a1", "event_time": "2026-09-01T11:55:00Z",
             "event_type": "DELETE_RECORD", "target_system": "account_service",
             "resource_id": "account_1", "reported_result": "SUCCESS"},
            {"activity_id": "a2", "event_time": "2026-09-01T12:05:00Z",
             "event_type": "DELETE_RECORD", "target_system": "account_service",
             "resource_id": "account_2", "reported_result": "FAILED"},
        ]
        self.assertEqual(correlate_workflow_lineage(
            self.case(), {"user_id": "user_1"}, {}, activity, [self.case()]
        ), [])

    def test_augmentation_invalidates_identifier_cache(self):
        identity = {"lineage_resource_ids": ["search_1"], "_match_identifiers": ["old"]}
        augment_workflow_lineage(identity, [{"resource_id": "account_1"}])
        self.assertEqual(identity["lineage_resource_ids"], ["search_1", "account_1"])
        self.assertNotIn("_match_identifiers", identity)
