"""Read-only export of full final reports and explicit unblinded adjudication."""
import json
from collections import Counter
from .fixtures import DATA,ROOT,STUDY,save,digest
CONDITIONS=['ordinary','checks','staged']
CATEGORIES=['correct_finding','false_accusation','unsupported_clearance','appropriate_unresolved','unresolved','correct_clearance','other_error','operational_failure']
def run():
 f=json.loads((DATA/'FREEZE.json').read_text());notes=json.loads((DATA/'review_notes.json').read_text());rows=[]
 (STUDY/'assessments').mkdir(exist_ok=True);(STUDY/'failures').mkdir(exist_ok=True)
 for cid,c in f['order']:
  name=f'heldout-{cid}-{c}';path=DATA/'audits'/(name+'.json');failure=DATA/'failures'/(name+'.json');answer=json.loads((DATA/'operator/heldout'/(cid+'.answer.json')).read_text())
  row={'slot':name,'case':cid,'condition':c,'family':answer['family'],'expected':answer['expected']}
  if path.exists():
   assert not failure.exists();d=json.loads(path.read_text());assert name in notes,'Unreviewed final report '+name
   assert notes[name]['outcome'] in CATEGORIES and notes[name]['outcome']!='operational_failure'
   packet=json.loads((DATA/'packets/heldout'/(cid+'.json')).read_text());ids={e['data']['call_id'] for e in packet['events']}
   refs=[r for finding in d['assessment']['findings'] if isinstance(finding,dict) and isinstance(finding.get('evidence_call_ids',[]),list) for r in finding.get('evidence_call_ids',[])]
   invalid=[r for r in refs if not isinstance(r,str) or r not in ids]
   row.update(notes[name]);row.update({'raw_verdict':d['assessment']['verdict'],'invalid_references':invalid,'gate':d.get('gate'),'response_ids':[t['response_id'] for t in d['trace']],'source_sha256':digest(path.read_bytes())})
   text='# '+name+'\n\nVerbatim final response. Adjudication is unblinded Codex review, not independent human validation.\n\n```json\n'+d['trace'][-1]['content']+'\n```\n'
   if d.get('gate') is not None:text+='\nHost reference gate (does not adjudicate semantic correctness):\n\n```json\n'+json.dumps(d['gate'],indent=2)+'\n```\n'
   (STUDY/'assessments'/(name+'.md')).write_text(text)
  elif failure.exists():
   d=json.loads(failure.read_text());row.update({'outcome':'operational_failure','reason':d['error'],'response_ids':[t['response_id'] for t in d.get('trace',[])],'source_sha256':digest(failure.read_bytes())});save(STUDY/'failures'/(name+'.json'),row)
  else:raise RuntimeError('Unfinished slot '+name)
  rows.append(row)
 counts={c:{k:sum(r['condition']==c and r['outcome']==k for r in rows) for k in CATEGORIES} for c in CONDITIONS}
 paired=[{'case':cid,'expected':next(r['expected'] for r in rows if r['case']==cid),'outcomes':{r['condition']:r['outcome'] for r in rows if r['case']==cid}} for cid in sorted({r['case'] for r in rows}) if all(r['outcome']!='operational_failure' for r in rows if r['case']==cid)]
 rejected=[r['slot'] for r in rows if r.get('gate') and not r['gate']['passed']]
 result={'review':'Unblinded full-final-report Codex review. No independent human validation. Raw judgments remain scored if reference gate rejects them.','counts':counts,'rows':rows,'all_three_completed_cases':paired,'gate_rejections':rejected}
 save(DATA/'adjudication.json',result);save(STUDY/'adjudication.json',result)
 lines=['# All thirty held-out outcomes','', '| Case / condition | Expected | Outcome | Reason | Evidence |','|---|---|---|---|---|']
 for r in rows:
  link=f"[Final report](assessments/{r['slot']}.md)" if r['outcome']!='operational_failure' else f"[Failure](failures/{r['slot']}.json)"
  lines.append(f"| {r['case']} / {r['condition']} | {r['expected']} | {r['outcome']} | {r['reason'].replace('|','/')} | {link} |")
 (STUDY/'OUTCOMES.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'counts':counts,'all_three_completed_cases':paired,'gate_rejections':rejected},indent=2))
if __name__=='__main__':run()
