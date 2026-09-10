"""Explicit syntax-only target-response adapter; never rewrites file contents."""
import hashlib
import re

from .core import digest, strict_json
from .workspace import validate_payload

MODE = 'json_envelope_v1'

def parse_payload(text, mode=None):
    if mode not in (None, MODE):
        raise ValueError('Unknown payload normalization mode')
    candidate = text
    changes = []
    ignored = {}
    if mode == MODE:
        match = re.fullmatch(r'```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```', text.strip(), re.IGNORECASE)
        if match:
            candidate = match.group(1)
            changes.append('removed_single_outer_markdown_fence')
    value = strict_json(candidate)
    if mode == MODE and isinstance(value, dict):
        extras = set(value) - {'strategy', 'writes'}
        if (extras and extras <= {'notes', 'actions'} and
                ('notes' not in extras or isinstance(value['notes'], str)) and
                ('actions' not in extras or value['actions'] is None)):
            ignored = {k: value[k] for k in sorted(extras)}
            value = {k: v for k,v in value.items() if k not in extras}
            changes.append('ignored_unused_envelope_metadata')
    payload = validate_payload(value)
    return payload, {'mode': mode, 'changes': changes, 'ignored_metadata': ignored,
                     'raw_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                     'payload_sha256': digest(payload)}
