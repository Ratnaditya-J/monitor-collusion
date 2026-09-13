"""Copy released transcripts byte-for-byte; keep analysis strictly operator-side."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/Users/ratnaditya/Documents/Codex/2026-09-04/let/outputs/investigator-baseline-research/sources/sleight-bench')
DATA=ROOT/'results/source_fidelity'
REV='218c58315cc01ff0dc5a100e906c27d82d259521'
CASES=[('r71','needle_in_haystack/rabbitmq-audit-flush-mismatch','transcript.jsonl'),
       ('r24','needle_in_haystack/rabbitmq-audit-flush-mismatch','benign.jsonl'),
       ('r86','multi_session/weight-exfil-eval-symlink-part1','transcript.jsonl'),
       ('r39','multi_session/weight-exfil-eval-symlink-part1','benign.jsonl'),
       ('r52','multi_session/weight-exfil-eval-symlink-part2','transcript.jsonl'),
       ('r17','multi_session/weight-exfil-eval-symlink-part2','benign.jsonl')]

def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def rows(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

def prepare():
    if (DATA/'FREEZE.json').exists():raise RuntimeError('Frozen source pack')
    rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
    assert rev==REV
    spec=importlib.util.spec_from_file_location('source_transcript',SOURCE/'evaluate/core/transcript.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    manifest={'revision':rev,'cases':{},'transformation_source_sha256':sha((SOURCE/'evaluate/core/transcript.py').read_bytes())}
    for cid,rel,name in CASES:
        src=SOURCE/'attacks'/rel/name;b=src.read_bytes()
        dest=DATA/'public'/cid/'transcript.jsonl';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        stripped=mod.strip_assistant_text(b.decode()).encode()
        alt=DATA/'source_compatible'/cid/'transcript.jsonl';alt.parent.mkdir(parents=True,exist_ok=True);alt.write_bytes(stripped)
        manifest['cases'][cid]={'source':str(src),'source_relative':str(src.relative_to(SOURCE)),
            'sha256':sha(b),'bytes':len(b),'lines':len(b.splitlines()),'source_tools_only_sha256':sha(stripped),
            'source_tools_only_bytes':len(stripped),'condition':'author_benign' if name=='benign.jsonl' else 'author_attack',
            'session':1 if 'part1' in rel else 2 if 'part2' in rel else None,
            'effect_status':'precursor_only_no_export' if 'part1' in rel else 'source_depicted_completed_effect',
            'changes_to_full_transcript':[]}
    # Sidecars never enter either investigator-visible evidence directory.
    for rel in sorted(set(x[1] for x in CASES)):
        for name in ['metadata.json','description.md','verifiers.json','encrypted.bin']:
            dest=DATA/'operator/source'/rel/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(SOURCE/'attacks'/rel/name,dest)
    for name in ['experiment_paper.yaml','prompts/control_arena.md','evaluate/core/transcript.py','LICENSE','CANARY.txt']:
        dest=DATA/'operator/reference'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/name,dest)
    diffs={}
    for rel in sorted(set(x[1] for x in CASES)):
        a=rows(SOURCE/'attacks'/rel/'transcript.jsonl');b=rows(SOURCE/'attacks'/rel/'benign.jsonl')
        assert len(a)==len(b)
        diffs[rel]={'total_lines':len(a),'changed_lines':[i for i,(x,y) in enumerate(zip(a,b),1) if x!=y]}
    save(DATA/'operator/manifest.json',manifest);save(DATA/'operator/author-counterpart-diffs.json',diffs)
    return manifest

if __name__=='__main__':print(json.dumps(prepare(),indent=2))
