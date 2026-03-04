# DSM — Daryl Sharding Memory

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Append-only, auditable memory kernel for AI agents.

## Key features

- **Append-only shards** — JSON shards per domain (projects, insights, technical, etc.), no in-place edits.
- **Catalog index** — Rebuildable index of shards (path, size, mtime, optional hash).
- **Integrity manifest** — SHA256 manifest for tamper detection; verify/rebuild.
- **Event log** — Append-only JSONL (`event_log.jsonl`) for every append; audit and replay.
- **Loop engine** — Optional watcher that reads the event log and runs tasks (e.g. write insights).
- **A/B benchmark** — Record runs (normal vs DSM memory) and compare success rate, time, rework.

## Architecture

```
Agents → Modules (router, validator, loop, …) → Kernel (DSMKernel) → Shards / Index
                                                                           ↓
                                            event_log.jsonl ←───────────────┘
                                            catalog, manifest, index dir
```

- **Kernel** (`src/dsm_kernel/`): config, API facade, catalog, integrity, event log. Stable, minimal.
- **Modules** (`src/dsm_modules/`): router, validator, rr, cache, loop (watcher, orchestrator, ab_utils).
- **Shards**: `data/shards/*.json`. **Index**: `data/index/` (catalog, manifest, event_log.jsonl).

See [docs/architecture/kernel-vs-modules.md](docs/architecture/kernel-vs-modules.md).

## Repo structure

```
dsm/
├── README.md
├── LICENSE
├── docs/
│   ├── quickstart.md
│   ├── architecture/
│   │   └── kernel-vs-modules.md
│   ├── loop/
│   │   └── README.md
│   └── benchmarks/
│       ├── README.md
│       └── ab_protocol.md
├── src/
│   ├── dsm_kernel/          # config, api, catalog, integrity, event_log, shard_manager
│   ├── dsm_modules/         # dsm_router, dsm_validator, dsm_loop, dsm_rr, dsm_cache, …
│   └── dsm_tools/
│       └── cli.py           # CLI entrypoint
├── scripts/
│   ├── run_loop.py          # Loop engine
│   └── ab_report.py         # A/B benchmark report
└── tests/
    ├── kernel/
    └── modules/
```

## Quickstart

From repo root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
# No pip install required when using PYTHONPATH=src
```

Minimal demo (copy-paste from repo root; uses temp dir so it runs anywhere):

```bash
# From repo root, with Python 3
set PYTHONPATH=src
python -c "
import sys, json, tempfile
from pathlib import Path
src = Path('src')
sys.path.insert(0, str(src))
tmp = Path(tempfile.mkdtemp())
shards = tmp / 'data' / 'shards'
shards.mkdir(parents=True)
(shards / 'shard_projects.json').write_text(json.dumps({'config':{'id':'shard_projects','name':'Projects'},'transactions':[],'metadata':{}}))

import dsm_kernel.shard_manager as shard_mgr
import dsm_modules.dsm_router.router as router_mod
shard_mgr.SHARDS_DIR = shards
shard_mgr.MEMORY_DIR = tmp
router_mod.SHARDS_DIR = shards
router_mod.MEMORY_DIR = tmp

from dsm_kernel.config import DSMConfig
from dsm_kernel.api import DSMKernel
from dsm_modules.dsm_router.router import ShardRouter
from dsm_modules.dsm_validator.link_validator import LinkValidator
cfg = DSMConfig(base_dir=tmp)
r = ShardRouter(); r.load_all_shards()
k = DSMKernel(config=cfg, router=r, validator=LinkValidator(), rr=None, cache=None)
k.append_event('shard_projects', {'content': 'hello DSM'})
print(k.query('shard_projects', 'hello', limit=5))
"
```

On Linux/macOS use `export PYTHONPATH=src` instead of `set PYTHONPATH=src`. Full steps and troubleshooting: [docs/quickstart.md](docs/quickstart.md).

## Loop engine

Watcher reads `data/index/event_log.jsonl` (new lines after offset); orchestrator appends insights on each append event.

Run (from repo root):

```bash
python scripts/run_loop.py
```

Set `DSM_BASE_DIR` if your data is not under the repo. The **insights** shard must exist (e.g. `data/shards/insights.json` or `shard_insights.json` depending on router). See [docs/loop/README.md](docs/loop/README.md).

## Benchmark (A/B)

Record runs with `record_ab_run(kernel, task_id, memory_mode, agent, success, time_min, rework_commits)` into the **technical** shard; then generate the report:

```bash
python scripts/ab_report.py
```

Or via CLI:

```bash
python src/dsm_tools/cli.py benchmark report
```

CLI is invoked as `python src/dsm_tools/cli.py <command>`. See [docs/benchmarks/README.md](docs/benchmarks/README.md) and [docs/benchmarks/ab_protocol.md](docs/benchmarks/ab_protocol.md).

## Safety and guiding principles

- **Kernel minimal** — No business logic in the kernel; stable API (append, query, catalog, integrity, event log).
- **Modules evolve** — Router, validator, loop, benchmarks can change without breaking the kernel.
- **Derived index rebuildable** — Catalog and integrity manifest are derived from shards; safe to delete and rebuild.

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching, PR size, tests, and kernel rules.

## Roadmap

- **Done**: PR1 (import legacy), PR2 (kernel API + config), PR3 (shard catalog), PR4 (integrity manifest), PR5 (event log), PR6 (loop engine), PR7 (A/B benchmark).
- **Next**: Graph/cross-ref indexing, event-log replay, optional persistence of loop `last_offset`.

## License

MIT. See [LICENSE](LICENSE).
