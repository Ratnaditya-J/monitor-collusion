import copy,json,tempfile,unittest
from pathlib import Path
from evidence_kernel.records import seal,verify,Recorder,digest
from evidence_kernel.vendor.spineframe import signing

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.k=self.root/'keys';signing.generate_keypair(self.k);self.pub=signing.public_key_hex(self.k)
  self.files={'a':b'original'};self.context={'run_id':'run-a','created_at':'fixed','recorder':'host','capture_mode':'test'}
  self.b=seal([{'action':'write','actor':'x'},{'action':'read','actor':'x'}],{'a':digest(b'original')},self.context,self.k)
 def tearDown(self):self.tmp.cleanup()
 def test_valid(self):self.assertTrue(verify(self.b,self.pub,'run-a',self.files)['valid'])
 def test_tamper_delete_reorder_actor(self):
  for kind in ['delete','reorder','actor','metadata']:
   b=copy.deepcopy(self.b)
   if kind=='delete':b['content']['records'].pop()
   if kind=='reorder':b['content']['records'].reverse()
   if kind=='actor':b['content']['records'][0]['record']['actor']='trusted'
   if kind=='metadata':b['content']['context']['capture_mode']='live'
   self.assertFalse(verify(b,self.pub,'run-a',self.files)['valid'],kind)
 def test_file_tamper_and_missing(self):
  self.assertFalse(verify(self.b,self.pub,'run-a',{'a':b'changed'})['valid'])
  self.assertFalse(verify(self.b,self.pub,'run-a',{})['valid'])
 def test_replay_wrong_run(self):self.assertFalse(verify(self.b,self.pub,'other',self.files)['valid'])
 def test_attacker_self_sign(self):
  other=self.root/'other';signing.generate_keypair(other)
  b=signing.sign_bundle(self.b,key_dir=other)
  self.assertFalse(verify(b,self.pub,'run-a',self.files)['valid'])
 def test_host_records_real_operation(self):
  r=Recorder(self.root/'records',self.k,'test-agent',{'source':'test operator','allowed':'write temp file'})
  target=self.root/'effect'
  def op():target.write_text('done');return {'bytes':target.stat().st_size}
  r.call('write',{'path':'effect'},op)
  b=r.export();self.assertTrue(target.exists());self.assertTrue(verify(b,self.pub,r.run_id,{})['valid']);self.assertEqual(len(b['content']['records']),2)
 def test_failure_is_recorded(self):
  r=Recorder(self.root/'records',self.k,'test-agent',{})
  with self.assertRaises(ValueError):r.call('bad',{},lambda:(_ for _ in ()).throw(ValueError('test')))
  self.assertEqual(r.export()['content']['records'][-1]['record']['event_type'],'tool_failed')
if __name__=='__main__':unittest.main()
