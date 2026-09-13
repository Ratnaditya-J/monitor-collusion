"""Read-only reconciliation against OpenRouter generation history."""
import json,urllib.request
from decimal import Decimal
from .qwen import DATA,Client,key,save

def reconcile():
    c=Client();rows=[]
    for row in c.summary()['calls']:
        p=DATA/'api'/(row['id']+'.response.json')
        if not p.exists():
            maps=[json.loads(x.read_text()) for x in DATA.glob('timeout_reconciliation*.json')]
            match=next((x for x in maps if x['call']==row['id']),None)
            if not match:raise RuntimeError('Missing billing mapping '+row['id'])
            r={'id':match['generation']}
        else:r=json.loads(p.read_text())
        out=DATA/'billing'/(row['id']+'.json')
        if out.exists():g=json.loads(out.read_text())
        else:
            req=urllib.request.Request('https://openrouter.ai/api/v1/generation?id='+r['id'],headers={'Authorization':'Bearer '+key()})
            g=json.load(urllib.request.urlopen(req,timeout=30));save(out,g)
        cost=Decimal(str(g['data']['total_cost']))
        rows.append({'call':row['id'],'generation':r['id'],'response_cost':row['cost'],'generation_cost':str(cost),'matches':cost==Decimal(row['cost']),'provider':g['data'].get('provider_name'),'model':g['data'].get('model')})
    save(DATA/'billing_reconciliation.json',{'checks':rows,'all_match':all(r['matches'] for r in rows),'generation_cost_usd':str(sum((Decimal(r['generation_cost']) for r in rows),Decimal(0))),'note':'Read-only OpenRouter generation history, not bank invoice.'})
    print('Reconciled',len(rows),'requests; all match:',all(r['matches'] for r in rows))

if __name__=='__main__':reconcile()
