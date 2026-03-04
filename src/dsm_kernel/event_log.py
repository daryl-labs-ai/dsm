#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Append-only event log for DSM writes. JSONL, atomic append. Uses DSMConfig paths.
Does not change shard behavior; audit and replay only.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dsm_kernel.config import DSMConfig


def _utc_iso_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class EventLogger:
    """Append-only JSONL event log. Ensures index dir; appends with ts and event_id."""

    def __init__(self, config: DSMConfig):
        self._config = config

    def ensure_index_dir(self) -> None:
        """Create index dir (and parents) if missing."""
        self._config.index_dir.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: Dict[str, Any]) -> None:
        """Add ts (UTC ISO) and event_id (uuid4 hex) if missing; write one JSON line; flush."""
        if "ts" not in event:
            event = {**event, "ts": _utc_iso_now()}
        if "event_id" not in event:
            event = {**event, "event_id": uuid.uuid4().hex}
        self.ensure_index_dir()
        path = Path(self._config.event_log_path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()

    def read_events(self, limit: int | None = None) -> List[Dict[str, Any]]:
        """Read event log file; return parsed events. If limit set, return last limit events."""
        path = Path(self._config.event_log_path)
        if not path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if limit is not None and limit >= 0:
            events = events[-limit:]
        return events
