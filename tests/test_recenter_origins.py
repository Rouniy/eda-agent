# SPDX-License-Identifier: Apache-2.0
"""The PCB origin repair must plan against one board before any mutation."""

import asyncio
from pathlib import Path

from eda_agent.tools import pcb as pcb_mod
from eda_agent.tools.registry import ToolRegistry
from tests.pascal_source import load


def _tool(monkeypatch):
    sent = []

    class Bridge:
        async def send_command_async(self, command, params=None, timeout=None):
            sent.append((command, params, timeout))
            return {"board_path": "C:\\test\\board.PcbDoc", "candidate_count": 1,
                    "plan": "U1@0,0>100,100"}

    monkeypatch.setattr(pcb_mod, "get_bridge", lambda: Bridge())
    registry = ToolRegistry()
    pcb_mod.register_pcb_tools(registry)
    tools = {tool.name: tool.fn for tool in asyncio.run(registry.list_tools())}
    return tools["pcb_recenter_component_origins"], sent


def test_dry_run_and_exact_plan(monkeypatch):
    tool, sent = _tool(monkeypatch)
    path = "C:\\test\\board.PcbDoc"
    result = asyncio.run(tool(path, designator="U1"))
    assert result["candidate_count"] == 1
    assert sent[-1][0] == "pcb.recenter_component_origins"
    assert sent[-1][1]["apply"] == "false"
    assert sent[-1][1]["board_path"] == path
    result = asyncio.run(tool(path, designator="U1", apply=True,
                              expected_plan=result["plan"]))
    assert result["plan"] == "U1@0,0>100,100"
    assert sent[-1][1]["expected_plan"] == result["plan"]


def test_apply_requires_plan_and_rejects_relative_path(monkeypatch):
    tool, sent = _tool(monkeypatch)
    assert asyncio.run(tool("board.PcbDoc"))["error"] == "BAD_BOARD_PATH"
    assert asyncio.run(tool("C:\\test\\board.PcbDoc", apply=True))["error"] == "PLAN_REQUIRED"
    assert sent == []


def test_native_preflights_board_and_preserves_pad_centroid():
    source = Path(__file__).resolve().parents[1] / "scripts/altium/PCB.pas"
    handler = load(source)["PCB_RecenterComponentOrigins"]
    for fragment in ("GetPCBBoardForMutation", "TARGET_CHANGED",
                     "PLAN_CHANGED", "expected_plan", "PadCount",
                     "Prim.MoveByXY(-Dx, -Dy)", "Comp.MoveByXY(Dx, Dy)",
                     "Round(SumX / PadCount) = Cx"):
        assert fragment in handler
