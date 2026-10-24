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
