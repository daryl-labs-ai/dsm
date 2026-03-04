#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B benchmark report: load DSM, filter ab_run events from technical shard, print metrics by memory_mode.
"""
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
src = repo / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from dsm_kernel.config import DSMConfig
from dsm_kernel.api import DSMKernel
from dsm_modules.dsm_router.router import ShardRouter
from dsm_modules.dsm_validator.link_validator import LinkValidator
from dsm_modules.dsm_loop.ab_utils import AB_SHARD_ID


def _collect_ab_runs(kernel: DSMKernel):
    """Return list of ab_run event dicts from technical shard."""
    try:
        shard = kernel.get_shard(AB_SHARD_ID)
    except KeyError:
        return []
    runs = []
    for t in shard.transactions:
        content = t.get("content") or "{}"
        try:
            data = json.loads(content)
            if isinstance(data, dict) and data.get("type") == "ab_run":
                runs.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return runs


def _metrics_by_mode(runs):
    """Group runs by memory_mode; return dict mode -> {success_rate_pct, avg_time, avg_rework}."""
    by_mode = {}
    for r in runs:
        mode = r.get("memory_mode") or "unknown"
        if mode not in by_mode:
            by_mode[mode] = {"successes": 0, "total": 0, "time_sum": 0.0, "rework_sum": 0}
        by_mode[mode]["total"] += 1
        if r.get("success"):
            by_mode[mode]["successes"] += 1
        by_mode[mode]["time_sum"] += float(r.get("time_min") or 0)
        by_mode[mode]["rework_sum"] += int(r.get("rework_commits") or 0)

    result = {}
    for mode, agg in by_mode.items():
        n = agg["total"]
        result[mode] = {
            "success_rate_pct": (100.0 * agg["successes"] / n) if n else 0.0,
            "avg_time": agg["time_sum"] / n if n else 0.0,
            "avg_rework": agg["rework_sum"] / n if n else 0.0,
        }
    return result


def main():
    config = DSMConfig()
    router = ShardRouter()
    router.load_all_shards()
    validator = LinkValidator()
    kernel = DSMKernel(config=config, router=router, validator=validator, rr=None, cache=None)

    runs = _collect_ab_runs(kernel)
    metrics = _metrics_by_mode(runs)

    print("DSM vs normal memory")
    print()
    if not metrics:
        print("No ab_run events found in technical shard.")
        return

    print("success rate")
    for mode in ("normal", "dsm"):
        if mode in metrics:
            print(f"  {mode:6} : {metrics[mode]['success_rate_pct']:.0f}%")
    print()
    print("avg time")
    for mode in ("normal", "dsm"):
        if mode in metrics:
            print(f"  {mode:6} : {metrics[mode]['avg_time']:.1f} min")
    print()
    print("avg rework")
    for mode in ("normal", "dsm"):
        if mode in metrics:
            print(f"  {mode:6} : {metrics[mode]['avg_rework']:.1f}")


if __name__ == "__main__":
    main()
