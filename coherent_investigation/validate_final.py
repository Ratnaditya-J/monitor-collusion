"""Offline post-run verification; performs no model calls and changes no protocol."""
import json
from decimal import Decimal
from .fixtures import DATA, ROOT, STUDY, save, digest
from .run import frozen, initial, payload, evidence_gate

def run():
    f = frozen()
    rows = []
    for cid, condition in f['order']:
        name = f'heldout-{cid}-{condition}'
        request = json.loads((DATA/'api'/('coherent_'+name+'_0.request.json')).read_text())
        assert request == payload(initial('heldout', cid, condition), 8192), name
        audit = DATA/'audits'/(name+'.json')
        failure = DATA/'failures'/(name+'.json')
        assert audit.exists() != failure.exists(), name
        if audit.exists() and condition == 'staged':
            d=json.loads(audit.read_text())
            packet=json.loads((DATA/'packets/heldout'/(cid+'.json')).read_text())
            assert d['gate'] == evidence_gate(packet,d['assessment'])
        rows.append({'slot':name,'request_matches_frozen_protocol':True,'terminal': 'assessment' if audit.exists() else 'operational_failure'})
    assert len(rows)==30 and len({r['slot'] for r in rows})==30
    for cid in {r[0] for r in f['order']}:
        assert initial('heldout',cid,'checks')[1] == initial('heldout',cid,'staged')[1]
        assert initial('heldout',cid,'checks')[1]['content'].startswith(initial('heldout',cid,'ordinary')[1]['content'])
    manifest=json.loads((STUDY/'ARTIFACT_MANIFEST.json').read_text())
    for original, record in manifest.items():
        p=STUDY/record['artifact']
        assert 'keys' not in p.parts and p.suffix!='.pem'
        assert digest(p.read_bytes()) == record['sha256'] == digest((ROOT/original).read_bytes())
    billing=json.loads((DATA/'billing_reconciliation.json').read_text())
    assert Decimal(billing['held_usd'])==0 and Decimal(billing['cumulative_usd'])<=1
    assert all(r['matched'] for r in billing['rows'])
    result={'frozen_hashes_and_source_check_signatures_valid':True,'all_requests_match_frozen_inputs_and_settings':True,'same_underlying_facts_all_conditions':True,'checks_and_staged_user_inputs_identical':True,'unique_terminal_slots':30,'exported_artifacts_verified':len(manifest),'no_private_signing_keys_exported':True,'all_billing_reconciled':True,'budget_within_cap':True,'rows':rows}
    save(STUDY/'FINAL_VALIDATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if __name__=='__main__':run()
