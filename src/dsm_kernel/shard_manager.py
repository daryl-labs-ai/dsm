#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shard manager: MemoryShard, file I/O, load/save, shard paths.
Migrated from memory_sharding_system.py (buralux/dsm).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Configuration
MEMORY_DIR = Path("/home/buraluxtr/clawd/memory")
SHARDS_DIR = MEMORY_DIR / "shards"
SHARD_CONFIG_FILE = SHARDS_DIR / "shard_config.json"

# Définition des shards par domaine
SHARD_DOMAINS = {
    "projects": {
        "name": "Projets en cours",
        "description": "Projets actifs, tâches en cours, objectifs",
        "keywords": ["projet", "task", "project", "todo", "goal", "objective"]
    },
    "insights": {
        "name": "Insights et Leçons",
        "description": "Leçons apprises, patterns identifiés, décisions importantes",
        "keywords": ["leçon", "lesson", "pattern", "insight", "décision", "decision"]
    },
    "people": {
        "name": "Personnes et Relations",
        "description": "Contacts, experts, builders, relations importantes",
        "keywords": ["@", "contact", "person", "expert", "builder", "relation"]
    },
    "technical": {
        "name": "Technique et Architecture",
        "description": "Architecture, code, protocoles, frameworks",
        "keywords": ["architecture", "framework", "code", "protocol", "shard", "layer", "pillar"]
    },
    "strategy": {
        "name": "Stratégie et Vision",
        "description": "Vision à long terme, priorités, stratégies de contenu",
        "keywords": ["stratégie", "vision", "priority", "tendance", "trend"]
    }
}


class MemoryShard:
    """Représente un shard de mémoire"""

    def __init__(self, shard_id, domain):
        self.shard_id = shard_id
        self.domain = domain
        self.config = SHARD_DOMAINS[domain]
        self.transactions = []
        self.metadata = {
            "version": "2.0",
            "importance_score": 0.0,
            "last_updated": None
        }
        self._load()

    def _load(self):
        """Charge les transactions depuis le fichier JSON"""
        shard_path = SHARDS_DIR / f"{self.shard_id}.json"

        if not shard_path.exists():
            self.metadata["created_at"] = datetime.now().isoformat()
            self._save()
            return

        try:
            with open(shard_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.transactions = data.get("transactions", [])
            self.metadata.update(data.get("metadata", {}))
        except Exception as e:
            print(f"❌ Error loading shard {self.shard_id}: {e}")

    def add_transaction(self, content, source="manual", importance=0.5, cross_refs=None):
        """
        Ajoute une transaction (mémoire) à ce shard
        """
        transaction = {
            "id": f"{self.shard_id}_{len(self.transactions)}_{datetime.now().timestamp()}",
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "importance": importance,
            "cross_refs": cross_refs or []
        }
        self.transactions.append(transaction)
        self._update_importance()
        self._save()
        return transaction["id"]

    def query(self, query_text, limit=10):
        """Recherche dans ce shard"""
        query_lower = query_text.lower()
        results = []
        for t in reversed(self.transactions):
            if query_lower in t["content"].lower():
                results.append(t)
            if len(results) >= limit:
                break
        return results

    def _update_importance(self):
        if not self.transactions:
            return
        avg_importance = sum(t["importance"] for t in self.transactions) / len(self.transactions)
        transaction_count = min(len(self.transactions), 100)
        count_bonus = transaction_count / 100.0
        self.metadata["importance_score"] = avg_importance + count_bonus
        self.metadata["last_updated"] = datetime.now().isoformat()

    def _save(self):
        """Sauvegarde les données du shard"""
        shard_path = SHARDS_DIR / f"{self.shard_id}.json"
        data = {
            "config": {
                "id": self.shard_id,
                "name": self.config["name"],
                "domain": self.domain,
                "keywords": self.config["keywords"],
                "created_at": self.metadata.get("created_at", datetime.now().isoformat())
            },
            "transactions": self.transactions,
            "metadata": self.metadata
        }
        try:
            with open(shard_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving shard {self.shard_id}: {e}")

    def to_dict(self):
        """Serialization for API/Web UI compatibility."""
        return {
            "config": {
                "id": self.shard_id,
                "name": self.config["name"],
                "domain": self.domain,
                "keywords": self.config.get("keywords", []),
            },
            "transactions": self.transactions,
            "metadata": self.metadata,
        }
