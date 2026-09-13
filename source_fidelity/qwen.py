"""Frozen Qwen replication; fresh $1 ledger, pinned provider, no paid retries."""
import hashlib,json,os,re,shlex,sqlite3,urllib.request
from decimal import Decimal
from pathlib import Path
from .api import save,canonical,now,hard_deadline,NoRedirect
from . import investigate as original
from baseline_cases.tools import dispatch
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/qwen_comparison'
MODEL='qwen/qwen3.5-35b-a3b'
CAP=Decimal('1')

def key():
    if os.getenv('OPENROUTER_API_KEY'):return os.environ['OPENROUTER_API_KEY']
    for line in (Path.home()/'.zshrc').read_text().splitlines():
        m=re.match(r'\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*)',line)
        if m:
            token=re.search(r'sk-or-v1-[A-Za-z0-9]+',m[1])
            if token:return token.group(0)
    raise RuntimeError('Credential unavailable')

def payload(messages,turn):
    p=dict(model=MODEL,messages=messages,max_tokens=24576,reasoning={'effort':'high','exclude':False},provider={'only':['parasail/fp8'],'allow_fallbacks':False,'require_parameters':True,'quantizations':['fp8'],'max_price':{'prompt':.15,'completion':1}})
    if turn<7:p['tools']=[{'type':'function','function':{k:v for k,v in t.items() if k!='type'}} for t in original.TOOLS]
    return p

class Client:
    def __init__(self):
        self.root=DATA/'api';self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'ledger.sqlite3');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,sha TEXT,status TEXT,reserve TEXT,cost TEXT)');self.db.commit()
    def summary(self):
        rows=[dict(r) for r in self.db.execute('SELECT * FROM calls')]
        cost=sum((Decimal(r['cost'] or '0') for r in rows),Decimal(0));held=sum((Decimal(r['reserve']) for r in rows if r['status']!='settled'),Decimal(0))
        return {'cap_usd':str(CAP),'reported_cost_usd':str(cost),'held_usd':str(held),'available_usd':str(CAP-cost-held),'calls':rows}
    def call(self,cid,p):
        credential=key();body=canonical(p).encode();h=hashlib.sha256(body).hexdigest()
        # UTF8 bytes conservatively bound text tokens; extra framing allowance.
        bound=len(body)+4096
        if bound+24576>262144:raise RuntimeError('Conservative context bound exceeded')
        reserve=(Decimal(bound)*Decimal('.15')+Decimal(24576))/1000000
        self.db.execute('BEGIN IMMEDIATE')
        prior=self.db.execute('SELECT * FROM calls WHERE id=?',(cid,)).fetchone()
        if prior:
            self.db.rollback()
            if prior['sha']!=h or prior['status']!='settled':raise RuntimeError('Existing unresolved or changed request; no duplicate')
            return json.loads((self.root/(cid+'.response.json')).read_text())
        s=self.summary()
        if (self.root/'STOP.json').exists() or Decimal(s['held_usd']) or reserve>Decimal(s['available_usd']):
            self.db.rollback();raise RuntimeError('Budget or billing stop')
        self.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',(cid,h,'reserved',str(reserve),None));self.db.commit()
        save(self.root/(cid+'.request.json'),p)
        try:
            req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=body,headers={'Authorization':'Bearer '+credential,'Content-Type':'application/json'})
            with hard_deadline(300):
                with urllib.request.build_opener(NoRedirect).open(req,timeout=300) as response:r=json.load(response)
            save(self.root/(cid+'.response.json'),r)
            if r.get('model')!=MODEL or r.get('provider')!='Parasail':raise RuntimeError('Identity/provider mismatch')
            u=r.get('usage',{});cost=Decimal(str(u.get('cost','NaN')))
            if not cost.is_finite() or cost<0 or cost>reserve:raise RuntimeError('Unresolved usage cost')
            with self.db:self.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
            save(self.root/'ledger.json',self.summary());return r
        except BaseException:
            with self.db:self.db.execute('UPDATE calls SET status=? WHERE id=?',('unknown',cid))
            save(self.root/'ledger.json',self.summary());raise

def verify():
    f=json.loads((DATA/'FREEZE.json').read_text())
    for path,h in f['files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise RuntimeError('Freeze mismatch '+path)
    return f

def run():
    client=Client()
    for batch,cid,rep in verify()['order']:
        out=DATA/'audits'/f'{cid}-{rep}.json';fail=DATA/'failures'/f'{cid}-{rep}.json'
        if out.exists() or fail.exists():continue
        original.DATA=ROOT/'results'/batch;messages=original.initial(cid);trace=[]
        print('START',cid,rep,flush=True)
        try:
            for turn in range(8):
                verify()
                if turn==7:messages.append({'role':'user','content':'This is the final response turn. Give your assessment, stating any unresolved limitations.'})
                r=client.call(f'qwen_{cid}_{rep}_{turn}',payload(messages,turn))
                choice=r['choices'][0];m=choice['message'];trace.append({'turn':turn,'response_id':r['id'],'message':m})
                if choice['finish_reason'] not in ('stop','tool_calls'):raise RuntimeError('Incomplete response '+str(choice['finish_reason']))
                calls=m.get('tool_calls',[])
                if not calls:
                    if not m.get('content'):raise RuntimeError('Empty final assessment')
                    save(out,{'case':cid,'repeat':rep,'report':m['content'],'trace':trace});break
                messages.append({k:v for k,v in m.items() if k in ('role','content','tool_calls','reasoning_details')})
                results=[]
                for c in calls:
                    if c['function']['name']!='inspect':raise RuntimeError('Unknown function')
                    req=json.loads(c['function']['arguments']);res=dispatch(original.DATA/'public'/cid,req);results.append({'request':req,'result':res})
                    messages.append({'role':'tool','tool_call_id':c['id'],'content':canonical(res)})
                trace[-1]['tool_results']=results
                save(DATA/'checkpoints'/f'{cid}-{rep}.json',trace)
            if not out.exists():raise RuntimeError('No final assessment')
            print('DONE',cid,rep,flush=True)
        except Exception as e:
            save(fail,{'at':now(),'case':cid,'repeat':rep,'error':str(e),'trace':trace});print('FAIL',cid,rep,str(e),flush=True)
            if Decimal(client.summary()['held_usd']):raise
        save(DATA/'state.json',{'at':now(),'last':[cid,rep],'budget':client.summary()})
    save(DATA/'api/STOP.json',{'at':now(),'reason':'Fixed evaluation finished; no further dispatch'})

if __name__=='__main__':run()
