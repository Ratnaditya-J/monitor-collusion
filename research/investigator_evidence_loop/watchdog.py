"""Wall-clock supervisor for the frozen request deadlines; no API dispatch."""
import datetime as dt,json,os,signal,sqlite3,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PID=int(sys.argv[1]);API=ROOT/'results/investigator_evidence_loop/api'
signaled=set()
while True:
    p=subprocess.run(['ps','-p',str(PID),'-o','command='],capture_output=True,text=True)
    if p.returncode or not any(x in p.stdout for x in ['-m investigator_evidence_loop.study','-m investigator_evidence_loop.scoring','research/investigator_evidence_loop/complete_grading.py']):break
    db=sqlite3.connect(API/'ledger.sqlite3');db.row_factory=sqlite3.Row
    pending=[dict(r) for r in db.execute("SELECT * FROM calls WHERE status='reserved'")];db.close()
    for row in pending:
        if row['id'] in signaled:continue
        record=json.loads(row['record']);start=dt.datetime.fromisoformat(record['at'])
        limit=180 if row['id'].endswith(('_select','_select_recovery1')) else 600
        elapsed=(dt.datetime.now(dt.timezone.utc)-start).total_seconds()
        if elapsed>limit+5:
            # Re-check process identity immediately before signaling.
            cmd=subprocess.run(['ps','-p',str(PID),'-o','command='],capture_output=True,text=True)
            if cmd.returncode or cmd.stdout!=p.stdout:raise SystemExit('Worker identity changed')
            os.kill(PID,signal.SIGALRM);signaled.add(row['id'])
            with (API.parent/'watchdog-events.jsonl').open('a') as f:
                f.write(json.dumps({'at':dt.datetime.now(dt.timezone.utc).isoformat(),'request':row['id'],'elapsed_wall_seconds':elapsed,'deadline_seconds':limit,'action':'SIGALRM invokes frozen timeout/recovery handler'})+'\n')
    time.sleep(10)
