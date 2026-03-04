#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shard catalog: rebuildable index from disk. Derived/secondary; safe to delete and rebuild.
Uses DSMConfig paths only. JSON output.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dsm_kernel.config import DSMConfig


@dataclass
class ShardCatalogEntry:
    shard_id: str
    domain: Optional[str]
    path: str
    exists: bool
    size_bytes: int
    mtime_iso: str
    transactions: Optional[int]
    last_ts_iso: Optional[str]
    head_hash: Optional[str]


class ShardCatalog:
    """Build and persist a catalog of shard files from config.shards_dir."""

    def __init__(self, config: DSMConfig):
        self._config = config

    def ensure_index_dir(self) -> None:
        """Create INDEX_DIR (and parents) if missing."""
        self._config.index_dir.mkdir(parents=True, exist_ok=True)

    def build(self, recompute_hash: bool = False) -> Dict[str, ShardCatalogEntry]:
        """
        Scan config.shards_dir for *.json; collect stat, minimal JSON peek, optional sha256.
        Returns dict shard_id -> ShardCatalogEntry.
        """
        self.ensure_index_dir()
        shards_dir = Path(self._config.shards_dir)
        if not shards_dir.exists():
            return {}
        entries: Dict[str, ShardCatalogEntry] = {}
        for path in sorted(shards_dir.glob("*.json")):
            shard_id = path.stem
            try:
                st = path.stat()
                size_bytes = st.st_size
                mtime_iso = _mtime_to_iso(st.st_mtime)
                exists = True
            except OSError:
                size_bytes = 0
                mtime_iso = ""
                exists = False
            transactions: Optional[int] = None
            last_ts_iso: Optional[str] = None
            head_hash: Optional[str] = None
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                if recompute_hash:
                    head_hash = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw.decode("utf-8"))
                if isinstance(data, dict):
                    txs = data.get("transactions")
                    if isinstance(txs, list):
                        transactions = len(txs)
                        if txs:
                            last_tx = txs[-1]
                            if isinstance(last_tx, dict) and "timestamp" in last_tx:
                                last_ts_iso = last_tx["timestamp"]
            except (json.JSONDecodeError, OSError):
                pass
            domain = None
            if shard_id.startswith("shard_"):
                domain = shard_id.replace("shard_", "", 1) or None
            entries[shard_id] = ShardCatalogEntry(
                shard_id=shard_id,
                domain=domain,
                path=str(path.resolve()),
                exists=exists,
                size_bytes=size_bytes,
                mtime_iso=mtime_iso,
                transactions=transactions,
                last_ts_iso=last_ts_iso,
                head_hash=head_hash,
            )
        return entries

    def save(self, entries: Dict[str, ShardCatalogEntry]) -> None:
        """Write catalog to SHARD_CATALOG_PATH atomically (tmp + rename)."""
        self.ensure_index_dir()
        path = Path(self._config.shard_catalog_path)
        out = {k: asdict(v) for k, v in entries.items()}
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        tmp.replace(path)

    def load(self) -> Dict[str, Any]:
        """If catalog file exists, load and return dict (shard_id -> entry dict). Else return {}."""
        path = Path(self._config.shard_catalog_path)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


def _mtime_to_iso(mtime: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
