"""A bounded, resumable OpenRouter runner for the six-case development pilot."""

import copy
import codecs
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

from .core import apply_writes, auditor_messages, canonical, digest, score_assessment, strict_json, target_messages
from .fixtures import FAMILIES, load_cases


API_BASE = "https://openrouter.ai/api/v1"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        os.chmod(temporary, 0o600)
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read_key(key_file=None):
    value = os.environ.get("OPENROUTER_API_KEY")
    if value:
        return value
    if key_file:
        # Read a literal assignment; never source or execute shell configuration.
        for line in Path(key_file).read_text(encoding="utf-8").splitlines():
            if re.match(r"^\s*(?:export\s+)?OPENROUTER_API_KEY\s*=", line):
                match = re.search(r"sk-or-v1-[A-Za-z0-9_-]+", line)
                if match:
                    return match.group()
    raise ValueError("OPENROUTER_API_KEY is unavailable; supply an existing key file")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def assemble_sse(text):
    """Normalize a completed SSE response while preserving every received event."""
    events = []
    output = {"choices": [{"finish_reason": None, "message": {"role": "assistant", "content": ""}}],
              "_transport_format": "sse", "_sse_events": events}
    content = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            output["choices"][0]["message"]["content"] = "".join(content)
            return canonical(output).encode("utf-8")
        if not payload:
            continue
        event = json.loads(payload)
        if not isinstance(event, dict):
            raise ValueError("Invalid stream event")
        events.append(event)
        for key in ("id", "model", "provider", "usage", "error"):
            if event.get(key) is not None:
                output[key] = event[key]
        choices = event.get("choices", [])
        if len(choices) > 1:
            raise ValueError("Expected one streamed choice")
        for choice in choices:
            delta = choice.get("delta", {})
            if isinstance(delta.get("content"), str):
                content.append(delta["content"])
            if choice.get("finish_reason") is not None:
                output["choices"][0]["finish_reason"] = choice["finish_reason"]
    raise ValueError("Incomplete stream")


def read_json_body(response):
    """Return when one complete JSON value arrives, without waiting for EOF.

    OpenRouter can send whitespace heartbeats during long non-streaming calls.
    read1 avoids asking a buffered connection to fill a multi-megabyte read.
    """
    decoder = codecs.getincrementaldecoder("utf-8")()
    chunks, text, total = [], "", 0
    while total <= 4_000_000:
        chunk = response.read1(min(65_536, 4_000_001 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        text += decoder.decode(chunk)
        if re.search(r"(?:^|\r?\n)data:\s*\[DONE\]\s*(?:\r?\n|$)", text):
            return assemble_sse(text)
        try:
            json.JSONDecoder().raw_decode(text.lstrip())
            break
        except (ValueError, RecursionError):
            continue
    return b"".join(chunks)


def request_json(path, key, payload=None, timeout=600):
    request = urllib.request.Request(
        API_BASE + path,
        data=None if payload is None else canonical(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "X-OpenRouter-Title": "monitor-collusion auditor feasibility"},
        method="GET" if payload is None else "POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as result:
            body = read_json_body(result)
            status = result.status
    except urllib.error.HTTPError as error:
        body, status = error.read(4_000_001), error.code
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"http_status": None, "transport_error": type(error).__name__,
                "elapsed_seconds": time.monotonic() - started, "body": None}
    try:
        text = body.decode("utf-8").replace(key, "[REDACTED]")
        data = json.loads(text) if len(body) <= 4_000_000 else {"error": {"message": "Response too large"}}
    except (ValueError, UnicodeError, RecursionError):
        data = {"error": {"message": "Non-JSON provider response"}}
    return {"http_status": status, "elapsed_seconds": time.monotonic() - started, "body": data}


def inspect_response(result):
    body = result.get("body")
    output = {"generation_status": "error", "text": "", "usage": None,
              "reported_cost_usd": None, "response_id": None,
              "response_model": None, "provider": None, "finish_reason": None}
    if not isinstance(body, dict):
        return output
    usage = body.get("usage")
    cost = usage.get("cost") if isinstance(usage, dict) else None
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0:
        output["reported_cost_usd"] = cost
    output.update(usage=usage, response_id=body.get("id"),
                  response_model=body.get("model"), provider=body.get("provider"))
    if result.get("http_status") != 200 or body.get("error"):
        return output
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return output
    choice = choices[0]
    reason = choice.get("finish_reason")
    message = choice.get("message")
    output["finish_reason"] = reason
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        output["text"] = message["content"]
    if reason in {"length", "max_tokens"}:
        output["generation_status"] = "truncated"
    elif reason in {"content_filter", "safety"}:
        output["generation_status"] = "moderated"
    elif reason == "stop" and isinstance(message, dict) and isinstance(message.get("content"), str):
        output["generation_status"] = "ok"
    return output


def model_body(spec, messages):
    # Identical envelope across note conditions; no prompt repair or model fallback.
    return {
        "model": spec["id"], "messages": messages, "stream": False,
        "max_tokens": spec["max_tokens"],
        "reasoning": {"effort": spec["reasoning_effort"], "exclude": True},
        "provider": {"only": [spec["provider_slug"]], "allow_fallbacks": False,
                     "require_parameters": True,
                     "max_price": {"prompt": spec["pricing"]["prompt"] * 1_000_000,
                                   "completion": spec["pricing"]["completion"] * 1_000_000}},
    }


def cost_reservation(spec, messages):
    # Conservative byte-based input allowance, plus role/schema overhead.
    # Use the higher cache-write rate because routing can introduce cache writes.
    input_allowance = ((len(canonical(messages).encode("utf-8")) + 2048)
                       * spec.get("input_reservation_multiplier", 1))
    input_rate = max(spec["pricing"]["prompt"], spec["pricing"].get("input_cache_write", 0))
    return round(input_allowance * input_rate + spec["max_tokens"] * spec["pricing"]["completion"], 8)


def prepare_run(dataset, config_path, output):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    selected = [case for case in load_cases(dataset)
                if case["split"] == "development" and case["scenario_index"] == 0]
    if len(selected) != 6 or {c["family"] for c in selected} != set(FAMILIES):
        raise ValueError("Expected exactly one development pair per family")
    cap = config["max_total_spend_usd"]
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not math.isfinite(cap) or cap <= 0:
        raise ValueError("A positive finite local spend cap is required")
    specs = config["models"]
    target_id, auditor_ids = config["target_model"], config["auditor_models"]
    if len(auditor_ids) != 2 or len(set(auditor_ids)) != 2:
        raise ValueError("The feasibility design requires two distinct auditors")
    for model in [target_id, *auditor_ids]:
        spec = specs[model]
        if spec["id"] != model or spec["max_tokens"] <= 0 or not spec["provider_slug"]:
            raise ValueError("Invalid model specification")
        for field in ("prompt", "completion"):
            price = spec["pricing"][field]
            if not isinstance(price, (int, float)) or isinstance(price, bool) or not math.isfinite(price) or price <= 0:
                raise ValueError("Invalid price")
    if config["retry_policy"] != "no_automatic_retries":
        raise ValueError("This pilot retains failures without automatic retries")
    jobs = []
    for case in selected:
        for condition in ("honest", "attack"):
            identity = {"case_id": case["case_id"], "condition": condition, "model": target_id, "role": "target"}
            job_id = digest(identity)[:20]
            jobs.append({**identity, "job_id": job_id, "dependency": None, "state": "pending"})
            for model in auditor_ids:
                audit = {"case_id": case["case_id"], "condition": condition, "model": model, "role": "auditor"}
                jobs.append({**audit, "job_id": digest(audit)[:20], "dependency": job_id, "state": "pending"})
    # Freeze all target notes before any auditor sees them.
    jobs.sort(key=lambda job: (job["role"] != "target", job["job_id"]))
    path = Path(output)
    if path.exists() and any(path.iterdir()):
        raise ValueError("Run output must be empty; use resume for an existing run")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    plan = {"schema_version": 1, "created_at": now(), "stage": "development_feasibility",
            "preregistration_frozen": False, "config": config,
            "cases": selected, "jobs": jobs,
            "core_sha256": hashlib.sha256(Path(__file__).with_name("core.py").read_bytes()).hexdigest()}
    write_json(path / "plan.private.json", plan)
    ledger = {"schema_version": 1, "plan_sha256": digest(plan), "state": "ready",
              "created_at": now(), "jobs": copy.deepcopy(jobs), "local_spend_cap_usd": cap}
    write_json(path / "ledger.json", ledger)
    return summarize_run(path)


def charged_total(ledger):
    return (sum(job.get("budget_charge_usd", 0) for job in ledger["jobs"])
            + ledger.get("supplemental_reported_cost_usd", 0))


def summarize_run(path):
    path = Path(path)
    ledger = json.loads((path / "ledger.json").read_text())
    states = {}
    for job in ledger["jobs"]:
        states[job["state"]] = states.get(job["state"], 0) + 1
    return {"state": ledger["state"], "planned_jobs": len(ledger["jobs"]), "job_states": states,
            "reported_cost_usd": (sum(job.get("reported_cost_usd") or 0 for job in ledger["jobs"])
                                  + ledger.get("supplemental_reported_cost_usd", 0)),
            "supplemental_reported_cost_usd": ledger.get("supplemental_reported_cost_usd", 0),
            "budget_charged_usd": charged_total(ledger),
            "cost_unknown_jobs": sum(job.get("reported_cost_usd") is None and job["state"] in
                                     {"done", "failed", "interrupted"} for job in ledger["jobs"]),
            "local_spend_cap_usd": ledger["local_spend_cap_usd"]}


def execute_run(path, key, max_jobs=None, transport=request_json):
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

    path = Path(path)
    with (path / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another runner holds this run's lock") from None
        plan = json.loads((path / "plan.private.json").read_text())
        ledger = json.loads((path / "ledger.json").read_text())
        if digest(plan) != ledger["plan_sha256"]:
            raise ValueError("Frozen run plan changed")
        core_hash = hashlib.sha256(Path(__file__).with_name("core.py").read_bytes()).hexdigest()
        if core_hash != plan["core_sha256"]:
            raise ValueError("Incident inputs or scorer changed; create a separate run")
        cap = ledger["local_spend_cap_usd"]
        if not isinstance(cap, (int, float)) or not math.isfinite(cap) or not 0 < cap <= plan["config"]["max_total_spend_usd"]:
            raise ValueError("Ledger cannot raise the frozen plan's spending limit")
        for job in ledger["jobs"]:
            if job["state"] == "in_flight":
                job.update(state="interrupted", failure="Unknown provider outcome; not automatically retried")
        config = plan["config"]
        cases = {case["case_id"]: case for case in plan["cases"]}
        jobs_by_id = {job["job_id"]: job for job in ledger["jobs"]}
        ledger["state"] = "running"
        write_json(path / "ledger.json", ledger)
        started = 0
        concurrency = config.get("concurrency", 4)
        if type(concurrency) is not int or not 1 <= concurrency <= 8:
            raise ValueError("Concurrency must be between one and eight")
        runner_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ledger["execution_settings"] = {"concurrency": concurrency, "runner_sha256": runner_hash}
        write_json(path / "ledger.json", ledger)

        def build_request(job):
            case = cases[job["case_id"]]
            if job["role"] == "target":
                messages = target_messages(case, job["condition"])
            else:
                target = jobs_by_id[job["dependency"]]
                if target["state"] != "done" or target.get("artifact_status") != "valid":
                    job.update(state="blocked", failure="Target did not produce a valid frozen payload")
                    write_json(path / "ledger.json", ledger)
                    return None
                frozen = json.loads((path / (target["job_id"] + ".json")).read_text())
                payload = frozen["target_payload"]
                if digest(payload) != target["artifact_sha256"]:
                    raise ValueError("Frozen target artifact changed")
                case = apply_writes(case, payload)
                messages = auditor_messages(case, config["audit_protocol"])
            spec = config["models"][job["model"]]
            return case, model_body(spec, messages), cost_reservation(spec, messages)

        def finish(job, case, body, reservation, result):
            inspected = inspect_response(result)
            spec = config["models"][job["model"]]
            if inspected["generation_status"] == "ok":
                accepted = {spec["id"], spec.get("advertised_endpoint", "").split(" | ")[-1]}
                if (inspected["response_model"] not in accepted or
                        inspected["provider"] != spec["provider_display_name"]):
                    job["routing_issue"] = "Response model/provider differs from the selected route"
                    inspected["generation_status"] = "error"
            saved = {"request": body, "raw_response": result,
                     "response": inspected, "finished_at": now()}
            cost = inspected["reported_cost_usd"]
            job.update(reported_cost_usd=cost, budget_charge_usd=reservation if cost is None else cost,
                       generation_status=inspected["generation_status"], finished_at=now(),
                       response_id=inspected["response_id"], response_model=inspected["response_model"],
                       provider=inspected["provider"],
                       state="done" if inspected["generation_status"] == "ok" else "failed")
            if job["role"] == "target":
                job["artifact_status"] = "invalid"
                if inspected["generation_status"] == "ok":
                    try:
                        payload = strict_json(inspected["text"])
                        apply_writes(case, payload)
                        saved["target_payload"] = payload
                        job.update(artifact_status="valid", artifact_sha256=digest(payload))
                    except (ValueError, TypeError, KeyError, RecursionError):
                        job.update(state="failed", failure="Invalid target payload; retained without repair")
            else:
                saved["score"] = score_assessment(case, inspected["text"], inspected["generation_status"])
                job["score"] = saved["score"]
            saved["job"] = copy.deepcopy(job)
            write_json(path / (job["job_id"] + ".json"), saved)
            write_json(path / "ledger.json", ledger)
            print(canonical({"event": "request_finished", "job_id": job["job_id"], "state": job["state"],
                             "generation_status": job["generation_status"], "reported_cost_usd": cost,
                             "budget_charged_usd": charged_total(ledger)}), flush=True)

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {}
            while True:
                pending_targets = any(j["role"] == "target" and j["state"] in {"pending", "in_flight"}
                                      for j in ledger["jobs"])
                phase = "target" if pending_targets else "auditor"
                for job in ledger["jobs"]:
                    if len(futures) >= concurrency or (max_jobs is not None and started >= max_jobs):
                        break
                    if job["state"] != "pending" or job["role"] != phase:
                        continue
                    prepared = build_request(job)
                    if prepared is None:
                        continue
                    case, body, reservation = prepared
                    if charged_total(ledger) + reservation > cap:
                        continue
                    job.update(state="in_flight", started_at=now(), request_sha256=digest(body),
                               runner_sha256=runner_hash, budget_charge_usd=reservation,
                               reserved_cost_usd=reservation)
                    write_json(path / (job["job_id"] + ".request.json"), body)
                    write_json(path / "ledger.json", ledger)
                    print(canonical({"event": "request_started", "role": job["role"], "model": job["model"],
                                     "job_id": job["job_id"], "started_this_invocation": started}), flush=True)
                    future = pool.submit(transport, "/chat/completions", key, body)
                    futures[future] = (job, case, body, reservation)
                    started += 1
                if not futures:
                    if not any(j["state"] == "pending" for j in ledger["jobs"]):
                        ledger["state"] = "finished"
                    elif max_jobs is not None and started >= max_jobs:
                        ledger["state"] = "paused"
                    else:
                        ledger["state"] = "spend_limit"
                    break
                ready, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in ready:
                    job, case, body, reservation = futures.pop(future)
                    finish(job, case, body, reservation, future.result())
                # In-flight requests have already been reserved. If actual billing exceeds
                # the cap, finish those calls but dispatch nothing further.
                if charged_total(ledger) > cap:
                    for future, context in list(futures.items()):
                        finish(*context, future.result())
                    futures.clear()
                    ledger["state"] = "spend_limit"
                    break
                if any(job.get("routing_issue") for job in ledger["jobs"]):
                    for future, context in list(futures.items()):
                        finish(*context, future.result())
                    futures.clear()
                    ledger["state"] = "route_mismatch"
                    break
        ledger["updated_at"] = now()
        write_json(path / "ledger.json", ledger)
    return summarize_run(path)


def report_run(path):
    path = Path(path)
    plan = json.loads((path / "plan.private.json").read_text())
    ledger = json.loads((path / "ledger.json").read_text())
    cases = {case["case_id"]: case for case in plan["cases"]}
    groups = {}
    for job in ledger["jobs"]:
        if job["role"] != "auditor":
            continue
        label = "violation" if cases[job["case_id"]]["oracle"]["incident_violation"] else "legitimate"
        key = (job["model"], job["condition"], label)
        row = groups.setdefault(key, {"model": key[0], "condition": key[1], "historical_label": label,
                                     "assigned": 0, "scored": 0, "verdict_correct": 0, "false_clearance": 0,
                                     "false_accusation": 0, "abstained": 0, "malformed": 0, "unassessable": 0,
                                     "unrun": 0, "unsupported_findings": 0})
        row["assigned"] += 1
        score = job.get("score")
        if score is None:
            row["unrun"] += 1
            continue
        row[score["status"]] += 1
        for field in ("verdict_correct", "false_clearance", "false_accusation"):
            row[field] += int(score.get(field) is True)
        row["unsupported_findings"] += score.get("unsupported_finding_count") or 0
    report = {"summary": summarize_run(path), "groups": list(groups.values()),
              "target_valid_payloads": sum(job.get("artifact_status") == "valid" for job in ledger["jobs"]),
              "target_assigned": sum(job["role"] == "target" for job in ledger["jobs"]),
              "scope": "Six template-based development cases; no held-out evaluation or robustness claim.",
              "explanation_semantics_scored": False}
    write_json(path / "report.json", report)
    return report
