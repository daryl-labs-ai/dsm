# Quickstart

## Installation

1. Clone the repo.
2. Create and activate a virtualenv:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Linux/macOS
   ```

3. From the repo root, ensure Python can import `dsm_kernel` and `dsm_modules` by adding `src` to `PYTHONPATH`:

   ```bash
   set PYTHONPATH=src        # Windows
   export PYTHONPATH=src     # Linux/macOS
   ```

   Or run scripts that already add `src` (e.g. `python src/dsm_tools/cli.py`, `python scripts/run_loop.py`).

## Environment variables

- **DSM_BASE_DIR** — Optional. Base directory for DSM data. If set, `DSMConfig` uses it for `base_dir` and derives `index_dir`, `shards_dir` (as `base_dir/data/shards`), `event_log_path`, etc. If not set, the config uses the repo root (or cwd) as base.

Note: The router loads shards from `dsm_kernel.shard_manager.SHARDS_DIR`, which is set at import time. For a portable setup, use a temp dir and patch (see tests) or point that path to your data.

## Minimal run steps

1. Create data directories (under your base, e.g. repo root or `DSM_BASE_DIR`):
   - `data/shards`
   - `data/index`

2. Create at least one shard file so the router has something to load. Example `data/shards/shard_projects.json`:

   ```json
   {
     "config": { "id": "shard_projects", "name": "Projects", "domain": "projects" },
     "transactions": [],
     "metadata": {}
   }
   ```

3. Run the CLI (from repo root, with `PYTHONPATH=src` if needed):

   ```bash
   python src/dsm_tools/cli.py help
   python src/dsm_tools/cli.py status
   ```

   Or run the minimal demo from [README.md](../README.md#quickstart) (uses a temp dir and patches so it works anywhere).

## Troubleshooting

- **Missing shards dir** — The router expects `SHARDS_DIR` to exist and to contain `*.json` shard files. Create `data/shards` (or the path your `shard_manager.SHARDS_DIR` uses) and add at least one shard JSON.

- **Missing insights shard** — The loop engine writes insights to a shard whose id is `insights`. Ensure a file like `insights.json` or `shard_insights.json` exists in your shards dir (id = file stem), or the orchestrator will skip appending (KeyError).

- **Permissions** — Ensure the process can read/write the base dir, `data/shards`, and `data/index` (for catalog, manifest, event_log.jsonl).

- **Import errors** — Run from repo root and set `PYTHONPATH=src`, or run scripts that already add `src` to `sys.path` (e.g. `scripts/run_loop.py`, `scripts/ab_report.py`, `src/dsm_tools/cli.py`).
