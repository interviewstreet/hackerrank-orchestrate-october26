import unittest
from code.temporal import filter_events

class TemporalTests(unittest.TestCase):
 def setUp(self):
  self.ident={'user_id':'u1','all_emails':['a@x.test'],'all_phones':[],'all_email_hashes':[]}
  self.events=[
   {'event_time':'2026-01-03Z','resource_id':'r','details':'u1'},
   {'event_time':'2026-01-01Z','resource_id':'r','details':'a@x.test'},
   {'event_time':'2026-01-02Z','resource_id':'r','details':'someone else'}]
 def test_after_excluded(self): self.assertEqual(len(filter_events(self.events,self.ident,'2026-01-02Z')),1)
 def test_unrelated_excluded(self): self.assertFalse(any('someone' in x['details'] for x in filter_events(self.events,self.ident,'2026-01-04Z')))
 def test_sorted(self):
  out=filter_events(self.events,self.ident,'2026-01-04Z'); self.assertEqual([x['event_time'] for x in out],sorted(x['event_time'] for x in out))
 def test_user_id_boundary(self):
  events=[{'event_time':'2026-01-01Z','resource_id':'r','details':'linked to user_10'}]
  self.assertEqual(filter_events(events,self.ident,'2026-01-02Z'),[])
