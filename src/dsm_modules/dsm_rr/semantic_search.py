#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SemanticSearch - Recherche vectorielle pour DARYL Sharding Memory
Migrated from semantic_search.py (buralux/dsm).
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

from dsm_modules.dsm_cache.embedding_service import EmbeddingService


class SemanticSearch:
    """Recherche sémantique basée sur les embeddings"""

    def __init__(self, shards_directory="memory/shards", threshold=0.7, top_k=5):
        self.shards_dir = shards_directory
        self.threshold = threshold
        self.top_k = top_k
        self.embedding_service = EmbeddingService()
        self.shards_data = {}
        self._load_all_shards()

    def _load_all_shards(self):
        shards_path = Path(self.shards_dir)
        if not shards_path.exists():
            print(f"❌ Répertoire des shards non trouvé: {self.shards_dir}")
            return
        shard_files = list(shards_path.glob("*.json"))
        print(f"📁 Chargement de {len(shard_files)} shards depuis {self.shards_dir}")
        for shard_file in shard_files:
            shard_id = shard_file.stem
            try:
                with open(shard_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                transactions = data.get("transactions", [])
                for tx in transactions:
                    if "embedding" not in tx and "content" in tx:
                        embedding = self.embedding_service.generate_embedding(tx["content"])
                        if embedding is not None:
                            tx["embedding"] = embedding
                self.shards_data[shard_id] = {
                    "config": data.get("config", {}),
                    "transactions": transactions
                }
                print(f"  ✅ {shard_id}: {len(transactions)} transactions chargées")
            except Exception as e:
                print(f"  ❌ {shard_id}: Erreur de chargement - {e}")

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        try:
            a = np.array(vec_a, dtype=np.float32)
            b = np.array(vec_b, dtype=np.float32)
            if np.all(a == 0) or np.all(b == 0):
                return 0.0
            dot = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0.0 or norm_b == 0.0:
                return 0.0
            similarity = dot / (norm_a * norm_b)
            return max(-1.0, min(1.0, similarity))
        except Exception as e:
            print(f"❌ Erreur calcul similarité: {e}")
            return 0.0

    def search(self, query_text: str, shard_id: Optional[str] = None) -> List[Dict]:
        query_embedding = self.embedding_service.generate_embedding(query_text)
        if query_embedding is None:
            print(f"❌ Erreur génération embedding pour: {query_text}")
            return []
        results = []
        shards_to_search = [shard_id] if shard_id else list(self.shards_data.keys())
        for sid in shards_to_search:
            if sid not in self.shards_data:
                continue
            shard_data = self.shards_data[sid]
            transactions = shard_data.get("transactions", [])
            for tx in transactions:
                if "embedding" not in tx:
                    continue
                similarity = self._cosine_similarity(query_embedding, tx["embedding"])
                if similarity >= self.threshold:
                    results.append({
                        "shard_id": sid,
                        "shard_name": shard_data.get("config", {}).get("name", sid),
                        "transaction_id": tx.get("id", ""),
                        "content": tx.get("content", ""),
                        "importance": tx.get("importance", 0),
                        "timestamp": tx.get("timestamp", ""),
                        "source": tx.get("source", ""),
                        "score": float(similarity)
                    })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:self.top_k]

    def hybrid_search(self, query_text: str, shard_id: Optional[str] = None) -> List[Dict]:
        semantic_results = self.search(query_text, shard_id)
        query_lower = query_text.lower()
        text_results = []
        shards_to_search = [shard_id] if shard_id else list(self.shards_data.keys())
        for sid in shards_to_search:
            if sid not in self.shards_data:
                continue
            shard_data = self.shards_data[sid]
            transactions = shard_data.get("transactions", [])
            config = shard_data.get("config", {})
            keywords = config.get("keywords", [])
            for tx in transactions:
                content = tx.get("content", "").lower()
                keyword_matches = sum(1 for kw in keywords if kw.lower() in content)
                if keyword_matches > 0:
                    text_results.append({
                        "shard_id": sid,
                        "shard_name": config.get("name", sid),
                        "transaction_id": tx.get("id", ""),
                        "content": tx.get("content", ""),
                        "importance": tx.get("importance", 0),
                        "timestamp": tx.get("timestamp", ""),
                        "source": tx.get("source", ""),
                        "score": 0.5,
                        "match_type": "keyword"
                    })
        seen_ids = set()
        hybrid_results = []
        for r in semantic_results:
            if r["transaction_id"] not in seen_ids:
                r["match_type"] = "semantic"
                hybrid_results.append(r)
                seen_ids.add(r["transaction_id"])
        for r in text_results:
            if r["transaction_id"] not in seen_ids:
                hybrid_results.append(r)
                seen_ids.add(r["transaction_id"])
        for r in hybrid_results:
            r["hybrid_score"] = r["score"]
            if r.get("match_type") == "keyword":
                r["hybrid_score"] += 0.3
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return hybrid_results[:self.top_k]

    def find_similar_transactions(self, transaction_id: str, shard_id: str, threshold: float = 0.9, top_k: int = 5) -> List[Dict]:
        if shard_id not in self.shards_data:
            return []
        shard_data = self.shards_data[shard_id]
        transactions = shard_data.get("transactions", [])
        target_tx = None
        for tx in transactions:
            if tx.get("id") == transaction_id:
                target_tx = tx
                break
        if target_tx is None or "embedding" not in target_tx:
            return []
        target_embedding = target_tx["embedding"]
        similar_transactions = []
        for tx in transactions:
            if tx.get("id") == transaction_id:
                continue
            if "embedding" not in tx:
                continue
            similarity = self._cosine_similarity(target_embedding, tx["embedding"])
            if similarity >= threshold:
                similar_transactions.append({
                    "transaction_id": tx.get("id"),
                    "content": tx.get("content", ""),
                    "score": float(similarity),
                    "importance": tx.get("importance", 0),
                    "timestamp": tx.get("timestamp", "")
                })
        similar_transactions.sort(key=lambda x: x["score"], reverse=True)
        return similar_transactions[:top_k]

    def get_search_stats(self) -> Dict[str, int]:
        total_transactions = sum(len(shard.get("transactions", [])) for shard in self.shards_data.values())
        total_embeddings = sum(1 for shard in self.shards_data.values() for tx in shard.get("transactions", []) if "embedding" in tx)
        cache_stats = self.embedding_service.get_cache_stats()
        return {
            "total_shards": len(self.shards_data),
            "total_transactions": total_transactions,
            "total_embeddings": total_embeddings,
            "cache_size": cache_stats.get("cache_size", 0),
            "model_name": cache_stats.get("model_name", ""),
            "embedding_dimension": cache_stats.get("embedding_dimension", 0)
        }
