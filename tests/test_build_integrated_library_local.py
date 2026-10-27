# SPDX-License-Identifier: Apache-2.0
"""The integrated-library command must confirm a fresh Altium artifact."""

import asyncio
from pathlib import Path

from eda_agent.tools import library


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, *, write=True, fail=None):
        self.write = write
        self.fail = fail
        self.commands = []

    async def send_command_async(self, command, params, timeout=None):
        self.commands.append(command)
        if command == self.fail:
            return {"success": False}
        if command == "project.compile" and self.write:
            package = Path(params["project_path"])
            target = package.parent / f"Project Outputs for {package.stem}" / f"{package.stem}.IntLib"
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(b"compiled")
        if command == "library.install_library":
            return {"installed": True}
        return {"success": True}


def _run(monkeypatch, bridge, package, sources, **kwargs):
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return asyncio.run(mcp.tools["lib_build_integrated_library"](
        str(package), [str(source) for source in sources], **kwargs))


def test_build_requires_new_artifact_and_can_install(tmp_path, monkeypatch):
    source = tmp_path / "parts.PcbLib"
    source.write_bytes(b"library")
    package = tmp_path / "parts.LibPkg"
    bridge = _Bridge()
    result = _run(monkeypatch, bridge, package, [source], install=True)
    assert result["built"] and result["success"]
    assert result["intlib_bytes"] == 8
    assert bridge.commands == ["project.create", "project.add_document",
                               "project.save", "project.compile",
                               "library.install_library"]


def test_build_rejects_stale_artifact_and_failed_add(tmp_path, monkeypatch):
    source = tmp_path / "parts.PcbLib"
    source.write_bytes(b"library")
    package = tmp_path / "parts.LibPkg"
    package.write_text("[Design]")
    target = tmp_path / "Project Outputs for parts" / "parts.IntLib"
    target.parent.mkdir()
    target.write_bytes(b"old")
    stale = _run(monkeypatch, _Bridge(write=False), package, [source])
    assert not stale["built"] and stale["intlib"] is None
    failed_bridge = _Bridge(fail="project.add_document")
    failed = _run(monkeypatch, failed_bridge, package, [source])
    assert failed["stage"] == "add_document"
    assert "project.compile" not in failed_bridge.commands
