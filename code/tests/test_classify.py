import unittest
from code.classify import classify_request
class MemoryCache:
 def __init__(self): self.d={}
 def make_key(self,a,b): return a+b
 def get(self,k): return self.d.get(k)
 def set(self,k,v): self.d[k]=v
class ClassifyTests(unittest.TestCase):
 def check(self,text,want): self.assertEqual(classify_request(text,'c',MemoryCache()),want)
 def test_english(self): self.check('Please delete my account','DELETION')
 def test_spanish(self): self.check('Intenté eliminar mi cuenta','DELETION')
 def test_french(self): self.check('Je demande la suppression définitive','DELETION')
 def test_access(self): self.check('I request access to my records','NOT_APPLICABLE')
 def test_marketing(self): self.check('Please opt out of marketing','NOT_APPLICABLE')
 def test_korean_deletion(self): self.check('이 계정의 영구 삭제를 요청합니다','DELETION')
 def test_portable_copy(self): self.check('I need a copy of my data in a portable format','NOT_APPLICABLE')
 def test_keep_active(self): self.check('Replace my phone and leave the account active','NOT_APPLICABLE')
