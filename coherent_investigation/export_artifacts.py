"""Export verifiable observations/anchors without copying any private signing keys."""
import json,shutil
from .fixtures import ROOT,DATA,STUDY,save,digest

def run():
 manifest={};destroot=STUDY/'artifacts'
 # All held-out frozen data, including operator scoring keys for reproducible adjudication.
 freeze=json.loads((DATA/'FREEZE.json').read_text())
 paths=[ROOT/name for name in freeze['files'] if name.startswith('results/coherent_investigation/')]
 # Preserve development trajectories, failed approaches and their public signing evidence.
 for folder in ['packets','checks']:
  paths+=list((DATA/folder).rglob('*.json'))
 for pattern in ['*/bundle.json','*/checks.bundle.json','*/anchor.json','*.answer.json']:
  paths+=list((DATA/'operator/development').glob(pattern))
 paths+=list((DATA/'operator/derivations_before_index').rglob('*.json'))
 paths+=list((DATA/'operator/derivations_before_held_variant').rglob('*.json'))
 paths+=list(DATA.glob('DEVELOPMENT*'))
 for p in sorted(set(paths)):
  if not p.is_file():continue
  if 'keys' in p.parts or p.suffix=='.pem':raise RuntimeError('Private key export forbidden')
  relative=p.relative_to(DATA);out=destroot/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
  manifest[str(p.relative_to(ROOT))]={'artifact':str(out.relative_to(STUDY)),'sha256':digest(out.read_bytes())}
 save(STUDY/'ARTIFACT_MANIFEST.json',manifest)
 # Final responses only; no hidden reasoning copied from raw API responses.
 for p in sorted((DATA/'audits').glob('development*.json')):
  d=json.loads(p.read_text());out=STUDY/'development_assessments'/(p.stem+'.json');save(out,{'case':d['case'],'condition':d['condition'],'assessment':d['assessment'],'gate':d.get('gate'),'response_ids':[t['response_id'] for t in d['trace']],'raw_source_sha256':digest(p.read_bytes())})
 for p in sorted((DATA/'failures').glob('development*.json')):
  d=json.loads(p.read_text());save(STUDY/'development_failures'/p.name,{'case':d['case'],'condition':d['condition'],'error':d['error'],'response_ids':[t['response_id'] for t in d.get('trace',[])],'paid_request_count':len(list((DATA/'api').glob('coherent_'+p.stem+'_*.request.json'))),'raw_source_sha256':digest(p.read_bytes())})
 print('Exported',len(manifest),'observation/verification artifacts; no private keys')
if __name__=='__main__':run()
