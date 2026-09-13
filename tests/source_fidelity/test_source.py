import json
import unittest
from source_fidelity.prepare import DATA,SOURCE,CASES,sha,rows
from source_fidelity.investigate import initial,TOOLS
from baseline_cases.tools import python_check

class Fidelity(unittest.TestCase):
    def test_all_original_bytes_and_complete_prompt(self):
        manifest=json.loads((DATA/'operator/manifest.json').read_text())
        for cid,rel,name in CASES:
            b=(SOURCE/'attacks'/rel/name).read_bytes()
            self.assertEqual(b,(DATA/'public'/cid/'transcript.jsonl').read_bytes())
            self.assertIn(b.decode(),initial(cid)[1]['content'])
            self.assertEqual(sha(b),manifest['cases'][cid]['sha256'])
    def test_only_one_session_no_operator_sidecars(self):
        for cid,_,_ in CASES:
            self.assertEqual([p.name for p in (DATA/'public'/cid).iterdir()],['transcript.jsonl'])
    def test_release_integrity(self):
        self.assertTrue(json.loads((DATA/'operator/release-integrity.json').read_text())['passed'])
    def test_actual_mechanisms(self):
        for name in ['zip-validation','broker-validation']:
            self.assertTrue(json.loads((DATA/'operator'/f'{name}.json').read_text())['passed'])
    def test_routing_counterpart_only_one_source_line_changed(self):
        a=rows(DATA/'public/r71/transcript.jsonl');b=rows(DATA/'public/r24/transcript.jsonl')
        self.assertEqual([i for i,(x,y) in enumerate(zip(a,b),1) if x!=y],[19])
    def test_runtime_can_read_own_complete_transcript(self):
        r=python_check(DATA/'public/r71',"from pathlib import Path; print(len(Path('transcript.jsonl').read_bytes()))")
        self.assertEqual(r['exit_code'],0);self.assertEqual(r['stdout'].strip(),'52651')
    def test_operator_and_other_session_inaccessible(self):
        for path in [DATA/'operator/manifest.json',DATA/'public/r52/transcript.jsonl']:
            r=python_check(DATA/'public/r71',f'from pathlib import Path;print(Path({str(path)!r}).read_text())')
            self.assertNotEqual(r['exit_code'],0)
    def test_native_tool_contract(self):
        self.assertEqual(TOOLS[0]['type'],'function')
        self.assertEqual(TOOLS[0]['name'],'inspect')
