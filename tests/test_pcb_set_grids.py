# SPDX-License-Identifier: Apache-2.0
"""Board-grid writes are exact-board, planned and read back."""

import asyncio
import math

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"
OLD = {"snap_x": 10.0, "snap_y": 10.0,
       "component_x": 10.0, "component_y": 10.0,
       "track": 5.0, "via": 5.0,
       "visible": 20.0, "visible_big": 100.0,
       "visible_factor": 1.0, "visible_big_factor": 10.0,
       "snap_unit": "mil", "visible_unit": "mil",
       "visible_big_unit": "mil", "dot_grid": True}


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


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_set_grids"], bridge


def _read():
    return {"board_path": PATH, "wrote": False, "changed": False,
            "before": OLD, "grids": OLD, "not_applied": []}


def test_read_and_plan_use_one_native_read(monkeypatch):
    tool, bridge = _tool(monkeypatch, [_read()])
    assert asyncio.run(tool(PATH))["grids"] == OLD
    assert bridge.calls == [("pcb.set_grids", {"board_path": PATH})]
    tool, bridge = _tool(monkeypatch, [_read()])
    plan = asyncio.run(tool(PATH, snap_x=7.5, dot_grid=False))
    assert plan["dry_run"] and plan["would_set"] == {"snap_x": 7.5, "dot_grid": False}
    assert len(bridge.calls) == 1


def test_write_carries_full_old_snapshot_and_verifies_new_values(monkeypatch):
    applied = {**_read(), "wrote": True, "changed": True,
               "grids": {**OLD, "track": 7.5, "dot_grid": False}}
    tool, bridge = _tool(monkeypatch, [_read(), applied])
    result = asyncio.run(tool(PATH, track=7.5, dot_grid=False, dry_run=False))
    assert result["grids"]["track"] == 7.5
    assert result["save_required"] is True
    assert bridge.calls[1][0] == "pcb.set_grids"
    params = bridge.calls[1][1]
    assert params["board_path"] == PATH and params["track"] == "7.5"
    assert params["expect_snap_x"] == "10.0"
    assert params["expect_visible_big"] == "100.0"
    assert params["expect_dot_grid"] == "true"
    assert params["expect_visible_big_factor"] == "10.0"
    assert params["expect_snap_unit"] == "mil"
    tool, _ = _tool(monkeypatch, [_read(), {**applied, "not_applied": ["track"]}])
    assert asyncio.run(tool(PATH, track=7.5, dry_run=False))["ok"] is False


def test_invalid_size_and_wrong_board_refuse_before_write(monkeypatch):
    tool, bridge = _tool(monkeypatch, [_read()])
    assert asyncio.run(tool(PATH, via=math.nan, dry_run=False))["ok"] is False
    assert not bridge.calls
    tool, bridge = _tool(monkeypatch, [{**_read(), "board_path": r"D:\other.PcbDoc"}])
    assert asyncio.run(tool(PATH, via=5, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1


def test_coarse_factor_and_units_keep_the_exact_board_contract(monkeypatch):
    applied = {**_read(), "wrote": True, "changed": True,
               "grids": {**OLD, "visible_big_factor": 8.0,
                         "visible_unit": "mm"}}
    tool, bridge = _tool(monkeypatch, [_read(), applied])
    result = asyncio.run(tool(PATH, visible_big_factor=8.0,
                              visible_unit="mm", dry_run=False))
    assert result["grids"]["visible_big_factor"] == 8.0
    params = bridge.calls[1][1]
    assert params["expect_visible_big_factor"] == "10.0"
    assert params["expect_visible_unit"] == "mil"
    assert params["visible_big_factor"] == "8.0"
    assert params["visible_unit"] == "mm"
