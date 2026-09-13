"""Read-only post-study validation of artifacts, dispatch parity and accounting."""
import json
from decimal import Decimal
from pathlib import Path
from .run import ROOT, DATA, freeze, initial, Client
from .collect import sha
from source_fidelity.qwen import payload
from source_fidelity.api import save

def run():
 f=freeze(); checks=[f"All {len(f['files'])} frozen artifacts unchanged"]
 audits=failures=0
 for condition,cid,rep in f['order']:
  name=f'{condition}-{cid}-{rep}'
  a=DATA/'audits'/(name+'.json');b=DATA/'failures'/(name+'.json')
  assert a.exists()!=b.exists(),name
  audits+=a.exists();failures+=b.exists()
  request=json.loads((DATA/'api'/('obs_'+name+'_0.request.json')).read_text())
  assert request['messages']==initial(condition,cid),name
  expected=payload(initial(condition,cid),0)
  for key in ('model','provider','reasoning','max_tokens'):
   assert request[key]==expected[key],(name,key)
  if condition=='observations':
   raw=(DATA/'public'/condition/cid/'runtime_observations.json').read_text()
   assert raw in request['messages'][-1]['content']
   assert sha(raw.encode())==sha((ROOT/'studies/recorder_observations/observations'/(cid+'.json')).read_bytes())
 for path in (DATA/'api').glob('obs_*.request.json'):
  request=json.loads(path.read_text());expected=payload([],0)
  for key in ('model','provider','reasoning','max_tokens'):assert request[key]==expected[key],(path.name,key)
 checks+=['All 40 fixed slots have exactly one terminal outcome and a saved request', 'Every initial request matches its frozen condition; every observation packet included in full', 'Saved neutral observation copies match used bytes', 'Model/provider/reasoning/output allowance identical across all paid requests']
 notes=json.loads((DATA/'review_notes.json').read_text());assert len(notes)==audits
 assert all(p.stem in notes for p in (DATA/'audits').glob('*.json'))
 checks.append('Every completed final assessment has explicit assistant adjudication')
 c=Client();s=c.summary();assert Decimal(s['held_usd'])==0;assert Decimal(s['reported_cost_usd'])<=Decimal(s['cap_usd'])
 billing=json.loads((DATA/'billing_reconciliation.json').read_text())
 calls=[r for r in s['calls'] if r['id'].startswith('obs_')]
 assert len(calls)==len(billing['rows']);assert all(r['status']=='settled' for r in calls)
 assert all(r['matched'] for r in billing['rows'])
 assert Decimal(billing['new_actual_spend_usd'])+Decimal('.29592635')==Decimal(s['reported_cost_usd'])
 assert (DATA/'api/STOP.json').exists()
 checks+=['All new request costs reconciled or explicitly policy-classified; no unresolved reservations', 'All failed-turn charges included; cumulative Qwen charges within $1', 'Fixed schedule closed without replacement sampling']
 result={'checks':checks,'completed':audits,'operational_failures':failures,'review':'Deterministic post-run checks plus unblinded assistant adjudication; no independent human validation','cost':{k:v for k,v in s.items() if k!='calls'}}
 save(DATA/'FINAL_VALIDATION.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':run()
