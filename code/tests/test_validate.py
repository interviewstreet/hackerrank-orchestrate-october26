import json,unittest
from code.validate import validate_case_coverage, validate_output, validate_row_count
BASE={'step_no':1,'phase':'FINDING','system_id':'s','resource_id':'r','operation':'REPORT_REMAINING_RECORD','state':'PRESENT','evidence_id':'e'}
def row(step,status='INCOMPLETE'):return {'case_id':'c','deletion_status':status,'steps_json':json.dumps(step)}
class ValidateTests(unittest.TestCase):
 def assertError(self,r,text):self.assertTrue(any(text in x for x in validate_output([r])),validate_output([r]))
 def test_status(self):self.assertError(row([], 'WRONG'),'invalid deletion_status')
 def test_gap(self):self.assertError(row([{**BASE,'step_no':2}]),'step_no gap')
 def test_phase(self):self.assertError(row([{**BASE,'phase':'VERIFICATION','operation':'VERIFY_RECORD_ABSENT','state':'ABSENT'},{**BASE,'step_no':2}]),'wrong phase order')
 def test_remediation_evidence(self):self.assertError(row([{**BASE,'phase':'REMEDIATION','operation':'DELETE_RECORD','state':'ABSENT'}]),'non-empty evidence_id')
 def test_pair(self):self.assertError(row([{**BASE,'state':'ACTIVE'}]),'invalid operation+state pair')
 def test_duplicate_case(self):
  r=row([BASE]);self.assertTrue(any('duplicate case_id' in e for e in validate_output([r,r])))
 def test_future_verification_evidence(self):
  steps=[BASE,{**BASE,'step_no':2,'phase':'VERIFICATION','operation':'VERIFY_RECORD_ABSENT','state':'ABSENT'}]
  self.assertError(row(steps),'future VERIFICATION')
 def test_complete_findings_rejected(self):self.assertError(row([BASE],'COMPLETE'),'verification steps only')
 def test_empty_complete_rejected(self):self.assertError(row([],'COMPLETE'),'at least one evidence-backed verification')
 def test_resource_id_format_rejected(self):self.assertError(row([{**BASE,'resource_id':'account_service'}]),'invalid resource_id format')
 def test_row_count_duplicates(self):
  self.assertTrue(any('duplicate case_id' in e for e in validate_row_count([{'case_id':'c'},{'case_id':'c'}],expected=2)))
 def test_case_coverage(self):
  errors=validate_case_coverage([{'case_id':'case_1'},{'case_id':'case_extra'}],['case_1','case_2'])
  self.assertTrue(any('missing case_id' in e for e in errors))
  self.assertTrue(any('unexpected case_id' in e for e in errors))
