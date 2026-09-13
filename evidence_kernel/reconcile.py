"""Read-only generation-history reconciliation; never resends a paid request."""
import json,urllib.request
from decimal import Decimal
from .client import Client
from source_fidelity.qwen import key
from source_fidelity.api import save,now

def run():
 c=Client();rows=[]
 for row in c.summary()['calls']:
  cid=row['id']
  if not cid.startswith('evidence_'):continue
  path=c.root/(cid+'.response.json');frames=c.root/(cid+'.frames.json')
  if path.exists():gid=json.loads(path.read_text()).get('id')
  elif frames.exists():gid=next((f.get('id') for f in json.loads(frames.read_text()) if f.get('id')),None)
  else:gid=None
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
 result={'at':now(),'new_requests':len(rows),'new_actual_spend_usd':str(total),'prior_baseline_usd':'0.09902675','cumulative_cost_usd':c.summary()['reported_cost_usd'],'available_usd':c.summary()['available_usd'],'held_usd':c.summary()['held_usd'],'rows':rows}
 save(c.root.parent/'billing_reconciliation.json',result)
 print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':run()
