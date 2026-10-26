"""Script deployment follows Altium's registered project and server workspace."""

from pathlib import Path

from eda_agent import cli


def test_unique_registered_project_sets_script_destination(monkeypatch, tmp_path):
    dest = tmp_path / "registered"
    monkeypatch.setattr(cli, "_read_global_projects",
                        lambda: [str(tmp_path / "other.PrjScr"),
                                 str(dest / "Altium_API.PrjScr")])
    assert cli.get_registered_scripts_dirs() == [dest]
    assert cli.get_default_scripts_dest() == dest


def test_ambiguous_registered_projects_keep_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_read_global_projects",
                        lambda: [str(tmp_path / "a" / "Altium_API.PrjScr"),
                                 str(tmp_path / "b" / "Altium_API.PrjScr")])
    assert cli.get_default_scripts_dest() == cli.get_fallback_scripts_dest()


def test_install_points_script_at_server_workspace(monkeypatch, tmp_path):
    dest = tmp_path / "custom" / "scripts"
    workspace = tmp_path / "server-workspace"
    pointer = tmp_path / "pointer.txt"
    monkeypatch.setattr(cli, "_read_global_projects",
                        lambda: [str(dest / "Altium_API.PrjScr")])
    monkeypatch.setenv("EDA_AGENT_WORKSPACE", str(workspace))
    monkeypatch.setenv("EDA_AGENT_POINTER_FILE", str(pointer))

    assert cli.cmd_install_scripts(force=True) == 0
    assert (dest / "Altium_API.PrjScr").is_file()
    assert workspace.is_dir()
    assert not (dest.parent / "workspace").exists()
    assert Path(pointer.read_text(encoding="mbcs").strip().rstrip("\\/")) == workspace
