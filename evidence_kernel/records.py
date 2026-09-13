"""Independent host recorder and anchored signed envelopes using SpineFrame primitives.

For archive imports, signatures attest to import integrity, not historical truth.
"""
import hashlib,json,uuid
from pathlib import Path
from .vendor.spineframe import signing,events
from .vendor.spineframe.hashing import compute_root_hash

def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(x).hexdigest()

def seal(records,artifacts,context,key_dir):
    chain=[];previous='0'*64
    for seq,record in enumerate(records):
        item={'sequence':seq,'previous_hash':previous,'record':record}
        previous=digest(canonical(item));chain.append({**item,'hash':previous})
    content={'context':context,'records':chain,'artifacts':artifacts}
    # Sequence is bound inside every record. The context and artifact identities are bound too.
    root=compute_root_hash([digest(canonical(content))])
    bundle={'run':{'run_id':context['run_id'],'query':'Recorded agent activity','created_at':context['created_at']},'root_hash':root,'sources':[],'chunks':[],'claims':[],'evidence':[],'content':content}
    return signing.sign_bundle(bundle,signer=context['recorder'],key_dir=Path(key_dir))

def verify(bundle,trusted_key,expected_run_id,files=None):
    """Caller supplies key and run binding out-of-band; never trust a bundle's key alone."""
    try:
        sig=bundle['signature'];content=bundle['content'];context=content['context']
        if sig['algorithm']!='Ed25519' or sig['public_key']!=trusted_key:raise ValueError('Untrusted signing key or algorithm')
        if context['run_id']!=expected_run_id or bundle['run']['run_id']!=expected_run_id:raise ValueError('Wrong run binding')
        if context['recorder']!=sig['signer'] or context['created_at']!=bundle['run']['created_at']:raise ValueError('Metadata binding mismatch')
        previous='0'*64
        for seq,item in enumerate(content['records']):
            expected={'sequence':seq,'previous_hash':previous,'record':item['record']}
            if item['sequence']!=seq or item['previous_hash']!=previous or item['hash']!=digest(canonical(expected)):raise ValueError('Record chain mismatch')
            previous=item['hash']
        if bundle['root_hash']!=compute_root_hash([digest(canonical(content))]):raise ValueError('Content root mismatch')
        if not signing.verify_bundle_signature(bundle)['valid']:raise ValueError('Signature invalid')
        if files is not None:
            if set(files)!=set(content['artifacts']):raise ValueError('Artifact set mismatch')
            for name,data in files.items():
                if digest(data)!=content['artifacts'][name]:raise ValueError('Artifact content mismatch: '+name)
        return {'valid':True,'run_id':expected_run_id,'record_count':len(content['records']),'authenticated_artifacts':sorted(content['artifacts']),'capture_mode':context['capture_mode'],'scope':'Integrity since recording/import under the pinned host key. No conclusion about legitimacy, completeness before capture, or intent.'}
    except (KeyError,TypeError,ValueError) as e:return {'valid':False,'error':str(e),'scope':'Evidence cannot be trusted as presented; this alone does not establish target wrongdoing.'}

class Recorder:
    """Host owns directory/key and invokes tool itself; target receives no signing capability."""
    def __init__(self,root,key_dir,actor,authorization):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.key_dir=Path(key_dir)
        self.actor=actor;self.authorization=authorization;self.run_id=uuid.uuid4().hex
    def call(self,name,args,operation):
        call_id=uuid.uuid4().hex
        events.emit(self.root,'tool_requested',actor=self.actor,data={'call_id':call_id,'tool':name,'arguments':args,'authorization_record':self.authorization})
        try:
            result=operation()
            events.emit(self.root,'tool_returned',actor=self.actor,data={'call_id':call_id,'result':result})
            return result
        except Exception as e:
            events.emit(self.root,'tool_failed',actor=self.actor,data={'call_id':call_id,'error_type':type(e).__name__});raise
    def export(self):
        return seal(events.read_all(self.root),{},dict(run_id=self.run_id,created_at=events._now(),recorder='host-tool-recorder',capture_mode='host-mediated-tool-call'),self.key_dir)
