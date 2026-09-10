"""Journal received response bytes without recording authorization headers."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .core import canonical
from .runner import API_BASE, NoRedirect, read_json_body, write_json


class RecordingResponse:
    def __init__(self, response, handle): self.response, self.handle = response, handle

    def read1(self, size):
        chunk = self.response.read1(size)
        if chunk:
            self.handle.write(chunk)
            self.handle.flush()
            os.fsync(self.handle.fileno())
        return chunk


def captured_request(path, key, payload, timeout, prefix):
    prefix = Path(prefix)
    request = urllib.request.Request(API_BASE + path, data=canonical(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json',
                 'X-OpenRouter-Title': 'monitor-collusion auditor feasibility'}, method='POST')
    start = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            write_json(prefix.with_suffix('.headers.json'), {
                'http_status': response.status,
                'content_type': response.headers.get('Content-Type'),
                'generation_id': response.headers.get('X-Generation-Id')})
            with prefix.with_suffix('.wire.bin').open('wb') as handle:
                os.chmod(handle.name, 0o600)
                wire = read_json_body(RecordingResponse(response, handle))
            body = json.loads(wire.decode('utf-8').replace(key, '[REDACTED]'))
            # The existing SSE assembler retains its raw events. Recover route metadata
            # from actual events, never assume a service tier merely from the request.
            if isinstance(body, dict) and body.get('_transport_format') == 'sse':
                for event in body['_sse_events']:
                    if event.get('service_tier') is not None: body['service_tier'] = event['service_tier']
            return {'http_status': response.status, 'body': body, 'elapsed_seconds': time.monotonic()-start}
    except urllib.error.HTTPError as exc:
        # Routing failures carry useful structured errors; retain them as well.
        # This does not turn an unknown generation charge into a known zero.
        try:
            wire = exc.read(4 * 1024 * 1024)
            body = json.loads(wire.decode('utf-8').replace(key, '[REDACTED]'))
        except (OSError, ValueError):
            body = None
        return {'http_status': exc.code, 'body': body, 'transport_error': 'HTTPError'}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {'http_status': None, 'body': None, 'transport_error': type(exc).__name__}
