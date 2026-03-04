# DSM Benchmarks

## A/B protocol (DSM vs normal memory)

We compare agent performance with **normal memory** vs **DSM memory** by recording runs and aggregating metrics.

- **Run A** : `memory_mode = "normal"` — agent uses standard (non-DSM) memory.
- **Run B** : `memory_mode = "dsm"` — agent uses DSM shards for context and persistence.

Each run must record one event in the DSM shard **technical** with the following structure (stored as a transaction whose `content` is JSON):

```json
{
  "type": "ab_run",
  "task_id": "...",
  "memory_mode": "normal|dsm",
  "agent": "cursor|clawdbot",
  "success": true|false,
  "time_min": number,
  "rework_commits": number
}
```

- `task_id`: unique identifier for the task (e.g. same task run in both modes).
- `memory_mode`: `"normal"` or `"dsm"`.
- `agent`: e.g. `"cursor"`, `"clawdbot"`.
- `success`: whether the task was considered successful.
- `time_min`: duration in minutes.
- `rework_commits`: number of rework/amend commits.

These events are used to compute **success rate**, **average time**, and **average rework** per `memory_mode`, and to compare DSM vs normal memory performance.

Events are stored in the **shard_technical** shard (file `shard_technical.json`); the report script reads that shard and filters transactions whose `content` is JSON with `type == "ab_run"`.

See [ab_protocol.md](ab_protocol.md) for how to run tasks, how agents should record runs, and how to generate the report.

### Example report output

```
DSM vs normal memory

success rate
  normal : 50%
  dsm    : 80%

avg time
  normal : 12.5 min
  dsm    : 10.2 min

avg rework
  normal : 2.0
  dsm    : 1.2
```
