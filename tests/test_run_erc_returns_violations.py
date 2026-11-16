# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""ERC must compile and read violations from the same named project."""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import generic as generic_tools

from tests.pascal_source import load

_GENERIC = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Generic.pas"


def test_the_handler_compiles_the_named_project():
    body = load(_GENERIC)["Gen_RunERC"]
    assert "FindProjectByPath(Workspace, ProjectPath)" in body
    assert "SmartCompile(Project)" in body
    assert 'EscapeJsonString(Project.DM_ProjectFullPath)' in body


def test_the_runner_does_not_call_a_later_declared_reader():
    """DelphiScript cannot call a function declared further down."""
    text = _GENERIC.read_text(encoding="utf-8")
    assert text.index("Function Gen_RunERC(") < text.index(
        "Function Gen_GetErcViolations(")
    assert "Gen_GetErcViolations(" not in load(_GENERIC)["Gen_RunERC"]


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, run_reply, page_reply=None):
        self.run_reply = run_reply
        self.page_reply = page_reply or {"violation_count": 2,
                                         "violations": [{}, {}]}
        self.sent = []

    async def send_command_async(self, command, params=None, timeout=None):
        self.sent.append((command, dict(params or {})))
        if command == "generic.run_erc":
            return dict(self.run_reply)
        if command == "generic.get_erc_violations":
            return dict(self.page_reply)
        return {}


def _run(monkeypatch, bridge, **kwargs):
    monkeypatch.setattr(generic_tools, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    generic_tools.register_generic_tools(mcp)
    return asyncio.run(mcp.tools["proj_run_erc"](**kwargs))


def test_run_and_page_use_the_same_explicit_project(monkeypatch):
    path = r"Z:\checks\copy\board.PrjPcb"
    bridge = _Bridge({"success": True, "project_path": path,
                      "violation_count": 209, "compile_action": "compiled"},
                     {"violation_count": 8, "suppressed_count": 201,
                      "violations": [{"detail": "one pin"}]})
    out = _run(monkeypatch, bridge, project_path=path,
               include_suppressed=True, limit=0)
    assert out["project_path"] == path
    assert out["compile_action"] == "compiled"
    assert out["violation_count"] == 8
    assert out["suppressed_count"] == 201
    assert out["violations"][0]["detail"] == "one pin"
    assert bridge.sent == [
            ("generic.run_erc", {"project_path": path}),
        ("generic.get_erc_violations", {"limit": "0",
                                        "include_suppressed": "true",
                                        "project_path": path}),
    ]


def test_an_old_script_reply_is_followed_by_the_list(monkeypatch):
    bridge = _Bridge({"success": True, "message": "ERC completed on project"})
    out = _run(monkeypatch, bridge)
    assert out["violation_count"] == 2
    assert [name for name, _ in bridge.sent] == [
        "generic.run_erc", "generic.get_erc_violations"]


def test_failed_run_does_not_read_an_old_violation_list(monkeypatch):
    bridge = _Bridge({"success": False, "error": "PROJECT_NOT_FOUND"})
    out = _run(monkeypatch, bridge, project_path=r"Z:\missing.PrjPcb")
    assert out["success"] is False
    assert [name for name, _ in bridge.sent] == ["generic.run_erc"]
