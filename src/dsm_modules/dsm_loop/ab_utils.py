#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B benchmark helpers: record ab_run events in DSM technical shard.
"""

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from dsm_kernel.api import DSMKernel

AB_SHARD_ID = "shard_technical"


def record_ab_run(
    kernel: "DSMKernel",
    task_id: str,
    memory_mode: str,
    agent: str,
    success: bool,
    time_min: float,
    rework_commits: int,
) -> None:
    """Append an ab_run event to the DSM technical shard via kernel.append_event."""
    payload = {
        "type": "ab_run",
        "task_id": task_id,
        "memory_mode": memory_mode,
        "agent": agent,
        "success": success,
        "time_min": time_min,
        "rework_commits": rework_commits,
    }
    kernel.append_event(
        AB_SHARD_ID,
        {"content": json.dumps(payload), "source": "ab_benchmark", "importance": 0.5},
        validate=False,
    )
