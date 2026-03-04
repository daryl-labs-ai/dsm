#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI pour le Système de Sharding de Mémoire DARYL v2.0
Migrated from cli/daryl_memory_cli.py (buralux/dsm).
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dsm_modules.dsm_router.router import ShardRouter
from dsm_kernel.config import DSMConfig
from dsm_kernel.shard_catalog import ShardCatalog


def cmd_add(args):
    if not args:
        print("Usage: daryl-memory add \"<content>\" [--importance <0.5-1.0>] [--source <source>]")
        return
    content = args[0]
    importance = 0.5
    source = "manual"
    i = 1
    while i < len(args):
        if args[i] == "--importance":
            importance = float(args[i + 1])
            i += 2
        elif args[i] == "--source":
            source = args[i + 1]
            i += 2
        else:
            i += 1
    router = ShardRouter()
    router.load_all_shards()
    transaction_id = router.add_memory(content, source=source, importance=importance)
    parts = transaction_id.split("_")
    shard_id = "_".join(parts[:-2])
    shard = router.shards.get(shard_id)
    if shard:
        print("✅ Mémoire ajoutée")
        print(f"  Shard: {shard.config['name']}")
        print(f"  ID: {transaction_id}")
        print(f"  Source: {source}")
        print(f"  Importance: {importance}")
    else:
        print("❌ Erreur: Impossible de trouver le shard cible")


def cmd_query(args):
    if len(args) < 1:
        print("Usage: daryl-memory query \"<query>\" [--limit <n>] [--cross]")
        return
    query_text = args[0]
    limit = 10
    cross_shard = False
    i = 1
    while i < len(args):
        if args[i] == "--limit":
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--cross":
            cross_shard = True
            i += 1
        else:
            i += 1
    router = ShardRouter()
    router.load_all_shards()
    if cross_shard:
        results = router.cross_shard_search(query_text)
        print(f"🔍 Recherche cross-shard: \"{query_text}\"")
    else:
        results = router.query(query_text, limit=limit)
    print(f"  Limit: {limit}")
    print(f"  Cross-shard: {cross_shard}")
    print(f"  Résultats: {len(results)} trouvés")
    for r in results[:limit]:
        shard_name = r.get("shard_name", "Inconnu")
        content = r.get("content", "")
        content = content[:70] + "..." if len(content) > 70 else content
        print(f"  • [{shard_name}] {content}")


def cmd_search(args):
    if len(args) < 2:
        print("Usage: daryl-memory search <shard_id> \"<query>\" [--limit <n>]")
        return
    shard_id = args[0]
    query_text = args[1]
    limit = 5
    i = 2
    while i < len(args):
        if args[i] == "--limit":
            limit = int(args[i + 1])
            i += 2
        else:
            i += 1
    router = ShardRouter()
    router.load_all_shards()
    if shard_id not in router.shards:
        print(f"❌ Erreur: Shard '{shard_id}' introuvable")
        return
    shard = router.shards[shard_id]
    results = shard.query(query_text, limit=limit)
    print(f"🔍 Recherche dans \"{shard.config['name']}\":")
    print(f"  Texte: {query_text}")
    print(f"  Résultats: {len(results)} trouvés")
    for r in results:
        content = r.get("content", "")
        content = content[:70] + "..." if len(content) > 70 else content
        print(f"  • {content}")


def cmd_status(args):
    router = ShardRouter()
    router.load_all_shards()
    print("📊 Statut des Shards DARYL:")
    print()
    status = router.get_all_shards_status()
    for shard_status in status:
        name = shard_status["name"]
        count = shard_status["transactions_count"]
        importance = shard_status["importance_score"]
        last = (shard_status.get("last_updated") or "N/A")[:19]
        if count == 0:
            emoji = "📭"
        elif count < 5:
            emoji = "📁"
        elif count < 20:
            emoji = "📚"
        else:
            emoji = "📖"
        print(f"  {emoji} {name}: {count} transactions (importance: {importance:.2f}) | {last}")
    summary = router.export_shards_summary()
    print(f"\n📊 Total: {summary['total_shards']} shards, {summary['total_transactions']} transactions")


def cmd_catalog_rebuild(args):
    recompute_hash = "--hash" in args or "-h" in args
    config = DSMConfig()
    catalog = ShardCatalog(config)
    entries = catalog.build(recompute_hash=recompute_hash)
    if entries:
        catalog.save(entries)
    path = config.shard_catalog_path
    print(f"📂 Catalog: {len(entries)} entries -> {path}")


def cmd_help(args):
    print("=== DARYL Sharding Memory CLI v2.0 ===")
    print()
    print("Usage: daryl-memory [arguments...]")
    print()
    print("Commandes disponibles:")
    print("  add \"<content>\"     Ajouter une mémoire")
    print("  query \"<query>\"    Rechercher des mémoires")
    print("  search <shard> \"<query>\"  Rechercher dans un shard")
    print("  status             Afficher le statut des shards")
    print("  catalog rebuild [--hash]  Reconstruire l'index catalogue shards")
    print("  help               Afficher cette aide")
    print()
    print("Exemples:")
    print("  daryl-memory add \"Projet: Finaliser la doc\" --importance 0.8")
    print("  daryl-memory query \"stratégie\" --limit 5")
    print("  daryl-memory search shard_projects \"GitHub\"")


def main():
    if len(sys.argv) < 2:
        cmd_help([])
        return
    command = sys.argv[1].lower()
    rest = sys.argv[2:]
    if command == "add":
        cmd_add(rest)
    elif command == "query":
        cmd_query(rest)
    elif command == "search":
        cmd_search(rest)
    elif command == "status":
        cmd_status(rest)
    elif command == "catalog":
        if rest and rest[0].lower() == "rebuild":
            cmd_catalog_rebuild(rest[1:])
        else:
            print("Usage: daryl-memory catalog rebuild [--hash]")
    elif command == "help":
        cmd_help(rest)
    else:
        print(f"❌ Commande inconnue: {command}")
        print("Utilisez 'daryl-memory help' pour voir les commandes disponibles")


if __name__ == "__main__":
    main()
