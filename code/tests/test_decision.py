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
 def test_identifiable_tombstone_with_stable_reference_is_redacted(self):
  rules={'ACCOUNT_TOMBSTONE':{'required_action':'REDACT','condition':'stable reference'}}
  ev={'tombstone_1':[{'resource_id':'tombstone_1','system_id':'identity_service',
      'data_category':'ACCOUNT_TOMBSTONE','state':'PRESENT','file_id':'e',
      'record':{'subject_reference':'user_1','email':'a@example.test'}}]}
  result=decide({'request_text':'delete','case_id':'c'}, {'user_id':'u'},ev,[],rules,classify)
  self.assertEqual(result['findings'][0]['required_action'],'REDACT')
