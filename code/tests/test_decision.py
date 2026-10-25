import unittest
from code.decision import decide
RULE={'USER_PROFILE':{'required_action':'DELETE','condition':'Always'}}
def classify(*args):return 'DELETION'
class DecisionTests(unittest.TestCase):
 def run_state(self,state):
  ev={'r':[{'resource_id':'r','system_id':'s','data_category':'USER_PROFILE','state':state,'file_id':'e'}]}
  return decide({'request_text':'delete','case_id':'c'}, {'user_id':'u'},ev,[],RULE,classify)
 def test_complete(self):self.assertEqual(self.run_state('ABSENT')['status'],'COMPLETE')
 def test_incomplete(self):self.assertEqual(self.run_state('ACTIVE')['status'],'INCOMPLETE')
 def test_no_evidence_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'no eligible evidence'):
   decide({'request_text':'delete','case_id':'c'}, {'user_id':'u'}, {}, [], RULE, classify)
 def test_anonymized_record_keeps_strong_verification_treatment(self):
  rules={'ANALYTICS_PROFILE':{'required_action':'ANONYMIZE','condition':'attributable'}}
  ev={'analytics_1':[{'resource_id':'analytics_1','system_id':'analytics_platform',
      'data_category':'ANALYTICS_PROFILE','state':'ANONYMIZED','file_id':'e','record':{}}]}
  result=decide({'request_text':'delete','case_id':'c'}, {'user_id':'u'},ev,[],rules,classify)
  self.assertEqual(result['compliant_resources'][0]['required_action'],'ANONYMIZE')
 def test_unblockable_backup_requires_deletion(self):
  rules={'BACKUP_ARCHIVE':{'required_action':'RETAIN','condition':'blockable'}}
  ev={'backup_1':[{'resource_id':'backup_1','system_id':'backup_service',
      'data_category':'BACKUP_ARCHIVE','state':'ACTIVE','file_id':'e',
      'record':{'restore_can_be_blocked':False,'restore_allowed':True}}]}
  result=decide({'request_text':'delete','case_id':'c','requested_at':'2026-01-01T00:00:00Z'},
      {'user_id':'u'},ev,[],rules,classify)
  self.assertEqual(result['findings'][0]['required_action'],'DELETE')
 def test_failed_activity_outcome_does_not_prove_risk_removed(self):
  ev={'account_1':[{'resource_id':'account_1','system_id':'account_service',
      'data_category':'USER_PROFILE','state':'ABSENT','file_id':'e','record':{}}]}
  event={'event_type':'SYNC_RECORD','event_time':'2026-01-02T00:00:00Z',
      'resource_id':'data_flow_1','target_system':'integration_service',
      'reported_result':'FAILED','activity_id':'a'}
  result=decide({'request_text':'delete','case_id':'c','requested_at':'2026-01-01T00:00:00Z'},
      {'user_id':'u'},ev,[event],RULE,classify)
  self.assertEqual(result['status'],'INCOMPLETE')
  self.assertEqual(result['findings'][0]['type'],'active_data_flow')
 def test_identifiable_tombstone_with_stable_reference_is_redacted(self):
  rules={'ACCOUNT_TOMBSTONE':{'required_action':'REDACT','condition':'stable reference'}}
  ev={'tombstone_1':[{'resource_id':'tombstone_1','system_id':'identity_service',
      'data_category':'ACCOUNT_TOMBSTONE','state':'PRESENT','file_id':'e',
      'record':{'subject_reference':'user_1','email':'a@example.test'}}]}
  result=decide({'request_text':'delete','case_id':'c'}, {'user_id':'u'},ev,[],rules,classify)
  self.assertEqual(result['findings'][0]['required_action'],'REDACT')
