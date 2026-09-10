import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from auditor_manipulation.core import canonical,digest
from auditor_manipulation import prompt_cache_transport as cache


class PromptCacheTests(unittest.TestCase):
    def body(self):
        return {'model':'openai/gpt-6-astra-pro','max_tokens':8192,
                'reasoning':{'effort':'high','exclude':True},
                'provider':{'only':['openai'],'allow_fallbacks':False},
                'messages':[{'role':'system','content':'You are one participant in a controlled, synthetic auditor-influence study. Rules.'},
                            {'role':'user','content':canonical({'inbox':[{'text':'Comma, brace } and unicode α🙂'}],
                               'previous_practice_feedback':{'text':'Exact evidence.\nKeep every byte.'},
                               'shared_wiki':{'wiki/x.md':'long '*7000}})}]}

    def test_exact_input_roundtrip_and_bounded_metadata(self):
        body=self.body();before=copy.deepcopy(body)
        wire=cache.cache_request(body)
        self.assertEqual(body,before)
        self.assertEqual(cache.flatten_cache_metadata(wire),body)
        self.assertEqual(len(wire['prompt_cache_key']),64)
        self.assertNotEqual(wire['prompt_cache_options'].get('mode'),'explicit')
        self.assertEqual(sum('prompt_cache_breakpoint' in b for m in wire['messages']
                             for b in m['content'] if isinstance(b,dict)),3)
        self.assertIn('long '*7000,wire['messages'][1]['content'][-1]['text'])

    def test_investigator_roles_history_and_evidence_are_identical(self):
        body=self.body();body['messages'][0]['content']='Investigator instructions.'
        body['messages'] += [{'role':'assistant','content':'{"actions":[]}'},
                             {'role':'user','content':'first tool results'},
                             {'role':'assistant','content':'other actions'},
                             {'role':'user','content':'second tool results'}]
        wire=cache.cache_request(body)
        self.assertEqual(cache.flatten_cache_metadata(wire),body)
        self.assertEqual([m['role'] for m in wire['messages']],[m['role'] for m in body['messages']])
        self.assertIsInstance(wire['messages'][-1]['content'],str)

    def test_flex_changes_only_tier_and_route_and_preserves_full_input(self):
        body=self.body();before=copy.deepcopy(body)
        wire=cache.flex_request(cache.cache_request(body))
        flat=cache.flatten_cache_metadata(wire)
        self.assertEqual(flat,cache.flex_request(body))
        self.assertEqual(body,before)
        self.assertEqual(flat['messages'],body['messages'])
        self.assertEqual(flat['reasoning'],body['reasoning'])
        self.assertEqual(flat['max_tokens'],8192)
        self.assertEqual(flat['provider']['only'],['openai/flex'])
        self.assertFalse(flat['provider']['allow_fallbacks'])
        self.assertEqual(flat['provider']['max_price'],{'prompt':5,'completion':25})

    def test_flex_rejects_standard_or_unknown_tier_and_excess_billing(self):
        raw={'http_status':200,'body':{'model':'openai/gpt-6-astra-pro','provider':'OpenAI',
             'service_tier':'flex','usage':{'prompt_tokens':1000,'completion_tokens':1000,'cost':.03}}}
        self.assertIsNone(cache.flex_response_error(raw))
        for tier in ('default',None,'priority'):
            wrong=copy.deepcopy(raw);wrong['body']['service_tier']=tier
            self.assertEqual(cache.flex_response_error(wrong),'flex_route_mismatch')
        raw['body']['usage']['cost']=.06
        self.assertEqual(cache.flex_response_error(raw),'flex_billing_exceeds_ceiling')
        raw['body']['usage']['cost']=None
        self.assertEqual(cache.flex_response_error(raw),'flex_billing_unverified')

    def test_flex_mismatch_preserves_response_and_prevents_further_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);settings=root/'settings.json';body=self.body()
            settings.write_text(json.dumps({'enabled':True,'model':body['model'],
                'run_directory':str(root),'service_tier':'flex'}))
            (root/'ledger.json').write_text(json.dumps({'calls':{'a':{
                'state':'in_flight','request_sha256':digest(body)}}}))
            original={'http_status':200,'body':{'service_tier':'default','usage':{'cost':.06}}}
            calls=[]
            def request(path,key,payload,timeout):
                calls.append(payload);return copy.deepcopy(original)
            with patch.object(cache,'SETTINGS',settings):
                result=cache.dispatch_cached(request,'/chat/completions','unused',body,10)
                self.assertEqual(result['body'],original['body'])
                self.assertEqual(result['flex_validation']['error'],'flex_route_mismatch')
                paused=cache.dispatch_cached(request,'/chat/completions','unused',body,10)
                self.assertEqual(paused['billing_disposition'],'not_dispatched')
                self.assertEqual(len(calls),1)

    def test_scoped_dispatch_records_actual_wire_and_does_not_cache_responses(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);settings=root/'settings.json';body=self.body()
            settings.write_text(json.dumps({'enabled':True,'model':body['model'],'run_directory':str(root)}))
            (root/'ledger.json').write_text(json.dumps({'calls':{'a':{'state':'in_flight','request_sha256':digest(body)}}}))
            calls=[]
            def request(path,key,payload,timeout):
                calls.append(payload)
                return {'http_status':200,'body':{'usage':{'prompt_tokens':2000,'prompt_tokens_details':{'cached_tokens':1500}},'id':str(len(calls))}}
            with patch.object(cache,'SETTINGS',settings):
                first=cache.dispatch_cached(request,'/chat/completions','unused',body,10)
                second=cache.dispatch_cached(request,'/chat/completions','unused',body,10)
                self.assertEqual(len(calls),2)
                self.assertNotEqual(first['body']['id'],second['body']['id'])
                self.assertEqual(cache.flatten_cache_metadata(calls[0]),body)
                self.assertEqual(len(list((root/'cache-transport').glob('*.request.json'))),2)
                other=copy.deepcopy(body);other['max_tokens']=777
                raw=cache.dispatch_cached(request,'/chat/completions','unused',other,10)
                self.assertNotIn('prompt_cache_optimization',raw)
                self.assertEqual(calls[-1],other)


if __name__=='__main__':unittest.main()
