import io
import json
import tempfile
import unittest

from auditor_manipulation.captured_transport import RecordingResponse
from auditor_manipulation.runner import read_json_body


class ResponseCaptureTests(unittest.TestCase):
    def test_partial_content_survives_transport_failure(self):
        class Broken:
            def __init__(self): self.calls = 0
            def read1(self, size):
                self.calls += 1
                if self.calls == 1: return b'{"id":"gen-test","choices":'
                raise TimeoutError('unfinished response')
        with tempfile.TemporaryFile() as f:
            with self.assertRaises(TimeoutError): read_json_body(RecordingResponse(Broken(), f))
            f.seek(0)
            self.assertEqual(f.read(), b'{"id":"gen-test","choices":')

    def test_complete_response_does_not_wait_for_closed_connection(self):
        class HeldOpen:
            def __init__(self): self.calls = 0
            def read1(self, size):
                self.calls += 1
                if self.calls > 1: raise AssertionError('Should not wait for EOF')
                return b'{"id":"gen-test","service_tier":"flex"}'
        with tempfile.TemporaryFile() as f:
            body = read_json_body(RecordingResponse(HeldOpen(), f))
            self.assertEqual(json.loads(body)['service_tier'], 'flex')
            f.seek(0); self.assertEqual(f.read(), body)


if __name__ == '__main__': unittest.main()
