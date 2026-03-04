# Kernel vs modules

## What belongs where

- **dsm_kernel** (`src/dsm_kernel/`): Core, stable API and data model. Config, API facade, catalog, integrity, event log, shard manager. No business rules beyond “append only” and “derived indexes”.
- **dsm_modules** (`src/dsm_modules/`): Optional, evolving features. Router, validator, rr, cache, loop (watcher, orchestrator, ab_utils), cleaner, compressor. Can depend on the kernel; the kernel does not depend on modules for its core behavior.

## Rules

- **No massive refactor** — Documentation and small, backward-compatible changes only in the kernel; no large rewrites in a single PR.
- **Stable API** — Kernel facade (DSMKernel) is the contract: append_event, query, list_shards, rebuild_catalog, integrity and event-log entry points. New optional methods are allowed; existing behavior is not changed for “docs only” or “hygiene” work.
- **Derived indexes** — Catalog and integrity manifest are derived from shard files. They can be deleted and rebuilt; no kernel logic depends on them for append/query.

## Current kernel components

| Component | Role |
|----------|------|
| `config.py` | DSMConfig, paths (base_dir, shards_dir, index_dir, catalog, manifest, event_log). |
| `api.py` | DSMKernel: append_event, query, list_shards, rebuild_catalog, integrity, event logger. |
| `shard_manager.py` | MemoryShard, SHARDS_DIR, save/load, add_transaction. |
| `shard_catalog.py` | ShardCatalog: build/save/load from shards_dir. |
| `integrity.py` | IntegrityManager: sha256 manifest, verify/rebuild. |
| `event_log.py` | EventLogger: append-only JSONL. |

## Current module components

| Module | Role |
|--------|------|
| dsm_router | ShardRouter: load shards, route content, query. |
| dsm_validator | LinkValidator: validate cross-refs. |
| dsm_loop | EventWatcher, LoopOrchestrator, run_loop, ab_utils (record_ab_run). |
| dsm_rr | SemanticSearch. |
| dsm_cache | EmbeddingService. |
| dsm_cleaner | MemoryCleaner (TTL). |
| dsm_compressor | MemoryCompressor. |
