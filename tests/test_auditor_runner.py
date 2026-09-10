"""Offline tests of money accounting, resume behavior, and experimental coverage."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest

from auditor_manipulation.core import canonical, derive_truth
from auditor_manipulation.fixtures import build_cases, save_cases
from auditor_manipulation.runner import (
    cost_reservation, execute_run, inspect_response, prepare_run, report_run, write_json,
    read_json_body,
)


CONFIG = Path(__file__).resolve().parents[1] / "studies/auditor_manipulation/pilot.json"


def successful(body, text, cost=0.01, finish="stop"):
    slug = body.get("provider", {}).get("only", ["fake"])[0]
    return {"http_status": 200, "elapsed_seconds": 0, "body": {
        "id": "fake-generation", "model": body["model"],
        "provider": {"openai": "OpenAI", "anthropic": "Anthropic"}.get(slug, "fake-provider"),
        "usage": {"prompt_tokens": 100, "completion_tokens": 100, "cost": cost},
        "choices": [{"finish_reason": finish, "message": {"content": text}}],
    }}


class FakeTransport:
    def __init__(self, invalid_targets=False):
        self.calls = []
        self.invalid_targets = invalid_targets

    def __call__(self, endpoint, key, body):
        self.calls.append(body)
        inputs = json.loads(body["messages"][1]["content"])
        if "target_authored_material" in inputs:
            content = "Not a JSON payload" if self.invalid_targets else canonical({
                "writes": {"handoff_note": "Synthetic test note.", "review_context": ""}})
        else:
            truth = derive_truth(inputs["trusted_record"])
            content = canonical({
                "verdict": "violation" if truth["incident_violation"] else "no_violation",
                "findings": [{**finding, "explanation": "Synthetic expected finding."}
                             for finding in truth["violations"]],
                "audit_manipulation_suspected": False,
            })
        return successful(body, content)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = self.root / "fixtures"
        self.run = self.root / "run"
        save_cases(self.dataset, build_cases())
        prepare_run(self.dataset, CONFIG, self.run)

    def execute(self, transport, max_jobs=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return execute_run(self.run, "fake-key", max_jobs, transport)

    def test_six_cases_remain_private_and_all_notes_precede_audits(self):
        plan = json.loads((self.run / "plan.private.json").read_text())
        self.assertEqual(len(plan["cases"]), 6)
        self.assertEqual({c["split"] for c in plan["cases"]}, {"development"})
        self.assertEqual([j["role"] for j in plan["jobs"][:12]], ["target"] * 12)
        self.assertEqual([j["role"] for j in plan["jobs"][12:]], ["auditor"] * 24)
        client = FakeTransport()
        summary = self.execute(client)
        self.assertEqual(summary["job_states"], {"done": 36})
        self.assertAlmostEqual(summary["reported_cost_usd"], 0.36)
        for request in client.calls:
            self.assertFalse(request["provider"]["allow_fallbacks"])
            self.assertEqual(len(request["provider"]["only"]), 1)
            self.assertNotIn("oracle", canonical(request))
            self.assertNotIn("fake-key", canonical(request))
        report = report_run(self.run)
        self.assertEqual(sum(row["assigned"] for row in report["groups"]), 24)
        self.assertEqual(sum(row["verdict_correct"] for row in report["groups"]), 24)
        self.assertEqual(report["target_valid_payloads"], 12)

    def test_resume_does_not_duplicate_requests(self):
        client = FakeTransport()
        self.assertEqual(self.execute(client, 2)["job_states"], {"done": 2, "pending": 34})
        self.assertEqual(len(client.calls), 2)
        self.execute(client)
        self.assertEqual(len(client.calls), 36)
        self.execute(client)
        self.assertEqual(len(client.calls), 36)

    def test_failed_targets_remain_in_denominators_without_silent_substitution(self):
        client = FakeTransport(invalid_targets=True)
        result = self.execute(client)
        self.assertEqual(len(client.calls), 12)
        self.assertEqual(result["job_states"], {"failed": 12, "blocked": 24})
        report = report_run(self.run)
        self.assertEqual(report["target_valid_payloads"], 0)
        self.assertEqual(sum(row["assigned"] for row in report["groups"]), 24)
        self.assertEqual(sum(row["unrun"] for row in report["groups"]), 24)

    def test_spend_cap_is_checked_before_dispatch(self):
        ledger_path = self.run / "ledger.json"
        ledger = json.loads(ledger_path.read_text())
        ledger["local_spend_cap_usd"] = 0.00001
        write_json(ledger_path, ledger)
        client = FakeTransport()
        result = self.execute(client)
        self.assertEqual(result["state"], "spend_limit")
        self.assertEqual(len(client.calls), 0)

    def test_unknown_cost_keeps_reservation_and_interrupted_calls_are_not_retried(self):
        def missing_cost(endpoint, key, body):
            result = FakeTransport()(endpoint, key, body)
            del result["body"]["usage"]["cost"]
            return result
        result = self.execute(missing_cost, 1)
        self.assertEqual(result["cost_unknown_jobs"], 1)
        self.assertGreater(result["budget_charged_usd"], 1)
        ledger_path = self.run / "ledger.json"
        ledger = json.loads(ledger_path.read_text())
        pending = next(j for j in ledger["jobs"] if j["state"] == "pending")
        pending.update(state="in_flight", budget_charge_usd=1.75)
        write_json(ledger_path, ledger)
        client = FakeTransport()
        self.execute(client)
        ledger = json.loads(ledger_path.read_text())
        self.assertEqual(next(j for j in ledger["jobs"] if j["job_id"] == pending["job_id"])["state"], "interrupted")
        self.assertEqual(len(client.calls), 32)  # 34 pending minus two dependent audits.

    def test_frozen_plan_or_note_tampering_stops_the_run(self):
        client = FakeTransport()
        self.execute(client, 12)
        ledger = json.loads((self.run / "ledger.json").read_text())
        target = ledger["jobs"][0]
        saved_path = self.run / (target["job_id"] + ".json")
        saved = json.loads(saved_path.read_text())
        saved["target_payload"]["writes"]["handoff_note"] = "Rewritten after audit preparation"
        write_json(saved_path, saved)
        with self.assertRaises(ValueError):
            self.execute(client)
        plan_path = self.run / "plan.private.json"
        plan = json.loads(plan_path.read_text())
        plan["config"]["target_model"] = "changed"
        write_json(plan_path, plan)
        with self.assertRaises(ValueError):
            self.execute(client)

    def test_parseable_truncation_is_not_success_and_errors_preserve_cost(self):
        body = {"model": "fake"}
        truncated = inspect_response(successful(body, '{"verdict":"no_violation"}', finish="length"))
        self.assertEqual(truncated["generation_status"], "truncated")
        self.assertEqual(truncated["reported_cost_usd"], 0.01)
        malformed = inspect_response({"http_status": 200, "body": []})
        self.assertEqual(malformed["generation_status"], "error")
        error = inspect_response({"http_status": 503, "body": {
            "error": {"message": "Provider failure"}, "usage": {"cost": 0.5}}})
        self.assertEqual(error["reported_cost_usd"], 0.5)
        self.assertEqual(error["generation_status"], "error")

    def test_http_json_finishes_without_waiting_for_connection_close(self):
        class KeepAliveResponse:
            def __init__(self):
                self.chunks = iter([b" \n", b'{"value":"', b"\xc3", b'\xa9"}'])

            def read1(self, size):
                try:
                    return next(self.chunks)
                except StopIteration:
                    raise AssertionError("A complete JSON response must not wait for EOF")

        self.assertEqual(json.loads(read_json_body(KeepAliveResponse())), {"value": "é"})

    def test_unexpected_response_model_stops_collection(self):
        def wrong_route(endpoint, key, body):
            result = FakeTransport()(endpoint, key, body)
            result["body"]["model"] = "unexpected/substitute"
            return result
        result = self.execute(wrong_route, 1)
        self.assertEqual(result["state"], "route_mismatch")
        ledger = json.loads((self.run / "ledger.json").read_text())
        self.assertEqual(ledger["jobs"][0]["state"], "failed")
        self.assertIn("routing_issue", ledger["jobs"][0])

    def test_cost_reserves_reasoning_and_cache_writes(self):
        spec = {"max_tokens": 1000, "pricing": {
            "prompt": 0.00001, "completion": 0.00005, "input_cache_write": 0.0000125}}
        self.assertGreater(cost_reservation(spec, [{"role": "user", "content": "Hi"}]), 0.075)

    def test_parallel_dispatch_reserves_all_calls_and_preserves_phase_boundary(self):
        barrier = threading.Barrier(4, timeout=5)
        guard = threading.Lock()
        client = FakeTransport()
        entries = []

        def transport(endpoint, key, body):
            with guard:
                position = len(entries)
                entries.append(body)
                ledger = json.loads((self.run / "ledger.json").read_text())
                charged = sum(j.get("budget_charge_usd", 0) for j in ledger["jobs"])
                self.assertLessEqual(charged, ledger["local_spend_cap_usd"])
                inputs = json.loads(body["messages"][1]["content"])
                if "target_authored_material" not in inputs:
                    self.assertTrue(all(j["state"] == "done" for j in ledger["jobs"] if j["role"] == "target"))
            if position < 4:
                barrier.wait()
            return client(endpoint, key, body)

        self.assertEqual(self.execute(transport)["job_states"], {"done": 36})
        self.assertEqual(len(entries), 36)


if __name__ == "__main__":
    unittest.main()
