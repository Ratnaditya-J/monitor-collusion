"""Offline acceptance and read-only access check; freezes before the first model call."""
import json,sqlite3,hashlib,tempfile,urllib.request
from pathlib import Path
from unittest.mock import patch
from .prepare import DATA,ROOT
from . import client
from .run import dispatch,receipt,initial
from .records import digest
from source_fidelity.api import save,now
from source_fidelity.qwen import key,MODEL,payload

def main():
 if (DATA/'FREEZE.json').exists():raise RuntimeError('Already frozen')
 # Existing baseline ledger is copied, not reset or reopened.
 dest=DATA/'api';dest.mkdir(exist_ok=True)
 with sqlite3.connect(ROOT/'results/qwen_comparison/api/ledger.sqlite3') as src,sqlite3.connect(dest/'ledger.sqlite3') as db:src.backup(db)
 assert client.Client().summary()['available_usd']=='0.90097325'
 results=[]
 for cid in json.loads((DATA/'operator/trust.json').read_text()):
  for name in ['transcript.jsonl','action_records.jsonl','capture_context.json']:
   assert (DATA/'public/structured'/cid/name).read_bytes()==(DATA/'public/verified'/cid/name).read_bytes()
  assert receipt('verified',cid)['valid']
  assert receipt('structured',cid)['valid'] is None
 results.append('All ten U/V semantic inputs identical; signed artifact and record commitments verified')
 r=dispatch('verified',cid,{'action':'python','code':'from pathlib import Path; print(Path("transcript.jsonl").exists()); print(Path("'+str(DATA/'operator/keys/signing_key.pem')+'").read_text())'})
 assert r['exit_code']!=0 and 'True' in r['stdout'] and 'Operation not permitted' in r['stderr'],r
 results.append('Original inspector reads evidence and cannot read signing key')
 with tempfile.TemporaryDirectory() as tmp,patch.object(client,'DATA',Path(tmp)),patch.object(client,'key',return_value='test'),patch.object(client.urllib.request,'Request',side_effect=AssertionError('Network reached')):
  c=client.Client()
  for status,cost in [('unknown',None),('settled','.99')]:
   c.db.execute('DELETE FROM calls');c.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('prior','x',status,'.1',cost));c.db.commit()
   try:c.call('new',payload([],0))
   except RuntimeError as e:assert str(e)=='Budget or billing stop'
   else:raise AssertionError('Guard failed')
 results.append('Unknown charge and reservation overflow both block before network')
 req=urllib.request.Request('https://openrouter.ai/api/v1/key',headers={'Authorization':'Bearer '+key()});json.load(urllib.request.urlopen(req,timeout=30))
 endpoints=json.load(urllib.request.urlopen('https://openrouter.ai/api/v1/models/'+MODEL+'/endpoints',timeout=30));save(DATA/'provider.json',endpoints)
 e=next(x for x in endpoints['data']['endpoints'] if x['tag']=='parasail/fp8')
 assert e['pricing']['prompt']=='0.00000015' and e['pricing']['completion']=='0.000001' and all(x in e['supported_parameters'] for x in ['tools','reasoning'])
 results.append('Credential works; pinned provider model, tool/reasoning access and rates verified')
 paths=list((ROOT/'evidence_kernel').rglob('*.py'))+list((ROOT/'evidence_kernel/fixtures').glob('*'))+list((DATA/'public').rglob('*'))+[DATA/'operator/trust.json',ROOT/'studies/spineframe_qwen/PROTOCOL.md',ROOT/'source_fidelity/qwen.py',ROOT/'source_fidelity/investigate.py',ROOT/'baseline_cases/tools.py']
 files={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths if p.is_file()}
 save(DATA/'preflight.json',{'at':now(),'checks':results,'tests':'9 local unit tests passed','paid_development_calls':0})
 save(DATA/'FREEZE.json',{'at':now(),'order':json.loads((DATA/'order.json').read_text()),'files':files})
 save(DATA/'HANDOFF.json',{'phase':'frozen','next':'python -m evidence_kernel.run','instructions':'Forty fixed slots. Keep all outcomes. Reconcile unknown calls from persisted generation IDs before continuation. Do not edit protocol/fixtures or retry failed slots. Finish with manual assistant adjudication and report.'})
 print('PASS: frozen 40 slots; credentials and guards verified')
if __name__=='__main__':main()
