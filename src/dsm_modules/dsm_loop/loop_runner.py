#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loop runner: bootstrap kernel, watcher, orchestrator; poll event log and process events.
"""

import sys
import time
from pathlib import Path

# Ensure src is on path when run as script
_src = Path(__file__).resolve().parent.parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from dsm_kernel.config import DSMConfig
from dsm_kernel.api import DSMKernel
from dsm_modules.dsm_router.router import ShardRouter
from dsm_modules.dsm_validator.link_validator import LinkValidator
from dsm_modules.dsm_loop.watcher import EventWatcher
from dsm_modules.dsm_loop.orchestrator import LoopOrchestrator


def run_loop() -> None:
    """Instantiate DSMKernel, EventWatcher, LoopOrchestrator; watch events, process, sleep(2)."""
    config = DSMConfig()
    router = ShardRouter()
    router.load_all_shards()
    validator = LinkValidator()
    kernel = DSMKernel(config=config, router=router, validator=validator, rr=None, cache=None)
    watcher = EventWatcher(config.event_log_path)
    orchestrator = LoopOrchestrator(kernel)

    last_offset = 0
    while True:
        for event, new_offset in watcher.watch(last_offset=last_offset):
            orchestrator.process_event(event)
            last_offset = new_offset
        time.sleep(2)
