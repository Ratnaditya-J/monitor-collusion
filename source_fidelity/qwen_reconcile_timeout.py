"""Settle a transport failure using an operator-matched generation ID; never retry it."""
import datetime,json,sys,urllib.request
from decimal import Decimal
from .qwen import DATA,Client,key,save

def reconcile(cid,gid):
    c=Client();row=c.db.execute('SELECT * FROM calls WHERE id=?',(cid,)).fetchone()
    assert row and row['status']=='unknown'
    g=json.load(urllib.request.urlopen(urllib.request.Request('https://openrouter.ai/api/v1/generation?id='+gid,headers={'Authorization':'Bearer '+key()}),timeout=30));d=g['data']
    assert d['provider_name']=='Parasail' and d['model']=='qwen/qwen3.5-35b-a3b-20260224'
    assert d['user_agent']=='Python-urllib/3.14'
    start=datetime.datetime.fromisoformat(d['created_at'].replace('Z','+00:00')).timestamp()
    assert abs(start-(DATA/'api'/(cid+'.request.json')).stat().st_mtime)<2
    assert Decimal(str(d['total_cost']))<=Decimal(row['reserve'])
    assert sum(r['status']=='unknown' for r in c.summary()['calls'])==1
    save(DATA/'billing'/(cid+'.json'),g)
    save(DATA/('timeout_reconciliation-'+cid+'.json'),{'call':cid,'generation':gid,'match_basis':'Only pending request; matching timestamp within two seconds, model/provider and user agent; ID located in UI generation history.','cost':d['total_cost'],'assessment_status':'unscorable; no paid retry; no response body recovered'})
    with c.db:c.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(d['total_cost']),cid))
    save(DATA/'api/ledger.json',c.summary());print('Reconciled',cid,d['total_cost'])

if __name__=='__main__':reconcile(*sys.argv[1:])
