"""Read-only evidence tools; optional Python runs under macOS filesystem/network sandbox."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def resolve(root,path):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root):raise ValueError('Path outside case workspace')
    return p

def inventory(root):
    root=Path(root)
    return [{'path':str(p.relative_to(root)), 'type':'symlink' if p.is_symlink() else 'file',
             **({'target':os.readlink(p)} if p.is_symlink() else {'bytes':p.stat().st_size})}
            for p in sorted(root.rglob('*')) if p.is_file() or p.is_symlink()]

def python_check(root,code):
    root=Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='astra-analysis-') as tmp:
        scratch=Path(tmp).resolve()
        paths=['/System','/usr','/Library','/opt/homebrew','/dev','/private/var/db',str(root),str(scratch)]
        allow=' '.join('(subpath '+json.dumps(x)+')' for x in paths)
        profile='(version 1)(allow default)(deny network*)(deny file-write*)(deny file-read*)'
        profile+='(allow file-read-metadata)(allow file-read* (literal "/") (literal "/opt") (literal "/private") (literal "/private/var") '+allow+')'
        profile+='(allow file-write* (subpath '+json.dumps(str(scratch))+') (literal "/dev/null"))'
        proc=subprocess.run(['/usr/bin/sandbox-exec','-p',profile,sys.executable,'-I','-S','-c',code],
            cwd=root,env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch)},capture_output=True,text=True,timeout=20)
        if len(proc.stdout)+len(proc.stderr)>30000: return {'error':'Output exceeds 30000 characters; narrow the computation.'}
        return {'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}

def dispatch(root,request):
    try:
        action=request['action']
        if action=='list':return inventory(root)
        if action=='read':
            p=resolve(root,request['path']);b=p.read_bytes()
            if len(b)>30000:return {'error':'File too large; inspect a range with Python.'}
            return {'path':request['path'],'text':b.decode('utf-8')}
        if action=='python':return python_check(root,request['code'])
        return {'error':'Unknown action'}
    except (ValueError,KeyError,OSError,UnicodeError,subprocess.TimeoutExpired) as exc:
        return {'error':str(exc)}
