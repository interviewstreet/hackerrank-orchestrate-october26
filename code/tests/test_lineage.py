import unittest

from code.lineage import augment_identity_lineage, catalog_resource_ids


class LineageTests(unittest.TestCase):
    def test_only_explicit_catalog_links_seed_resources(self):
        events = [
            {
                "event_type": "DELETE_RECORD",
                "resource_id": "account_claim",
                "details": "Workflow claimed account_claim was deleted.",
            },
            {
                "event_type": "LINK_RESOURCE_IDENTITY",
                "resource_id": "analytics_123",
                "details": "Data catalog linked analytics_123 and object_456 to user_1.",
            },
        ]
        self.assertEqual(
            catalog_resource_ids(events), ["analytics_123", "object_456"]
        )

    def test_augmentation_deduplicates_and_invalidates_match_cache(self):
        identity = {
            "lineage_resource_ids": ["search_1"],
            "_match_identifiers": ["stale"],
        }
        events = [
            {
                "event_type": "LINK_RESOURCE_IDENTITY",
                "resource_id": "search_1",
                "details": "Data catalog linked search_1 to user_1.",
            },
            {
                "event_type": "LINK_RESOURCE_IDENTITY",
                "resource_id": "backup_2",
                "details": "Data catalog linked backup_2 to user_1.",
            },
        ]
        augment_identity_lineage(identity, events)
        self.assertEqual(identity["lineage_resource_ids"], ["search_1", "backup_2"])
        self.assertNotIn("_match_identifiers", identity)
