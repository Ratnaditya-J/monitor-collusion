"""Real subprocess deadline checks without network calls."""
import time
import unittest
import json

from auditor_manipulation.network import bounded_request_json
from auditor_manipulation.runner import inspect_response, read_json_body

def never_returns(connection, path, key, payload, timeout):
    # Simulates a transport kept alive by heartbeats without completing a result.
    time.sleep(10)

def returns_response(connection, path, key, payload, timeout):
    connection.send({"http_status": 200, "body": {"result": payload}})
    connection.close()

class NetworkDeadlineTests(unittest.TestCase):
    def test_sse_response_completed_without_waiting_for_connection_close(self):
        events = [
            {"id": "g1", "model": "m", "provider": "p", "choices": [{"delta": {"content": "hé"}}]},
            {"choices": [{"delta": {"content": "llo"}, "finish_reason": "stop"}]},
            {"usage": {"cost": .02}, "choices": []},
        ]
        wire = (": keepalive\n\n" + "".join("data: " + json.dumps(e, ensure_ascii=False) + "\n\n" for e in events) + "data: [DONE]\n\n").encode()
        class Stream:
            def __init__(self): self.position = 0
            def read1(self, size):
                if self.position >= len(wire): raise AssertionError("Waited past stream completion")
                chunk = wire[self.position:self.position + 7]; self.position += 7
                return chunk
        body = json.loads(read_json_body(Stream()))
        parsed = inspect_response({"http_status": 200, "body": body})
        self.assertEqual(parsed["text"], "héllo")
        self.assertEqual(parsed["generation_status"], "ok")
        self.assertEqual(parsed["reported_cost_usd"], .02)
        self.assertEqual(body["_sse_events"], events)

    def test_stalled_worker_has_wall_deadline(self):
        result = bounded_request_json("/test", "not-a-real-key", {}, timeout=.25, _worker=never_returns)
        self.assertEqual(result["transport_error"], "LocalWallDeadlineExceeded")
        self.assertEqual(result["upstream_completion_and_billing"], "unknown")
        self.assertLess(result["local_elapsed_seconds"], 3)
        self.assertNotIn("not-a-real-key", str(result))

    def test_finished_worker_response_preserved(self):
        result = bounded_request_json("/test", "not-a-real-key", {"hello": "world"},
                                      timeout=3, _worker=returns_response)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["body"], {"result": {"hello": "world"}})

if __name__ == "__main__":
    unittest.main()
