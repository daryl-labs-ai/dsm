#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSM kernel configuration. No hardcoded absolute paths.
Prefers environment overrides (DSM_BASE_DIR, etc.).
"""

import os
from pathlib import Path
from typing import Optional


def _default_base_dir() -> Path:
    """Repo root or cwd. Env DSM_BASE_DIR overrides."""
    base = os.environ.get("DSM_BASE_DIR")
    if base:
        return Path(base).resolve()
    # Assume src/dsm_kernel/config.py -> repo root = parent of src
    this_file = Path(__file__).resolve()
    src = this_file.parent.parent  # src
    root = src.parent  # repo root
    if (root / "src").is_dir():
        return root
    return Path.cwd()


# Module-level defaults (used by facade and tests)
DSM_BASE_DIR: Path = _default_base_dir()
SHARDS_DIR: Path = DSM_BASE_DIR / "data" / "shards"
TTL_CONFIG_PATH: Path = DSM_BASE_DIR / "config" / "ttl_config.json"
INDEX_DIR: Path = DSM_BASE_DIR / "data" / "index"
SHARD_CATALOG_PATH: Path = INDEX_DIR / "shard_catalog.json"


class DSMConfig:
    """Kernel config: base dir, shards dir, TTL config path, index dir, shard catalog path."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        shards_dir: Optional[Path] = None,
        ttl_config_path: Optional[Path] = None,
        index_dir: Optional[Path] = None,
        shard_catalog_path: Optional[Path] = None,
    ):
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = _default_base_dir()
        self.shards_dir: Path = Path(shards_dir).resolve() if shards_dir is not None else (self.base_dir / "data" / "shards")
        self.ttl_config_path: Path = Path(ttl_config_path).resolve() if ttl_config_path is not None else (self.base_dir / "config" / "ttl_config.json")
        self.index_dir: Path = Path(index_dir).resolve() if index_dir is not None else (self.base_dir / "data" / "index")
        self.shard_catalog_path: Path = Path(shard_catalog_path).resolve() if shard_catalog_path is not None else (self.index_dir / "shard_catalog.json")
