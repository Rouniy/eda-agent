# SPDX-License-Identifier: Apache-2.0
"""sch_place_no_ercs: many No-ERC markers in one call, on pin ends or points.

Ported from TechAUmNu's fork (carrier-local) onto this tree's helpers.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import generic
from tests.pascal_source import load

GENERIC_PAS = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Generic.pas"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self):
        self.sent = []

    async def send_command_async(self, command, params=None, **kwargs):
        self.sent.append((command, params))
        return {"placed": 2, "skipped": 0, "failed": 0, "total": 2, "items": []}


def _tool(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    generic.register_generic_tools(mcp)
    return mcp.tools["sch_place_no_ercs"], bridge


def test_pin_and_point_targets_go_as_one_batch(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    asyncio.run(tool([{"designator": "U7", "pin": "23"}, {"x": 1200, "y": 3400.5}]))
    assert bridge.sent == [("generic.place_no_ercs",
                            {"targets": "designator=U7;pin=23~~x=1200;y=3400.5"})]


def test_a_bad_target_refuses_the_whole_call(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    for bad in ([{"designator": "U7"}], [{"x": "12", "y": 3}], [{"designator": "U;7", "pin": "1"}], ["x"], []):
        out = asyncio.run(tool(bad))
        assert out["ok"] is False, bad
    assert bridge.sent == []


def test_the_handler_places_inside_one_edit_round_on_drawn_pins():
    units = load(GENERIC_PAS)
    body = units["Gen_PlaceNoERCs"]
    assert body.count("SchBeginEdit(SchDoc, '');") == 1 and body.count("SchEndEdit(SchDoc, 'Edit');") == 1
    assert body.index("SchBeginEdit(") < body.index("NextBatchOp(Remaining)") < body.index("SchEndEdit(")
    assert "ApplyNoErcDefaults(NoERC);" in body
    assert "'ALREADY_MARKED'" in body and "'PIN_NOT_FOUND'" in body
    assert "PinShownOn(Comp, Pin)" in units["SheetPinEnd"]
    text = GENERIC_PAS.read_text(encoding="utf-8")
    assert "'place_no_ercs':    Result := Gen_PlaceNoERCs(Params, RequestId);" in text
    assert text.index("Function SheetPinEnd(") < text.index("Function Gen_PlaceNoERCs(")
    assert text.index("Procedure ApplyNoErcDefaults(") < text.index("Function Gen_PlaceNoERCs(")
