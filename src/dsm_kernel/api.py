#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSM kernel API facade. Append-only events, query modes, no change to legacy behavior.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from dsm_kernel.config import DSMConfig
from dsm_kernel.integrity import IntegrityManager
from dsm_kernel.shard_catalog import ShardCatalog

if TYPE_CHECKING:
    from dsm_kernel.shard_manager import MemoryShard
    from dsm_modules.dsm_router.router import ShardRouter
    from dsm_modules.dsm_validator.link_validator import LinkValidator
    from dsm_modules.dsm_rr.semantic_search import SemanticSearch
    from dsm_modules.dsm_cache.embedding_service import EmbeddingService


class DSMKernel:
    """
    Stable kernel API facade. Delegates to router/validator/rr/cache.
    """

    def __init__(
        self,
        config: DSMConfig,
        router: "ShardRouter",
        validator: "LinkValidator",
        rr: Optional["SemanticSearch"] = None,
        cache: Optional["EmbeddingService"] = None,
    ):
        self._config = config
        self._router = router
        self._validator = validator
        self._rr = rr
        self._cache = cache
        self._catalog = ShardCatalog(config)
        self._integrity = IntegrityManager(config)

    def list_shards(self) -> List[Dict[str, Any]]:
        """List shards: prefer catalog if exists, else build+save then return. Stable keys."""
        loaded = self._catalog.load()
        if loaded:
            return list(loaded.values())
        entries = self._catalog.build(recompute_hash=False)
        if entries:
            self._catalog.save(entries)
            return [asdict(e) for e in entries.values()]
        return self._router.get_all_shards_status()

    def rebuild_catalog(self, recompute_hash: bool = False) -> List[Dict[str, Any]]:
        """Rebuild catalog from disk, save, return list of entry dicts."""
        entries = self._catalog.build(recompute_hash=recompute_hash)
        if entries:
            self._catalog.save(entries)
        return [asdict(e) for e in entries.values()]

    def rebuild_integrity_manifest(self) -> Dict[str, Any]:
        """Rebuild sha256 manifest from disk, save atomically, return manifest."""
        return self._integrity.rebuild()

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify shard files against manifest. Returns report with ok, missing, extra, changed."""
        return self._integrity.verify()

    def verify_shard_integrity(self, shard_id: str) -> Dict[str, Any]:
        """Verify single shard against manifest entry."""
        return self._integrity.verify_shard(shard_id)

    def get_shard(self, shard_id: str) -> "MemoryShard":
        """Return MemoryShard for shard_id. Raises if not found."""
        shard = self._router.get_shard_by_id(shard_id)
        if shard is None:
            raise KeyError(f"Shard not found: {shard_id}")
        return shard

    def append_event(
        self,
        shard_id: str,
        payload: Dict[str, Any],
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Append-only: add one transaction to the shard and save.
        payload: content (or text), source, importance, cross_refs.
        If validate=True, cross_refs are validated via LinkValidator.
        """
        content = payload.get("content") or payload.get("text") or ""
        source = payload.get("source", "manual")
        importance = float(payload.get("importance", 0.5))
        cross_refs = list(payload.get("cross_refs") or [])

        if validate and cross_refs:
            for to_shard in cross_refs:
                ok, msg = self._validator.validate_link(shard_id, to_shard)
                if not ok:
                    raise ValueError(f"Invalid cross-ref {shard_id} -> {to_shard}: {msg}")

        shard = self.get_shard(shard_id)
        tx_id = shard.add_transaction(
            content=content,
            source=source,
            importance=importance,
            cross_refs=cross_refs or None,
        )
        return {"id": tx_id, "shard_id": shard_id}

    def query(
        self,
        shard_id: str,
        query: str,
        *,
        mode: str = "fulltext",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Query one shard. mode: fulltext (MemoryShard.query), semantic, hybrid.
        """
        if mode == "fulltext":
            shard = self.get_shard(shard_id)
            results = shard.query(query, limit=limit)
            for r in results:
                r.setdefault("shard_id", shard_id)
                r.setdefault("shard_name", shard.config.get("name", shard_id))
            return results
        if mode == "semantic" and self._rr:
            return self._rr.search(query, shard_id=shard_id)[:limit]
        if mode == "hybrid" and self._rr:
            return self._rr.hybrid_search(query, shard_id=shard_id)[:limit]
        # Fallback to fulltext when semantic/hybrid requested but rr unavailable
        shard = self.get_shard(shard_id)
        results = shard.query(query, limit=limit)
        for r in results:
            r.setdefault("shard_id", shard_id)
            r.setdefault("shard_name", shard.config.get("name", shard_id))
        return results

    def query_global(
        self,
        query: str,
        *,
        mode: str = "router",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Query across shards. mode=router: use ShardRouter to query (fulltext across shards).
        """
        if mode == "router":
            return self._router.query(query, limit=limit)
        return self._router.query(query, limit=limit)
