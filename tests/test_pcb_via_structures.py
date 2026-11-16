# SPDX-License-Identifier: Apache-2.0
"""The via structure summary must identify its board and any truncation."""

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
    return mcp.tools["pcb_via_structures"], bridge


def test_exact_board_summary_and_limit(monkeypatch):
    reply = {"board_path": BOARD, "vias": 20, "omitted_vias": 3,
             "truncated": True, "structures": [{"vias": 17, "structure_type": -1}]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(BOARD, 5)) == reply
    assert bridge.calls == [("pcb.via_structures", {"board_path": BOARD, "limit": "5"})]
    assert asyncio.run(tool(BOARD, 0))["ok"] is False
    assert len(bridge.calls) == 1


def test_wrong_board_reply_refused(monkeypatch):
    tool, _ = _tool(monkeypatch, {"board_path": r"D:\other.PcbDoc",
                                  "vias": 0, "omitted_vias": 0,
                                  "truncated": False, "structures": []})
    assert asyncio.run(tool(BOARD))["ok"] is False
