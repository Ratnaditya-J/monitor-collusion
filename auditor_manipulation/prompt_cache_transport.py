"""Opt-in cache metadata; never change text, roles, order, or model settings."""
import copy
import hashlib
import json
import math
import uuid
from pathlib import Path

from .core import digest
from .runner import now, write_json, inspect_response

SETTINGS = Path(__file__).resolve().parents[1] / 'studies/auditor_manipulation/cache_transport.json'


def json_value_ends(text, wanted):
    """Locate exact top-level JSON value ends without reserializing the text."""
    decoder=json.JSONDecoder()
    position=0
    def spaces(i):
        while i<len(text) and text[i].isspace():i+=1
        return i
    position=spaces(position)
    if position>=len(text) or text[position]!='{':return []
    position+=1
    ends=[]
    while True:
        position=spaces(position)
        if position>=len(text) or text[position]=='}':break
        key,position=decoder.raw_decode(text,position)
        position=spaces(position)
        if text[position]!=':':raise ValueError('Invalid JSON separator')
        _,position=decoder.raw_decode(text,spaces(position+1))
        if key in wanted:ends.append(position)
        position=spaces(position)
        if text[position]=='}':break
        if text[position]!=',':raise ValueError('Invalid JSON separator')
        position+=1
    return ends


def marked_text(text, ends):
    ends=sorted(set(e for e in ends if 0<e<=len(text)))
    blocks=[]
    start=0
    for end in ends:
        blocks.append({'type':'text','text':text[start:end],
                       'prompt_cache_breakpoint':{'mode':'explicit'}})
        start=end
    if start<len(text):blocks.append({'type':'text','text':text[start:]})
    return blocks


def flatten_cache_metadata(body):
    value=copy.deepcopy(body)
    value.pop('prompt_cache_key',None)
    value.pop('prompt_cache_options',None)
    for message in value.get('messages',[]):
        content=message.get('content')
        if isinstance(content,list):
            if any(set(b)-{'type','text','prompt_cache_breakpoint'} or b.get('type')!='text' for b in content):
                raise ValueError('Only text cache blocks are supported')
            message['content']=''.join(b['text'] for b in content)
    return value


def cache_request(body):
    if any(k in body for k in ('prompt_cache_key','prompt_cache_options')):
        raise ValueError('Existing cache configuration must not be overwritten')
    value=copy.deepcopy(body)
    messages=value.get('messages',[])
    if not messages or any(not isinstance(m.get('content'),str) for m in messages):
        raise ValueError('Expected the study text-message format')
    if messages[0]['role']!='system':raise ValueError('Expected study system prompt')
    system=messages[0]['content']
    value['prompt_cache_key']=hashlib.sha256((body['model']+'\n'+system).encode()).hexdigest()
    # Retain automatic caching, adding at most three explicit breakpoints.
    # There is no output/response cache: every study call still generates anew.
    value['prompt_cache_options']={'ttl':'30m'}
    marks={0:[len(system)]}
    if system.startswith('You are one participant in a controlled, synthetic auditor-influence study.'):
        if len(messages)>1:
            marks[1]=json_value_ends(messages[1]['content'],{'inbox','previous_practice_feedback'})
    else:
        users=[i for i,m in enumerate(messages) if m['role']=='user']
        for index in ([users[0]] if users else [])+([users[-2]] if len(users)>1 else []):
            marks[index]=[len(messages[index]['content'])]
    for index,ends in marks.items():
        if ends:messages[index]['content']=marked_text(messages[index]['content'],ends)
    if flatten_cache_metadata(value)!=body:raise AssertionError('Cache transform changed study input')
    return value


def flex_request(body):
    """Change only the explicitly authorized service tier and routing price cap."""
    if body.get('model')!='openai/gpt-6-astra-pro' or 'service_tier' in body:
        raise ValueError('Unexpected Flex source request')
    value=copy.deepcopy(body)
    value['service_tier']='flex'
    value['provider'].update(only=['openai/flex'],allow_fallbacks=False,
                             max_price={'prompt':5,'completion':25})
    return value


def flex_response_error(raw):
    """Require observed tier and a conservative Flex billing ceiling on success."""
    if raw.get('http_status')!=200:return None
    body=raw.get('body') or {}
    if body.get('error'):return None
    if (body.get('service_tier')!='flex' or body.get('provider')!='OpenAI'
            or body.get('model')!='openai/gpt-6-astra-pro'):
        return 'flex_route_mismatch'
    usage=body.get('usage') or {}
    values=[usage.get(k) for k in ('prompt_tokens','completion_tokens','cost')]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in values):
        return 'flex_billing_unverified'
    prompt,completion,cost=values
    # Even if every input token were a cache write, this bounds the Flex cost.
    # Apply the published long-context rate when applicable; do not truncate.
    ceiling=prompt*(.0000125 if prompt>272000 else .00000625)+completion*(.0000375 if prompt>272000 else .000025)
    if cost>ceiling+1e-6:return 'flex_billing_exceeds_ceiling'
    return None


def inspect_transport_response(raw):
    response=inspect_response(raw)
    error=(raw.get('flex_validation') or {}).get('error')
    if error:
        response.update(generation_status='error',failure=error)
    return response


def dispatch_cached(request,path,key,payload,timeout):
    """Enable only for an opted-in, matching in-flight study request."""
    if path!='/chat/completions' or not isinstance(payload,dict) or not SETTINGS.exists():
        return request(path,key,payload,timeout=timeout)
    settings=json.loads(SETTINGS.read_text())
    if not settings.get('enabled') or payload.get('model')!=settings['model']:
        return request(path,key,payload,timeout=timeout)
    directory=Path(settings['run_directory'])
    ledger=json.loads((directory/'ledger.json').read_text())
    logical_sha=digest(payload)
    matching=[label for label,c in ledger['calls'].items()
              if c['state']=='in_flight' and c['request_sha256']==logical_sha]
    if not matching:return request(path,key,payload,timeout=timeout)
    if settings.get('halt_new_requests') or (directory/'flex-route-halt.json').exists():
        return {'http_status':None,'transport_paused':True,
                'billing_disposition':'not_dispatched',
                'body':{'error':{'message':'Study paused by user; request was not sent to provider.'}}}
    wire=cache_request(payload)
    use_flex=settings.get('service_tier')=='flex'
    if use_flex:wire=flex_request(wire)
    journal=directory/'cache-transport'
    journal.mkdir(exist_ok=True)
    identifier=uuid.uuid4().hex
    metadata={'version':1,'started_at':now(),'logical_request_sha256':logical_sha,
              'wire_request_sha256':digest(wire),'matching_labels':matching,
              'wire_file':identifier+'.request.json','text_roles_order_and_settings_unchanged':True,
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if use_flex:
        metadata.update(version=2,service_tier='flex',text_roles_order_and_settings_unchanged=False,
                        text_roles_order_and_generation_settings_unchanged=True,
                        routing_amendment='flex-transport-amendment.json')
    write_json(journal/metadata['wire_file'],wire)
    write_json(journal/(identifier+'.metadata.json'),metadata)
    raw=request(path,key,wire,timeout=timeout)
    raw['prompt_cache_optimization']=metadata
    if use_flex:
        error=flex_response_error(raw)
        raw['flex_validation']={'error':error,'service_tier':(raw.get('body') or {}).get('service_tier')}
        if error:
            write_json(directory/'flex-route-halt.json',{'recorded_at':now(),'error':error,
                       'wire_request_sha256':digest(wire),'response_id':(raw.get('body') or {}).get('id')})
    usage=(raw.get('body') or {}).get('usage',{})
    write_json(journal/(identifier+'.usage.json'),{'finished_at':now(),'http_status':raw.get('http_status'),
               'logical_request_sha256':logical_sha,'usage':usage,
               'service_tier':(raw.get('body') or {}).get('service_tier'),
               'flex_validation':raw.get('flex_validation')})
    return raw
