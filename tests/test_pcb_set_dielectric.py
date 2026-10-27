# SPDX-License-Identifier: Apache-2.0
"""Dielectric edits use exact-board snapshots and reject unpersisted fields."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
OLD = {"order": 4, "name": "Dielectric 1", "kind": "dielectric",
       "dielectric_type": 2, "material": "PP", "constant": 4.74,
       "loss_tangent": 0.02, "thickness_mils": 7.7165, "stiffener": False}


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return next(self.replies)


def _tools(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools, bridge


def _stack(item=OLD, board=BOARD):
    return {"board_path": board, "style": 0, "layer_count": 1,
            "total_thickness_mils": 8, "layers": [item]}


def test_plan_and_verified_write(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_stack()])
    plan = asyncio.run(tools["pcb_set_dielectric"](
        BOARD, "Dielectric 1", constant=4.8))
    assert plan["before"]["constant"] == 4.74
    assert plan["would_set"] == {"constant": 4.8}
    assert len(bridge.calls) == 1

    after = {**OLD, "constant": 4.8}
    tools, bridge = _tools(monkeypatch, [_stack(), {"changed": True}, _stack(after)])
    result = asyncio.run(tools["pcb_set_dielectric"](
        BOARD, "Dielectric 1", constant=4.8, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_constant"] == "4.74"


def test_stiffener_and_wrong_board_refused(monkeypatch):
    tools, bridge = _tools(monkeypatch, [])
    assert asyncio.run(tools["pcb_set_dielectric"](
        BOARD, "Dielectric 1", stiffener=True, dry_run=False))["ok"] is False
    assert bridge.calls == []
    tools, bridge = _tools(monkeypatch, [_stack(board=r"D:\other.PcbDoc")])
    assert asyncio.run(tools["pcb_set_dielectric"](
        BOARD, "Dielectric 1", constant=4.8, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1
