# SPDX-License-Identifier: Apache-2.0
"""Stack style writes use exact-board old-style and layer-count checks."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
STACK0 = {"board_path": BOARD, "style": 0, "layer_count": 2,
          "total_thickness_mils": 60.0, "layers": [{}, {}]}
STACK1 = {**STACK0, "style": 1}


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


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_set_stack_style"], bridge


def test_plan_and_verified_style_change(monkeypatch):
    tool, bridge = _tool(monkeypatch, [STACK0])
    plan = asyncio.run(tool(BOARD, 1))
    assert plan["dry_run"] and plan["before_style"] == 0
    assert len(bridge.calls) == 1

    native = {"board_path": BOARD, "before_style": 0, "after_style": 1,
              "layer_count": 2, "changed": True}
    tool, bridge = _tool(monkeypatch, [STACK0, native, STACK1])
    result = asyncio.run(tool(BOARD, 1, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1] == ("pcb.set_stack_style",
                               {"board_path": BOARD, "style": "1",
                                "expect_style": "0", "expect_layer_count": "2"})


def test_wrong_board_and_missing_readback_refused(monkeypatch):
    tool, bridge = _tool(monkeypatch, [{**STACK0, "board_path": r"D:\other.PcbDoc"}])
    assert asyncio.run(tool(BOARD, 1, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1
    native = {"board_path": BOARD, "before_style": 0, "after_style": 1,
              "layer_count": 2, "changed": True}
    tool, _ = _tool(monkeypatch, [STACK0, native, STACK0])
    assert asyncio.run(tool(BOARD, 1, dry_run=False))["ok"] is False
