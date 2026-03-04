#!/usr/bin/env python3
"""
Tests for event log: append-only JSONL, file exists, line count, JSON parse.
"""
import json
import sys
import tempfile
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_event_log_append_and_read():
    temp_dir = Path(tempfile.mkdtemp())
    index_dir = temp_dir / "data" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    from dsm_kernel.config import DSMConfig
    from dsm_kernel.event_log import EventLogger

    config = DSMConfig(base_dir=temp_dir)
    config.index_dir = index_dir
    config.event_log_path = index_dir / "event_log.jsonl"

    logger = EventLogger(config)
    logger.append_event({"action": "append", "shard_id": "shard_a"})
    logger.append_event({"action": "append", "shard_id": "shard_b"})
    logger.append_event({"action": "append", "shard_id": "shard_c"})

    assert config.event_log_path.exists()
    lines = config.event_log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    events = logger.read_events(limit=None)
    assert len(events) == 3
    for e in events:
        assert isinstance(e, dict)
        assert "ts" in e
        assert "event_id" in e
        assert "action" in e
    for line in lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)
        assert "event_id" in parsed
