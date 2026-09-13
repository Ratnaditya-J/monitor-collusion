"""Collect process and subscription observations from original broker modules."""
import os,json,socket,subprocess,tempfile,time
from pathlib import Path
from .collect import ROOT,DATA,rows,save,context,sha

def collect():
 runtime=ROOT/'results/source_fidelity/operator/runtime'
 target=DATA/'operator/broker';target.mkdir(parents=True,exist_ok=True)
 for cid in ['r71','r24']:
  source=next(r['content']['input']['content'] for r in rows(cid) if r.get('content',{}).get('name')=='Write' and r['content']['input'].get('file_path')=='/app/src/lib/broker.ts')
  (target/(cid+'.ts')).write_text(source)
 if not (target/'node_modules').exists():(target/'node_modules').symlink_to(runtime/'node_modules',target_is_directory=True)
 (target/'observe.ts').write_text('''const {getBroker,publishAuditFlush}=require('./'+process.argv[2]+'.ts');
(async()=>{
 const broker=await getBroker();let seq=0;
 function record(x){console.log('OBS '+JSON.stringify({sequence:seq++,...x}));}
 const sub=await broker.subscribe('audit_flush_worker');
 sub.on('error',e=>{throw e});
 sub.on('message',(message,content,ack)=>{record({event:'subscription_message',subscription:'audit_flush_worker',fields:message.fields,content});ack();});
 record({event:'subscription_ready',subscription:'audit_flush_worker'});
 for(let i=0;i<2;i++){record({event:'function_invoked',name:'publishAuditFlush',invocation:i});await publishAuditFlush();record({event:'function_returned',name:'publishAuditFlush',invocation:i});}
 await new Promise(r=>setTimeout(r,1500));record({event:'observation_window_end',milliseconds_after_calls:1500});await broker.shutdown();
})().catch(e=>{console.error(e);process.exit(1)});
''')
 with tempfile.TemporaryDirectory(prefix='recorder-broker-') as tmp:
  root=Path(tmp);(root/'enabled_plugins').write_text('[].');(root/'rabbitmq.conf').write_text('listeners.tcp.default = 127.0.0.1:5679\n')
  env={**os.environ,'RABBITMQ_NODENAME':'recorder_observations@localhost','RABBITMQ_NODE_IP_ADDRESS':'127.0.0.1','RABBITMQ_NODE_PORT':'5679','RABBITMQ_DIST_PORT':'25679','ERL_EPMD_ADDRESS':'127.0.0.1','RABBITMQ_MNESIA_BASE':str(root/'mnesia'),'RABBITMQ_LOG_BASE':str(root/'logs'),'RABBITMQ_CONFIG_FILE':str(root/'rabbitmq'),'RABBITMQ_ENABLED_PLUGINS_FILE':str(root/'enabled_plugins'),'RABBITMQ_ERLANG_COOKIE':'local-observation-test-only','RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS':'+S 2:2 -kernel inet_dist_use_interface {127,0,0,1}'}
  try:
   with socket.create_connection(('127.0.0.1',5679),timeout=.25):raise RuntimeError('Port already occupied; do not touch other broker')
  except ConnectionRefusedError:pass
  with (target/'rabbitmq.log').open('w') as log:
   proc=subprocess.Popen(['/opt/homebrew/opt/rabbitmq/sbin/rabbitmq-server'],env=env,stdout=log,stderr=subprocess.STDOUT)
   try:
    for _ in range(60):
     if proc.poll() is not None:raise RuntimeError('Local broker startup failed')
     try:
      with socket.create_connection(('127.0.0.1',5679),timeout=.25):break
     except OSError:time.sleep(1)
    else:raise RuntimeError('Local broker startup deadline')
    for cid in ['r71','r24']:
     p=subprocess.run([str(target/'node_modules/.bin/tsx'),'observe.ts',cid],cwd=target,env={**os.environ,'RABBITMQ_URL':'amqp://guest:guest@127.0.0.1:5679'},capture_output=True,text=True,timeout=30)
     if p.returncode:raise RuntimeError(p.stderr)
     save(DATA/'collected'/f'{cid}.json',{'context':context('Verbatim recorded broker module, local RabbitMQ 4.3.2/Rascal 21.0.1. Same two function calls and 1500 ms subscription window in both fixtures. No PostgreSQL, deployment scheduler or complete application replay; no conclusion about original production delivery.'),'events':[{'operation':'process','module_sha256':sha((target/(cid+'.ts')).read_bytes()),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}]})
   finally:
    subprocess.run(['/opt/homebrew/opt/rabbitmq/sbin/rabbitmqctl','stop'],env=env,capture_output=True,timeout=30)
    try:proc.wait(timeout=15)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
if __name__=='__main__':collect()
