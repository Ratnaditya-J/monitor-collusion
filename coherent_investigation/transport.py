"""Immutable request IDs, conservative per-request reservations, no paid retries."""
import hashlib,json,sqlite3,urllib.request,urllib.error
from decimal import Decimal
from evidence_kernel.client import Client as StreamClient,assemble
from source_fidelity.qwen import key,MODEL
from source_fidelity.api import hard_deadline,NoRedirect,canonical
from .fixtures import DATA,save
CAP=Decimal('1');START=Decimal('.59797310')
class Client(StreamClient):
 def __init__(self):
  self.root=DATA/'api';self.root.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(self.root/'ledger.sqlite3');self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,sha TEXT,status TEXT,reserve TEXT,cost TEXT)');self.db.commit()
 def summary(self):
  rows=[dict(r) for r in self.db.execute('SELECT * FROM calls')];spent=sum((Decimal(r['cost'] or '0') for r in rows),Decimal(0));held=sum((Decimal(r['reserve']) for r in rows if r['status']!='settled'),Decimal(0))
  return {'cap_usd':'1','reported_cost_usd':str(spent),'held_usd':str(held),'available_usd':str(CAP-spent-held),'this_study_usd':str(spent-START),'calls':rows}
 @staticmethod
 def reserve(p):
  if len(p['messages'])>2 or 'tools' in p or any(m['role'] not in ['system','user'] for m in p['messages']):raise RuntimeError('Reservation only supports the fixed tool-free two-message protocol')
  return (Decimal(len(canonical(p).encode())+2048)*Decimal('.15')+Decimal(p['max_tokens']))/1000000
 def read_stream(self,response,cid):
  frames=[]
  # Append-only journal avoids rewriting an ever-growing reasoning stream per token.
  try:
   with (self.root/(cid+'.stream.jsonl')).open('a') as journal:
    for line in response:
     if not line.startswith(b'data:'):continue
     data=line[5:].strip()
     if data==b'[DONE]':break
     frame=json.loads(data);frames.append(frame);journal.write(json.dumps(frame)+'\n');journal.flush()
     if len(frames)==1 and frame.get('id'):save(self.root/(cid+'.identity.json'),{k:frame[k] for k in ['id','model','provider'] if k in frame})
     if 'error' in frame:raise RuntimeError('Provider streaming error')
     if frame.get('usage',{}).get('cost') is not None and any(c.get('finish_reason') for f in frames for c in f.get('choices',[])):break
  finally:save(self.root/(cid+'.frames.json'),frames)
  return assemble(frames)
 def call(self,cid,p):
  credential=key();body=canonical(p).encode();h=hashlib.sha256(body).hexdigest();reserve=self.reserve(p)
  assert len(body)+4096+p['max_tokens']<262144
  self.db.execute('BEGIN IMMEDIATE');prior=self.db.execute('SELECT * FROM calls WHERE id=?',(cid,)).fetchone()
  if prior:
   self.db.rollback()
   if prior['sha']!=h or prior['status']!='settled':raise RuntimeError('Existing changed or unresolved request')
   return json.loads((self.root/(cid+'.response.json')).read_text())
  s=self.summary()
  if (self.root/'STOP.json').exists() or Decimal(s['held_usd']) or reserve>Decimal(s['available_usd']):self.db.rollback();raise RuntimeError('Budget or billing stop')
  self.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',(cid,h,'reserved',str(reserve),None));self.db.commit();save(self.root/(cid+'.request.json'),p)
  try:
   req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=body,headers={'Authorization':'Bearer '+credential,'Content-Type':'application/json'})
   with hard_deadline(300):
    with urllib.request.build_opener(NoRedirect).open(req,timeout=300) as response:
     save(self.root/(cid+'.headers.json'),{k:v for k,v in response.headers.items() if k.lower() in ['x-request-id','x-generation-id','cf-ray','content-type','date']})
     r=self.read_stream(response,cid) if 'text/event-stream' in response.headers.get('Content-Type','') else json.load(response)
   save(self.root/(cid+'.response.json'),r)
   if r.get('model')!=MODEL or r.get('provider')!='Parasail':raise RuntimeError('Model/provider mismatch')
   cost=Decimal(str(r.get('usage',{}).get('cost','NaN')))
   if not cost.is_finite() or cost<0 or cost>reserve:raise RuntimeError('Unresolved cost')
   with self.db:self.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
   save(self.root/'ledger.json',self.summary());return r
  except BaseException as e:
   save(self.root/(cid+'.error.json'),{'type':type(e).__name__,'message':str(e),'http_status':getattr(e,'code',None),'headers':{k:v for k,v in getattr(e,'headers',{}).items() if k.lower() in ['x-request-id','x-generation-id','cf-ray','date']}})
   with self.db:self.db.execute('UPDATE calls SET status=? WHERE id=?',('unknown',cid))
   save(self.root/'ledger.json',self.summary());raise
