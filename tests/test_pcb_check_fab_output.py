# SPDX-License-Identifier: Apache-2.0
"""Exact-board, uncapped fab package comparison contract."""

import asyncio

from eda_agent.fileio import gerber_check
from eda_agent.tools import pcb


PATH = r"D:\fab\board.PcbDoc"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, facts):
        self.facts = facts
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.facts


def _facts(**changes):
    facts = {"board_path": PATH, "copper_layers": 4,
             "outline_mm": {"width": 50.0, "height": 30.0},
             "pad_holes": 5001, "via_holes": 3, "hole_count": 5004}
    facts.update(changes)
    return facts


def _summary(*args, **kwargs):
    return {"ok": True, "copper_layers": 4,
            "outline_mm": {"width": 50.0, "height": 30.0},
            "drills": {"hits": 5004, "files": 1, "smallest_mm": 0.3},
            "min_aperture_mm": 0.2}


def _tool(monkeypatch, facts):
    bridge = _Bridge(facts)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    monkeypatch.setattr(gerber_check, "summarise_package", _summary)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_check_fab_output"], bridge


def test_complete_snapshot_can_pass_beyond_5000_pads(monkeypatch):
    tool, bridge = _tool(monkeypatch, _facts())
    result = asyncio.run(tool(r"D:\fab\export", PATH))
    assert result["ok"] and result["passed"]
    assert set(result["checks_run"]) == {"copper_layers", "outline", "hole_count"}
    assert result["board_facts"]["hole_count"] == 5004
    assert bridge.calls == [("pcb.get_fab_board_facts", {"board_path": PATH})]


def test_wrong_or_incomplete_board_never_passes(monkeypatch):
    for facts in (_facts(board_path=r"D:\fab\other.PcbDoc"),
                  _facts(hole_count=5000),
                  _facts(outline_mm={"width": 0, "height": 30})):
        tool, _ = _tool(monkeypatch, facts)
        result = asyncio.run(tool(r"D:\fab\export", PATH))
        assert result["ok"] is False and "board facts unavailable" in result["reason"]


def test_missing_export_outline_cannot_pass(monkeypatch):
    tool, _ = _tool(monkeypatch, _facts())
    monkeypatch.setattr(gerber_check, "summarise_package",
                        lambda *a, **kw: {**_summary(), "outline_mm": None})
    result = asyncio.run(tool(r"D:\fab\export", PATH))
    assert result["ok"] is False and result["passed"] is False
    assert "outline" in result["reason"]


def test_relative_path_rejected_before_parsing(monkeypatch):
    tool, bridge = _tool(monkeypatch, _facts())
    result = asyncio.run(tool(r"D:\fab\export", "board.PcbDoc"))
    assert result["ok"] is False and not bridge.calls


def test_fact_tool_exposes_exact_snapshot(monkeypatch):
    bridge = _Bridge(_facts())
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    result = asyncio.run(mcp.tools["pcb_get_fab_board_facts"](PATH))
    assert result["hole_count"] == 5004
    assert bridge.calls == [("pcb.get_fab_board_facts", {"board_path": PATH})]
