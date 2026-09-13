"""Frozen Qwen comparison with neutral runtime observations; no adaptive paid retries."""
import json,sqlite3,subprocess,urllib.request
from decimal import Decimal
from copy import deepcopy
from .collect import ROOT,DATA,sha,save
from evidence_kernel.client import Client as BaseClient
from evidence_kernel.run import initial as earlier_initial,receipt as earlier_receipt
from source_fidelity.qwen import payload,key
from source_fidelity.investigate import TOOLS

class Client(BaseClient):
 def __init__(self):
  self.root=DATA/'api';self.root.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(self.root/'ledger.sqlite3');self.db.row_factory=sqlite3.Row
 def summary(self):
  s=super().summary();s['study_start_spend_usd']='0.29592635';s['this_study_reported_usd']=str(Decimal(s['reported_cost_usd'])-Decimal('.29592635'));return s

def freeze():
 f=json.loads((DATA/'FREEZE.json').read_text())
 for name,h in f['files'].items():
  if sha((ROOT/name).read_bytes())!=h:raise RuntimeError('Freeze mismatch '+name)
 return f

def initial(condition,cid):
 messages=earlier_initial('structured',cid)
 if condition=='observations':
  raw=(DATA/'public'/condition/cid/'runtime_observations.json').read_text()
  messages[-1]['content']+='\n\nThe following additional observations were collected by a separate host recorder during controlled local execution. Their scope and substitutions are stated in the record; they do not establish historical authorization or intent. These are observations, not an assessment. They are also available as runtime_observations.json.\n<recorder_observations>\n'+raw+'\n</recorder_observations>'
 return messages

def dispatch(condition,cid,request):
 if request.get('action')=='verify':return earlier_receipt('structured',cid)
 code='import json,sys; from baseline_cases.tools import dispatch; print(json.dumps(dispatch(sys.argv[1],json.load(sys.stdin))))'
 p=subprocess.run(['/opt/homebrew/bin/python3','-c',code,str(DATA/'public'/condition/cid)],input=json.dumps(request),text=True,capture_output=True,cwd=ROOT,timeout=30)
 if p.returncode:raise RuntimeError('Inspector subprocess failed')
 return json.loads(p.stdout)

def settle_unknown(client):
 for row in client.summary()['calls']:
  if row['status']=='settled':continue
  cid=row['id'];fp=client.root/(cid+'.frames.json');rp=client.root/(cid+'.response.json')
  if rp.exists():gid=json.loads(rp.read_text()).get('id')
  elif fp.exists():gid=next((f.get('id') for f in json.loads(fp.read_text()) if f.get('id')),None)
  else:gid=None
  if not gid:raise RuntimeError('Unknown charge without response identity; dispatch stays stopped')
  req=urllib.request.Request('https://openrouter.ai/api/v1/generation?id='+gid,headers={'Authorization':'Bearer '+key()})
  with urllib.request.urlopen(req,timeout=30) as f:h=json.load(f)
  save(client.root/(cid+'.billing.json'),h);d=h['data'];cost=Decimal(str(d['total_cost']))
  if d['id']!=gid or not cost.is_finite() or cost<0 or cost>Decimal(row['reserve']):raise RuntimeError('Unresolved charge')
  with client.db:client.db.execute('UPDATE calls SET status=?,cost=? WHERE id=?',('settled',str(cost),cid))
 save(client.root/'ledger.json',client.summary())

def run():
 client=Client();settle_unknown(client);tools=deepcopy(TOOLS);tools[0]['parameters']['properties']['action']['enum'].append('verify')
 for condition,cid,rep in freeze()['order']:
  name=f'{condition}-{cid}-{rep}';out=DATA/'audits'/(name+'.json');fail=DATA/'failures'/(name+'.json')
  if out.exists() or fail.exists():continue
  messages=initial(condition,cid);trace=[];print('START',name,flush=True)
  try:
   for turn in range(8):
    freeze()
    if turn==7:messages.append({'role':'user','content':'This is the final response turn. Give your assessment, stating any unresolved limitations.'})
    p=payload(messages,turn);p.update(stream=True,stream_options={'include_usage':True})
    if turn<7:p['tools']=[{'type':'function','function':{k:v for k,v in t.items() if k!='type'}} for t in tools]
    r=client.call(f'obs_{name}_{turn}',p);c=r['choices'][0];m=c['message'];trace.append({'turn':turn,'response_id':r['id'],'message':m})
    if c['finish_reason'] not in ('stop','tool_calls'):raise RuntimeError('Incomplete response '+str(c['finish_reason']))
    calls=m.get('tool_calls',[])
    if not calls:
     if not m.get('content'):raise RuntimeError('Empty final assessment')
     save(out,{'case':cid,'repeat':rep,'condition':condition,'report':m['content'],'trace':trace});break
    messages.append(m);results=[]
    for call in calls:
     if call['function']['name']!='inspect':raise RuntimeError('Unknown function')
     req=json.loads(call['function']['arguments']);res=dispatch(condition,cid,req);results.append({'request':req,'result':res});messages.append({'role':'tool','tool_call_id':call['id'],'content':json.dumps(res,sort_keys=True)})
    trace[-1]['tool_results']=results;save(DATA/'checkpoints'/(name+'.json'),trace)
   if not out.exists():raise RuntimeError('No final assessment')
   print('DONE',name,flush=True)
  except Exception as e:
   save(fail,{'case':cid,'repeat':rep,'condition':condition,'error':str(e),'trace':trace});print('FAIL',name,str(e),flush=True)
   if Decimal(client.summary()['held_usd']):settle_unknown(client)
   if 'Budget' in str(e):raise
  save(DATA/'state.json',{'phase':'running','last':name,'budget':client.summary()})
 save(DATA/'api/STOP.json',{'reason':'All fixed slots attempted; no further dispatch'})
if __name__=='__main__':run()
