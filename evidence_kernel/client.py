"""Budgeted Qwen transport with persisted streaming frames and no automatic paid retries."""
import hashlib,json,sqlite3,urllib.request
from decimal import Decimal
from .prepare import DATA
from source_fidelity.qwen import key,MODEL,CAP
from source_fidelity.api import canonical,save,hard_deadline,NoRedirect

class Client:
 def __init__(self):
  self.root=DATA/'api';self.root.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(self.root/'ledger.sqlite3');self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,sha TEXT,status TEXT,reserve TEXT,cost TEXT)');self.db.commit()
 def summary(self):
  rows=[dict(r) for r in self.db.execute('SELECT * FROM calls')];cost=sum((Decimal(r['cost'] or '0') for r in rows),Decimal(0));held=sum((Decimal(r['reserve']) for r in rows if r['status']!='settled'),Decimal(0))
  return {'cap_usd':str(CAP),'reported_cost_usd':str(cost),'held_usd':str(held),'available_usd':str(CAP-cost-held),'calls':rows,'prior_baseline_usd':'0.09902675'}
 def call(self,cid,p):
  credential=key();body=canonical(p).encode();h=hashlib.sha256(body).hexdigest();bound=len(body)+4096
  if bound+24576>262144:raise RuntimeError('Conservative context bound exceeded')
  reserve=(Decimal(bound)*Decimal('.15')+Decimal(24576))/1000000
  self.db.execute('BEGIN IMMEDIATE');prior=self.db.execute('SELECT * FROM calls WHERE id=?',(cid,)).fetchone()
  if prior:
   self.db.rollback()
   if prior['sha']!=h or prior['status']!='settled':raise RuntimeError('Existing unresolved or changed request')
   return json.loads((self.root/(cid+'.response.json')).read_text())
  s=self.summary()
  if (self.root/'STOP.json').exists() or Decimal(s['held_usd']) or reserve>Decimal(s['available_usd']):self.db.rollback();raise RuntimeError('Budget or billing stop')
  self.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',(cid,h,'reserved',str(reserve),None));self.db.commit();save(self.root/(cid+'.request.json'),p)
  try:
   req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=body,headers={'Authorization':'Bearer '+credential,'Content-Type':'application/json'})
   with hard_deadline(300):
    with urllib.request.build_opener(NoRedirect).open(req,timeout=300) as response:
     if 'text/event-stream' in response.headers.get('Content-Type',''):r=self.read_stream(response,cid)
     else:r=json.load(response)
   save(self.root/(cid+'.response.json'),r)
   if r.get('model')!=MODEL or r.get('provider')!='Parasail':raise RuntimeError('Model/provider mismatch')
   cost=Decimal(str(r.get('usage',{}).get('cost','NaN')))
   if not cost.is_finite() or cost<0 or cost>reserve:raise RuntimeError('Unresolved cost')
   with self.db:self.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
   save(self.root/'ledger.json',self.summary());return r
  except BaseException:
   with self.db:self.db.execute('UPDATE calls SET status=? WHERE id=?',('unknown',cid))
   save(self.root/'ledger.json',self.summary());raise
 def read_stream(self,response,cid):
  frames=[]
  for line in response:
   if not line.startswith(b'data:'):continue
   data=line[5:].strip()
   if data==b'[DONE]':break
   frame=json.loads(data);frames.append(frame);save(self.root/(cid+'.frames.json'),frames)
   if 'error' in frame:raise RuntimeError('Provider streaming error')
   # Usage is the completion marker. Avoid waiting for an HTTP connection to close.
   if frame.get('usage',{}).get('cost') is not None and any(c.get('finish_reason') for f in frames for c in f.get('choices',[])):break
  return assemble(frames)

def assemble(frames):
 message={'role':'assistant','content':''};calls={};details={};r={'choices':[{'message':message,'finish_reason':None}]}
 for f in frames:
  for k in ['id','model','provider','usage']:
   if f.get(k) is not None:r[k]=f[k]
  for c in f.get('choices',[]):
   if c.get('index',0)!=0:raise RuntimeError('Unexpected extra choice')
   if c.get('finish_reason'):r['choices'][0]['finish_reason']=c['finish_reason']
   d=c.get('delta',c.get('message',{}))
   if d.get('content'):message['content']+=d['content']
   for t in d.get('tool_calls',[]):
    i=t.get('index',0);v=calls.setdefault(i,{'type':'function','id':'','function':{'name':'','arguments':''}})
    if t.get('id'):v['id']=t['id']
    for k in ['name','arguments']:
     if t.get('function',{}).get(k):v['function'][k]+=t['function'][k]
   for item in d.get('reasoning_details',[]):
    i=item.get('index',0);v=details.setdefault(i,{k:x for k,x in item.items() if k not in ('text','data','summary')})
    for k in ['text','data','summary']:
     if item.get(k):v[k]=v.get(k,'')+item[k]
 if calls:message['tool_calls']=[calls[i] for i in sorted(calls)]
 if details:message['reasoning_details']=[details[i] for i in sorted(details)]
 return r
