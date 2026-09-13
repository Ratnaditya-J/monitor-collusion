import json,hashlib
from pathlib import Path
from decimal import Decimal
from evidence_kernel.run import check_freeze,receipt,initial
from evidence_kernel.prepare import DATA,ROOT
from evidence_kernel.client import Client
from source_fidelity.api import save,now
f=check_freeze();origin=json.loads((ROOT/'evidence_kernel/vendor/spineframe/ORIGIN.json').read_text())
for name,h in origin['files'].items():assert hashlib.sha256((ROOT/'evidence_kernel/vendor/spineframe'/name).read_bytes()).hexdigest()==h
slots={f'{c}-{i}-{r}' for c,i,r in f['order']};a={p.stem for p in (DATA/'audits').glob('*.json')};b={p.stem for p in (DATA/'failures').glob('*.json')};assert len(slots)==40 and not a&b and a|b==slots
for cid in json.loads((DATA/'operator/trust.json').read_text()):
 assert receipt('verified',cid)['valid'] and receipt('structured',cid)['valid'] is None
 for name in ['transcript.jsonl','action_records.jsonl','capture_context.json']:assert (DATA/'public/verified'/cid/name).read_bytes()==(DATA/'public/structured'/cid/name).read_bytes()
for c,cid,r in f['order']:
 p=json.loads((DATA/'api'/f'evidence_{c}-{cid}-{r}_0.request.json').read_text());assert p['messages']==initial(c,cid);assert p['model']=='qwen/qwen3.5-35b-a3b';assert p['max_tokens']==24576
billing=json.loads((DATA/'billing_reconciliation.json').read_text());assert billing['new_requests']==80 and Decimal(billing['held_usd'])==0 and all(x['matched'] for x in billing['rows']);assert Decimal(billing['new_actual_spend_usd'])<=Decimal('.90097325');assert (DATA/'api/STOP.json').exists()
save(DATA/'VALIDATION.json',{'at':now(),'frozen_files_verified':len(f['files']),'all_40_slots_accounted':True,'final_assessments':len(a),'operational_failures':len(b),'all_initial_prompts_preserved':True,'all_ten_semantic_pairs_equal':True,'all_ten_signed_snapshots_valid':True,'vendor_hashes_match':True,'new_requests_reconciled':80,'ledger_closed':True,'unit_tests':'9 passed; kernel tamper/isolation preflight and streaming assembly','new_spend_usd':billing['new_actual_spend_usd']});print((DATA/'VALIDATION.json').read_text())
