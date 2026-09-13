"""Deterministic, label-free archive import for a fixed unsigned/signed comparison."""
import json,shutil,hashlib,random
from pathlib import Path
from .records import seal,digest,canonical,verify
from .vendor.spineframe import signing,events
from source_fidelity.api import save
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'results/spineframe_qwen'

def normalized(raw):
    out=[]
    for line_no,line in enumerate(raw.decode().splitlines(),1):
        x=json.loads(line);c=x.get('content',{})
        out.append({'source_line':line_no,'recorded_role':x.get('role','metadata'),'identity_status':'Role label from imported benchmark, not authenticated historical identity','event_type':c.get('type','metadata') if isinstance(c,dict) else 'text','event':x})
    return out

def prepare():
    if (DATA/'FREEZE.json').exists():raise RuntimeError('Already frozen')
    keys=DATA/'operator/keys';signing.generate_keypair(keys)
    trust={};order=[]
    fixture_manifest=json.loads((ROOT/'evidence_kernel/fixtures/MANIFEST.json').read_text())
    for cid,meta in fixture_manifest['cases'].items():
            raw=(ROOT/'evidence_kernel/fixtures'/(cid+'.jsonl')).read_bytes()
            assert digest(raw)==meta['sha256']
            indexed=normalized(raw);index=b''.join(canonical(x)+b'\n' for x in indexed)
            identity={'run_id':'archive-'+cid,'created_at':events._now(),'recorder':'monitor-collusion-importer','capture_mode':'historical-transcript-import','source_sha256':digest(raw),'authorization_scope':'Original user requests are inside the transcript. No authenticated historical authorization or actor identity is asserted.'}
            artifact_bytes={'transcript.jsonl':raw,'action_records.jsonl':index,'capture_context.json':(json.dumps(identity,indent=2)+'\n').encode()}
            bundle=seal(indexed,{k:digest(v) for k,v in artifact_bytes.items()},identity,keys)
            pub=signing.public_key_hex(keys);receipt=verify(bundle,pub,identity['run_id'],artifact_bytes)
            assert receipt['valid'];trust[cid]={'key':pub,'run_id':identity['run_id'],'root_hash':bundle['root_hash']}
            for condition in ['structured','verified']:
                d=DATA/'public'/condition/cid;d.mkdir(parents=True,exist_ok=True)
                for name,b in artifact_bytes.items():(d/name).write_bytes(b)
                # Equal semantic content. Only signed condition supplies a cryptographic envelope.
                save(d/'capture_context.json',identity)
                if condition=='verified':save(d/'signed_bundle.json',bundle)
                for rep in [1,2]:order.append([condition,cid,rep])
    random.Random(130926).shuffle(order)
    save(DATA/'operator/trust.json',trust);save(DATA/'order.json',order)
    save(DATA/'state.json',{'phase':'prepared','paid_calls':0,'planned_assessments':40})
    print('Prepared',len(order),'slots; no model calls')
if __name__=='__main__':prepare()
