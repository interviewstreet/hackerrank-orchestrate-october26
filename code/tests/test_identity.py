import unittest
from code.ingest import load_all
from code.identity import resolve_identity

class IdentityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.data=load_all('.')
 def test_current(self): self.assertEqual(resolve_identity('amina.elmasri@gmail.com','',self.data)['user_id'],'user_01')
 def test_historical(self): self.assertEqual(resolve_identity('o.walker6695@yahoo.com','',self.data)['user_id'],'user_523')
 def test_unknown(self): self.assertIsNone(resolve_identity('nobody@example.invalid','',self.data))
