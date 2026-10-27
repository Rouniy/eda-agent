# SPDX-License-Identifier: Apache-2.0
"""A pour growth write must use the previewed exact board and bounds."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
BOUNDS = {"left": 10.0, "bottom": 20.0, "right": 30.0, "top": 40.0}


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, preview, write=None):
        self.replies = [preview, write]
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params.copy()))
        return self.replies[len(self.calls) - 1]


def _tool(monkeypatch, preview, write=None):
    bridge = _Bridge(preview, write)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_grow_pour"], bridge


def _preview():
    return {"board_path": BOARD, "index": 3, "name": "GND",
            "layer": "TopLayer", "point_count_before": 4, "dry_run": True,
            "bounds_before": BOUNDS}


def test_preview_then_write_uses_bounds_token(monkeypatch):
    write = {**_preview(), "dry_run": False, "bounds_after":
             {"left": 9.0, "bottom": 19.0, "right": 31.0, "top": 41.0}}
    tool, bridge = _tool(monkeypatch, _preview(), write)
    assert asyncio.run(tool(BOARD, 3, "GND", "TopLayer", 1.0, BOUNDS, False)) == write
    assert len(bridge.calls) == 2
    assert bridge.calls[1][1]["expected_points"] == 4
    assert bridge.calls[1][1]["expected_left"] == 10.0
    assert bridge.calls[1][1]["dry_run"] is False


def test_wrong_board_preview_never_writes(monkeypatch):
    tool, bridge = _tool(monkeypatch, {**_preview(), "board_path": r"D:\other.PcbDoc"})
    assert asyncio.run(tool(BOARD, 3, "GND", "TopLayer", 1.0, BOUNDS, False))["ok"] is False
    assert len(bridge.calls) == 1


def test_stale_index_bounds_never_write(monkeypatch):
    tool, bridge = _tool(monkeypatch, {**_preview(), "bounds_before":
                                      {**BOUNDS, "left": 12.0}})
    assert asyncio.run(tool(BOARD, 3, "GND", "TopLayer", 1.0, BOUNDS, False))["ok"] is False
    assert len(bridge.calls) == 1
