# SPDX-License-Identifier: Apache-2.0
"""The fork's update report distinguishes source, deployment and VM state."""
from __future__ import annotations

import json
from pathlib import Path

from eda_agent import cli
from eda_agent.diag import update


def _state(**changes):
    state = {
        "repo_root": "/repo", "editable": True, "fetched": True,
        "behind": 0, "ahead": 0, "branch": "main", "dirty": False,
        "bundled_scripts": "/repo/scripts/altium",
        "deployed_scripts": "/repo/scripts/altium",
        "bundled_version": "2026.10.27.93",
        "deployed_version": "2026.10.27.93",
        "script_source_mode": "editable checkout",
        "registered_scripts": ["/repo/scripts/altium"],
        "package_version": "0.7.1",
    }
    state.update(changes)
    return state


def test_update_plan_separates_all_four_layers():
    steps = update.plan(_state(), compiled_version="2026.10.27.93")
    assert [(s.name, s.status) for s in steps] == [
        ("your remote", "current"), ("python package", "current"),
        ("altium scripts", "current"), ("altium session", "current")]
    assert "no separate copy" in steps[2].message


def test_stale_disk_and_compiled_script_are_distinct_findings():
    steps = update.plan(_state(deployed_version="2026.10.27.90"),
                        compiled_version="2026.10.27.89")
    found = {s.name: s for s in steps}
    assert found["altium scripts"].status == "action"
    assert found["altium session"].status == "action"
    assert "2026.10.27.89" in found["altium session"].message


def test_unknown_altium_is_not_reported_as_everything_current():
    steps = update.plan(_state(registered_scripts=[]), compiled_version=None)
    report = update.format_report(steps)
    assert "Some states could not be verified" in report
    assert "Everything is current" not in report


def test_unknown_altium_does_not_set_action_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: _state(registered_scripts=[]))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    assert cli.cmd_update_status(as_json=True) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["exit_code"] == 0
    assert any(step["status"] == "unknown" for step in report["steps"])


def test_action_still_sets_update_status_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: _state(deployed_version="2026.10.27.90"))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    assert cli.cmd_update_status(as_json=True) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["exit_code"] == 1
    assert any(step["status"] == "action" for step in report["steps"])


def test_status_json_does_not_apply_an_update(monkeypatch, capsys):
    monkeypatch.setattr(update, "gather_state", lambda **_kw: _state())
    monkeypatch.setattr(update, "altium_runtime", lambda: {
        "script_version": "2026.10.27.93",
        "script_projects": ["/repo/scripts/altium/Altium_API.PrjScr"]})
    assert cli.cmd_update_status(as_json=True) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["exit_code"] == 0
    assert report["steps"][-1]["name"] == "altium session"


def test_failed_named_remote_fetch_cannot_prove_upstream_current(monkeypatch):
    calls = []

    def git(args, _root, **_kw):
        calls.append(args)
        if args == ["remote"]:
            return "origin\nupstream"
        if args[:1] == ["fetch"]:
            return None
        if args[:1] == ["rev-list"]:
            return "8\t0"
        if args[:1] == ["show"]:
            return '__version__ = "0.7.1"'
        return None

    monkeypatch.setattr(update, "_run_git", git)
    remote = update._remote_state(Path("/repo"), "upstream", "main",
                                  fetch=True)
    assert ["fetch", "upstream", "--quiet", "--no-tags"] in calls
    assert remote["upstream_fetch_failed"] is True
    step = {s.name: s for s in update.plan(_state(**remote))}[
        "original project"]
    assert step.status == "unknown"
    assert "cannot prove" in step.message


def test_successful_named_remote_fetch_can_report_current(monkeypatch):
    def git(args, _root, **_kw):
        if args == ["remote"]:
            return "origin\nupstream"
        if args[:1] == ["fetch"]:
            return ""
        if args[:1] == ["rev-list"]:
            return "8\t0"
        if args[:1] == ["show"]:
            return '__version__ = "0.7.1"'
        return None

    monkeypatch.setattr(update, "_run_git", git)
    remote = update._remote_state(Path("/repo"), "upstream", "main",
                                  fetch=True)
    step = {s.name: s for s in update.plan(_state(**remote))}[
        "original project"]
    assert remote["upstream_fetched"] is True
    assert step.status == "current"


def test_failed_own_remote_fetch_does_not_claim_current():
    step = {s.name: s for s in update.plan(
        _state(fetch_failed=True, fetched=False))}["your remote"]
    assert step.status == "unknown"


def test_failed_fetch_marks_nonzero_counts_as_cached():
    state = _state(behind=2, fetched=False, fetch_failed=True,
                   upstream_remote="upstream", upstream_ref="upstream/main",
                   upstream_behind=3, upstream_fetched=False,
                   upstream_fetch_failed=True)
    steps = {s.name: s for s in update.plan(state)}
    assert steps["your remote"].status == "action"
    assert steps["original project"].status == "action"
    assert "fetch failed" in steps["your remote"].message
    assert "fetch failed" in steps["original project"].message


def test_gather_records_failed_push_remote_fetch_without_importing_tags(
        tmp_path, monkeypatch):
    scripts = tmp_path / "scripts" / "altium"
    scripts.mkdir(parents=True)
    (scripts / "Main.pas").write_text(
        "SCRIPT_VERSION = '2026.10.28.167';", encoding="utf-8")
    (scripts / "Altium_API.PrjScr").write_text("", encoding="utf-8")
    monkeypatch.setattr(update, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(update, "_is_editable_install", lambda: True)
    monkeypatch.setattr(cli, "get_bundled_scripts_path", lambda: scripts)
    monkeypatch.setattr(cli, "get_default_scripts_dest",
                        lambda: tmp_path / "absent")
    monkeypatch.setattr(cli, "get_registered_scripts_dirs", lambda: [])
    calls = []

    def git(args, _root, **_kw):
        calls.append(args)
        if args[:1] == ["fetch"]:
            return None
        if args[:1] == ["rev-list"]:
            return "0\t0"
        return ""

    monkeypatch.setattr(update, "_run_git", git)
    state = update.gather_state(fetch=True)
    assert ["fetch", "--quiet", "--no-tags"] in calls
    assert state["fetch_failed"] is True
    assert state["fetched"] is False


def test_status_ping_has_a_fixed_wait_budget(monkeypatch):
    seen = []

    class Bridge:
        async def send_command_async(self, command, **kwargs):
            seen.append((command, kwargs))
            return {"script_version": "2026.10.27.93"}

    monkeypatch.setattr("eda_agent.bridge.get_bridge", lambda: Bridge())
    assert update.altium_version() == "2026.10.27.93"
    assert seen == [("application.ping", {"timeout": 3.0,
                                          "max_extensions": 0})]


def test_loaded_script_project_must_match_checked_source():
    right = update.plan(_state(
        loaded_script_projects=["/repo/scripts/altium/Altium_API.PrjScr"]),
        compiled_version="2026.10.27.93")
    wrong = update.plan(_state(
        loaded_script_projects=["/elsewhere/Altium_API.PrjScr"]),
        compiled_version="2026.10.27.93")
    assert {s.name: s for s in right}["script folder"].status == "current"
    assert {s.name: s for s in wrong}["script folder"].status == "action"


def test_editable_main_script_is_not_treated_as_missing_deployment(
        tmp_path, monkeypatch):
    scripts = tmp_path / "scripts" / "altium"
    scripts.mkdir(parents=True)
    (scripts / "Altium_API.PrjScr").write_text("", encoding="utf-8")
    (scripts / "Main.pas").write_text(
        "SCRIPT_VERSION = '2026.10.27.93';", encoding="utf-8")
    monkeypatch.setattr(update, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(update, "_is_editable_install", lambda: True)
    monkeypatch.setattr(update, "_run_git", lambda *a, **k: "")
    monkeypatch.setattr(cli, "get_bundled_scripts_path", lambda: scripts)
    monkeypatch.setattr(cli, "get_default_scripts_dest",
                        lambda: tmp_path / "missing-copy")
    monkeypatch.setattr(cli, "get_registered_scripts_dirs", lambda: [])
    state = update.gather_state()
    assert state["script_source_mode"] == "editable checkout"
    assert state["deployed_scripts"] == str(scripts)
    assert state["deployed_version"] == "2026.10.27.93"
