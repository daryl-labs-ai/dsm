#!/usr/bin/env python3
"""
Tests for shard catalog: build from temp shards, assert file and entries.
"""
import json
import sys
import tempfile
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_catalog_build_and_save():
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    index_dir = temp_dir / "data" / "index"

    # Two minimal shard-like JSON files
    (shards_dir / "shard_a.json").write_text(json.dumps({"config": {"id": "shard_a"}, "transactions": [], "metadata": {}}), encoding="utf-8")
    (shards_dir / "shard_b.json").write_text(
        json.dumps({
            "config": {"id": "shard_b"},
            "transactions": [{"id": "b1", "timestamp": "2025-01-01T12:00:00Z", "content": "x"}],
            "metadata": {}
        }),
        encoding="utf-8"
    )

    from dsm_kernel.config import DSMConfig
    from dsm_kernel.shard_catalog import ShardCatalog

    config = DSMConfig(base_dir=temp_dir, shards_dir=shards_dir)
    config.index_dir = index_dir
    config.shard_catalog_path = index_dir / "shard_catalog.json"

    catalog = ShardCatalog(config)
    entries = catalog.build(recompute_hash=False)
    assert len(entries) == 2
    catalog.save(entries)

    path = config.shard_catalog_path
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert len(data) == 2
    for shard_id, entry in data.items():
        assert "size_bytes" in entry
        assert "mtime_iso" in entry
        assert isinstance(entry["size_bytes"], int)
        assert isinstance(entry["mtime_iso"], str)


def test_catalog_list_shards_via_kernel():
    """DSMKernel.list_shards returns catalog entries when catalog exists (temp dir, patched router)."""
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    (shards_dir / "shard_projects.json").write_text(
        json.dumps({
            "config": {"id": "shard_projects", "name": "Projects", "domain": "projects"},
            "transactions": [],
            "metadata": {}
        }),
        encoding="utf-8"
    )

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

        config = DSMConfig(base_dir=temp_dir)
        router = ShardRouter()
        validator = LinkValidator()
        kernel = DSMKernel(config=config, router=router, validator=validator, rr=None, cache=None)

        # First call builds and saves catalog when missing, returns list
        list1 = kernel.list_shards()
        assert isinstance(list1, list)
        assert len(list1) >= 1
        assert config.shard_catalog_path.exists()

        # Rebuild and get list again
        rebuilt = kernel.rebuild_catalog(recompute_hash=False)
        assert isinstance(rebuilt, list)
        assert len(rebuilt) >= 1
        for e in rebuilt:
            assert "shard_id" in e
            assert "size_bytes" in e
            assert "mtime_iso" in e
    finally:
        shard_mgr.SHARDS_DIR = orig_shards
        shard_mgr.MEMORY_DIR = orig_memory
        router_mod.SHARDS_DIR = orig_shards
        router_mod.MEMORY_DIR = orig_memory
