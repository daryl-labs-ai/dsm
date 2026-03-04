#!/usr/bin/env python3
"""
Tests for integrity module: build manifest, verify ok; after tamper/remove, verify fails.
"""
import json
import sys
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_integrity_build_and_verify_ok():
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    index_dir = temp_dir / "data" / "index"

    (shards_dir / "shard_a.json").write_text(
        json.dumps({"config": {"id": "shard_a"}, "transactions": [], "metadata": {}}),
        encoding="utf-8",
    )
    (shards_dir / "shard_b.json").write_text(
        json.dumps({
            "config": {"id": "shard_b"},
            "transactions": [{"id": "b1", "timestamp": "2025-01-01T12:00:00Z", "content": "x"}],
            "metadata": {},
        }),
        encoding="utf-8",
    )

    from dsm_kernel.config import DSMConfig
    from dsm_kernel.integrity import IntegrityManager

    config = DSMConfig(base_dir=temp_dir, shards_dir=shards_dir)
    config.index_dir = index_dir
    config.heads_manifest_path = index_dir / "heads_manifest.json"

    mgr = IntegrityManager(config)
    manifest = mgr.rebuild()
    assert len(manifest) == 2
    assert config.heads_manifest_path.exists()

    report = mgr.verify()
    assert report["ok"] is True
    assert report["checked"] == 2
    assert report["missing"] == []
    assert report["extra"] == []
    assert report["changed"] == []


def test_integrity_verify_fails_after_tamper():
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    index_dir = temp_dir / "data" / "index"

    (shards_dir / "shard_a.json").write_text(
        json.dumps({"config": {"id": "shard_a"}, "transactions": [], "metadata": {}}),
        encoding="utf-8",
    )
    (shards_dir / "shard_b.json").write_text(
        json.dumps({
            "config": {"id": "shard_b"},
            "transactions": [{"id": "b1", "timestamp": "2025-01-01T12:00:00Z", "content": "x"}],
            "metadata": {},
        }),
        encoding="utf-8",
    )

    from dsm_kernel.config import DSMConfig
    from dsm_kernel.integrity import IntegrityManager

    config = DSMConfig(base_dir=temp_dir, shards_dir=shards_dir)
    config.index_dir = index_dir
    config.heads_manifest_path = index_dir / "heads_manifest.json"

    mgr = IntegrityManager(config)
    mgr.rebuild()
    report = mgr.verify()
    assert report["ok"] is True

    # Tamper: append a character to shard_b
    path_b = shards_dir / "shard_b.json"
    path_b.write_text(path_b.read_text(encoding="utf-8") + " ", encoding="utf-8")

    report = mgr.verify()
    assert report["ok"] is False
    changed_ids = [c["shard_id"] for c in report["changed"]]
    assert "shard_b" in changed_ids


def test_integrity_verify_reports_missing():
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    shards_dir = temp_dir / "data" / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    index_dir = temp_dir / "data" / "index"

    (shards_dir / "shard_a.json").write_text(
        json.dumps({"config": {"id": "shard_a"}, "transactions": [], "metadata": {}}),
        encoding="utf-8",
    )
    (shards_dir / "shard_b.json").write_text(
        json.dumps({
            "config": {"id": "shard_b"},
            "transactions": [],
            "metadata": {},
        }),
        encoding="utf-8",
    )

    from dsm_kernel.config import DSMConfig
    from dsm_kernel.integrity import IntegrityManager

    config = DSMConfig(base_dir=temp_dir, shards_dir=shards_dir)
    config.index_dir = index_dir
    config.heads_manifest_path = index_dir / "heads_manifest.json"

    mgr = IntegrityManager(config)
    mgr.rebuild()
    (shards_dir / "shard_b.json").unlink()

    report = mgr.verify()
    assert report["ok"] is False
    assert "shard_b" in report["missing"]
