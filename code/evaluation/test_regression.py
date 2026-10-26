import unittest
import csv
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from code.main import (
    get_identity_info,
    is_non_deletion_request,
    query_case_resources,
    build_case_steps,
    DELETION_RULES
)

class TestDeletionAuditRegression(unittest.TestCase):

    def setUp(self):
        self.dataset_dir = os.path.join(REPO_ROOT, 'dataset')
        with open(os.path.join(self.dataset_dir, 'user_identities.csv'), 'r', encoding='utf-8') as f:
            self.identities = list(csv.DictReader(f))
        with open(os.path.join(self.dataset_dir, 'user_audit_log.csv'), 'r', encoding='utf-8') as f:
            self.audit_logs = list(csv.DictReader(f))
        with open(os.path.join(self.dataset_dir, 'system_activity.csv'), 'r', encoding='utf-8') as f:
            self.system_activities = list(csv.DictReader(f))
        with open(os.path.join(self.dataset_dir, 'evidence_files.csv'), 'r', encoding='utf-8') as f:
            self.evidence_manifest = list(csv.DictReader(f))

    def test_audit_at_cutoff_enforcement(self):
        # Historical email changed AFTER audit_at should NOT be resolved for cutoff
        req_email = "nadia.ionescu@yahoo.com"
        cutoff_early = "2024-01-01T00:00:00Z"
        info = get_identity_info(req_email, cutoff_early, self.identities, self.audit_logs)
        if info:
            # Check historical emails captured only up to cutoff_early
            self.assertNotIn("n.petrescu@yahoo.com", info['all_emails'])

    def test_historical_email_alias_resolution(self):
        req_email = "nadia.ionescu@yahoo.com"
        cutoff_late = "2026-09-18T12:25:00Z"
        info = get_identity_info(req_email, cutoff_late, self.identities, self.audit_logs)
        self.assertIsNotNone(info)
        self.assertEqual(info['user_id'], 'user_10')
        self.assertIn("nadia.petrescu@yahoo.com", info['all_emails'])

    def test_non_deletion_intent_detection(self):
        self.assertTrue(is_non_deletion_request("The mobile number on my profile is out of date. Please replace it with the new one and leave the account active."))
        self.assertTrue(is_non_deletion_request("I'd like to download my account information in a portable format. Please keep the account as it is."))
        self.assertFalse(is_non_deletion_request("Please delete my personal data completely from all systems."))

    def test_retained_records_policy_rules(self):
        self.assertEqual(DELETION_RULES.get('SECURITY_AUDIT_LOG'), 'RETAIN')
        self.assertEqual(DELETION_RULES.get('ACCOUNT_TOMBSTONE'), 'REDACT')
        self.assertEqual(DELETION_RULES.get('ANALYTICS_PROFILE'), 'ANONYMIZE')
        self.assertEqual(DELETION_RULES.get('USER_PROFILE'), 'DELETE')

    def test_remediation_dependency_ordering(self):
        mock_resources = [
            {'system_id': 'analytics_platform', 'resource_id': 'analytics_001', 'is_compliant': False, 'evidence_id': 'evidence_01'},
            {'system_id': 'integration_service', 'resource_id': 'data_flow_001', 'is_compliant': False, 'evidence_id': 'evidence_01'},
            {'system_id': 'search_service', 'resource_id': 'search_001', 'is_compliant': False, 'evidence_id': 'evidence_01'},
            {'system_id': 'backup_service', 'resource_id': 'backup_001', 'is_compliant': False, 'evidence_id': 'evidence_01'}
        ]
        status, steps = build_case_steps(mock_resources, 'evidence_01')
        self.assertEqual(status, 'INCOMPLETE')

        rem_steps = [s for s in steps if s['phase'] == 'REMEDIATION']
        op_sequence = [s['operation'] for s in rem_steps]

        # DISABLE_DATA_FLOW must come before DELETE_RECORD and ANONYMIZE_RECORD
        df_idx = op_sequence.index('DISABLE_DATA_FLOW')
        bk_idx = op_sequence.index('BLOCK_RESTORE')
        del_idx = op_sequence.index('DELETE_RECORD')
        anon_idx = op_sequence.index('ANONYMIZE_RECORD')

        self.assertLess(df_idx, del_idx)
        self.assertLess(bk_idx, del_idx)
        self.assertLess(del_idx, anon_idx)

if __name__ == '__main__':
    unittest.main()
