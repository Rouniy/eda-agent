# SPDX-License-Identifier: Apache-2.0
"""Plane connection reads must retain the exact board and pad identity."""

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
    return mcp.tools["pcb_plane_connections"], bridge


def test_exact_board_and_pad(monkeypatch):
    reply = {"board_path": BOARD, "designator": "U1", "plane_layers": 2,
             "pad_count": 1, "pads": [{"pad": "1", "net": "GND", "rule_style": 1,
             "relief_width_mils": 10, "relief_entries": 4, "air_gap_mils": 8,
             "relief_expansion_mils": 0, "plane_clearance_mils": 10}]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(BOARD, "U1", "1")) == reply
    assert bridge.calls == [("pcb.plane_connections", {
        "board_path": BOARD, "designator": "U1", "pad": "1"})]


def test_wrong_board_or_incomplete_reply(monkeypatch):
    for reply in (
        {"board_path": r"D:\other.PcbDoc", "designator": "U1",
         "plane_layers": 0, "pad_count": 0, "pads": []},
        {"board_path": BOARD, "designator": "U1", "plane_layers": 2,
         "pad_count": 1, "pads": []},
    ):
        tool, _ = _tool(monkeypatch, reply)
        assert asyncio.run(tool(BOARD, "U1"))["ok"] is False
