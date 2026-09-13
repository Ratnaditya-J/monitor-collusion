"""Read-only generation-history reconciliation; never resends a paid request."""
import json,urllib.request
from decimal import Decimal
from .run import Client
from source_fidelity.qwen import key
from source_fidelity.api import save,now

def run():
 c=Client();rows=[]
 for row in c.summary()['calls']:
  cid=row['id']
  if not cid.startswith('obs_'):continue
  classification=c.root/(cid+'.billing-classification.json')
  if classification.exists():
   evidence=json.loads(classification.read_text());assert evidence['http_status'] in (429,524) and evidence['completion_stream_received'] is False and evidence['cost_usd']=='0'
   rows.append({'request':cid,'generation':evidence['generation'],'reported_cost':row['cost'],'history_cost':'0','matched':row['cost']=='0','basis':'Verified upstream rejection and zero-output billing policy; no generation history record'})
   continue
  path=c.root/(cid+'.response.json');frames=c.root/(cid+'.frames.json')
  if path.exists():gid=json.loads(path.read_text()).get('id')
  elif frames.exists():gid=next((f.get('id') for f in json.loads(frames.read_text()) if f.get('id')),None)
  else:gid=None
  recovered=c.root/(cid+'.identity-recovery.json')
  if not gid and recovered.exists():gid=json.loads(recovered.read_text())['generation']
  if not gid:raise RuntimeError('Missing response identity: '+cid)
  dest=c.root/(cid+'.billing.json')
  if dest.exists():history=json.loads(dest.read_text())
  else:
   req=urllib.request.Request('https://openrouter.ai/api/v1/generation?id='+gid,headers={'Authorization':'Bearer '+key()})
   with urllib.request.urlopen(req,timeout=30) as f:history=json.load(f)
   save(dest,history)
  d=history['data'];cost=Decimal(str(d['total_cost']))
  if d['id']!=gid or not cost.is_finite() or cost<0 or cost>Decimal(row['reserve']):raise RuntimeError('Billing verification failed: '+cid)
  prior=row['cost']
  with c.db:c.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
  rows.append({'request':cid,'generation':gid,'reported_cost':prior,'history_cost':str(cost),'matched':prior is None or Decimal(prior)==cost})
 save(c.root/'ledger.json',c.summary())
 total=sum((Decimal(r['history_cost']) for r in rows),Decimal(0))
 result={'at':now(),'new_requests':len(rows),'new_actual_spend_usd':str(total),'prior_baseline_usd':'0.29592635','cumulative_cost_usd':c.summary()['reported_cost_usd'],'available_usd':c.summary()['available_usd'],'held_usd':c.summary()['held_usd'],'rows':rows}
 save(c.root.parent/'billing_reconciliation.json',result)
 print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':run()
