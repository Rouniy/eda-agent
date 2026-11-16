# SPDX-License-Identifier: Apache-2.0
"""Drill-pair writes require a complete exact-board snapshot and readback."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"
PAIR = {"index": 0, "low_layer_id": 1, "high_layer_id": 32,
        "backdrill": False, "plot_drill_drawing": True,
        "plot_drill_guide": True}


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
        self.replies = replies
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.replies[len(self.calls) - 1]


def _tools(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools, bridge


def _read(**overrides):
    return {"board_path": PATH, "count": 1, "reported_count": 1,
            "unreadable_count": 0, "pairs": [PAIR], **overrides}


def test_incomplete_or_wrong_board_snapshot_refuses_write(monkeypatch):
    for bad in (_read(board_path=r"D:\other.PcbDoc"),
                _read(reported_count=2), _read(unreadable_count=1),
                _read(pairs=[])):
        tools, bridge = _tools(monkeypatch, [bad])
        assert asyncio.run(tools["pcb_set_drill_pair"](
            PATH, 0, backdrill=True, dry_run=False))["ok"] is False
        assert len(bridge.calls) == 1


def test_set_plan_preconditions_and_readback(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_read()])
    plan = asyncio.run(tools["pcb_set_drill_pair"](PATH, 0, backdrill=True))
    assert plan["dry_run"] and plan["before"] == PAIR
    assert len(bridge.calls) == 1

    changed = {**PAIR, "backdrill": True}
    tools, bridge = _tools(monkeypatch, [_read(),
                                        {"board_path": PATH, "count": 1,
                                         "changed": True, "pair": changed}])
    result = asyncio.run(tools["pcb_set_drill_pair"](
        PATH, 0, backdrill=True, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_backdrill"] == "false"
    assert bridge.calls[1][1]["expect_plot_drill_guide"] == "true"

    tools, _ = _tools(monkeypatch, [_read(),
                                  {"board_path": PATH, "count": 1,
                                   "changed": True, "pair": PAIR}])
    assert asyncio.run(tools["pcb_set_drill_pair"](
        PATH, 0, backdrill=True, dry_run=False))["ok"] is False


def test_add_requires_count_delta_and_preserves_old_pair(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_read()])
    assert asyncio.run(tools["pcb_add_drill_pair"](
        PATH, "Top Layer", "Mid-Layer 1"))["dry_run"]
    assert len(bridge.calls) == 1

    new = {**PAIR, "index": 1, "high_layer_id": 2}
    reply = {"board_path": PATH, "count_before": 1, "count_after": 2,
             "returned_count": 2, "unreadable_count": 0,
             "pairs": [PAIR, new]}
    tools, bridge = _tools(monkeypatch, [_read(), reply])
    result = asyncio.run(tools["pcb_add_drill_pair"](
        PATH, "Top Layer", "Mid-Layer 1", dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expected_count"] == "1"

    tools, _ = _tools(monkeypatch, [_read(), {**reply, "pairs": [new, new]}])
    assert asyncio.run(tools["pcb_add_drill_pair"](
        PATH, "Top Layer", "Mid-Layer 1", dry_run=False))["ok"] is False
