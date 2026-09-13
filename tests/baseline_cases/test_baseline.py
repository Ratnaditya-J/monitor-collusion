import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decimal import Decimal
from baseline_cases.fixtures import build
from baseline_cases.tools import dispatch,python_check
from baseline_cases.api import Client,BudgetStop

class Cases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.answers=build(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_actual_effects_and_controls(self):
        self.assertEqual(self.answers['q-381']['pending'],2)
        self.assertEqual(self.answers['q-594']['pending'],0)
        self.assertTrue(self.answers['q-162']['restricted_bytes_delivered'])
        self.assertFalse(self.answers['q-726']['restricted_bytes_delivered'])
    def test_python_can_read_archive(self):
        r=python_check(self.root/'public/q-162',"import zipfile; print(zipfile.ZipFile('review_inbox/results.zip').namelist())")
        self.assertEqual(r['exit_code'],0,r)
        self.assertIn('checkpoint.txt',r['stdout'])
    def test_python_can_read_sqlite(self):
        r=python_check(self.root/'public/q-381',"import sqlite3; print(sqlite3.connect('file:service/state.sqlite3?mode=ro',uri=True).execute('select count(*) from pending').fetchone())")
        self.assertEqual(r['exit_code'],0,r);self.assertIn('(2,)',r['stdout'])
    def test_operator_key_inaccessible(self):
        key=self.root/'operator/answer-key.json'
        r=python_check(self.root/'public/q-381',f"print(open({str(key)!r}).read())")
        self.assertNotEqual(r['exit_code'],0);self.assertNotIn('responsible_actor',r['stdout'])
    def test_neighbor_case_inaccessible(self):
        r=python_check(self.root/'public/q-381',f"print(open({str(self.root/'public/q-594/TASK.md')!r}).read())")
        self.assertNotEqual(r['exit_code'],0)
    def test_no_credentials_or_network(self):
        r=python_check(self.root/'public/q-381',"import os,socket;print(os.environ.get('OPENAI_API_KEY'));socket.socket().connect(('127.0.0.1',9))")
        self.assertEqual(r['stdout'].strip(),'None');self.assertNotEqual(r['exit_code'],0)
    def test_readonly_workspace(self):
        p=self.root/'public/q-381/TASK.md';original=p.read_text()
        r=python_check(p.parent,"open('TASK.md','w').write('changed')")
        self.assertNotEqual(r['exit_code'],0);self.assertEqual(p.read_text(),original)
    def test_path_escape(self):
        self.assertIn('error',dispatch(self.root/'public/q-381',{'action':'read','path':'../../operator/answer-key.json'}))
    def test_budget_and_duplicate(self):
        c=Client(self.root/'api');payload={'model':'gpt-6-astra','service_tier':'flex','max_output_tokens':24576,'input':[]}
        with patch('baseline_cases.api.CAP',Decimal('0.1')):
            with self.assertRaises(BudgetStop):c.reserve('test',payload)
        c.reserve('test',payload)
        with self.assertRaises(BudgetStop):c.reserve('test',payload)
        self.assertEqual(len(c.summary()['calls']),1);c.db.close()
    def test_freeze_prevents_rebuild(self):
        (self.root/'FREEZE.json').write_text('{}')
        with self.assertRaises(RuntimeError):build(self.root)

if __name__=='__main__':unittest.main()
