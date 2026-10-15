"""Recovery policy for the long-running network MCP monitor."""

import importlib.util
from pathlib import Path


def _load_monitor():
    path = Path(__file__).resolve().parents[1] / "scripts" / "keep-altium-mcp.py"
    spec = importlib.util.spec_from_file_location("keep_altium_mcp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_relaunch_is_bounded_per_altium_process():
    monitor = _load_monitor()
    budget = monitor.ScriptLaunchBudget()
    budget.observe(100)
    for _ in range(monitor.MAX_SCRIPT_LAUNCHES_PER_PROCESS):
        assert budget.allow_launch()
        budget.record_launch()
    assert not budget.allow_launch()

    budget.observe(100)
    assert not budget.allow_launch()
    budget.observe(100, ping_ok=True)
    assert budget.allow_launch()

    budget.record_launch()
    budget.observe(101)
    assert budget.allow_launch()
    budget.observe(None)
    assert not budget.allow_launch()
