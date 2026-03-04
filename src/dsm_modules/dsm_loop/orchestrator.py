#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loop orchestrator: process events from the watcher and trigger tasks (e.g. append insights).
"""

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from dsm_kernel.api import DSMKernel


class LoopOrchestrator:
    """Process events; on append, create task and append insight to shard 'insights'."""

    def __init__(self, kernel: "DSMKernel"):
        self._kernel = kernel

    def process_event(self, event: Dict[str, Any]) -> None:
        """Apply rules: if action==append, create task and append insight to DSM shard 'insights'."""
        if not isinstance(event, dict):
            return
        if event.get("action") == "append":
            task = {
                "type": "memory_append_detected",
                "shard_id": event.get("shard_id", ""),
                "payload_size": event.get("payload_size", 0),
            }
            content = f"Loop: memory_append_detected on shard {task['shard_id']}, payload_size {task['payload_size']}"
            try:
                self._kernel.append_event(
                    "insights",
                    {"content": content, "source": "loop", "importance": 0.6},
                    validate=False,
                )
            except KeyError:
                # insights shard not found; skip
                pass
