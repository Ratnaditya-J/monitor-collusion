import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from auditor_manipulation.preparation_pilot import MODEL, PilotBank, payload_for, reserve_usd


class PilotBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = {'status': 'ready', 'attempted_calls': 0, 'reported_cost_usd': 0, 'reserved_usd': 0}
        self.messages = [{'role': 'user', 'content': 'Controlled synthetic test'}]

    def success(self, cost=.02):
        return {'http_status': 200, 'body': {'model': MODEL, 'provider': 'OpenAI', 'service_tier': 'flex',
                'usage': {'cost': cost, 'prompt_tokens': 1000, 'completion_tokens': 600},
                'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}}

    def bank(self, response):
        sender = Mock(return_value=response)
        return PilotBank(self.temp.name, 'fake-key', self.ledger, sender), sender

    def test_reserves_full_model_capacity_not_requested_output(self):
        payload = payload_for(MODEL, self.messages)
        self.assertGreater(reserve_usd(payload), 3.2)
        self.assertEqual(payload['provider']['only'], ['openai/flex'])
        self.assertFalse(payload['provider']['allow_fallbacks'])

    def test_stops_before_dispatch_if_budget_cannot_fit(self):
        self.ledger['reported_cost_usd'] = 5
        bank, sender = self.bank(self.success())
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        sender.assert_not_called()
        self.assertEqual(self.ledger['status'], 'budget_stop')

    def test_previous_pilot_charges_reduce_remaining_budget(self):
        self.ledger.update(prior_cost_usd=1.44430575, reported_cost_usd=3.5)
        bank, sender = self.bank(self.success())
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        sender.assert_not_called()
        self.assertEqual(self.ledger['status'], 'budget_stop')

    def test_unknown_charge_preserves_reservation_and_blocks_retry(self):
        bank, sender = self.bank({'http_status': None, 'body': None})
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        self.assertGreater(self.ledger['reserved_usd'], 3.2)
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        self.assertEqual(sender.call_count, 1)

    def test_persists_reservation_before_request(self):
        bank, sender = self.bank(self.success())
        def send(*args):
            state = json.loads(Path(self.temp.name, 'ledger.json').read_text())
            self.assertEqual(state['status'], 'request_in_flight')
            self.assertGreater(state['reserved_usd'], 3.2)
            return self.success()
        sender.side_effect = send
        bank.call('pilot/target/01', MODEL, self.messages)
        self.assertEqual(self.ledger['reported_cost_usd'], .02)
        self.assertEqual(self.ledger['reserved_usd'], 0)

    def test_paid_route_mismatch_still_counts_cost_and_halts(self):
        raw = self.success(); raw['body']['service_tier'] = 'default'
        bank, sender = self.bank(raw)
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        self.assertEqual(self.ledger['reported_cost_usd'], .02)
        self.assertEqual(self.ledger['status'], 'response_stop')

    def test_investigator_and_tenth_call_are_rejected(self):
        bank, sender = self.bank(self.success())
        with self.assertRaises(ValueError): bank.call('pilot/investigator/01', MODEL, self.messages)
        self.ledger['attempted_calls'] = 9
        with self.assertRaises(ValueError): bank.call('pilot/target/10', MODEL, self.messages)
        sender.assert_not_called()

    def test_no_silent_fallback_or_truncated_generation(self):
        raw = self.success(); raw['body']['choices'][0]['finish_reason'] = 'length'
        bank, sender = self.bank(raw)
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        self.assertEqual(self.ledger['status'], 'response_stop')

    def test_price_overrun_halts(self):
        bank, sender = self.bank(self.success(.04))
        with self.assertRaises(ValueError): bank.call('pilot/target/01', MODEL, self.messages)
        self.assertIn('flex_price_exceeded', self.ledger['last_errors'])


if __name__ == '__main__': unittest.main()
