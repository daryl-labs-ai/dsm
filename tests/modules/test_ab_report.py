#!/usr/bin/env python3
"""
Test A/B report: mock kernel with sample ab_run events; verify metrics computation.
"""
import importlib.util
import json
import sys
from pathlib import Path

src = Path(__file__).resolve().parent.parent.parent / "src"
repo = Path(__file__).resolve().parent.parent.parent
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

# Load ab_report module to get _metrics_by_mode and _collect_ab_runs
spec = importlib.util.spec_from_file_location("ab_report", repo / "scripts" / "ab_report.py")
ab_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab_report)


def test_metrics_by_mode():
    """Verify success_rate, avg_time, avg_rework grouped by memory_mode."""
    sample_runs = [
        {"type": "ab_run", "memory_mode": "normal", "success": True, "time_min": 10.0, "rework_commits": 0},
        {"type": "ab_run", "memory_mode": "normal", "success": False, "time_min": 20.0, "rework_commits": 3},
        {"type": "ab_run", "memory_mode": "dsm", "success": True, "time_min": 8.0, "rework_commits": 0},
        {"type": "ab_run", "memory_mode": "dsm", "success": True, "time_min": 12.0, "rework_commits": 1},
    ]
    metrics = ab_report._metrics_by_mode(sample_runs)
    assert "normal" in metrics
    assert "dsm" in metrics
    # normal: 1 success / 2 total = 50%, avg time 15, avg rework 1.5
    assert metrics["normal"]["success_rate_pct"] == 50.0
    assert metrics["normal"]["avg_time"] == 15.0
    assert metrics["normal"]["avg_rework"] == 1.5
    # dsm: 2 success / 2 = 100%, avg time 10, avg rework 0.5
    assert metrics["dsm"]["success_rate_pct"] == 100.0
    assert metrics["dsm"]["avg_time"] == 10.0
    assert metrics["dsm"]["avg_rework"] == 0.5


def test_collect_ab_runs_mock_kernel():
    """Mock kernel.get_shard returns transactions with JSON content; _collect_ab_runs filters ab_run."""
    ab_run_ok = {"type": "ab_run", "memory_mode": "dsm", "success": True, "time_min": 5.0, "rework_commits": 0}
    not_ab = {"type": "other", "x": 1}
    mock_transactions = [
        {"content": json.dumps(ab_run_ok)},
        {"content": json.dumps(not_ab)},
        {"content": json.dumps({**ab_run_ok, "memory_mode": "normal"})},
    ]
    mock_shard = type("Shard", (), {"transactions": mock_transactions})()
    class MockKernel:
        def get_shard(self, shard_id):
            return mock_shard
    runs = ab_report._collect_ab_runs(MockKernel())
    assert len(runs) == 2
    modes = {r["memory_mode"] for r in runs}
    assert "dsm" in modes
    assert "normal" in modes
