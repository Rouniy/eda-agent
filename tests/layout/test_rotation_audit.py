# SPDX-License-Identifier: Apache-2.0
"""Two-pad parts are scored at the four right angles about their origin."""

from __future__ import annotations

import pytest

from eda_agent.layout.audit import CHECKS, run_audits
from eda_agent.layout.model import BOTTOM, Component, LayoutBoard, Pad
from eda_agent.layout.rotation_audit import mst_length, suggest_rotations


def _board(rotation: float = 0.0, side: str = "top", gnd_fanout: int = 0) -> LayoutBoard:
    """R1 sits between U1.1 (A, left) and U2.1 (B, right).

    At rotation 0 its pads run left to right, A on the left: the short way.
    ``rotation`` turns the pads about R1's origin as Altium would, so 180
    puts A on the right and B on the left, the long way.
    """
    import math
    a = math.radians(rotation)
    def at(dx: float) -> tuple[float, float]:
        return (dx * math.cos(a), dx * math.sin(a))
    (x1, y1), (x2, y2) = at(-30), at(30)
    comps = [Component("U1", x=-200, y=0), Component("U2", x=200, y=0),
             Component("R1", x=0, y=0, rotation=rotation, side=side)]
    pads = [Pad("U1", "1", -200, 0, net="A"), Pad("U2", "1", 200, 0, net="B"),
            Pad("R1", "1", x1, y1, net="A"), Pad("R1", "2", x2, y2, net="B")]
    for i in range(gnd_fanout):
        pads.append(Pad("U1", f"G{i}", -500 - i, 300, net="GND"))
    return LayoutBoard(name="t", components=comps, pads=pads)


def test_mst_length_of_a_unit_square_is_three_sides():
    assert mst_length([(0, 0), (1, 0), (1, 1), (0, 1)]) == pytest.approx(3.0)
    assert mst_length([(5, 5)]) == 0.0


def test_a_part_turned_the_long_way_is_told_to_turn_back():
    found = suggest_rotations(_board(180))
    assert found["checked"] == 1
    (s,) = found["suggestions"]
    assert s["designator"] == "R1"
    assert s["current_rotation"] == 180
    assert s["suggested_rotation"] == 0
    assert s["bbox_changes"] is False
    # A: 170 -> 230 in each net's airline, so the gain is 2 x 60 mils.
    assert s["improvement_mils"] == pytest.approx(120.0)


def test_a_part_already_the_short_way_gets_nothing():
    assert suggest_rotations(_board(0))["suggestions"] == []


def test_a_gain_under_the_threshold_is_not_reported():
    assert suggest_rotations(_board(180), min_improvement_mils=500)["suggestions"] == []


def test_a_quarter_turn_reports_the_box_change():
    (s,) = suggest_rotations(_board(90))["suggestions"]
    assert s["suggested_rotation"] == 0
    assert s["bbox_changes"] is True


def test_a_bottom_side_part_is_checked_like_a_top_side_one():
    """Measured, not assumed.

    Bottom-side parts were skipped while it was unknown whether a
    rotation value turns a mirrored part clockwise or anticlockwise in
    board coordinates. Measured against Altium 26.11.1.5 on 2026-10-25:
    four parts flipped with `pcb_flip_component` and read back turn
    their pads in world coordinates by exactly the delta applied to
    `Rotation`, the same as a top-side part, at 45 degrees as well as
    at right angles.

    The scoring never needed a side term: it rotates the pad's WORLD
    position about the component origin, and the mirroring is already
    in the position the board reports. So the same board on the bottom
    gives the same answer.
    """
    top = suggest_rotations(_board(180))
    bottom = suggest_rotations(_board(180, side=BOTTOM))

    assert bottom["skipped"] == []
    assert bottom["checked"] == top["checked"] == 1
    assert bottom["suggestions"] == top["suggestions"]


def test_a_plane_net_scores_the_nearest_return_pad():
    board = _board(0)
    board.pads[2].net = ""     # R1.1 unconnected, so only the ground pad scores
    board.pads[3].net = "GND"  # R1.2 at (30, 0)
    board.pads.extend(Pad("U1", f"G{i}", 10 * i, -200, net="GND") for i in range(5))
    (s,) = suggest_rotations(board, plane_net_pads=3)["suggestions"]
    # A quarter turn clockwise puts the ground pad at (0, -30), facing the
    # ground pins 170 mils away instead of 200.
    assert s["suggested_rotation"] == 270
    assert s["improvement_mils"] == pytest.approx(30.0)
    assert [set(t) for t in s["suggested_pads"]] == [{"pad", "net", "nearest_return_mils"}]


def test_rotation_audit_is_a_registered_advisory_check():
    assert "rotation_audit" in CHECKS
    check = run_audits(_board(180), ["rotation_audit"])["checks"]["rotation_audit"]
    assert check["pass"] is True and check["advisory"] is True
    assert check["counts"] == {"checked": 1, "suggestions": 1, "skipped": 0}


def test_multi_pad_part_moves_all_pads_on_a_net_together():
    board = LayoutBoard(
        name="multi",
        components=[Component("LEFT", x=-200), Component("RIGHT", x=200),
                    Component("U3", rotation=180)],
        pads=[Pad("LEFT", "1", -200, 0, net="A"),
              Pad("RIGHT", "1", 200, 0, net="B"),
              Pad("U3", "1", 30, 0, net="A"),
              Pad("U3", "2", 40, 0, net="A"),
              Pad("U3", "3", -30, 0, net="B")],
    )
    found = suggest_rotations(board)
    assert found["checked"] == 1
    (suggestion,) = found["suggestions"]
    assert suggestion["suggested_rotation"] == 0
    assert suggestion["improvement_mils"] == pytest.approx(130.0)
    assert {term["net"] for term in suggestion["current_pads"]} == {"A", "B"}
    assert next(term for term in suggestion["current_pads"] if term["net"] == "A")["pad"] == "*"


def test_two_pads_on_one_net_are_scored_as_one_net():
    board = LayoutBoard(
        name="shared-net",
        components=[Component("LEFT", x=-200), Component("R1")],
        pads=[Pad("LEFT", "1", -200, 0, net="A"),
              Pad("R1", "1", -20, 0, net="A"),
              Pad("R1", "2", 40, 0, net="A")],
    )
    (suggestion,) = suggest_rotations(board, min_improvement_mils=1)["suggestions"]
    assert suggestion["suggested_rotation"] == 180
    assert suggestion["improvement_mils"] == pytest.approx(20.0)
    assert len(suggestion["current_pads"]) == 1


def test_a_courtyard_collision_blocks_the_best_turn():
    board = _board(90)
    part = next(c for c in board.components if c.ref == "R1")
    part.courtyard = [(-10, -40), (10, -40), (10, 40), (-10, 40)]
    part.courtyard_source = "courtyard"
    board.components.append(Component(
        "BLOCK", x=30, courtyard=[(20, -10), (40, -10),
                                  (40, 10), (20, 10)],
        courtyard_source="courtyard"))
    found = suggest_rotations(board)
    assert found["suggestions"] == []
    (blocked,) = found["blocked"]
    assert blocked["designator"] == "R1"
    assert blocked["suggested_rotation"] == 0
    assert blocked["collides_with"] == "BLOCK"
    assert blocked["courtyard_checked"] is True


def test_opposite_side_courtyard_does_not_block_turn():
    board = _board(90)
    part = next(c for c in board.components if c.ref == "R1")
    part.courtyard = [(-10, -40), (10, -40), (10, 40), (-10, 40)]
    part.courtyard_source = "courtyard"
    board.components.append(Component(
        "BACK", x=30, side=BOTTOM,
        courtyard=[(20, -10), (40, -10), (40, 10), (20, 10)],
        courtyard_source="courtyard"))
    (suggestion,) = suggest_rotations(board)["suggestions"]
    assert suggestion["suggested_rotation"] == 0
