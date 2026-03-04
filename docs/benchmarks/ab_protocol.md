# A/B protocol: DSM vs normal memory

## How to run normal vs DSM tasks

1. **Normal mode**  
   Run the same task with the agent using its default (normal) memory: no DSM retrieval, no DSM writes for context.  
   After the run, record an `ab_run` event with `memory_mode: "normal"`.

2. **DSM mode**  
   Run the same task with the agent using DSM: retrieve from DSM at start, optionally write insights during/after the task.  
   After the run, record an `ab_run` event with `memory_mode: "dsm"`.

Use the same `task_id` for both runs so that pairs can be compared. Vary only `memory_mode` and the actual metrics (`success`, `time_min`, `rework_commits`).

## How agents should record runs

Agents (e.g. Cursor, Clawdbot) should call the helper after each run:

```python
from dsm_modules.dsm_loop.ab_utils import record_ab_run

record_ab_run(
    kernel=kernel,
    task_id="task-123",
    memory_mode="normal",  # or "dsm"
    agent="cursor",
    success=True,
    time_min=12.5,
    rework_commits=2,
)
```

This appends a transaction to the DSM shard **shard_technical** with `content` = JSON of the `ab_run` payload. The shard must exist (file `shard_technical.json` in your shards directory).

## How to generate the report

From the repo root:

```bash
python scripts/ab_report.py
```

Or via the CLI:

```bash
daryl-memory benchmark report
```

The report loads the DSM kernel, reads all transactions from the **shard_technical** shard, keeps only those with `type == "ab_run"`, then computes by `memory_mode`:

- **success rate** (percentage of runs with `success == true`)
- **avg time** (average of `time_min`)
- **avg rework** (average of `rework_commits`)

Output is printed in a simple text format comparing normal vs dsm.
