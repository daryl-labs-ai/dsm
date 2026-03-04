#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrity layer for shards: sha256 manifest, tamper detection. Derived; rebuildable.
Uses DSMConfig paths only. Does not change shard format or append behavior.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsm_kernel.config import DSMConfig


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute sha256 of file by streaming; does not load entire file into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _mtime_to_iso(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class IntegrityHead:
    shard_id: str
    path: str
    head_hash: str
    size_bytes: int
    mtime_iso: str
    transactions: Optional[int]
    last_ts_iso: Optional[str]


class IntegrityManager:
    """Build and verify sha256 manifest of shard files. Atomic writes."""

    def __init__(self, config: DSMConfig):
        self._config = config

    def ensure_index_dir(self) -> None:
        """Create index dir (and parents) if missing."""
        self._config.index_dir.mkdir(parents=True, exist_ok=True)

    def build_manifest(self) -> Dict[str, Dict[str, Any]]:
        """
        Scan config.shards_dir for *.json; compute sha256 (streaming), stat, best-effort JSON.
        Same approach as ShardCatalog for transactions/last_ts. Return dict shard_id -> head dict.
        """
        self.ensure_index_dir()
        shards_dir = Path(self._config.shards_dir)
        if not shards_dir.exists():
            return {}
        manifest: Dict[str, Dict[str, Any]] = {}
        for path in sorted(shards_dir.glob("*.json")):
            shard_id = path.stem
            try:
                st = path.stat()
                size_bytes = st.st_size
                mtime_iso = _mtime_to_iso(st.st_mtime)
            except OSError:
                continue
            head_hash = sha256_file(path)
            transactions: Optional[int] = None
            last_ts_iso: Optional[str] = None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
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
            head = IntegrityHead(
                shard_id=shard_id,
                path=str(path.resolve()),
                head_hash=head_hash,
                size_bytes=size_bytes,
                mtime_iso=mtime_iso,
                transactions=transactions,
                last_ts_iso=last_ts_iso,
            )
            manifest[shard_id] = asdict(head)
        return manifest

    def load_manifest(self) -> Dict[str, Dict[str, Any]]:
        """If HEADS_MANIFEST_PATH exists, load json; else return {}."""
        path = Path(self._config.heads_manifest_path)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def save_manifest(self, manifest: Dict[str, Dict[str, Any]]) -> None:
        """Atomic write: write to .tmp then rename."""
        self.ensure_index_dir()
        path = Path(self._config.heads_manifest_path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        tmp.replace(path)

    def rebuild(self) -> Dict[str, Dict[str, Any]]:
        """Build manifest, save atomically, return manifest."""
        manifest = self.build_manifest()
        if manifest:
            self.save_manifest(manifest)
        return manifest

    def verify(self) -> Dict[str, Any]:
        """
        Load manifest; if empty return {ok: False, reason: "missing_manifest", ...}.
        Recompute current heads for shard files; report missing, extra, changed.
        ok=True only if no missing/extra/changed.
        """
        manifest = self.load_manifest()
        if not manifest:
            return {
                "ok": False,
                "reason": "missing_manifest",
                "missing": [],
                "extra": [],
                "changed": [],
                "checked": 0,
            }
        current = self.build_manifest()
        manifest_ids = set(manifest)
        current_ids = set(current)
        missing: List[str] = list(manifest_ids - current_ids)
        extra: List[str] = list(current_ids - manifest_ids)
        changed: List[Dict[str, Any]] = []
        for sid in manifest_ids & current_ids:
            exp = manifest[sid]
            act = current[sid]
            if exp.get("head_hash") != act.get("head_hash"):
                changed.append({"shard_id": sid, "expected": exp, "actual": act})
        checked = len(manifest_ids)
        ok = len(missing) == 0 and len(extra) == 0 and len(changed) == 0
        return {
            "ok": ok,
            "missing": missing,
            "extra": extra,
            "changed": changed,
            "checked": checked,
        }

    def verify_shard(self, shard_id: str) -> Dict[str, Any]:
        """Compare single shard to manifest entry. Return report with ok, expected, actual if mismatch."""
        manifest = self.load_manifest()
        if not manifest:
            return {"ok": False, "reason": "missing_manifest", "shard_id": shard_id}
        if shard_id not in manifest:
            return {"ok": False, "reason": "shard_not_in_manifest", "shard_id": shard_id}
        expected = manifest[shard_id]
        shards_dir = Path(self._config.shards_dir)
        path = shards_dir / f"{shard_id}.json"
        if not path.exists():
            return {
                "ok": False,
                "reason": "file_missing",
                "shard_id": shard_id,
                "expected": expected,
                "actual": None,
            }
        head_hash = sha256_file(path)
        try:
            st = path.stat()
            size_bytes = st.st_size
            mtime_iso = _mtime_to_iso(st.st_mtime)
        except OSError:
            return {
                "ok": False,
                "reason": "stat_error",
                "shard_id": shard_id,
                "expected": expected,
                "actual": None,
            }
        transactions: Optional[int] = None
        last_ts_iso: Optional[str] = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
        actual = {
            "shard_id": shard_id,
            "path": str(path.resolve()),
            "head_hash": head_hash,
            "size_bytes": size_bytes,
            "mtime_iso": mtime_iso,
            "transactions": transactions,
            "last_ts_iso": last_ts_iso,
        }
        ok = expected.get("head_hash") == head_hash
        return {
            "ok": ok,
            "reason": None if ok else "hash_mismatch",
            "shard_id": shard_id,
            "expected": expected,
            "actual": actual,
        }
