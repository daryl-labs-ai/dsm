#!/usr/bin/env python3
"""
Smoke test: import main DSM modules (kernel + modules).
Run from repo root with: PYTHONPATH=src python -m pytest tests/kernel/test_imports.py -v
"""
import sys
from pathlib import Path

# Ensure src is on path
src = Path(__file__).resolve().parent.parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))


def test_import_dsm_kernel_shard_manager():
    from dsm_kernel.shard_manager import MemoryShard, SHARDS_DIR, SHARD_DOMAINS, MEMORY_DIR
    assert MemoryShard is not None
    assert SHARD_DOMAINS is not None
    assert "projects" in SHARD_DOMAINS


def test_import_dsm_validator():
    from dsm_modules.dsm_validator.link_validator import LinkValidator
    v = LinkValidator()
    assert v.allowed_shards is not None
    valid, _ = v.validate_link("shard_projects", "shard_technical")
    assert valid is True


def test_import_dsm_cache_embedding_service():
    from dsm_modules.dsm_cache.embedding_service import EmbeddingService, DummyModel
    # Use DummyModel to avoid loading real model
    svc = EmbeddingService(model=DummyModel())
    emb = svc.generate_embedding("test")
    assert emb is not None
    assert len(emb) == 384


def test_import_dsm_router():
    # ShardRouter imports kernel + optional Phase2 modules; may print warnings if deps missing
    from dsm_modules.dsm_router.router import ShardRouter
    assert ShardRouter is not None
