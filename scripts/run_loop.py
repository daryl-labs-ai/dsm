#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the DSM loop engine (watcher + orchestrator)."""
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
src = repo / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from dsm_modules.dsm_loop.loop_runner import run_loop

if __name__ == "__main__":
    run_loop()
