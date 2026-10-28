"""A named checkout supplies scripts without changing the live destination."""

from pathlib import Path

from eda_agent import cli


def _source(root: Path) -> Path:
    package = root / "src" / "eda_agent"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "9.9"\n', encoding="utf-8")
    scripts = root / "scripts" / "altium"
    scripts.mkdir(parents=True)
    (scripts / "Main.pas").write_text("{ donor main }\n", encoding="utf-8")
    (scripts / "Altium_API.PrjScr").write_text(
        "[Document1]\nDocumentPath=Main.pas\n", encoding="utf-8")
    return scripts


def test_installs_named_checkout_into_the_same_destination(monkeypatch, tmp_path):
    source = tmp_path / "donor"
    scripts = _source(source)
    destination = tmp_path / "live"
    monkeypatch.setattr(cli, "get_registered_scripts_dirs", lambda: [])
    from eda_agent import config

    monkeypatch.setattr(config, "_default_workspace_dir",
                        lambda: tmp_path / "workspace")
    monkeypatch.setattr(config, "write_workspace_pointer", lambda _path: None)

    assert cli.cmd_install_scripts(dest=str(destination), force=True,
                                   source=str(source)) == 0
    assert (destination / "Main.pas").read_bytes() == (
        scripts / "Main.pas").read_bytes()
    assert (destination / "Altium_API.PrjScr").is_file()
    assert (scripts / "Main.pas").read_text(encoding="utf-8") == "{ donor main }\n"


def test_rejects_non_checkout_before_touching_destination(tmp_path):
    destination = tmp_path / "live"
    assert cli.cmd_install_scripts(dest=str(destination), force=True,
                                   source=str(tmp_path)) == 1
    assert not destination.exists()


def test_source_is_live_directory_needs_no_copy(tmp_path):
    source = tmp_path / "main"
    scripts = _source(source)
    original = (scripts / "Main.pas").read_bytes()
    assert cli.cmd_install_scripts(dest=str(scripts), force=True,
                                   source=str(source)) == 0
    assert (scripts / "Main.pas").read_bytes() == original
