#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShardRouter - routing policy and orchestration.
Migrated from memory_sharding_system.py (buralux/dsm).
"""

import json
import re
from datetime import datetime
from pathlib import Path

from dsm_kernel.shard_manager import (
    MemoryShard,
    SHARDS_DIR,
    MEMORY_DIR,
    SHARD_DOMAINS,
)

try:
    from dsm_modules.dsm_cache.embedding_service import EmbeddingService
    from dsm_modules.dsm_rr.semantic_search import SemanticSearch
    from dsm_modules.dsm_compressor.compressor import MemoryCompressor
    from dsm_modules.dsm_cleaner.cleaner import MemoryCleaner
except ImportError:
    EmbeddingService = None
    SemanticSearch = None
    MemoryCompressor = None
    MemoryCleaner = None


class ShardRouter:
    """Routeur de shards - Gestion intelligente de la mémoire"""

    def __init__(self):
        self.shards = {}
        self.shards_config = {
            "routing_config": {
                "importance_threshold": 0.6,
                "bonus_frequent_shards": 0.5,
                "bonus_keywords": 1.0,
                "max_cross_refs": 3,
                "whitelist_patterns": [
                    r"voir shard\s+(\w+)",
                    r"shard:\s*(\w+)",
                    r"shard\s*(\w+)",
                    r"@\s*(\w+)",
                    r"connecté avec\s*@\s*(\w+)",
                    r"relation\s*@\s*(\w+)",
                    r"expert\s*@\s*(\w+)",
                    r"builder\s*@\s*(\w+)",
                    r"contact\s*@\s*(\w+)",
                    r"discussion\s*avec\s*@\s*(\w+)",
                    r"réponse\s*à\s*@\s*(\w+)"
                ]
            }
        }
        self._load_all_shards()

        try:
            self.embedding_service = EmbeddingService()
            self.semantic_search = SemanticSearch(shards_directory=str(SHARDS_DIR))
            self.memory_compressor = MemoryCompressor(shards_directory=str(SHARDS_DIR), similarity_threshold=0.9)
            self.memory_cleaner = MemoryCleaner(shards_directory=str(SHARDS_DIR))
            print("✅ Phase 2 services initialized")
        except Exception as e:
            print(f"⚠️ Phase 2 services not available: {e}")
            self.embedding_service = None
            self.semantic_search = None
            self.memory_compressor = None
            self.memory_cleaner = None

    def load_all_shards(self):
        """Public alias for reloading shards (CLI compatibility)."""
        self._load_all_shards()

    def _load_all_shards(self):
        if not SHARDS_DIR.exists():
            SHARDS_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created shards directory: {SHARDS_DIR}")

        shard_files = list(SHARDS_DIR.glob("*.json"))
        print(f"📁 Loading {len(shard_files)} shards from {SHARDS_DIR}")

        for shard_file in shard_files:
            shard_id = shard_file.stem
            domain = shard_id.replace("shard_", "")
            try:
                with open(shard_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                shard = MemoryShard(shard_id, domain)
                shard.transactions = data.get("transactions", [])
                shard.metadata.update(data.get("metadata", {}))
                self.shards[shard_id] = shard
                print(f"  ✅ {shard_id}: {len(shard.transactions)} transactions")
            except Exception as e:
                print(f"  ❌ {shard_id}: Error loading - {e}")
        print(f"📊 Total shards loaded: {len(self.shards)}")

    def _find_best_shard_for_content(self, content):
        content_lower = content.lower()
        shard_scores = {}
        for shard_id, shard in self.shards.items():
            score = 0.0
            keywords = shard.config.get("keywords", [])
            keyword_matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            score += keyword_matches * self.shards_config["routing_config"]["bonus_keywords"]
            score += shard.metadata.get("importance_score", 0) * self.shards_config["routing_config"]["bonus_frequent_shards"]
            shard_scores[shard_id] = score
        if not shard_scores:
            return ("shard_technical", [])
        best_shard_id = max(shard_scores, key=lambda x: shard_scores[x])
        best_score = shard_scores[best_shard_id]
        threshold = self.shards_config["routing_config"]["importance_threshold"]
        if best_score < threshold and "shard_projects" in shard_scores:
            if shard_scores["shard_projects"] >= threshold:
                best_shard_id = "shard_projects"
        cross_refs = self._detect_cross_references(content)
        max_refs = self.shards_config["routing_config"]["max_cross_refs"]
        cross_refs = cross_refs[:max_refs]
        return (best_shard_id, cross_refs)

    def _detect_cross_references(self, content):
        cross_refs = []
        patterns = self.shards_config["routing_config"]["whitelist_patterns"]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                shard_match = re.search(r'(shard_|\w+)', match if isinstance(match, str) else str(match))
                if shard_match:
                    shard_id = shard_match.group(1).lower()
                    for valid_shard_id in self.shards.keys():
                        if valid_shard_id.lower() == shard_id:
                            cross_refs.append(valid_shard_id)
                            break
        return list(set(cross_refs))

    def add_memory(self, content, source="manual", importance=0.5, shard_id=None):
        if shard_id is None:
            shard_id, cross_refs = self._find_best_shard_for_content(content)
        else:
            cross_refs = []
        if shard_id not in self.shards:
            raise ValueError(f"Shard not found: {shard_id}")
        shard = self.shards[shard_id]
        tx_id = shard.add_transaction(content, source=source, importance=importance, cross_refs=cross_refs)
        return tx_id

    def query(self, query_text, limit=10, shard_id=None):
        if shard_id:
            if shard_id not in self.shards:
                return []
            shard = self.shards[shard_id]
            results = shard.query(query_text, limit=limit)
            for r in results:
                r["shard_id"] = shard_id
                r["shard_name"] = shard.config["name"]
            return results
        all_results = []
        for sid, shard in sorted(self.shards.items(), key=lambda x: x[1].metadata.get("importance_score", 0), reverse=True):
            shard_results = shard.query(query_text, limit=limit)
            for r in shard_results:
                r["shard_id"] = sid
                r["shard_name"] = shard.config["name"]
            all_results.extend(shard_results)
        return all_results[:limit]

    def semantic_search(self, query_text, shard_id=None, top_k=5, threshold=0.7):
        if self.semantic_search is None:
            print("❌ Semantic search not available")
            return []
        return self.semantic_search.search(query_text, shard_id=shard_id)

    def hybrid_search(self, query_text, shard_id=None, top_k=5, threshold=0.7):
        if self.semantic_search is None:
            print("❌ Semantic search not available")
            return []
        return self.semantic_search.hybrid_search(query_text, shard_id=shard_id)

    def compress_memory(self, shard_id=None, force=False):
        if self.memory_compressor is None:
            print("❌ Memory compressor not available")
            return {"error": "Memory compressor not available"}
        if shard_id:
            return self.memory_compressor.compress_shard(shard_id, force=force)
        return self.memory_compressor.compress_all_shards(force=force)

    def cleanup_expired(self, shard_id=None, dry_run=False):
        if self.memory_cleaner is None:
            print("❌ Memory cleaner not available")
            return {"error": "Memory cleaner not available"}
        if shard_id:
            return self.memory_cleaner.cleanup_expired_transactions(shard_id, dry_run=dry_run)
        return self.memory_cleaner.run_cleanup_all_shards(dry_run=dry_run)

    def find_similar_transactions(self, transaction_id, shard_id, top_k=5):
        if self.semantic_search is None:
            print("❌ Semantic search not available")
            return []
        return self.semantic_search.find_similar_transactions(transaction_id, shard_id, top_k=top_k)

    def cross_shard_search(self, query_text):
        semantic_results = []
        if self.semantic_search:
            semantic_results = self.semantic_search.search(query_text)
        text_results = []
        for shard_id, shard in self.shards.items():
            results = shard.query(query_text, limit=3)
            text_results.extend(results)
        seen_ids = set()
        cross_shard_results = []
        for r in semantic_results:
            tid = r.get("transaction_id")
            if tid not in seen_ids:
                cross_shard_results.append(r)
                seen_ids.add(tid)
        for r in text_results:
            tid = r.get("id")
            if tid not in seen_ids:
                r["transaction_id"] = tid
                cross_shard_results.append(r)
                seen_ids.add(tid)
        cross_shard_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return cross_shard_results[:10]

    def get_shard_status(self, shard_id):
        if shard_id not in self.shards:
            return {"error": "Shard not found"}
        shard = self.shards[shard_id]
        return {
            "shard_id": shard_id,
            "domain": shard.domain,
            "name": shard.config["name"],
            "transactions_count": len(shard.transactions),
            "importance_score": shard.metadata.get("importance_score", 0),
            "last_updated": shard.metadata.get("last_updated", "N/A")
        }

    def get_all_shards_status(self):
        status = []
        for shard_id, shard in self.shards.items():
            status.append({
                "shard_id": shard_id,
                "domain": shard.domain,
                "name": shard.config["name"],
                "transactions_count": len(shard.transactions),
                "importance_score": shard.metadata.get("importance_score", 0),
                "last_updated": shard.metadata.get("last_updated", "N/A")
            })
        status.sort(key=lambda x: x["importance_score"], reverse=True)
        return status

    def export_shards_summary(self):
        summary = {
            "exported_at": datetime.now().isoformat(),
            "total_shards": len(self.shards),
            "total_transactions": sum(len(s.transactions) for s in self.shards.values()),
            "domains_count": len(set(s.domain for s in self.shards.values())),
            "shards_status": self.get_all_shards_status(),
            "routing_config": self.shards_config["routing_config"]
        }
        summary_file = MEMORY_DIR / "shards_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return summary

    def get_all_shards(self):
        return self.shards

    def get_shard_by_domain(self, domain):
        return [shard for sid, shard in self.shards.items() if shard.domain == domain]

    def list_shards(self):
        """API compatibility: list shard IDs."""
        return list(self.shards.keys())

    def get_shard_by_id(self, shard_id):
        """API compatibility: get shard by ID."""
        return self.shards.get(shard_id)


def main():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SHARDS_DIR.mkdir(parents=True, exist_ok=True)
    router = ShardRouter()
    print("🚀 DARYL Sharding Memory v2.0")
    print("📁 Répertoire shards:", SHARDS_DIR)
    print()
    print("✅ Phase 2 Integration:")
    print(" - EmbeddingService: {}".format("✅" if router.embedding_service else "❌"))
    print(" - SemanticSearch: {}".format("✅" if router.semantic_search else "❌"))
    print(" - MemoryCompressor: {}".format("✅" if router.memory_compressor else "❌"))
    print(" - MemoryCleaner: {}".format("✅" if router.memory_cleaner else "❌"))
    print()
    print("📊 Shards Status:")
    for status in router.get_all_shards_status()[:5]:
        print(f" • [{status['domain']}] {status['name']}: {status['transactions_count']} tx (score: {status['importance_score']:.2f})")
    if len(router.shards) > 5:
        print(f" ... + {len(router.shards) - 5} more shards")
    print()
    summary = router.export_shards_summary()
    print(f"📊 Résumé exporté: {len(summary['shards_status'])} shards, {summary['total_transactions']} transactions")
    print("✅ DARYL Sharding Memory v2.0 ready!")


if __name__ == "__main__":
    main()
