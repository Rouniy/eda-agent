# SPDX-License-Identifier: Apache-2.0
"""Impedance profile mutations require exact, complete native snapshots."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
PROFILE = {"name": "D100", "target_ohms": 100.0, "tolerance": 10.0,
           "differential": True, "coplanar": False, "layers": []}


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


def _snapshot(profiles, board=BOARD, errors=0):
    return {"board_path": board, "board": "Board.PcbDoc",
            "profile_count": len(profiles), "read_errors": errors,
            "profiles": profiles}


def test_create_plan_and_native_readback(monkeypatch):
    tools, bridge = _tools(monkeypatch, [_snapshot([])])
    plan = asyncio.run(tools["pcb_impedance_profile"](
        BOARD, "create", "D100", target_ohms=100))
    assert plan["dry_run"] and plan["profile_count"] == 0
    assert len(bridge.calls) == 1

    tools, bridge = _tools(monkeypatch, [
        _snapshot([]), {"action": "create", "profiles_after": 1},
        _snapshot([PROFILE]),
    ])
    result = asyncio.run(tools["pcb_impedance_profile"](
        BOARD, "create", "D100", target_ohms=100, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_count"] == "0"


def test_set_passes_old_values_and_checks_new_values(monkeypatch):
    after = {**PROFILE, "target_ohms": 110.0, "coplanar": True}
    tools, bridge = _tools(monkeypatch, [
        _snapshot([PROFILE]), {"action": "set", "profiles_after": 1},
        _snapshot([after]),
    ])
    result = asyncio.run(tools["pcb_impedance_profile"](
        BOARD, "set", "D100", target_ohms=110, coplanar=True, dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_target_ohms"] == "100.0"
    assert bridge.calls[1][1]["expect_coplanar"] == "false"


def test_wrong_board_or_read_errors_stop_before_write(monkeypatch):
    for snapshot in (_snapshot([], board=r"D:\other.PcbDoc"),
                     _snapshot([PROFILE], errors=1)):
        tools, bridge = _tools(monkeypatch, [snapshot])
        result = asyncio.run(tools["pcb_impedance_profile"](
            BOARD, "set", "D100", tolerance=8, dry_run=False))
        assert result["ok"] is False
        assert len(bridge.calls) == 1
