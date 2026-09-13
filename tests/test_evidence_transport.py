import unittest
from evidence_kernel.client import assemble
class StreamTests(unittest.TestCase):
 def test_tool_fragments_and_reasoning(self):
  f=[{'id':'a','model':'m','provider':'p','choices':[{'delta':{'tool_calls':[{'index':0,'id':'c','function':{'name':'inspect','arguments':'{"act'}}],'reasoning_details':[{'index':0,'type':'reasoning.text','text':'first'}]}}]}, {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'arguments':'ion":"list"}'}}],'reasoning_details':[{'index':0,'type':'reasoning.text','text':' second'}]},'finish_reason':'tool_calls'}]},{'choices':[],'usage':{'cost':.01}}]
  r=assemble(f);m=r['choices'][0]['message'];self.assertEqual(m['tool_calls'][0]['function']['arguments'],'{"action":"list"}');self.assertEqual(m['reasoning_details'][0]['text'],'first second');self.assertEqual(r['usage']['cost'],.01)
 def test_final_content(self):
  r=assemble([{'choices':[{'delta':{'content':'Hello '}}]},{'choices':[{'delta':{'content':'world'},'finish_reason':'stop'}]}]);self.assertEqual(r['choices'][0]['message']['content'],'Hello world')
if __name__=='__main__':unittest.main()
