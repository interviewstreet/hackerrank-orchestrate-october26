import json,unittest
from code.validate import validate_output
BASE={'step_no':1,'phase':'FINDING','system_id':'s','resource_id':'r','operation':'REPORT_REMAINING_RECORD','state':'PRESENT','evidence_id':'e'}
def row(step,status='INCOMPLETE'):return {'case_id':'c','deletion_status':status,'steps_json':json.dumps(step)}
class ValidateTests(unittest.TestCase):
 def assertError(self,r,text):self.assertTrue(any(text in x for x in validate_output([r])),validate_output([r]))
 def test_status(self):self.assertError(row([], 'WRONG'),'invalid deletion_status')
 def test_gap(self):self.assertError(row([{**BASE,'step_no':2}]),'step_no gap')
 def test_phase(self):self.assertError(row([{**BASE,'phase':'VERIFICATION','operation':'VERIFY_RECORD_ABSENT','state':'ABSENT'},{**BASE,'step_no':2}]),'wrong phase order')
 def test_remediation_evidence(self):self.assertError(row([{**BASE,'phase':'REMEDIATION','operation':'DELETE_RECORD','state':'ABSENT'}]),'non-empty evidence_id')
 def test_pair(self):self.assertError(row([{**BASE,'state':'ACTIVE'}]),'invalid operation+state pair')
