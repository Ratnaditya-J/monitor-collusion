import json, tempfile, unittest
from decimal import Decimal
from pathlib import Path
from investigator_evidence_loop.api import Client, BudgetStop
from investigator_evidence_loop.fixtures import validate, retrieve, DATA, verify
from investigator_evidence_loop.study import preflight

class BudgetTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.c=Client(self.tmp.name);self.p={'max_output_tokens':100,'input':'hello'}
    def tearDown(self):self.c.db.close();self.tmp.cleanup()
    def test_unknown_blocks_and_duplicate_never_dispatches(self):
        self.assertIsInstance(self.c.reserve('one',self.p),bytes)
        for cid in ['one','two']:
            with self.assertRaises(BudgetStop):self.c.reserve(cid,self.p)
    def test_cap_and_long_context(self):
        for p in [{'max_output_tokens':600001},{'max_output_tokens':1,'input':'x'*272000}]:
            with self.assertRaises(BudgetStop):self.c.reserve('over',p)
        self.assertEqual(len(self.c.summary()['calls']),0)
    def test_cache_and_changed_request(self):
        self.c.reserve('one',self.p)
        with self.c.db:self.c.db.execute("UPDATE calls SET status='settled',cost='0.01' WHERE id='one'")
        self.assertIsNone(self.c.reserve('one',self.p))
        with self.assertRaises(BudgetStop):self.c.reserve('one',{'max_output_tokens':101})
        self.assertEqual(Decimal(self.c.summary()['available_usd']),Decimal('29.99'))
    def test_key_not_persisted(self):
        self.c.reserve('one',self.p)
        self.assertNotIn('OPENAI_API_KEY',(Path(self.tmp.name)/'one.request.json').read_text())

class FixtureTests(unittest.TestCase):
    def test_all_truths_and_tamper_checks(self):self.assertEqual(len(validate()),10)
    def test_tool_isolation(self):
        case=json.loads((DATA/'fixtures/r-482.json').read_text())
        with self.assertRaises(ValueError):retrieve(case,{'read':['../../results/investigator_evidence_loop/operator/answer-key.json']})
        with self.assertRaises(ValueError):retrieve(case,{'shell':'cat secret'})
        self.assertFalse(verify({'payload':{},'signature':'x'})['signature_valid'])
    def test_input_bytes_are_reserved_in_addition_to_output(self):
        from investigator_evidence_loop.study import estimate
        self.assertGreater(estimate([{'role':'user','content':'x'*1000}],100),Decimal('0.005'))

if __name__=='__main__':unittest.main()

class ClosureTests(unittest.TestCase):
    def test_closed_study_blocks_new_requests(self):
        with tempfile.TemporaryDirectory() as d:
            c=Client(d);(Path(d)/'STOP.json').write_text('{}')
            with self.assertRaises(BudgetStop):c.reserve('new',{'max_output_tokens':1})
            self.assertEqual(c.summary()['calls'],[]);c.db.close()
    def test_elapsed_deadline_interrupts(self):
        import time
        from investigator_evidence_loop.api import hard_deadline
        with self.assertRaises(TimeoutError):
            with hard_deadline(.02):time.sleep(.2)
    def test_metered_cache_breakdown(self):
        from investigator_evidence_loop.api import metered_cost
        r={'service_tier':'flex','usage':{'input_tokens':100,'input_tokens_details':{'cached_tokens':20,'cache_write_tokens':30},'output_tokens':10}}
        self.assertEqual(metered_cost(r),Decimal('0.0006975'))
    def test_action_timestamp_tampering_is_detected(self):
        case=json.loads((DATA/'fixtures/d-670.json').read_text())
        self.assertTrue(retrieve(case,{'verify':['audit/origin.json']})['verify:audit/origin.json']['activity_digest_matches'])
        case['files']['audit/activity.json'][2]['at']=10
        self.assertFalse(retrieve(case,{'verify':['audit/origin.json']})['verify:audit/origin.json']['activity_digest_matches'])

class ClientIntegrationTests(unittest.TestCase):
    def test_success_reconciles_and_resumes_without_network(self):
        import io
        from unittest.mock import patch,MagicMock
        from investigator_evidence_loop.api import MODEL
        response={'id':'mock-response','model':MODEL,'service_tier':'flex','status':'completed','usage':{'input_tokens':20,'input_tokens_details':{'cache_write_tokens':0,'cached_tokens':0},'output_tokens':10}}
        with tempfile.TemporaryDirectory() as d:
            client=Client(d);opener=MagicMock();opener.open.return_value=io.BytesIO(json.dumps(response).encode())
            with patch.dict('os.environ',{'OPENAI_API_KEY':'test-placeholder'}),patch('urllib.request.build_opener',return_value=opener):
                a=client.call('once',[{'role':'user','content':'test'}],100)
                b=client.call('once',[{'role':'user','content':'test'}],100)
            self.assertEqual(a,b);self.assertEqual(opener.open.call_count,1)
            self.assertEqual(client.summary()['metered_charge_usd'],'0.00035');client.db.close()
    def test_transport_failure_reserves_and_blocks(self):
        from unittest.mock import patch,MagicMock
        with tempfile.TemporaryDirectory() as d:
            client=Client(d);opener=MagicMock();opener.open.side_effect=TimeoutError('simulated')
            with patch.dict('os.environ',{'OPENAI_API_KEY':'test-placeholder'}),patch('urllib.request.build_opener',return_value=opener):
                with self.assertRaises(TimeoutError):client.call('failed',[{'role':'user','content':'test'}],100)
            self.assertEqual(client.summary()['calls'][0]['status'],'unknown')
            with self.assertRaises(BudgetStop):client.reserve('replacement',{'max_output_tokens':100})
            client.db.close()

class BoundedRecoveryTests(unittest.TestCase):
    def test_capped_failure_stays_reserved_without_freezing_safe_dispatch(self):
        from investigator_evidence_loop.api import MODEL,canonical
        p={'model':MODEL,'service_tier':'flex','max_output_tokens':100,'input':[{'role':'user','content':'test'}]}
        with tempfile.TemporaryDirectory() as d:
            c=Client(d);c.reserve('old',p)
            with c.db:c.db.execute("UPDATE calls SET status='unknown' WHERE id='old'")
            held=Decimal(c.summary()['unresolved_reserved_usd']);c.retain_failed_request_cap('old')
            self.assertEqual(Decimal(c.summary()['unresolved_reserved_usd']),held)
            self.assertIsInstance(c.reserve('new',p),bytes)
            self.assertGreater(Decimal(c.summary()['unresolved_reserved_usd']),held)
            with self.assertRaises(BudgetStop):c.reserve('old',p)
            c.db.close()

class RecoveryPolicyTests(unittest.TestCase):
    def test_only_transport_failure_gets_one_recovery(self):
        import io
        from unittest.mock import patch,MagicMock
        from investigator_evidence_loop.api import MODEL
        from investigator_evidence_loop.study import request
        r={'model':MODEL,'service_tier':'flex','status':'completed','usage':{'input_tokens':10,'input_tokens_details':{'cache_write_tokens':0,'cached_tokens':0},'output_tokens':5}}
        with tempfile.TemporaryDirectory() as d:
            c=Client(d);opener=MagicMock();opener.open.side_effect=[TimeoutError('mock'),io.BytesIO(json.dumps(r).encode())]
            with patch.dict('os.environ',{'OPENAI_API_KEY':'test-placeholder'}),patch('urllib.request.build_opener',return_value=opener),patch('investigator_evidence_loop.study.preflight'),patch('investigator_evidence_loop.study.save'):
                request(c,'logical',[{'role':'user','content':'test'}],100)
            self.assertEqual(opener.open.call_count,2)
            self.assertEqual([x['status'] for x in c.summary()['calls']],['capped_unknown','settled']);c.db.close()
