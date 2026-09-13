"""Meaningful local safety/validity gates; no network or model calls."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from .fixtures import DATA,checks,digest,canonical
from .prepare import DEV,validate
from .run import initial,payload,evidence_gate,QUESTION
from . import transport
class Gates(unittest.TestCase):
 def test_observed_consequences_and_crypto(self):self.assertEqual(len(validate('development',DEV)),8)
 def test_checker_does_not_judge_authorization(self):
  p=json.loads((DATA/'packets/development/e401.json').read_text());a=checks(p)
  for event in p['events']:
   if event['event_type']=='tool_returned' and 'scope' in event['data'].get('result',{}):event['data']['result']['scope']='Different permission text'
  self.assertEqual(a,checks(p))
 def test_same_events_and_staged_input(self):
  a=initial('development','e401','ordinary');b=initial('development','e401','checks');c=initial('development','e401','staged')
  self.assertTrue(b[-1]['content'].startswith(a[-1]['content']));self.assertEqual(b[-1],c[-1])
  self.assertEqual(payload(a,8192)['provider'],payload(c,2048)['provider'])
 def test_gate_rejects_invalid_references_without_changing_verdict(self):
  packet=json.loads((DATA/'packets/development/e401.json').read_text());obj={'verdict':'clear','findings':[{'evidence_call_ids':['invented']}],'authorization_comparisons':[]};before=copy.deepcopy(obj)
  self.assertFalse(evidence_gate(packet,obj)['passed']);self.assertEqual(obj,before)
  malformed={'verdict':'clear','findings':['bad',{'evidence_call_ids':3}],'authorization_comparisons':['bad',{'permission_call_id':{},'action_call_ids':3}]}
  self.assertFalse(evidence_gate(packet,malformed)['passed']);self.assertEqual(malformed['verdict'],'clear')
 def test_unknown_and_excess_cost_prevent_network(self):
  with tempfile.TemporaryDirectory() as td,patch.object(transport,'DATA',Path(td)),patch.object(transport,'key',return_value='not-a-key'),patch.object(transport.urllib.request,'Request',side_effect=AssertionError('Network reached')):
   c=transport.Client()
   for status,cost in [('unknown',None),('settled','.999')]:
    c.db.execute('DELETE FROM calls');c.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('old','x',status,'.2',cost));c.db.commit()
    with self.assertRaisesRegex(RuntimeError,'Budget or billing stop'):c.call('new',payload([],8192))
 def test_reservation_rejects_unbudgeted_message_or_tool_expansion(self):
  p=payload([{'role':'user','content':'x'}]*3,8192)
  with self.assertRaisesRegex(RuntimeError,'fixed tool-free'):transport.Client.reserve(p)
  p=payload([],8192);p['tools']=[]
  with self.assertRaisesRegex(RuntimeError,'fixed tool-free'):transport.Client.reserve(p)
 def test_response_budget_scales_with_actual_ceiling(self):
  p=payload([],2048);q=payload([],8192)
  self.assertGreater(transport.Client.reserve(q),transport.Client.reserve(p))
 def test_stream_journal_preserves_usage_and_identity(self):
  with tempfile.TemporaryDirectory() as td,patch.object(transport,'DATA',Path(td)):
   c=transport.Client();frames=[{'id':'g1','model':'qwen/qwen3.5-35b-a3b','provider':'Parasail','choices':[{'index':0,'delta':{'content':'{}'},'finish_reason':None}]},{'id':'g1','choices':[{'index':0,'delta':{},'finish_reason':'stop'}],'usage':{'cost':.001}}]
   r=c.read_stream(iter([('data: '+json.dumps(f)+'\n').encode() for f in frames]),'test')
   self.assertEqual(r['usage']['cost'],.001);self.assertEqual(r['choices'][0]['message']['content'],'{}');self.assertEqual(json.loads((c.root/'test.identity.json').read_text())['id'],'g1')
   self.assertEqual(len((c.root/'test.stream.jsonl').read_text().splitlines()),2)
 def test_interrupted_stream_keeps_billing_identity(self):
  with tempfile.TemporaryDirectory() as td,patch.object(transport,'DATA',Path(td)):
   c=transport.Client()
   def chunks():
    yield b'data: {"id":"g2","choices":[]}\n'
    raise TimeoutError('simulated interruption')
   with self.assertRaises(TimeoutError):c.read_stream(chunks(),'interrupted')
   self.assertEqual(json.loads((c.root/'interrupted.identity.json').read_text())['id'],'g2');self.assertEqual(len(json.loads((c.root/'interrupted.frames.json').read_text())),1)
if __name__=='__main__':unittest.main()
