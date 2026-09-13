"""Append-only event log for a run.

events.jsonl lives at run_dir/events.jsonl.
Each line is a JSON object with at minimum:
  - timestamp (ISO 8601)
  - event_type
  - stage_id (optional, "" for run-level events)
  - data (arbitrary dict)

The event log is the authoritative audit trail. It is never rewritten —
only appended to.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_EMIT_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(
    run_dir: Path,
    event_type: str,
    *,
    stage_id: str = "",
    data: dict[str, Any] | None = None,
    actor: str = "",
) -> None:
    """Append a single event to events.jsonl."""
    event = {
        "timestamp": _now(),
        "event_type": event_type,
        "stage_id": stage_id,
        "data": data or {},
    }
    if actor:
        event["actor"] = actor
    path = run_dir / "events.jsonl"
    with _EMIT_LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_all(run_dir: Path) -> list[dict[str, Any]]:
    """Read all events from the log. Returns empty list if file missing."""
    path = run_dir / "events.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            events.append(json.loads(line))
    return events


def read_for_stage(run_dir: Path, stage_id: str) -> list[dict[str, Any]]:
    """Read events filtered to a specific stage."""
    return [e for e in read_all(run_dir) if e.get("stage_id") == stage_id]
