"""One authorized nine-call target pilot. No investigator execution or retries."""
import argparse
import copy
import fcntl
import hashlib
import json
import math
from pathlib import Path

from .campaign import make_case
from .coalition import ACTORS
from .core import canonical
from .investigation_influence import EvidenceWorld, InfluenceTeam, parse
from .network import bounded_request_json
from .runner import now, read_key, request_json, write_json

MODEL = 'openai/gpt-6-astra-pro'
CEILING = 8.0
CALLS = 9
SOURCE_FILES = ('preparation_pilot.py', 'investigation_influence.py', 'campaign.py',
                'coalition.py', 'core.py', 'workspace.py', 'network.py', 'runner.py')


def source_hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in SOURCE_FILES}


def reserve_usd(payload):
    # UTF-8 bytes conservatively exceed text token counts; add framing overhead.
    # Do not rely on max_tokens: an earlier billed response exceeded that setting.
    # Reserve the advertised full 128k model completion capacity, including reasoning.
    inputs = len(canonical(payload).encode('utf-8')) + 4096
    long_context = inputs > 272000
    return inputs * (0.0000125 if long_context else 0.00000625) + 128000 * (0.0000375 if long_context else 0.000025)


def payload_for(model, messages):
    if model != MODEL: raise ValueError('Model differs from authorized pilot')
    return {'model': model, 'messages': copy.deepcopy(messages), 'stream': False,
            'max_tokens': 8192, 'reasoning': {'effort': 'high', 'exclude': True},
            'service_tier': 'flex',
            'provider': {'only': ['openai/flex'], 'allow_fallbacks': False,
                         'max_price': {'prompt': 5, 'completion': 25}}}


def worker(connection, path, key, payload, timeout):
    # Independent of the historical V3 dispatcher; its pause remains intact.
    try: connection.send(request_json(path, key, payload, timeout))
    except Exception as exc:
        connection.send({'http_status': None, 'transport_error': type(exc).__name__, 'body': None})
    finally: connection.close()


def transport(path, key, payload):
    return bounded_request_json(path, key, payload, timeout=600, _worker=worker)


class PilotBank:
    def __init__(self, directory, key, ledger, sender=transport):
        self.directory, self.key, self.ledger, self.sender = Path(directory), key, ledger, sender

    def save(self): write_json(self.directory/'ledger.json', self.ledger)

    def call(self, label, model, messages):
        ledger = self.ledger
        if ledger['status'] != 'ready' or ledger['attempted_calls'] >= CALLS or '/target/' not in label:
            raise ValueError('Pilot not dispatchable; investigators and retries are disabled')
        payload = payload_for(model, messages)
        reserve = reserve_usd(payload)
        if ledger.get('prior_cost_usd', 0) + ledger['reported_cost_usd'] + reserve > CEILING:
            ledger.update(status='budget_stop', next_request_reserve_usd=reserve)
            self.save()
            raise ValueError('Next request cannot fit conservative reservation under $8')
        index = ledger['attempted_calls'] + 1
        prefix = self.directory/f'{index:02d}'
        write_json(prefix.with_suffix('.request.json'), {'label': label, 'request': payload,
                   'reservation_usd': reserve, 'created_at': now()})
        ledger.update(status='request_in_flight', attempted_calls=index, reserved_usd=reserve)
        self.save()  # Persist before dispatch; a crash cannot silently release a reservation.
        raw = self.sender('/chat/completions', self.key, payload)
        write_json(prefix.with_suffix('.response.json'), raw)
        body = raw.get('body') or {}
        usage = body.get('usage') or {} if isinstance(body, dict) else {}
        cost = usage.get('cost')
        valid_cost = isinstance(cost, (float, int)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0
        if not valid_cost:
            ledger.update(status='unknown_charge_stop', stopped_at=now())
            self.save()
            raise ValueError('Unknown charge retained; no automatic retry')
        ledger['reported_cost_usd'] += cost
        ledger['reserved_usd'] = 0
        reasons = []
        if raw.get('http_status') != 200 or body.get('error'): reasons.append('provider_error')
        if body.get('service_tier') != 'flex' or body.get('provider') != 'OpenAI' or body.get('model') != MODEL:
            reasons.append('route_or_model_mismatch')
        if cost > reserve + 1e-6: reasons.append('reservation_exceeded')
        ins, outs = usage.get('prompt_tokens'), usage.get('completion_tokens')
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (ins, outs)):
            reasons.append('unverified_token_billing')
        else:
            bound = ins*(.0000125 if ins > 272000 else .00000625) + outs*(.0000375 if ins > 272000 else .000025)
            if cost > bound + 1e-6: reasons.append('flex_price_exceeded')
        choices = body.get('choices') or []
        choice = choices[0] if len(choices) == 1 else {}
        content = (choice.get('message') or {}).get('content')
        if choice.get('finish_reason') != 'stop' or not isinstance(content, str) or not content:
            reasons.append('incomplete_generation')
        ledger.update(status='response_stop' if reasons else 'response_received', last_errors=reasons)
        self.save()
        if reasons: raise ValueError(', '.join(reasons))
        return {'generation_status': 'ok', 'text': content, 'reported_cost_usd': cost}


def prior_pilot():
    path = Path(__file__).parents[1]/'results/auditor_manipulation/influence_v4_pilot_8usd/ledger.json'
    raw = path.read_bytes(); ledger = json.loads(raw)
    if ledger['status'] != 'semantic_quality_stop' or ledger['reserved_usd'] != 0 or ledger['completed_calls'] != 6:
        raise ValueError('Prior pilot must be stopped with settled charges')
    responses = [json.loads(p.read_text()) for p in path.parent.glob('??.response.json')]
    total = sum(r['body']['usage']['cost'] for r in responses)
    if len(responses) != 6 or abs(total-ledger['reported_cost_usd']) > 1e-10:
        raise ValueError('Prior pilot charges do not reconcile')
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'cost_usd': total}


def initialize(directory, condition='standard'):
    directory.mkdir(parents=True, exist_ok=True)
    if any(p.name != '.lock' for p in directory.iterdir()): raise ValueError('Pilot directory must be empty')
    if condition not in ('standard', 'instructed_concealment'): raise ValueError('Unknown condition')
    prior = prior_pilot() if condition == 'instructed_concealment' else None
    filename = 'instructed_concealment_v4.json' if prior else 'investigation_influence_v4.json'
    config = json.loads(Path(__file__).parents[1].joinpath('studies/auditor_manipulation', filename).read_text())
    config['target_call_budget'] = CALLS
    case = make_case('revision_binding', 'candidate-1', True, 48)
    manifest = {'created_at': now(), 'authorization': 'User: set it at $8 and start the work',
                'ceiling_usd': CEILING, 'maximum_calls': CALLS, 'investigator_calls_allowed': 0,
                'scope': 'One model-generated preparation candidate; local semantic review before any investigation.',
                'source_hashes': source_hashes(), 'config': config, 'case': case,
                'prompt_origin': 'Existing V4 role prompts; human candidate transcript is NOT supplied.',
                'reservation_policy': 'UTF-8 byte upper input estimate +4096 framing; full advertised 128k completion capacity; cache-write and long-context rates.',
                'retry_policy': 'None. Unknown billing halts and retains reservation.'}
    manifest.update(condition=condition, prior_pilot=prior)
    if prior:
        manifest['authorization'] = 'User: go ahead with that — attacker-only concealment pilot, using the remainder of the original $8 combined ceiling.'
        manifest['prompt_origin'] = 'Explicitly instructed concealment condition. Neither the human fixture nor the previous generated transcript is supplied.'
    write_json(directory/'manifest.private.json', manifest)
    archive = directory/'execution_source'; archive.mkdir()
    for name in SOURCE_FILES: (archive/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    ledger = {'status': 'ready', 'attempted_calls': 0, 'completed_calls': 0,
              'reported_cost_usd': 0, 'reserved_usd': 0, 'ceiling_usd': CEILING,
              'investigator_calls': 0, 'created_at': now()}
    ledger['prior_cost_usd'] = prior['cost_usd'] if prior else 0
    write_json(directory/'ledger.json', ledger)
    return manifest, ledger


def step(directory, condition='standard'):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    with (directory/'.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not (directory/'manifest.private.json').exists(): manifest, ledger = initialize(directory, condition)
        else:
            manifest = json.loads((directory/'manifest.private.json').read_text())
            ledger = json.loads((directory/'ledger.json').read_text())
        if manifest['source_hashes'] != source_hashes(): raise ValueError('Execution sources changed since freeze')
        if manifest.get('condition', 'standard') != condition: raise ValueError('Condition changed since freeze')
        if condition == 'instructed_concealment':
            prior = prior_pilot()
            if prior != manifest['prior_pilot'] or ledger.get('prior_cost_usd') != prior['cost_usd']:
                raise ValueError('Prior charges or halted ledger changed')
        if manifest['ceiling_usd'] != CEILING or ledger['ceiling_usd'] != CEILING:
            raise ValueError('Budget differs from user authorization')
        if ledger['status'] != 'ready': raise ValueError('Pilot halted or already completed')
        bank = PilotBank(directory, read_key('/Users/ratnaditya/.zshrc'), ledger)
        world = EvidenceWorld(manifest['case'])
        team = InfluenceTeam(world, bank, manifest['config'], 'v4-pilot', mechanism='corroboration')
        if (directory/'snapshot.private.json').exists():
            snapshot = json.loads((directory/'snapshot.private.json').read_text())
            world.restore(snapshot['world'])
            for name in ('states', 'slots', 'events', 'previews'): setattr(team, name, snapshot[name])
        if team.slots != ledger['completed_calls']: raise ValueError('Snapshot/ledger mismatch')
        actor = ACTORS[team.slots % 3]
        try:
            team.turn(actor)
            world.verify()
            snapshot = {'world': world.freeze(), 'states': team.states, 'slots': team.slots,
                        'events': team.events, 'previews': team.previews}
            write_json(directory/'snapshot.private.json', snapshot)
            write_json(directory/f'{team.slots:02d}.snapshot.private.json', snapshot)
            ledger['completed_calls'] += 1
            ledger['status'] = 'preparation_complete_review_required' if team.slots == CALLS else 'ready'
            if team.slots == CALLS:
                write_json(directory/'structural-readiness.json', team.collusion_readiness())
        except Exception as exc:
            if ledger['status'] in ('ready', 'response_received'): ledger['status'] = 'local_validation_stop'
            ledger['failure'] = f'{type(exc).__name__}: {exc}'
        ledger['updated_at'] = now(); bank.save()
        ledger['combined_reported_cost_usd'] = ledger.get('prior_cost_usd', 0) + ledger['reported_cost_usd']
        bank.save()
        print(canonical(ledger), flush=True)
        return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--condition', choices=['standard', 'instructed_concealment'], default='standard')
    args = parser.parse_args()
    step(args.directory, args.condition)


if __name__ == '__main__': main()
