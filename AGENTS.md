# DSM — Agent Integration Guide

DSM is a **memory kernel for AI agents**. Agents (Cursor, ClawDBot, DarylViz, and other autonomous agents) must use DSM as their long-term memory: query before work, append events after work, and never edit shard files directly.

---

## 1. Core principles

- **DSM memory is append-only.** No in-place edits. Every change is an event.
- **Memory must be auditable and replayable.** The event log and derived indexes support this.

**Agents must never modify shard files directly.** All writes must go through:

```python
DSMKernel.append_event(shard_id, payload)
```

---

## 2. Agent workflow

### Step 1 — Query memory

Agents should search DSM **before** starting work.

Examples:

```python
kernel.query("shard_technical", "router architecture")
kernel.query_global("semantic search")
```

### Step 2 — Perform the task

Agents implement code or changes (e.g. fix a bug, add a feature).

### Step 3 — Write memory event

Agents append a memory event describing the work.

Example payload:

```json
{
  "content": "Refactored router query logic",
  "source": "agent",
  "importance": 0.7
}
```

```python
kernel.append_event("shard_technical", {"content": "Refactored router query logic", "source": "agent", "importance": 0.7})
```

---

## 3. Loop integration

- **event_log.jsonl** records every memory write (one line per append).
- The **loop watcher** reads the log (polling) and yields new events.
- The **loop orchestrator** may generate insights automatically (e.g. append to the insights shard).

Agents **do not call the loop directly.** The loop runs as a separate process and reacts to events. Agents only use the kernel (`append_event`, `query`, etc.).

---

## 4. Benchmark protocol

Agents should record benchmark runs so DSM vs normal memory can be measured.

Use the A/B run payload type: **`type: "ab_run"`** with fields:

- `task_id`
- `memory_mode` (`"normal"` | `"dsm"`)
- `agent`
- `success`
- `time_min`
- `rework_commits`

Helper: `record_ab_run(kernel, task_id, memory_mode, agent, success, time_min, rework_commits)` in `src/dsm_modules/dsm_loop/ab_utils.py` appends to the technical shard. See [docs/benchmarks/ab_protocol.md](docs/benchmarks/ab_protocol.md).

---

## 5. Repository orientation for agents

| Area        | Path                     |
|------------|---------------------------|
| **Kernel** | `src/dsm_kernel/`        |
| **Modules**| `src/dsm_modules/`       |
| **Loop engine** | `src/dsm_modules/dsm_loop/` |
| **Tools**  | `src/dsm_tools/`         |
| **Docs**   | `docs/`                  |

- **Kernel**: config, API (`api.py`), catalog, integrity, event log, shard manager. Stable; do not refactor without an ADR and maintainer review.
- **Modules**: router, validator, loop (watcher, orchestrator, ab_utils), rr, cache, etc. Can evolve independently.
- **Tools**: CLI (`cli.py`). Entrypoint: `python src/dsm_tools/cli.py <command>`.

---

## 6. Kernel safety rules

Agents **must NOT**:

- Refactor kernel architecture
- Modify shard format (JSON structure of shard files)
- Bypass `append_event` (e.g. write to shard files or event log directly)

Kernel changes require:

- An **ADR document** in `docs/adr/`
- **Maintainer review** (see [GOVERNANCE.md](GOVERNANCE.md))

---

## 7. Example agent task cycle

1. **Agent receives** a GitHub issue (e.g. "Add validation for cross-refs").
2. **Agent queries DSM** (e.g. `kernel.query("shard_technical", "cross-ref validation")`) to load relevant context.
3. **Agent performs implementation** (code changes, tests).
4. **Agent writes memory event** (e.g. `kernel.append_event("shard_technical", {"content": "Added cross-ref validation in link_validator", "source": "agent", "importance": 0.8})`).
5. **Loop engine** (if running) reads the new event from `event_log.jsonl` and may append an insight or trigger other side effects.

---

This document is the single reference for how AI agents should interact with DSM: query first, append via the kernel only, and respect kernel safety rules.
