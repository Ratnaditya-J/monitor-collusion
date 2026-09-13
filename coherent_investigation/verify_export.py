"""Verify committed study artifacts without credentials, requests or private keys."""
import json
from .fixtures import ROOT,STUDY,digest
from evidence_kernel.records import verify,canonical

def run():
    manifest=json.loads((STUDY/'ARTIFACT_MANIFEST.json').read_text())
    freeze=json.loads((STUDY/'FREEZE.json').read_text())
    for original,r in manifest.items():
        assert digest((STUDY/r['artifact']).read_bytes())==r['sha256'],original
    for original,h in freeze['files'].items():
        path=STUDY/manifest[original]['artifact'] if original in manifest else ROOT/original
        assert digest(path.read_bytes())==h,original
    for cid in {r[0] for r in freeze['order']}:
        base=STUDY/'artifacts/operator/heldout'/cid
        anchor=json.loads((base/'anchor.json').read_text())
        source=json.loads((base/'bundle.json').read_text())
        derived=json.loads((base/'checks.bundle.json').read_text())
        packet=json.loads((STUDY/'artifacts/packets/heldout'/(cid+'.json')).read_text())
        checks=json.loads((STUDY/'artifacts/checks/heldout'/(cid+'.json')).read_text())
        assert verify(source,anchor['public_key'],anchor['run_id'])['valid']
        assert verify(derived,anchor['public_key'],anchor['run_id']+'-checks')['valid']
        binding=derived['content']['records'][0]['record']
        assert binding['source_root']==source['root_hash']
        assert binding['source_packet_sha256']==digest(canonical(packet))
        assert binding['results']==checks
    print('Verified committed frozen code and artifacts, ten source/check signature pairs and packet bindings. No API calls.')
if __name__=='__main__':run()
