# SPDX-License-Identifier: Apache-2.0
"""Rigid-flex snapshots identify the board and report complete lists."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.reply


def _tool(monkeypatch, reply):
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_get_board_regions"], bridge


def test_exact_board_snapshot(monkeypatch):
    reply = {"board_path": BOARD, "split_line_count": 0,
             "layer_stack_count": 1,
             "regions": [{"index": 0, "name": "Board Region", "bend_lines": []}],
             "split_lines": [],
             "layer_stacks": [{"name": "Main", "flex": False,
                               "copper_layers": ["Top Layer", "Bottom Layer"]}]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(BOARD)) == reply
    assert bridge.calls == [("pcb.flex_state", {"board_path": BOARD})]
    assert asyncio.run(tool("relative.PcbDoc"))["ok"] is False
    assert len(bridge.calls) == 1


def test_wrong_board_or_missing_stacks_refused(monkeypatch):
    for reply in (
        {"board_path": r"D:\other.PcbDoc", "split_line_count": 0,
         "layer_stack_count": 0, "regions": [], "split_lines": [], "layer_stacks": []},
        {"board_path": BOARD, "split_line_count": 0,
         "layer_stack_count": 1, "regions": [], "split_lines": [], "layer_stacks": []},
    ):
        tool, _ = _tool(monkeypatch, reply)
        assert asyncio.run(tool(BOARD))["ok"] is False
