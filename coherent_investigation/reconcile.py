"""Reconcile saved paid requests using read-only provider history; never resend."""
import json,urllib.request
from decimal import Decimal
from .fixtures import DATA,save
from .transport import Client
from source_fidelity.qwen import key

def run():
 c=Client();rows=[]
 for row in c.summary()['calls']:
  cid=row['id']
  if not cid.startswith('coherent_'):continue
  gid=None
  for suffix in ['response.json','identity.json','identity-recovery.json']:
   p=c.root/(cid+'.'+suffix)
   if p.exists():
    d=json.loads(p.read_text());gid=d.get('id') or d.get('generation')
    if gid:break
  if not gid:
   p=c.root/(cid+'.frames.json')
   if p.exists():gid=next((x['id'] for x in json.loads(p.read_text()) if x.get('id')),None)
  if not gid:raise RuntimeError('Unresolved request identity: '+cid)
  p=c.root/(cid+'.billing.json')
  if p.exists():h=json.loads(p.read_text())
  else:
   req=urllib.request.Request('https://openrouter.ai/api/v1/generation?id='+gid,headers={'Authorization':'Bearer '+key()})
   with urllib.request.urlopen(req,timeout=30) as f:h=json.load(f)
   save(p,h)
  d=h['data'];cost=Decimal(str(d['total_cost']))
  if d['id']!=gid or not cost.is_finite() or cost<0 or cost>Decimal(row['reserve']):raise RuntimeError('Invalid charge '+cid)
  with c.db:c.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
  rows.append({'request':cid,'generation':gid,'reported_cost':row['cost'],'history_cost':str(cost),'matched':row['cost'] is None or Decimal(row['cost'])==cost})
 s=c.summary();save(c.root/'ledger.json',s)
 totals={split:str(sum((Decimal(r['history_cost']) for r in rows if (('_heldout-' in r['request']) if split=='heldout' else ('_development' in r['request']))),Decimal(0))) for split in ['development','heldout']}
 result={'new_requests':len(rows),'prior_studies_usd':'0.59797310','new_actual_spend_usd':s['this_study_usd'],'cumulative_usd':s['reported_cost_usd'],'remaining_usd':s['available_usd'],'held_usd':s['held_usd'],'phase_costs':totals,'rows':rows}
 save(DATA/'billing_reconciliation.json',result);print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':run()
