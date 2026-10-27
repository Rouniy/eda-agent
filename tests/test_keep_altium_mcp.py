# SPDX-License-Identifier: Apache-2.0
"""Recovery policy for the long-running network MCP monitor."""

import importlib.util
import json
import os
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
    assert monitor.POLL_SECONDS == 20


def test_progress_marker_from_previous_altium_process_is_ignored(tmp_path, monkeypatch):
    monitor = _load_monitor()
    marker = tmp_path / "progress_previous.json"
    marker.write_text("{}")
    os.utime(marker, (100, 100))

    class Process:
        def create_time(self):
            return 200

    monkeypatch.setattr(monitor.psutil, "Process", lambda pid: Process())
    assert not monitor.active_altium_command(tmp_path, 42)
    os.utime(marker, (300, 300))
    assert monitor.active_altium_command(tmp_path, 42)
    assert not monitor.active_altium_command(tmp_path, 42, form_present=False)


def test_uri_launch_requires_one_ready_editor_and_no_script_form():
    monitor = _load_monitor()
    assert monitor.safe_script_launch_target(1, False, True)
    assert not monitor.safe_script_launch_target(2, False, True)
    assert not monitor.safe_script_launch_target(1, True, True)
    assert not monitor.safe_script_launch_target(1, False, False)


def test_stalled_script_stop_requires_disabled_form_in_sole_ready_editor():
    monitor = _load_monitor()
    assert monitor.safe_stall_stop_target(1, True, False, True)
    assert not monitor.safe_stall_stop_target(2, True, False, True)
    assert not monitor.safe_stall_stop_target(1, True, True, True)
    assert not monitor.safe_stall_stop_target(1, False, False, True)
