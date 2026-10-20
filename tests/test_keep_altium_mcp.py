"""Recovery policy for the long-running network MCP monitor."""

import importlib.util
import json
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


def test_status_is_published_atomically(tmp_path):
    monitor = _load_monitor()
    status = {"mcp_protocol_ok": True, "dialog": {"title": "Error"}}
    monitor.write_status(tmp_path, status)
    assert json.loads((tmp_path / "altium-mcp-supervisor-status.json").read_text()) == status
    assert not (tmp_path / "altium-mcp-supervisor-status.json.tmp").exists()
    assert monitor.POLL_SECONDS == 60
