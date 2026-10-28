"""Explicit four-layer updates keep the loaded script project singular."""

from __future__ import annotations

import json
from pathlib import Path

from eda_agent import cli
from eda_agent.diag import update


def state(tmp_path: Path, **changes):
    scripts = tmp_path / "scripts" / "altium"
    result = {
        "repo_root": str(tmp_path), "editable": True, "fetched": True,
        "fetch_failed": False, "behind": 0, "ahead": 0,
        "branch": "main", "dirty": False,
        "bundled_scripts": str(scripts), "deployed_scripts": str(scripts),
        "bundled_version": "2026.10.28.167",
        "deployed_version": "2026.10.28.167",
        "script_source_mode": "editable checkout",
        "registered_scripts": [], "package_version": "0.7.1",
    }
    result.update(changes)
    return result


def test_check_only_never_pulls_or_deploys(tmp_path, monkeypatch):
    current = state(tmp_path, behind=2, deployed_version="old",
                    deployed_scripts=str(tmp_path / "installed"))
    calls = []
    monkeypatch.setattr(update, "gather_state", lambda **_kw: current)
    monkeypatch.setattr(update, "_run_git",
                        lambda *_a, **_kw: calls.append("git"))
    monkeypatch.setattr(cli, "cmd_install_scripts",
                        lambda **_kw: calls.append("install"))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    steps, code = update.run_update(check_only=True, pull=True,
                                    force_scripts=True)
    assert code == 1
    assert calls == []
    assert any(step.needs_human for step in steps)


def test_loaded_main_project_is_never_copied(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: state(tmp_path))
    monkeypatch.setattr(cli, "cmd_install_scripts",
                        lambda **_kw: (_ for _ in ()).throw(
                            AssertionError("second runtime script copy")))
    monkeypatch.setattr(update, "altium_runtime", lambda: {
        "script_version": "2026.10.28.167",
        "script_projects": [str(tmp_path / "scripts" / "altium" /
                                "Altium_API.PrjScr")]})
    steps, code = update.run_update(force_scripts=True)
    assert code == 0
    assert {s.name: s for s in steps}["altium scripts"].status == "current"


def test_reconcile_deploys_named_folder_into_checked_destination(
        tmp_path, monkeypatch):
    donor = tmp_path / "donor"
    target = tmp_path / "installed"
    before = state(tmp_path, deployed_scripts=str(target),
                   deployed_version="old", source_ok=True,
                   source_dir=str(donor), source_scripts=str(donor / "scripts" / "altium"),
                   source_script_version="new", source_version="0.7.1")
    after = {**before, "deployed_version": "new"}
    readings = iter([before, after])
    monkeypatch.setattr(update, "gather_state", lambda **_kw: next(readings))
    monkeypatch.setattr(update, "altium_runtime", lambda: {
        "script_version": "old", "script_projects": [str(target / "Altium_API.PrjScr")]})
    seen = []
    monkeypatch.setattr(cli, "cmd_install_scripts",
                        lambda **kw: seen.append(kw) or 0)
    steps, code = update.run_update(source_dir=str(donor))
    assert seen == [{"dest": str(target), "force": True, "source": str(donor)}]
    assert code == 1  # Altium still has the old compiled script.
    assert {s.name: s for s in steps}["altium scripts"].status == "done"
    assert {s.name: s for s in steps}["altium session"].status == "action"


def test_named_folder_cannot_overwrite_active_main_sources(tmp_path,
                                                            monkeypatch):
    donor = tmp_path / "donor"
    scripts = tmp_path / "scripts" / "altium"
    current = state(tmp_path, source_ok=True, source_dir=str(donor),
                    source_scripts=str(donor / "scripts" / "altium"),
                    source_script_version="new", source_version="0.7.1")
    assert current["deployed_scripts"] == str(scripts)
    monkeypatch.setattr(update, "gather_state", lambda **_kw: current)
    monkeypatch.setattr(cli, "cmd_install_scripts",
                        lambda **_kw: (_ for _ in ()).throw(
                            AssertionError("overwrote active main project")))
    steps, code = update.run_update(source_dir=str(donor))
    assert code == 1
    assert "Merge" in steps[0].action


def test_failed_deployment_exits_two(tmp_path, monkeypatch):
    current = state(tmp_path, deployed_scripts=str(tmp_path / "installed"),
                    deployed_version="old")
    monkeypatch.setattr(update, "gather_state", lambda **_kw: current)
    monkeypatch.setattr(cli, "cmd_install_scripts", lambda **_kw: 1)
    steps, code = update.run_update()
    assert code == 2
    assert steps[0].name == "altium scripts"


def test_dirty_checkout_refuses_pull(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: state(tmp_path, behind=2, dirty=True))
    monkeypatch.setattr(update, "_run_git",
                        lambda *_a, **_kw: (_ for _ in ()).throw(
                            AssertionError("pulled dirty tree")))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    steps, code = update.run_update(pull=True)
    assert code == 1
    assert {s.name: s for s in steps}["working tree"].status == "action"


def test_requested_pull_is_not_silently_skipped_when_dirty_but_level(
        tmp_path, monkeypatch):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: state(tmp_path, dirty=True))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    steps, code = update.run_update(pull=True)
    assert code == 1
    assert {s.name: s for s in steps}["fast-forward"].status == "action"


def test_clean_pull_fast_forwards_and_rechecks_same_source(tmp_path, monkeypatch):
    before = state(tmp_path, behind=1)
    after = state(tmp_path, behind=0)
    readings = iter([before, after])
    options = []

    def gather(**kw):
        options.append(kw)
        return next(readings)

    git_calls = []
    monkeypatch.setattr(update, "gather_state", gather)
    monkeypatch.setattr(update, "_run_git",
                        lambda args, *_a, **_kw: git_calls.append(args) or "")
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    steps, code = update.run_update(pull=True, compare_remote="upstream")
    assert git_calls == [["pull", "--ff-only", "--no-tags"]]
    assert options == [
        {"fetch": False, "compare_remote": "upstream", "source_dir": ""},
        {"fetch": False, "compare_remote": "upstream", "source_dir": ""},
    ]
    assert code == 0
    assert {s.name: s for s in steps}["your remote"].status == "current"


def test_deploy_output_does_not_break_json(tmp_path, monkeypatch, capsys):
    before = state(tmp_path, deployed_scripts=str(tmp_path / "installed"),
                   deployed_version="old")
    after = {**before, "deployed_version": "2026.10.28.167"}
    readings = iter([before, after])
    monkeypatch.setattr(update, "gather_state", lambda **_kw: next(readings))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)

    def install(**_kw):
        print("installer progress")
        return 0

    monkeypatch.setattr(cli, "cmd_install_scripts", install)
    cli.cmd_update_reconcile(as_json=True)
    report = json.loads(capsys.readouterr().out)
    assert report["steps"]


def test_reconcile_json_carries_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(update, "gather_state",
                        lambda **_kw: state(tmp_path, behind=2))
    monkeypatch.setattr(update, "altium_runtime", lambda: None)
    code = cli.cmd_update_reconcile(check_only=True, as_json=True)
    report = json.loads(capsys.readouterr().out)
    assert code == report["exit_code"] == 1
    assert report["ok"] is True
