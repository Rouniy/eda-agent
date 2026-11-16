# SPDX-License-Identifier: Apache-2.0
"""proj_open says a project is open only when Altium lists it as open.

MEASURED 2026-11-15 on AD 26.11.1.5: proj_open on a path that did not exist
answered ``success: true, focused: false``. WorkspaceManager:OpenObject
raises nothing and shows nothing for a missing file, and the handler
reported success without looking. Every later call then failed with
"Project not found", one step away from the cause.
"""
from __future__ import annotations

import asyncio

from eda_agent.tools import project

PATH = r"Z:\work\Board\Board.PrjPcb"


class _Bridge:
    def __init__(self, open_reply, projects):
        self.open_reply = open_reply
        self.projects = projects
        self.sent = []

    async def send_command_async(self, command, params, **kwargs):
        self.sent.append(command)
        if command == "project.open":
            return dict(self.open_reply)
        if command == "project.get_open_projects":
            return self.projects
        raise AssertionError(f"unexpected command {command}")


def _proj_open(monkeypatch, bridge):
    monkeypatch.setattr(project, "get_bridge", lambda: bridge)
    captured = {}

    class _Mcp:
        def tool(self, *a, **k):
            def deco(fn):
                captured[fn.__name__] = fn
                return fn
            return deco

        def __getattr__(self, name):
            return lambda *a, **k: (lambda fn: fn)

    project.register_project_tools(_Mcp())
    return captured["proj_open"]


def _listing(*paths):
    return {"projects": [{"project_name": p.rsplit("\\", 1)[-1], "project_path": p}
                         for p in paths], "count": len(paths)}


def test_a_project_altium_lists_is_reported_open(monkeypatch):
    bridge = _Bridge({"success": True, "project_path": PATH, "focused": True},
                     _listing("Free Documents", PATH))
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH))
    assert reply["success"] is True
    assert reply["opened"] is True
    assert reply["focused"] is True
    assert bridge.sent == ["project.open", "project.get_open_projects"]


def test_a_missing_file_is_not_reported_open(monkeypatch):
    bridge = _Bridge({"success": True, "project_path": PATH, "focused": False},
                     _listing("Free Documents", r"D:\other\Other.PrjPcb"))
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH))
    assert reply["success"] is False
    assert reply["opened"] is False
    assert reply["project_path"] == PATH
    assert "Check the path" in reply["reason"]


def test_the_path_is_compared_without_case_or_slash_style(monkeypatch):
    bridge = _Bridge({"success": True, "project_path": PATH, "focused": True},
                     _listing(PATH.upper()))
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH.replace("\\", "/")))
    assert reply["success"] is True and reply["opened"] is True


def test_a_name_alone_does_not_count_as_the_project(monkeypatch):
    """Another project with the same file name in another folder is not it."""
    bridge = _Bridge({"success": True, "project_path": PATH, "focused": False},
                     _listing(r"D:\elsewhere\Board.PrjPcb"))
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH))
    assert reply["success"] is False


def test_a_refused_open_is_passed_through_unchanged(monkeypatch):
    refused = {"success": False, "error": "busy"}
    bridge = _Bridge(refused, _listing(PATH))
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH))
    assert reply == refused
    assert bridge.sent == ["project.open"], "nothing to confirm after a refusal"


def test_without_a_list_the_open_is_not_confirmed(monkeypatch):
    bridge = _Bridge({"success": True, "project_path": PATH, "focused": True},
                     {"unexpected": True})
    reply = asyncio.run(_proj_open(monkeypatch, bridge)(PATH))
    assert reply["success"] is True
    assert reply["opened"] is None
