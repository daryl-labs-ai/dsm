#!/usr/bin/env python3
"""
Smoke test: DSMKernel with minimal config and temp directory.
Append event, query, assert result structure. No exceptions.
"""
import json
import sys
import tempfile
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_api_smoke_append_and_query():
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    # Minimal shard so router can load it
    shard_file = shards_dir / "shard_projects.json"
    shard_data = {
        "config": {
            "id": "shard_projects",
            "name": "Projets en cours",
            "domain": "projects",
            "keywords": ["projet", "task", "goal"]
        },
        "transactions": [],
        "metadata": {"version": "2.0", "importance_score": 0.0, "last_updated": None}
    }
    with open(shard_file, "w", encoding="utf-8") as f:
        json.dump(shard_data, f, indent=2)

    # Patch kernel and router to use temp dir (before router instantiates)
    import dsm_kernel.shard_manager as shard_mgr
    import dsm_modules.dsm_router.router as router_mod
    orig_shards = shard_mgr.SHARDS_DIR
    orig_memory = shard_mgr.MEMORY_DIR
    shard_mgr.SHARDS_DIR = shards_dir
    shard_mgr.MEMORY_DIR = temp_dir
    router_mod.SHARDS_DIR = shards_dir
    router_mod.MEMORY_DIR = temp_dir

    try:
        from dsm_kernel import DSMConfig, DSMKernel
        from dsm_modules.dsm_router.router import ShardRouter
        from dsm_modules.dsm_validator.link_validator import LinkValidator

        router = ShardRouter()
        validator = LinkValidator()
        config = DSMConfig(base_dir=temp_dir)
        kernel = DSMKernel(config=config, router=router, validator=validator, rr=None, cache=None)

        # list_shards
        shards_list = kernel.list_shards()
        assert isinstance(shards_list, list)
        assert len(shards_list) >= 1

        # append_event (append-only)
        out = kernel.append_event("shard_projects", {"content": "smoke test payload", "source": "test"}, validate=True)
        assert isinstance(out, dict)
        assert "id" in out
        assert out.get("shard_id") == "shard_projects"

        # query fulltext
        results = kernel.query("shard_projects", "smoke", mode="fulltext", limit=5)
        assert isinstance(results, list)
        assert len(results) >= 1
        assert "content" in results[0]
        assert "smoke" in results[0]["content"].lower()

        # get_shard
        shard = kernel.get_shard("shard_projects")
        assert shard is not None
        assert len(shard.transactions) >= 1

        # query_global
        global_results = kernel.query_global("smoke", mode="router", limit=5)
        assert isinstance(global_results, list)
    finally:
        shard_mgr.SHARDS_DIR = orig_shards
        shard_mgr.MEMORY_DIR = orig_memory
        router_mod.SHARDS_DIR = orig_shards
        router_mod.MEMORY_DIR = orig_memory
