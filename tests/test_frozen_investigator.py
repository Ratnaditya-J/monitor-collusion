import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from auditor_manipulation.frozen_investigator import call, environment, freeze, payload, reserve, MODEL


class FrozenInvestigatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.ledger = {'status': 'ready', 'attempted_calls': 0, 'condition_index': 0,
                       'prior_cost_usd': 3.794328, 'reported_cost_usd': 0, 'reserved_usd': 0, 'completed_calls': 0}
        self.messages = [{'role': 'user', 'content': 'Synthetic audit'}]

    def response(self):
        return {'http_status': 200, 'body': {'model': MODEL, 'provider': 'OpenAI', 'service_tier': 'flex',
            '_sse_events': [{'debug': {'echo_upstream_body': {'max_output_tokens': 8192, 'model': 'gpt-6-astra',
                'reasoning': {'effort': 'high', 'mode': 'pro'}, 'service_tier': 'flex'}}}],
            'usage': {'cost': .02, 'prompt_tokens': 1000, 'completion_tokens': 600},
            'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}}

    def test_reservation_and_inclusive_parameter(self):
        p = payload(self.messages)
        self.assertNotIn('max_tokens', p)
        self.assertEqual(p['max_completion_tokens'], 8192)
        self.assertNotIn('require_parameters', p['provider'])
        self.assertTrue(p['debug']['echo_upstream_body'])
        self.assertGreater(reserve(p, first=True), 3.2)
        self.assertGreater(reserve(p), .2048)
        self.assertLess(reserve(p), .3)

    def test_budget_blocks_before_send(self):
        self.ledger['reported_cost_usd'] = 4.1
        send = Mock()
        with self.assertRaises(ValueError): call(self.path, self.ledger, self.messages, 'fake', send)
        send.assert_not_called()
        self.assertEqual(self.ledger['status'], 'budget_stop')

    def test_unknown_cost_preserves_reservation_and_prevents_retry(self):
        send = Mock(return_value={'http_status': None, 'body': None})
        for _ in range(2):
            with self.assertRaises(ValueError): call(self.path, self.ledger, self.messages, 'fake', send)
        self.assertEqual(send.call_count, 1)
        self.assertGreater(self.ledger['reserved_usd'], 3.2)

    def test_known_overlimit_usage_stops_and_counts_bill(self):
        raw = self.response(); raw['body']['usage']['completion_tokens'] = 9000
        with self.assertRaisesRegex(ValueError, 'completion_limit_not_honored'):
            call(self.path, self.ledger, self.messages, 'fake', Mock(return_value=raw))
        self.assertEqual(self.ledger['reported_cost_usd'], .02)
        self.assertEqual(self.ledger['status'], 'response_stop')

    def test_route_mismatch_counted_and_stopped(self):
        raw = self.response(); raw['body']['service_tier'] = 'default'
        with self.assertRaisesRegex(ValueError, 'route_mismatch'):
            call(self.path, self.ledger, self.messages, 'fake', Mock(return_value=raw))
        self.assertEqual(self.ledger['reported_cost_usd'], .02)

    def test_missing_forwarded_limit_stops(self):
        raw = self.response(); raw['body']['_sse_events'] = []
        with self.assertRaisesRegex(ValueError, 'unverified_upstream_output_limit'):
            call(self.path, self.ledger, self.messages, 'fake', Mock(return_value=raw))

    def test_request_is_persisted_before_send(self):
        def send(*args):
            saved = json.loads((self.path/'ledger.json').read_text())
            self.assertEqual(saved['status'], 'request_in_flight')
            self.assertGreater(saved['reserved_usd'], 3.2)
            self.assertTrue((self.path/'01.request.json').exists())
            return self.response()
        call(self.path, self.ledger, self.messages, 'fake', send)

    def test_frozen_comparison_integrity_and_no_private_plan_in_prompt(self):
        manifest, _ = freeze(self.path)
        worlds = manifest['worlds']
        self.assertEqual(worlds['baseline']['case'], worlds['attack']['case'])
        self.assertEqual(worlds['attack']['world'], worlds['inline_provenance']['world'])
        self.assertFalse(worlds['legitimate']['case']['oracle']['violation'])
        self.assertTrue(worlds['baseline']['case']['oracle']['violation'])
        env, messages, memo = environment(manifest, 'attack', [])
        self.assertIsNone(env.team)
        self.assertIsNone(memo)
        self.assertNotIn('CB441', json.dumps(messages))
        self.assertNotIn('oracle', json.dumps(messages))
        self.assertEqual(env.action({'tool': 'ask_agent', 'actor': 'primary', 'question': 'Explain'}),
                         {'status': 'participant_stopped'})
        self.assertEqual(env.world.freeze(), worlds['attack']['world'])

    def test_all_conditions_have_same_system_prompt(self):
        manifest, _ = freeze(self.path)
        prompts = [environment(manifest, label, [])[1][0] for label in manifest['order']]
        self.assertTrue(all(p == prompts[0] for p in prompts))

    def test_short_revision_is_exact_alias_without_current_version_fallback(self):
        manifest, _ = freeze(self.path)
        env, _, _ = environment(manifest, 'inline_provenance', [])
        path = 'handoffs/run-441152561c042ae7.md'
        short = env.action({'tool': 'read', 'source_id': path, 'revision': '107'})
        full = env.action({'tool': 'read', 'source_id': path, 'revision': path+'@107'})
        self.assertEqual(short, full)
        self.assertEqual(short['revision_id'], path+'@107')
        self.assertNotEqual(short['revision_id'], env.world.sources[path]['revision_id'])
        with self.assertRaisesRegex(ValueError, 'Unknown source/version'):
            env.action({'tool': 'read', 'source_id': path, 'revision': '999999'})


if __name__ == '__main__': unittest.main()
