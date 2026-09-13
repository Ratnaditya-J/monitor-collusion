import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from source_fidelity import qwen as q,investigate

class QwenComparisonTests(unittest.TestCase):
    def test_tool_and_prompt_preservation(self):
        messages=[{'role':'system','content':investigate.SYSTEM},{'role':'user','content':'test evidence'}]
        p=q.payload(messages,0)
        self.assertEqual(p['messages'],messages)
        self.assertEqual(p['tools'][0]['function'],{k:v for k,v in investigate.TOOLS[0].items() if k!='type'})
        self.assertFalse(p['provider']['allow_fallbacks'])
        self.assertEqual(p['max_tokens'],24576)
        self.assertNotIn('tools',q.payload(messages,7))
    def test_budget_guards_never_dispatch(self):
        for status,cost in [('unknown',None),('settled','.99')]:
            with tempfile.TemporaryDirectory() as t,patch.object(q,'DATA',Path(t)),patch.object(q,'key',return_value='test'),patch.object(q.urllib.request,'Request',side_effect=AssertionError('network reached')):
                c=q.Client()
                c.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('old','x',status,'.1',cost));c.db.commit()
                with self.assertRaisesRegex(RuntimeError,'Budget or billing stop'):
                    c.call('new',q.payload([{'role':'user','content':'test'}],0))
                c.db.close()
    def test_changed_request_is_not_reused(self):
        with tempfile.TemporaryDirectory() as t,patch.object(q,'DATA',Path(t)),patch.object(q,'key',return_value='test'):
            c=q.Client();c.db.execute('INSERT INTO calls VALUES(?,?,?,?,?)',('id','different','settled','.1','.01'));c.db.commit()
            with self.assertRaisesRegex(RuntimeError,'Existing unresolved or changed'):
                c.call('id',q.payload([],0))
            c.db.close()

if __name__=='__main__':unittest.main()
