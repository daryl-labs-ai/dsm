#!/usr/bin/env python3
"""
Test loop: simulate event_log with append event; verify orchestrator writes insight to shard insights.
"""
import json
import sys
import tempfile
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_orchestrator_writes_insight_on_append_event():
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    index_dir = temp_dir / "data" / "index"
    shards_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    # Insights shard (must exist for orchestrator to append)
    insights_data = {
        "config": {"id": "insights", "name": "Insights", "domain": "insights"},
        "transactions": [],
        "metadata": {"version": "2.0", "importance_score": 0.0, "last_updated": None},
    }
    (shards_dir / "insights.json").write_text(json.dumps(insights_data, indent=2), encoding="utf-8")

    # One append event in event log
    event_log_path = index_dir / "event_log.jsonl"
    append_event = {"action": "append", "shard_id": "shard_projects", "payload_size": 128}
    event_log_path.write_text(json.dumps(append_event) + "\n", encoding="utf-8")

    import dsm_kernel.shard_manager as shard_mgr
    import dsm_modules.dsm_router.router as router_mod
    orig_shards = shard_mgr.SHARDS_DIR
    orig_memory = shard_mgr.MEMORY_DIR
    shard_mgr.SHARDS_DIR = shards_dir
    shard_mgr.MEMORY_DIR = temp_dir
    router_mod.SHARDS_DIR = shards_dir
    router_mod.MEMORY_DIR = temp_dir

    try:
        from dsm_kernel.config import DSMConfig
        from dsm_kernel.api import DSMKernel
        from dsm_modules.dsm_router.router import ShardRouter
        from dsm_modules.dsm_validator.link_validator import LinkValidator
        from dsm_modules.dsm_loop.orchestrator import LoopOrchestrator

        config = DSMConfig(base_dir=temp_dir, shards_dir=shards_dir)
        config.event_log_path = event_log_path
        router = ShardRouter()
        validator = LinkValidator()
        kernel = DSMKernel(config=config, router=router, validator=validator, rr=None, cache=None)
        orchestrator = LoopOrchestrator(kernel)

        orchestrator.process_event(append_event)

        insights_shard = kernel.get_shard("insights")
        assert len(insights_shard.transactions) == 1
        content = insights_shard.transactions[0].get("content", "")
        assert "memory_append_detected" in content
        assert "shard_projects" in content
        assert "128" in content
    finally:
        shard_mgr.SHARDS_DIR = orig_shards
        shard_mgr.MEMORY_DIR = orig_memory
        router_mod.SHARDS_DIR = orig_shards
        router_mod.MEMORY_DIR = orig_memory
