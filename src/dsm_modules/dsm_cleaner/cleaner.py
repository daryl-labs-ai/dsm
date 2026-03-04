#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MemoryCleaner - Nettoyage TTL pour DARYL Sharding Memory
Migrated from memory_cleaner.py (buralux/dsm).
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Optional: SemanticSearch not used in cleaner logic but was a dependency in source
try:
    from dsm_modules.dsm_rr.semantic_search import SemanticSearch
except ImportError:
    SemanticSearch = None


class MemoryCleaner:
    """Module de nettoyage TTL pour DARYL"""

    def __init__(self, shards_directory: str = "memory/shards", ttl_config_file: str = "config/ttl_config.json"):
        self.shards_dir = shards_directory
        self.ttl_config_file = ttl_config_file
        self.ttl_config: Dict[str, Dict[str, int]] = {
            "shard_projects": {"ttl_days": 30, "max_transactions": 100},
            "shard_insights": {"ttl_days": 90, "max_transactions": 50},
            "shard_people": {"ttl_days": 90, "max_transactions": 50},
            "shard_technical": {"ttl_days": 180, "max_transactions": 200},
            "shard_strategy": {"ttl_days": 180, "max_transactions": 200}
        }
        self.stats: Dict[str, Any] = {
            "total_shards": 0,
            "expired_transactions": 0,
            "expired_transactions_by_shard": {},
            "archived_transactions": 0,
            "last_cleanup": None
        }
        self.shards_data: Dict[str, Dict[str, Any]] = {}
        self._load_ttl_config()
        self._load_all_shards()

    def _load_ttl_config(self) -> None:
        config_path = Path(self.ttl_config_file)
        if config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as f:
                    self.ttl_config = json.load(f)
                print(f"✅ Configuration TTL chargée depuis {config_path}")
            except Exception as e:
                print(f"⚠️ Erreur chargement TTL config, utilisation des valeurs par défaut: {e}")
        else:
            self._create_default_ttl_config()

    def _create_default_ttl_config(self) -> None:
        config_path = Path(self.ttl_config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            "shard_projects": {"ttl_days": 30, "max_transactions": 100},
            "shard_insights": {"ttl_days": 90, "max_transactions": 50},
            "shard_people": {"ttl_days": 90, "max_transactions": 50},
            "shard_technical": {"ttl_days": 180, "max_transactions": 200},
            "shard_strategy": {"ttl_days": 180, "max_transactions": 200}
        }
        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"✅ Configuration TTL par défaut créée: {config_path}")
        except Exception as e:
            print(f"❌ Erreur création config TTL: {e}")

    def _load_all_shards(self) -> None:
        shards_path = Path(self.shards_dir)
        if not shards_path.exists():
            print(f"❌ Répertoire des shards non trouvé: {self.shards_dir}")
            return
        shard_files = list(shards_path.glob("*.json"))
        print(f"📁 Chargement de {len(shard_files)} shards depuis {self.shards_dir}")
        for shard_file in shard_files:
            shard_id = shard_file.stem
            try:
                with shard_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if "transactions" not in data or not isinstance(data["transactions"], list):
                    data["transactions"] = []
                if "metadata" not in data or not isinstance(data["metadata"], dict):
                    data["metadata"] = {}
                self.shards_data[shard_id] = data
                print(f"  ✅ {shard_id}: {len(data.get('transactions', []))} transactions chargées")
            except Exception as e:
                print(f"  ❌ {shard_id}: Erreur de chargement - {e}")

    def _is_transaction_expired(self, transaction: Dict[str, Any], shard_id: str, current_date: datetime) -> bool:
        shard_ttl = self.ttl_config.get(shard_id, {"ttl_days": 180})
        ttl_days = int(shard_ttl.get("ttl_days", 180))
        timestamp_str = transaction.get("timestamp", "")
        if not timestamp_str:
            return True
        try:
            transaction_date = datetime.fromisoformat(timestamp_str)
            age_days = (current_date - transaction_date).days
            return age_days > ttl_days
        except Exception as e:
            print(f"⚠️ Erreur parsing timestamp '{timestamp_str}': {e}")
            return True

    def cleanup_expired_transactions(self, shard_id: str, dry_run: bool = False) -> Dict[str, Any]:
        if shard_id not in self.shards_data:
            return {"error": "Shard not found", "shard_id": shard_id}
        shard_data = self.shards_data[shard_id]
        transactions = shard_data.get("transactions", [])
        current_date = datetime.now()
        expired = []
        kept = []
        for tx in transactions:
            if self._is_transaction_expired(tx, shard_id, current_date):
                expired.append(tx)
            else:
                kept.append(tx)
        stats = {
            "shard_id": shard_id,
            "total_transactions": len(transactions),
            "expired_transactions": len(expired),
            "kept_transactions": len(kept),
            "dry_run": dry_run,
        }
        if not dry_run and len(expired) > 0:
            shard_data["transactions"] = kept
            shard_data.setdefault("metadata", {})
            shard_data["metadata"]["last_cleanup"] = current_date.isoformat()
            shard_data["metadata"]["expired_transactions"] = len(expired)
            self._save_shard(shard_id, shard_data)
        return stats

    def archive_transactions(self, transactions: List[Dict[str, Any]], archive_file: str = "memory/archives/expired.json") -> bool:
        archive_path = Path(archive_file)
        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            existing_archives = []
            if archive_path.exists():
                with archive_path.open("r", encoding="utf-8") as f:
                    existing_archives = json.load(f)
                if not isinstance(existing_archives, list):
                    existing_archives = []
            existing_archives.extend(transactions)
            with archive_path.open("w", encoding="utf-8") as f:
                json.dump(existing_archives, f, indent=2, ensure_ascii=False)
            print(f"✅ {len(transactions)} transactions archivées dans {archive_file}")
            return True
        except Exception as e:
            print(f"❌ Erreur archivage: {e}")
            return False

    def cleanup_max_transactions(self, shard_id: str, dry_run: bool = False) -> Dict[str, Any]:
        if shard_id not in self.shards_data:
            return {"error": "Shard not found", "shard_id": shard_id}
        shard_ttl = self.ttl_config.get(shard_id, {"max_transactions": 200})
        max_transactions = int(shard_ttl.get("max_transactions", 200))
        shard_data = self.shards_data[shard_id]
        transactions = shard_data.get("transactions", [])
        transactions_sorted = sorted(transactions, key=lambda x: x.get("timestamp", ""), reverse=True)
        kept = transactions_sorted[:max_transactions]
        removed = transactions_sorted[max_transactions:]
        stats = {
            "shard_id": shard_id,
            "total_transactions": len(transactions),
            "removed_transactions": len(removed),
            "kept_transactions": len(kept),
            "max_transactions": max_transactions,
            "dry_run": dry_run,
        }
        if not dry_run and len(removed) > 0:
            shard_data["transactions"] = kept
            self.archive_transactions(removed, f"memory/archives/shard_{shard_id}_expired.json")
            shard_data.setdefault("metadata", {})
            shard_data["metadata"]["last_cleanup_max"] = datetime.now().isoformat()
            shard_data["metadata"]["removed_for_max"] = len(removed)
            self._save_shard(shard_id, shard_data)
        return stats

    def run_cleanup_all_shards(self, dry_run: bool = False) -> Dict[str, Dict[str, Any]]:
        results = {}
        total_expired = 0
        total_removed_max = 0
        for shard_id in list(self.shards_data.keys()):
            expired_stats = self.cleanup_expired_transactions(shard_id, dry_run=dry_run)
            results[f"{shard_id}_expired"] = expired_stats
            total_expired += int(expired_stats.get("expired_transactions", 0))
            max_stats = self.cleanup_max_transactions(shard_id, dry_run=dry_run)
            results[f"{shard_id}_max"] = max_stats
            total_removed_max += int(max_stats.get("removed_transactions", 0))
        self.stats["total_shards"] = len(self.shards_data)
        self.stats["expired_transactions"] = total_expired
        self.stats["expired_transactions_by_shard"] = {
            sid: int(results.get(f"{sid}_expired", {}).get("expired_transactions", 0))
            for sid in self.shards_data.keys()
        }
        self.stats["archived_transactions"] = total_expired + total_removed_max
        self.stats["last_cleanup"] = datetime.now().isoformat()
        if not dry_run:
            print(f"🧹 Nettoyage terminé: {total_expired} expirées, {total_removed_max} supprimées (max)")
        else:
            print(f"🧹 DRY RUN: {total_expired} expirées, {total_removed_max} supprimées (max)")
        return results

    def _save_shard(self, shard_id: str, shard_data: Dict[str, Any]) -> None:
        shard_path = Path(self.shards_dir) / f"{shard_id}.json"
        try:
            with shard_path.open("w", encoding="utf-8") as f:
                json.dump(shard_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erreur sauvegarde shard {shard_id}: {e}")

    def get_cleanup_stats(self) -> Dict[str, Any]:
        return self.stats
