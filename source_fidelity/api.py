# Source-fidelity client. Carries forward ALL previous baseline costs/reservations under the SAME $10 ceiling.
"""Direct OpenAI client with durable reservations, no automatic retries or tools."""
import datetime as dt
from contextlib import contextmanager
import signal
import threading
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import urllib.request
import urllib.error

CAP=Decimal('10')
MODEL='gpt-6-astra'

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def save(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as f:
        f.write(json.dumps(x,indent=2)+'\n');f.flush();os.fsync(f.fileno())
    tmp.replace(path)

def metered_cost(record):
    u=record.get('usage')
    if not u:return Decimal(0)
    details=u.get('input_tokens_details',{})
    write=details.get('cache_write_tokens',0);cached=details.get('cached_tokens',0)
    ordinary=u['input_tokens']-write-cached
    if min(write,cached,ordinary)<0:raise BudgetStop('Inconsistent cache metering')
    factor=Decimal('.5') if record['service_tier']=='flex' else Decimal(1)
    return (Decimal(ordinary)*10+Decimal(write)*Decimal('12.5')+Decimal(cached)+Decimal(u['output_tokens'])*50)*factor/1000000

class BudgetStop(RuntimeError):pass
@contextmanager
def hard_deadline(seconds=1200):
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Paid client must run in the main thread for deadline enforcement')
    def expired(signum,frame):raise TimeoutError('Paid request exceeded elapsed-time deadline')
    previous=signal.signal(signal.SIGALRM,expired)
    old_timer=signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,*old_timer)
        signal.signal(signal.SIGALRM,previous)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

class Client:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'ledger.sqlite3',timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, sha TEXT, status TEXT, reserve TEXT, cost TEXT, record TEXT)')
        self.db.commit()
    def summary(self):
        rows=[dict(r) for r in self.db.execute('SELECT * FROM calls ORDER BY rowid')]
        spent=sum((Decimal(r['cost'] or '0') for r in rows),Decimal(0))
        held=sum((Decimal(r['reserve']) for r in rows if r['status'] in ('reserved','unknown','capped_unknown')),Decimal(0))
        metered=sum((metered_cost(json.loads(r['record'])) for r in rows if r['status']=='settled'),Decimal(0))
        return dict(cap_usd=str(CAP),metered_charge_usd=str(metered),usage_priced_upper_bound_usd=str(spent),unresolved_reserved_usd=str(held),available_usd=str(CAP-spent-held),calls=rows,
                    accounting_basis='Metered charge uses returned token/cache details and documented tier rates; enforcement uses higher all-input cache-write pricing. Not invoice reconciliation.')
    def reserve(self,call_id,payload):
        body=canonical(payload);sha=hashlib.sha256(body.encode()).hexdigest()
        # For our text-only requests, UTF-8 bytes plus framing allowance conservatively bound input tokens.
        input_bound=len(body.encode())+2048
        if input_bound>272000:raise BudgetStop('Long-context pricing not supported by this study')
        # Reserve standard rates including possible cache-write premium, even when requesting Flex.
        reserve=(Decimal(input_bound)*Decimal('12.5')+Decimal(payload['max_output_tokens'])*50)/1000000
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prior=self.db.execute('SELECT * FROM calls WHERE id=?',(call_id,)).fetchone()
            if prior:
                if prior['sha']!=sha:raise BudgetStop('Request ID reused with changed inputs')
                if prior['status']=='settled':self.db.rollback();return None
                raise BudgetStop('Request already attempted; no automatic duplicate')
            if (self.root/'STOP.json').exists():raise BudgetStop('Study closed: read STOP.json before any new dispatch')
            s=self.summary()
            if any(r['status'] in ('reserved','unknown') for r in s['calls']):raise BudgetStop('Unbounded or active request blocks new dispatch')
            if reserve>Decimal(s['available_usd']):raise BudgetStop('Reservation would exceed baseline cap')
            self.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)',(call_id,sha,'reserved',str(reserve),None,canonical({'at':now(),'input_token_bound':input_bound})))
            self.db.commit()
        except BaseException:
            self.db.rollback();raise
        save(self.root/(call_id+'.request.json'),payload)
        return body.encode()
    def retain_failed_request_cap(self,call_id):
        """Keep the full known request ceiling held; never claim its actual bill is known."""
        row=self.db.execute('SELECT * FROM calls WHERE id=?',(call_id,)).fetchone()
        if not row or row['status'] not in ('unknown','capped_unknown'):raise BudgetStop('Only stopped unresolved requests can be capped')
        payload=json.loads((self.root/(call_id+'.request.json')).read_text())
        if hashlib.sha256(canonical(payload).encode()).hexdigest()!=row['sha']:raise BudgetStop('Cannot establish original request')
        if payload.get('model')!=MODEL or payload.get('service_tier')!='flex' or len(canonical(payload).encode())+2048>272000:raise BudgetStop('Request pricing cannot be bounded')
        expected=(Decimal(len(canonical(payload).encode())+2048)*Decimal('12.5')+Decimal(payload['max_output_tokens'])*50)/1000000
        if expected!=Decimal(row['reserve']):raise BudgetStop('Reservation mismatch')
        if (self.root/(call_id+'.response.json')).exists():raise BudgetStop('Response exists; reconcile metering instead')
        if row['status']=='capped_unknown':return
        record={'at':now(),'prior':json.loads(row['record']),'actual_charge':'unknown','maximum_charge_permanently_reserved_usd':str(expected),'basis':'Exact text-only request; standard cache-write/input and maximum output rates; no retries or automatic tier fallback.'}
        with self.db:self.db.execute('UPDATE calls SET status=?,record=? WHERE id=?',('capped_unknown',canonical(record),call_id))
        save(self.root/'ledger.json',self.summary())

    def call(self,call_id,messages,max_output_tokens=16384,effort='high',deadline_seconds=600,tools=None):
        payload=dict(model=MODEL,input=messages,max_output_tokens=max_output_tokens,reasoning={'effort':effort},service_tier='flex',store=False)
        if tools is not None:payload['tools']=tools
        if not os.environ.get('OPENAI_API_KEY'):raise BudgetStop('Credential missing; no request sent')
        body=self.reserve(call_id,payload)
        if body is None:return json.loads((self.root/(call_id+'.response.json')).read_text())
        key=os.environ.get('OPENAI_API_KEY')
        if not key:raise BudgetStop('Credential missing after reservation; no request sent')
        try:
            req=urllib.request.Request('https://api.openai.com/v1/responses',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
            with hard_deadline(deadline_seconds):
                with urllib.request.build_opener(NoRedirect).open(req,timeout=deadline_seconds) as response:
                    result=json.load(response)
            save(self.root/(call_id+'.response.json'),result)
            if result.get('model') != MODEL:raise BudgetStop('Returned model identity changed; stop study')
            usage=result.get('usage')
            if not usage or result.get('service_tier') not in ('flex','default'):
                raise BudgetStop('Missing usage or unpriced service tier; reserve retained')
            for k in ('input_tokens','output_tokens'):
                if not isinstance(usage.get(k),int) or usage[k]<0:raise BudgetStop('Invalid usage')
            factor=Decimal('.5') if result['service_tier']=='flex' else Decimal(1)
            cost=(Decimal(usage['input_tokens'])*Decimal('12.5')+Decimal(usage['output_tokens'])*50)*factor/1000000
            # This is deliberately an upper bound: all input charged at cache-write rate.
            reserve=Decimal(self.db.execute('SELECT reserve FROM calls WHERE id=?',(call_id,)).fetchone()[0])
            if cost>reserve:raise BudgetStop('Usage exceeds reserved bound; halt for accounting review')
            with self.db:self.db.execute('UPDATE calls SET status=?,cost=?,record=? WHERE id=?',('settled',str(cost),canonical({'at':now(),'response_id':result.get('id'),'model':result.get('model'),'service_tier':result['service_tier'],'usage':usage,'response_status':result.get('status')}),call_id))
            save(self.root/'ledger.json',self.summary())
            return result
        except BaseException as exc:
            # Rejections and timeouts remain reserved until explicitly reconciled; never silent retries.
            with self.db:self.db.execute('UPDATE calls SET status=?,record=? WHERE id=?',('unknown',canonical({'at':now(),'error_type':type(exc).__name__,'http_status':getattr(exc,'code',None)}),call_id))
            save(self.root/'ledger.json',self.summary())
            raise

def output_text(r):
    return '\n'.join(c.get('text','') for item in r.get('output',[]) for c in item.get('content',[]) if c.get('type')=='output_text')
