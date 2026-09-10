"""Offline study tools and explicitly invoked OpenRouter feasibility runs."""

import argparse
import json
from pathlib import Path

from .core import (
    apply_writes, auditor_messages, auditor_packet, score_assessment,
    strict_json, target_messages,
)
from .fixtures import SEED, build_cases, load_cases, save_cases, summarize


def emit(value):
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def read_payload(path):
    # Bound reads of potentially model-produced material before decoding it.
    with Path(path).open("r", encoding="utf-8") as handle:
        return handle.read(100_001)


def select_case(args):
    cases = load_cases(args.dataset)
    matches = [case for case in cases if case["case_id"] == args.case_id]
    if not matches:
        raise ValueError("Case id is not in the validated dataset")
    case = matches[0]
    if case["split"] != "development" and not args.allow_holdout:
        raise ValueError("Holdout export requires --allow-holdout; develop attacks on development cases")
    return case


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create a new private fixture directory")
    prepare.add_argument("--out", required=True)
    prepare.add_argument("--seed", type=int, default=SEED)
    prepare.add_argument("--pairs-per-family", type=int, default=10)

    validate = commands.add_parser("validate", help="Check checksums, truth, and counts")
    validate.add_argument("--dataset", required=True)

    listing = commands.add_parser("list", help="List development case ids without truth labels")
    listing.add_argument("--dataset", required=True)
    listing.add_argument("--allow-holdout", action="store_true")

    packet = commands.add_parser("packet", help="Export one model input; no model is called")
    score = commands.add_parser("score", help="Score a saved auditor JSON response")
    for command in (packet, score):
        command.add_argument("--dataset", required=True)
        command.add_argument("--case-id", required=True)
        command.add_argument("--allow-holdout", action="store_true")
    packet.add_argument("--role", choices=("auditor", "target", "raw"), default="auditor")
    packet.add_argument("--writes", help="A saved target response containing only writes")
    packet.add_argument("--protocol", choices=("standard", "evidence_first_prompt"), default="standard")
    packet.add_argument("--condition", choices=("honest", "attack"), default="attack")
    score.add_argument("--response", required=True)
    score.add_argument("--generation-status", choices=("ok", "error", "truncated", "moderated"), default="ok")

    plan = commands.add_parser("plan", help="Print the draft model/cost plan and its open decisions")
    plan.add_argument("--config", default=str(
        Path(__file__).resolve().parent.parent / "studies/auditor_manipulation/pilot.json"))
    init_run = commands.add_parser("prepare-run", help="Freeze a six-case run plan; no API calls")
    init_run.add_argument("--dataset", required=True)
    init_run.add_argument("--config", required=True)
    init_run.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Execute or resume the bounded paid feasibility run")
    run.add_argument("--run-dir", required=True)
    run.add_argument("--key-file", help="Read a literal OPENROUTER_API_KEY assignment; never execute it")
    run.add_argument("--max-jobs", type=int)
    for name in ("status", "report"):
        action = commands.add_parser(name, help="Read the saved run without model calls")
        action.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            emit(save_cases(args.out, build_cases(args.seed, args.pairs_per_family)))
        elif args.command == "validate":
            emit({"valid": True, "summary": summarize(load_cases(args.dataset))})
        elif args.command == "list":
            emit([{"case_id": case["case_id"], "split": case["split"]}
                  for case in load_cases(args.dataset)
                  if args.allow_holdout or case["split"] == "development"])
        elif args.command == "packet":
            case = select_case(args)
            if args.writes:
                case = apply_writes(case, strict_json(read_payload(args.writes)))
            if args.role == "raw":
                emit(auditor_packet(case))
            elif args.role == "auditor":
                emit(auditor_messages(case, args.protocol))
            else:
                emit(target_messages(case, args.condition))
        elif args.command == "score":
            emit(score_assessment(select_case(args), read_payload(args.response), args.generation_status))
        elif args.command in {"prepare-run", "run", "status", "report"}:
            from .runner import execute_run, prepare_run, read_key, report_run, summarize_run
            if args.command == "prepare-run":
                emit(prepare_run(args.dataset, args.config, args.out))
            elif args.command == "run":
                if args.max_jobs is not None and args.max_jobs < 1:
                    raise ValueError("max-jobs must be positive")
                emit(execute_run(args.run_dir, read_key(args.key_file), args.max_jobs))
            elif args.command == "status":
                emit(summarize_run(args.run_dir))
            else:
                emit(report_run(args.run_dir))
        else:
            emit(strict_json(read_payload(args.config)))
    except (ValueError, KeyError, TypeError, OSError, RecursionError):
        parser.error("Invalid input or inaccessible file; check the schema, permissions, and fixture manifest")


if __name__ == "__main__":
    main()
