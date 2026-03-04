#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polling-based watcher for event_log.jsonl. Reads new lines after offset; yields parsed events.
"""

import json
from pathlib import Path
from typing import Any, Dict, Generator, Union


class EventWatcher:
    """Read event log from a given offset; yield (event, new_offset) for each new line."""

    def __init__(self, event_log_path: Union[Path, str]):
        self._path = Path(event_log_path)

    def watch(self, last_offset: int = 0) -> Generator[tuple[Dict[str, Any], int], None, None]:
        """Open event_log.jsonl, read new lines after offset, yield (parsed_event, byte_offset_after_line)."""
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            if last_offset > 0:
                f.seek(last_offset)
            while True:
                line = f.readline()
                if not line:
                    break
                new_offset = f.tell()
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if isinstance(event, dict):
                        yield event, new_offset
                except json.JSONDecodeError:
                    continue
