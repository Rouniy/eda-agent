# SPDX-License-Identifier: Apache-2.0
"""Per-layer profile edits use native state tokens and independent readback."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
BASE = {"board_path": BOARD, "profile": "D100", "layer": "Top Layer",
        "profile_count": 1, "profile_token": '{"name":"D100"}',
        "state_token": "null", "after": None, "before": None,
        "changed": False, "layer_added": False}


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
    return mcp.tools["pcb_impedance_profile_layer"], bridge


def test_read_and_plan_absent_layer(monkeypatch):
    tool, bridge = _tool(monkeypatch, [BASE])
    assert asyncio.run(tool(BOARD, "D100", "Top Layer"))["after"] is None
    tool, bridge = _tool(monkeypatch, [BASE])
    plan = asyncio.run(tool(BOARD, "D100", "Top Layer", width_mils=4))
    assert plan["layer_would_be_added"] is True
    assert plan["would_set"] == {"width_mils": 4}
    assert len(bridge.calls) == 1


def test_write_checks_tokens_and_independent_state(monkeypatch):
    state = {"width_mils": 4.0, "enabled": True}
    after = {**BASE, "state_token": '{"width_mils":4}',
             "after": state, "changed": True, "layer_added": True}
    reread = {**after, "changed": False, "layer_added": False}
    tool, bridge = _tool(monkeypatch, [BASE, after, reread])
    result = asyncio.run(tool(BOARD, "D100", "Top Layer",
                              enabled=True, width_mils=4, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_profile_token"] == BASE["profile_token"]
    assert bridge.calls[1][1]["expect_state_token"] == "null"
    assert bridge.calls[1][1]["expect_count"] == "1"


def test_wrong_board_or_missing_readback_refused(monkeypatch):
    tool, bridge = _tool(monkeypatch, [{**BASE, "board_path": r"D:\other.PcbDoc"}])
    assert asyncio.run(tool(BOARD, "D100", "Top Layer", width_mils=4,
                            dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1
    tool, bridge = _tool(monkeypatch, [BASE, {**BASE, "changed": True}, BASE])
    assert asyncio.run(tool(BOARD, "D100", "Top Layer", width_mils=4,
                            dry_run=False))["ok"] is False
