#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MemoryCompressor - Compression de mémoire pour DARYL Sharding Memory
Migrated from memory_compressor.py (buralux/dsm).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from dsm_modules.dsm_rr.semantic_search import SemanticSearch


class MemoryCompressor:
    """Module de compression de mémoire pour DARYL"""

    def __init__(self, shards_directory="memory/shards", similarity_threshold=0.9, max_age_days=90):
        self.shards_dir = shards_directory
        self.similarity_threshold = similarity_threshold
        self.max_age = max_age_days
        self.semantic_search = SemanticSearch(shards_directory=shards_directory, threshold=similarity_threshold, top_k=10)
        self.stats = {
            "total_transactions": 0,
            "consolidated_transactions": 0,
            "removed_duplicates": 0,
            "expired_transactions": 0,
            "last_compression": None
        }
        self._load_all_shards()

    def _load_all_shards(self):
        pass  # SemanticSearch already loads shards; no extra load needed here

    def _load_shard_data(self, shard_id: str) -> Optional[Dict]:
        shard_path = Path(self.shards_dir) / f"{shard_id}.json"
        if not shard_path.exists():
            return None
        try:
            with open(shard_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur chargement shard {shard_id}: {e}")
            return None

    def _find_similar_transactions(self, shard_data: Dict, transaction_id: str, top_k: int = 5) -> List[Dict]:
        transactions = shard_data.get("transactions", [])
        target_tx = None
        for tx in transactions:
            if tx.get("id") == transaction_id:
                target_tx = tx
                break
        if target_tx is None or "content" not in target_tx:
            return []
        config_id = shard_data.get("config", {}).get("id", "")
        similar_results = self.semantic_search.search(target_tx["content"], shard_id=config_id or None)
        filtered = [r for r in similar_results if r.get("transaction_id") != transaction_id]
        return filtered[:top_k]

    def _consolidate_transactions(self, shard_id: str, transaction_ids: List[str]) -> Optional[Dict]:
        shard_data = self._load_shard_data(shard_id)
        if shard_data is None:
            return None
        transactions = shard_data.get("transactions", [])
        target_transactions = [tx for tx in transactions if tx.get("id") in transaction_ids]
        if len(target_transactions) < 2:
            return None
        contents = [tx.get("content", "") for tx in target_transactions]
        importance_scores = [tx.get("importance", 0.5) for tx in target_transactions]
        base_content = max(contents, key=len)
        consolidated_tx = {
            "id": f"consolidated_{shard_id}_{datetime.now().timestamp()}",
            "content": f"[Consolidated: {len(transaction_ids)} items] {base_content}",
            "source": "memory_compressor",
            "importance": max(importance_scores),
            "timestamp": datetime.now().isoformat(),
            "consolidated_from": transaction_ids,
            "consolidated_count": len(transaction_ids),
            "cross_refs": []
        }
        return consolidated_tx

    def compress_shard(self, shard_id: str, force: bool = False) -> Dict:
        shard_data = self._load_shard_data(shard_id)
        if shard_data is None:
            return {"error": "Shard not found"}
        transactions = shard_data.get("transactions", [])
        removed_duplicates = []
        seen_contents = set()
        unique_transactions = []
        for tx in transactions:
            content = tx.get("content", "").strip().lower()
            content_hash = f"{content}_{tx.get('importance', 0)}"
            if content_hash in seen_contents:
                removed_duplicates.append(tx.get("id"))
                continue
            seen_contents.add(content_hash)
            unique_transactions.append(tx)
        consolidated_count = 0
        for i, tx in enumerate(unique_transactions):
            if "embedding" not in tx:
                continue
            similar = self._find_similar_transactions(shard_data, tx["id"], top_k=3)
            if len(similar) >= 2:
                similar_ids = [s.get("transaction_id") for s in similar]
                consolidated = self._consolidate_transactions(shard_id, similar_ids)
                if consolidated:
                    for t in unique_transactions:
                        if t.get("id") in similar_ids:
                            t["consolidated_into"] = consolidated["id"]
                    unique_transactions.append(consolidated)
                    consolidated_count += 1
                    break
        final_transactions = [tx for tx in unique_transactions if "consolidated_into" not in tx]
        shard_data["transactions"] = final_transactions
        shard_data["metadata"] = shard_data.get("metadata", {})
        shard_data["metadata"]["last_compression"] = datetime.now().isoformat()
        shard_data["metadata"]["consolidated_count"] = consolidated_count
        self._save_shard(shard_id, shard_data)
        return {
            "removed_duplicates": len(removed_duplicates),
            "consolidated_transactions": consolidated_count,
            "total_before": len(transactions),
            "total_after": len(final_transactions)
        }

    def _save_shard(self, shard_id: str, shard_data: Dict):
        shard_path = Path(self.shards_dir) / f"{shard_id}.json"
        try:
            with open(shard_path, 'w', encoding='utf-8') as f:
                json.dump(shard_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erreur sauvegarde shard {shard_id}: {e}")

    def compress_all_shards(self, force: bool = False) -> Dict:
        shards_path = Path(self.shards_dir)
        if not shards_path.exists():
            return {"error": "Shards directory not found"}
        results = {}
        for shard_file in shards_path.glob("*.json"):
            shard_id = shard_file.stem
            compression_result = self.compress_shard(shard_id, force=force)
            if "error" not in compression_result:
                results[shard_id] = compression_result
        self.stats["total_transactions"] = sum(r.get("total_before", 0) for r in results.values())
        self.stats["consolidated_transactions"] = sum(r.get("consolidated_transactions", 0) for r in results.values())
        self.stats["removed_duplicates"] = sum(r.get("removed_duplicates", 0) for r in results.values())
        self.stats["last_compression"] = datetime.now().isoformat()
        return results

    def get_compression_stats(self) -> Dict:
        return self.stats
