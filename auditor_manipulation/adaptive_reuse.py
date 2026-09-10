"""Lossless duplicate-envelope normalization and verified prior-call reuse."""
import copy
import json
import time
from pathlib import Path

from .core import canonical, digest, strict_json
from .runner import inspect_response, model_body, write_json
from .workspace_runner import Bank, read
from .coalition import without_actor_text_limits


def continuation_request(body):
    """Normalize only target system character instructions, never evidence."""
    body=copy.deepcopy(body)
    if (body.get('messages') and body['messages'][0].get('role')=='system' and
        body['messages'][0]['content'].startswith('You are one participant in a controlled, synthetic auditor-influence study.')):
        body['messages'][0]['content']=without_actor_text_limits(body['messages'][0]['content'])
    return body


def prior_call(source,label,seen=None):
    """Resolve a recorded reuse chain without treating it as a new dispatch."""
    seen=set() if seen is None else seen
    source=Path(source).resolve()
    if source in seen:raise ValueError('Cyclic reuse chain')
    seen.add(source)
    plan=read(source/'plan.private.json')
    ledger=read(source/'ledger.json')
    if digest(plan)!=ledger['plan_sha256']:raise ValueError('Source plan changed')
    call=ledger['calls'].get(label)
    if call and call['state']=='done':
        saved=read(source/(call['call_id']+'.json'))
        if digest(saved['request'])!=call['request_sha256'] or inspect_response(saved['raw_response'])!=saved['response']:
            raise ValueError('Prior request/response integrity failure')
        return source,plan,call,saved
    path=source/(digest(label)[:24]+'.reuse.json')
    if not path.exists():return None
    receipt=read(path)
    parent=Path(receipt['source'])
    if (parent.resolve()!=Path(plan['config'].get('reuse_source','')).resolve() or
        digest(read(parent/'plan.private.json'))!=receipt['source_plan_sha256']):
        raise ValueError('Unverified reuse parent')
    resolved=prior_call(parent,label,seen)
    if resolved is not None:
        _,_,call,saved=resolved
        if (call['call_id']!=receipt['source_call_id'] or digest(saved['request'])!=receipt['request_sha256'] or
            digest(saved['response'])!=receipt['response_sha256']):
            raise ValueError('Reuse receipt changed')
    return resolved


def normalize_identical_json(text):
    """Collapse 2-4 identical JSON objects, never choose between alternatives."""
    if not isinstance(text,str) or len(text)>100000:
        return text
    decoder=json.JSONDecoder()
    position=0
    objects=[]
    try:
        while position<len(text):
            while position<len(text) and text[position].isspace():position+=1
            if position==len(text):break
            start=position
            _,position=decoder.raw_decode(text,position)
            value=strict_json(text[start:position])
            if not isinstance(value,dict):return text
            objects.append(canonical(value))
            if len(objects)>4:return text
        if 2<=len(objects)<=4 and len(set(objects))==1:
            return objects[0]
    except (ValueError,TypeError,RecursionError):
        pass
    return text


class RecoveryBank(Bank):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        source=self.plan['config'].get('reuse_source')
        self.source=Path(source) if source else None
        self.reused={}
        if self.source:
            old=read(self.source/'plan.private.json')
            if digest(old)!=self.plan['reuse_source_plan_sha256']:
                raise ValueError('Source plan changed')
            if old['development_cases']!=self.plan['development_cases'] or old['holdout_cases']!=self.plan['holdout_cases']:
                raise ValueError('Source case plan differs')

    def wait_for_source_case(self,case):
        if not self.source:return
        prefix='development/'+case['case_id']
        path=self.source/(digest(prefix)[:24]+'.result.json')
        started=time.monotonic()
        while True:
            if path.exists() and read(path).get('state') in (
                'completed','baseline_not_calibrated','infrastructure_incomplete','no_eligible_attack','playbook_unavailable'):
                return
            ledger=read(self.source/'ledger.json')
            if ledger['state'] not in ('running','ready'):
                return
            if time.monotonic()-started>7200:
                raise RuntimeError('Source case did not settle within two hours')
            time.sleep(2)

    def call(self,label,model,messages):
        response=None
        if self.source and label not in self.ledger['calls']:
            resolved=prior_call(self.source,label)
            if resolved:
                source,source_plan,call,saved=resolved
                body=model_body(self.plan['config']['models'][model],messages)
                expected=digest(body)
                exact=call['request_sha256']==expected
                amended=(self.plan['config'].get('reuse_without_actor_text_limits') and
                         self.plan['config'].get('disable_actor_text_limits') and
                         continuation_request(saved['request'])==body)
                if saved['response']['generation_status']=='ok' and (exact or amended):
                    response=copy.deepcopy(saved['response'])
                    receipt={'label':label,'source':str(source),'source_call_id':call['call_id'],
                             'source_plan_sha256':digest(source_plan),
                             'request_sha256':call['request_sha256'],'response_sha256':digest(response),
                             'effective_request_sha256':expected,
                             'reuse_mode':'exact' if exact else 'historical_response_character_limit_amendment'}
                    with self.lock:
                        self.reused[label]=receipt
                        write_json(self.directory/(digest(label)[:24]+'.reuse.json'),receipt)
        if response is None:
            response=super().call(label,model,messages)
        if self.plan['config'].get('normalize_identical_json') and response.get('generation_status')=='ok':
            original=response['text']
            normalized=normalize_identical_json(original)
            if normalized!=original:
                response=copy.deepcopy(response)
                response['text']=normalized
                response['identical_json_normalized']=True
                write_json(self.directory/(digest(label)[:24]+'.normalization.json'),{
                    'label':label,'original_text_sha256':digest(original),'normalized_text_sha256':digest(normalized),
                    'operation':'Collapse identical JSON envelopes; no semantic edit.'})
        return response
