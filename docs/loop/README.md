# DSM Loop Engine

## Architecture

The loop engine is an **optional, external** component that watches the DSM event log and triggers tasks. It does not modify kernel or shard behavior.

- **Event log** (`event_log.jsonl`): append-only JSONL written by the kernel on each `append_event`. Each line is a JSON object (e.g. `action`, `shard_id`, `payload_size`).

- **EventWatcher** (`dsm_loop/watcher.py`): polling-based. Opens `event_log.jsonl`, reads new lines after a byte offset, yields parsed events and the new offset. No kernel dependency.

- **LoopOrchestrator** (`dsm_loop/orchestrator.py`): receives events and applies rules. For `action == "append"` it creates a task `memory_append_detected` and appends an insight to the DSM shard **insights** (via `kernel.append_event("insights", ...)`). The insights shard must exist.

- **Loop runner** (`dsm_loop/loop_runner.py`): builds `DSMKernel`, `EventWatcher`, and `LoopOrchestrator`; in a loop, reads new events, calls `process_event`, then sleeps 2 seconds.

Data flow:

```
Kernel append_event → event_log.jsonl
       ↑
EventWatcher.watch(last_offset) → events
       ↓
LoopOrchestrator.process_event(event) → kernel.append_event("insights", ...)
```

## How to run the loop

From the repo root:

```bash
python scripts/run_loop.py
```

Or with `DSM_BASE_DIR` set to your data directory:

```bash
set DSM_BASE_DIR=C:\path\to\dsm\data
python scripts/run_loop.py
```

The script instantiates the kernel (router + validator), the watcher on `config.event_log_path`, and the orchestrator. It then runs forever: read new events, process each, sleep 2s.

Ensure the **insights** shard exists (e.g. `data/shards/insights.json` or a shard whose id is `insights`), otherwise append-insight will be skipped (KeyError).

## How agents interact

- **Agents** (or any client) write memories via the kernel `append_event(shard_id, payload)`. The kernel appends to the shard and writes one line to `event_log.jsonl`.

- The **loop** runs separately (same or another process). It only reads the event log and, for each new append event, can run side effects (e.g. writing an insight, triggering pipelines). Agents do not call the loop; the loop reacts to events.

- To add new rules: extend `LoopOrchestrator.process_event` (e.g. other `action` values or filters) and optionally other shards or external systems.
