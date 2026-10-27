# SPDX-License-Identifier: Apache-2.0
"""Keep fractional mils across the board geometry bridge until native QA."""

from pathlib import Path

from tests.pascal_source import load


PCB = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


def test_board_geometry_readers_do_not_round_to_whole_mils():
    functions = load(PCB, minimum=20)
    for name in ("PCB_GetBoardOutlineForBoard", "PCB_GetNetRouting"):
        body = functions[name]
        assert "CoordToMils(" not in body, name
        assert "CoordToMilsF(" in body, name


def test_arc_writer_accepts_fractional_mils():
    body = load(PCB, minimum=20)["PCB_PlaceArc"]
    for field in ("ArcXC", "ArcYC", "ArcRad", "ArcWidth"):
        assert f"{field} := StrToFloatDef(" in body
        assert f"MilsToCoordF({field})" in body
        assert f"FloatToJsonStr({field})" in body
