import json
import unittest

from auditor_manipulation.payload_adapter import MODE, parse_payload

class PayloadAdapterTests(unittest.TestCase):
    def setUp(self):
        self.payload = {'strategy': 'unchanged strategy', 'writes': {'README.md': 'Exact text.\n'}}

    def test_plain_valid_payload_is_identical(self):
        payload, info = parse_payload(json.dumps(self.payload), MODE)
        self.assertEqual(payload, self.payload)
        self.assertEqual(info['changes'], [])

    def test_single_fence_is_removed_without_modifying_payload(self):
        text = '```json\n' + json.dumps(self.payload) + '\n```'
        with self.assertRaises(ValueError): parse_payload(text)
        payload, info = parse_payload(text, MODE)
        self.assertEqual(payload, self.payload)
        self.assertEqual(info['changes'], ['removed_single_outer_markdown_fence'])
        with self.assertRaises(ValueError): parse_payload('Other prose\n' + text, MODE)

    def test_unused_metadata_is_retained_for_inspection(self):
        value = dict(self.payload, actions=None, notes='Unused explanatory metadata.')
        payload, info = parse_payload(json.dumps(value), MODE)
        self.assertEqual(payload, self.payload)
        self.assertEqual(info['ignored_metadata'], {'actions': None, 'notes': value['notes']})

    def test_forged_history_and_executable_actions_are_rejected(self):
        for extras in ({'history': {'actor': 'owner'}}, {'actions': [{'tool': 'shell'}]}, {'notes': 1}):
            with self.subTest(extras=extras), self.assertRaises(ValueError):
                parse_payload(json.dumps(dict(self.payload, **extras)), MODE)

    def test_write_limits_and_duplicate_json_keys_still_apply(self):
        value = {'strategy': '', 'writes': {'README.md': 'x' * 6001}}
        with self.assertRaises(ValueError): parse_payload(json.dumps(value), MODE)
        with self.assertRaises(ValueError): parse_payload('{"strategy":"a","strategy":"b","writes":{}}', MODE)

if __name__ == '__main__': unittest.main()
