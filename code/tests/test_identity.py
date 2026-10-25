import unittest
from code.ingest import load_all
from code.identity import resolve_identity

class IdentityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.data=load_all('.')
 def test_current(self): self.assertEqual(resolve_identity('amina.elmasri@gmail.com','',self.data)['user_id'],'user_01')
 def test_historical(self): self.assertEqual(resolve_identity('o.walker6695@yahoo.com','',self.data)['user_id'],'user_523')
 def test_unknown(self): self.assertIsNone(resolve_identity('nobody@example.invalid','',self.data))
 def test_ambiguous_historical_email_is_rejected(self):
  data={
   'user_identities':{
    'u1':{'user_id':'u1','email':'one@example.test','updated_at':'2026-01-01T00:00:00Z'},
    'u2':{'user_id':'u2','email':'two@example.test','updated_at':'2026-01-01T00:00:00Z'}},
   'user_audit_log':{
    'u1':[{'event_time':'2026-01-02T00:00:00Z','field_name':'email','old_value':'shared@example.test','new_value':'one@example.test'}],
    'u2':[{'event_time':'2026-01-03T00:00:00Z','field_name':'email','old_value':'shared@example.test','new_value':'two@example.test'}]},
  }
  self.assertIsNone(resolve_identity('shared@example.test','2026-01-04T00:00:00Z',data))
 def test_future_identity_change_is_reversed_at_cutoff(self):
  data={
   'user_identities':{'user_x':{'user_id':'user_x','name':'X','email':'future@example.test','phone':'','email_hash':''}},
   'user_audit_log':{'user_x':[{'event_time':'2026-02-01T00:00:00Z','field_name':'email','old_value':'past@example.test','new_value':'future@example.test'}]},
  }
  identity=resolve_identity('past@example.test','2026-01-15T00:00:00Z',data)
  self.assertEqual(identity['current_email'],'past@example.test')
  self.assertNotIn('future@example.test',identity['all_emails'])
