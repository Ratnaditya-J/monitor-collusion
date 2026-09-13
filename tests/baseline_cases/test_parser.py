import unittest
from baseline_cases.run import parse
class Parser(unittest.TestCase):
 def response(self, texts):
  return {'status':'completed','output':[{'content':[{'type':'output_text','text':t}]} for t in texts]}
 def test_duplicate_is_single_request(self):
  s='{"requests":[{"action":"list"}]}'
  self.assertEqual(parse(self.response([s,s])), {'requests':[{'action':'list'}]})
 def test_conflicting_messages_rejected(self):
  with self.assertRaises(RuntimeError):parse(self.response(['{}','{"x":1}']))
