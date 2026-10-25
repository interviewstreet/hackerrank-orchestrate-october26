import unittest
from code.ingest import load_all
from code.policy import get_required_action
class PolicyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.rules=load_all('.')['deletion_rules']
 def test_all_categories(self):
  cases={
   'USER_PROFILE':({},'DELETE'),'SECONDARY_IDENTIFIER':({},'DELETE'),'SEARCH_INDEX_ENTRY':({},'DELETE'),'CACHE_ENTRY':({},'DELETE'),
   'SUPPORT_MESSAGE':({'has_shared_context':True},'REDACT'),'SUPPORT_ATTACHMENT':({'attachment_belongs_only_to_subject':False},'REDACT'),
   'ANALYTICS_PROFILE':({'record_still_attributable':True},'ANONYMIZE'),'PRODUCT_TELEMETRY':({'record_still_attributable':True},'ANONYMIZE'),
   'USER_EXPORT':({},'DELETE'),'MARKETING_PROFILE':({},'DELETE'),'EMAIL_DELIVERY_LOG':({'log_contains_email':True},'REDACT'),
   'SECURITY_AUDIT_LOG':({'within_retention_period':True},'RETAIN'),'LEGAL_HOLD_RECORD':({'legal_hold_active':True},'RETAIN'),
   'BACKUP_ARCHIVE':({'restore_can_be_blocked':True},'RETAIN'),'ACCOUNT_TOMBSTONE':({'only_stable_id_needed':True},'REDACT')}
  self.assertEqual(set(cases),set(self.rules))
  for cat,(ctx,want) in cases.items():
   with self.subTest(cat=cat): self.assertEqual(get_required_action(cat,ctx,self.rules),want)
 def test_expired_retention_and_inactive_hold_delete(self):
  self.assertEqual(get_required_action('SECURITY_AUDIT_LOG',{'within_retention_period':False},self.rules),'DELETE')
  self.assertEqual(get_required_action('LEGAL_HOLD_RECORD',{'legal_hold_active':False},self.rules),'DELETE')
