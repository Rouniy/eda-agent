# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Placing a part: side first, then rotation, then the move, then read back.

Measured 2026-10-23 on a 529-part board against the pads read back: a side
change mirrors a part about its bounding box and negates a rotation set
before it (bottom parts at 90/270 came out 180 off, a PowerPAK moved
29 mil), a rotation moves an asymmetric part's origin (an SO8 by 23 mil),
and a part already on the bottom was flipped again.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import pcb as pcb_tools
from eda_agent.tools.registry import ToolRegistry
from tests.pascal_source import load

_ALTIUM = Path(__file__).resolve().parents[1] / "scripts" / "altium"


def test_bottom_batch_flips_on_the_placed_board(monkeypatch):
    sent = []

    class Bridge:
        async def send_command_async(self, command, params):
            sent.append((command, params))
            if command == "pcb.place_components":
                return {"success": True, "placed": 1,
                        "board_path": "D:/boards/actual.PcbDoc"}
            return {"success": True, "new_layer": "BottomLayer"}

    monkeypatch.setattr(pcb_tools, "get_bridge", lambda: Bridge())
    registry = ToolRegistry()
    pcb_tools.register_pcb_tools(registry)
    tool = registry.get("pcb_place_components").fn
    out = asyncio.run(tool([{
        "footprint": "R0603", "library_path": "D:/lib/parts.PcbLib",
        "designator": "R1", "layer": "BottomLayer", "rotation": 0,
    }]))
    assert out["flipped_to_bottom"] == ["R1"]
    assert "rotation==180" in sent[0][1]["placements"]
    assert sent[1] == ("pcb.flip_component", {
        "designator": "R1", "board_path": "D:/boards/actual.PcbDoc"})


def test_bottom_batch_reports_a_failed_flip(monkeypatch):
    class Bridge:
        async def send_command_async(self, command, params):
            if command == "pcb.place_components":
                return {"success": True, "placed": 1,
                        "board_path": "D:/boards/actual.PcbDoc"}
            return {"success": False, "error": "part not found"}

    monkeypatch.setattr(pcb_tools, "get_bridge", lambda: Bridge())
    registry = ToolRegistry()
    pcb_tools.register_pcb_tools(registry)
    tool = registry.get("pcb_place_components").fn
    out = asyncio.run(tool([{
        "footprint": "R0603", "library_path": "D:/lib/parts.PcbLib",
        "designator": "R1", "layer": "BottomLayer",
    }]))
    assert out["success"] is False
    assert out["flip_failed"] == {"R1": "part not found"}


def _pcb():
    return load(_ALTIUM / "PCB.pas")


def test_import_flips_then_turns_then_moves():
    body = _pcb()["PCB_ImportPlacement"]
    flip = body.index("Comp.Layer := TargetLayer;")
    turn = body.index("If RotStr <> '' Then Comp.Rotation := StrToFloatDef(RotStr, 0);")
    move = body.index("Comp.MoveByXY(DeltaX, DeltaY);")
    assert flip < turn < move
    # The delta is taken after the flip and the turn, from where they left it.
    assert turn < body.index("DeltaX := WantX - Comp.x;") < move


def test_a_part_given_no_position_keeps_its_origin():
    body = _pcb()["PCB_ImportPlacement"]
    keep = body.index("WantX := Comp.x;")
    assert keep < body.index("If XStr <> '' Then WantX := MilsToCoordF(StrToFloatDef(XStr, 0));")
    assert keep < body.index("Comp.Layer := TargetLayer;")


def test_the_side_is_compared_as_top_or_bottom():
    body = _pcb()["PCB_ImportPlacement"]
    assert "If Pos('BOTTOM', UpperCase(LayerStr)) > 0 Then TargetLayer := eBottomLayer" in body
    assert "If (TargetLayer <> eNoLayer) And (Comp.Layer <> TargetLayer) Then" in body


def test_every_part_is_read_back():
    body = _pcb()["PCB_ImportPlacement"]
    back = body[body.index("Bad := '';"):]
    assert "(Abs(Comp.x - WantX) > 1) Or (Abs(Comp.y - WantY) > 1)" in back
    assert "SameAngle(Comp.Rotation, StrToFloatDef(RotStr, 0))" in back
    assert '"mismatched":' in body and '"mismatches":[' in body


def test_the_single_move_turns_before_it_moves():
    pcb = _pcb()
    body = pcb["PCB_MoveComponent"] if "PCB_MoveComponent" in pcb else None
    if body is None:
        text = (_ALTIUM / "PCB.pas").read_text(encoding="utf-8")
        i = text.index("If HasRot Then Comp.Rotation := NewRot;")
        body = text[i - 3000:i + 1500]
    turn = body.index("If HasRot Then Comp.Rotation := NewRot;")
    move = body.index("Comp.MoveByXY(DeltaX, DeltaY);", turn)
    assert turn < move


def test_a_new_part_gets_its_origin_last():
    text = (_ALTIUM / "PCB.pas").read_text(encoding="utf-8")
    # The batch path starts on top and flips bottom-side parts after commit.
    assert text.count("Comp.Layer := CompLayer;") == 1
    assert text.count("Comp.Layer := eTopLayer;") >= 2
    for start in [i for i in range(len(text)) if text.startswith("Comp.Layer := CompLayer;", i)]:
        chunk = text[start:start + 300]
        assert chunk.index("Comp.Rotation := Rotation;") < chunk.index("Comp.x := MilsToCoordF(X);")
