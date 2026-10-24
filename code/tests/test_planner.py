import unittest
from code.planner import plan_steps,OPERATION_STATE
class PlannerTests(unittest.TestCase):
 def test_order_and_contract(self):
  d={'status':'INCOMPLETE','findings':[{'type':'non_compliant_resource','required_action':'DELETE','system_id':'z','resource_id':'r','file_id':'e'},{'type':'active_data_flow','system_id':'a','resource_id':'flow','evidence_id':'act'}]}
  s=plan_steps(d,{},{}); phases=[x['phase'] for x in s]
  self.assertEqual(phases,sorted(phases,key=['FINDING','REMEDIATION','VERIFICATION'].index))
  ops=[x['operation'] for x in s];self.assertLess(ops.index('DISABLE_DATA_FLOW'),ops.index('DELETE_RECORD'))
  self.assertEqual([x['step_no'] for x in s],list(range(1,len(s)+1)))
  self.assertTrue(all(x['evidence_id']=='' for x in s if x['phase']=='REMEDIATION'))
  self.assertTrue(all(OPERATION_STATE[x['phase']].get(x['operation'])==x['state'] for x in s))
