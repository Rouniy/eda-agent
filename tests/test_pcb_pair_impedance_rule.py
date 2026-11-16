# SPDX-License-Identifier: Apache-2.0
"""Differential-pair impedance writes require exact identity and readback."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"
STATE = {"impedance_driven": False, "min_ohms": 90.0,
         "max_ohms": 110.0, "preferred_ohms": 100.0,
         "descriptor": "Differential Pairs Routing"}


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


def _reply(state=STATE, **extra):
    return {"board_path": PATH, "rule_name": "DiffPairsRouting",
            "rule_kind": 51, "changed": False, "before": STATE,
            "after": state, **extra}


def test_read_and_plan_require_exact_rule(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_reply()])
    assert asyncio.run(tools["pcb_get_pair_impedance_rule"](
        PATH, "DiffPairsRouting"))["after"] == STATE
    tools, bridge = _tools(monkeypatch, [_reply()])
    plan = asyncio.run(tools["pcb_set_pair_impedance_rule"](
        PATH, "DiffPairsRouting", impedance_driven=True))
    assert plan["dry_run"] and plan["would_set"] == {"impedance_driven": True}
    assert len(bridge.calls) == 1
    tools, bridge = _tools(monkeypatch, [_reply(board_path=r"D:\other.PcbDoc")])
    assert asyncio.run(tools["pcb_set_pair_impedance_rule"](
        PATH, "DiffPairsRouting", impedance_driven=True, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1


def test_write_passes_all_old_values_and_requires_independent_readback(monkeypatch):
    after = {**STATE, "impedance_driven": True}
    changed = _reply(after, changed=True)
    tools, bridge = _tools(monkeypatch, [_reply(), changed, _reply(after)])
    result = asyncio.run(tools["pcb_set_pair_impedance_rule"](
        PATH, "DiffPairsRouting", impedance_driven=True, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_min_ohms"] == "90.0"
    assert bridge.calls[1][1]["expect_impedance_driven"] == "false"
    tools, _ = _tools(monkeypatch, [_reply(), changed, _reply()])
    assert asyncio.run(tools["pcb_set_pair_impedance_rule"](
        PATH, "DiffPairsRouting", impedance_driven=True, dry_run=False))["ok"] is False


def test_numeric_write_refuses_before_native_call(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_reply()])
    assert asyncio.run(tools["pcb_set_pair_impedance_rule"](
        PATH, "DiffPairsRouting", min_ohms=120, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 0
