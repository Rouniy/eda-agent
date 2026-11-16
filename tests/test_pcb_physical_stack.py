# SPDX-License-Identifier: Apache-2.0
"""Physical stack reads preserve board identity and layer completeness."""

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
    return mcp.tools["pcb_physical_stack"], bridge


def test_exact_board_physical_stack(monkeypatch):
    reply = {"board_path": BOARD, "style": 0, "layer_count": 1,
             "total_thickness_mils": 1.0,
             "layers": [{"order": 0, "name": "Top Layer", "kind": "copper"}]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(BOARD)) == reply
    assert bridge.calls == [("pcb.physical_stack", {"board_path": BOARD})]
    assert asyncio.run(tool("relative.PcbDoc"))["ok"] is False
    assert len(bridge.calls) == 1


def test_incomplete_or_wrong_board_refused(monkeypatch):
    tool, _ = _tool(monkeypatch, {"board_path": BOARD, "style": 0,
                                  "layer_count": 2,
                                  "total_thickness_mils": 1.0,
                                  "layers": [{}]})
    assert asyncio.run(tool(BOARD))["ok"] is False
    tool, _ = _tool(monkeypatch, {"board_path": r"D:\other.PcbDoc", "style": 0,
                                  "layer_count": 0,
                                  "total_thickness_mils": 0.0,
                                  "layers": []})
    assert asyncio.run(tool(BOARD))["ok"] is False
