# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Offline cover for pcb_check_placement_collision.

Two halves:

1. A Python mirror of the geometry in PCB.pas PCB_CheckPlacementCollision,
   exercised against the false positive that motivated the fix. Checking a
   BGA24 (body 236 x 315 mil) reported 10 colliders, among them a 0201 whose
   box came back 81 x 281 mil -- a designator string, not a package -- and two
   BOTTOM-layer parts against a TOP-layer target, one of them carrying a
   bounding box belonging to a different component entirely.

2. Source-contract guards on the .pas itself, since the parts that broke are
   not reachable from Python: that colliders are measured with
   PCB_ComponentPlacementBBox rather than IPCB_Component.BoundingRectangle,
   and that the iterator loop never advances inside a branch that then relies
   on ``Continue`` from within a ``Try ... Except``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
PCB_PAS = REPO_ROOT / "scripts" / "altium" / "PCB.pas"
GENERIC_PAS = REPO_ROOT / "scripts" / "altium" / "Generic.pas"


# ---------------------------------------------------------------------------
# Mirror of PCB.pas PCB_CheckPlacementCollision. Coordinates are mils here;
# the Pascal works in internal units but every step below is scale-free apart
# from the integer divisions, which are mirrored exactly.
# ---------------------------------------------------------------------------


def _div(a: int, b: int) -> int:
    """Mirror Pascal ``Div``: truncates toward zero, unlike Python ``//``."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _is_quarter_turn(rot_delta: float) -> bool:
    """Mirror: the SwapWH test, +/-1 degree around a quarter turn."""
    return (abs(rot_delta - 90) < 1 or abs(rot_delta + 90) < 1
            or abs(rot_delta - 270) < 1 or abs(rot_delta + 270) < 1)


def placement_bbox(comp: dict) -> tuple[tuple[int, int, int, int], str]:
    """Mirror: PCB_ComponentPlacementBBox.

    Union of the footprint's pads / tracks / arcs / fills / regions, i.e. the
    body plus silkscreen outline, with every text primitive left out. Falls
    back to the text-inflated component rectangle only when the footprint has
    no measurable non-text primitive at all.
    """
    if comp.get("body"):
        return comp["body"], "footprint_body"
    return comp["full_rect"], "component_rect_including_text"


def predicted_bbox(comp: dict, new_x: int, new_y: int,
                   new_rot: float, margin: int) -> tuple[int, int, int, int]:
    """Mirror: the target's proposed AABB."""
    (x1, y1, x2, y2), _ = placement_bbox(comp)
    rot_delta = new_rot - comp["rotation"]

    width = x2 - x1
    height = y2 - y1
    off_x = _div(x1 + x2, 2) - comp["x"]
    off_y = _div(y1 + y2, 2) - comp["y"]

    if _is_quarter_turn(rot_delta):
        new_w, new_h = height, width
        # The reference-point-to-centre offset turns with the body. Altium
        # rotations are counter-clockwise: +90 maps (dx,dy) -> (-dy,dx).
        if abs(rot_delta - 90) < 1 or abs(rot_delta + 270) < 1:
            off_x, off_y = -off_y, off_x
        else:
            off_x, off_y = off_y, -off_x
    else:
        new_w, new_h = width, height

    return (
        new_x + off_x - _div(new_w, 2) - margin,
        new_y + off_y - _div(new_h, 2) - margin,
        new_x + off_x + _div(new_w, 2) + margin,
        new_y + off_y + _div(new_h, 2) + margin,
    )


def aabb_overlap(a: tuple[int, int, int, int],
                 b: tuple[int, int, int, int]) -> bool:
    """Mirror: the Overlap expression. Touching boxes count as a collision."""
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def check_placement_collision(target: dict, others: list[dict],
                              x: int, y: int, rotation: float | None = None,
                              margin_mils: int = 0) -> dict:
    """Mirror: PCB_CheckPlacementCollision end to end."""
    new_rot = target["rotation"] if rotation is None else rotation
    proposed = predicted_bbox(target, x, y, new_rot, margin_mils)
    target_layer = target.get("layer", "")
    same_side_only = target_layer != ""

    # Pass 1: candidate designators only, no geometry read here.
    candidates = [
        other["designator"] for other in others
        if other.get("designator")
        and other["designator"] != target["designator"]
        and (not same_side_only or other.get("layer", "") == target_layer)
    ]

    # Pass 2: look each candidate up by the refdes recorded above, so a box
    # can never end up attached to a designator it does not belong to.
    by_refdes = {o["designator"]: o for o in others}
    colliding = []
    for designator in candidates:
        other = by_refdes[designator]
        box, basis = placement_bbox(other)
        if aabb_overlap(proposed, box):
            colliding.append({
                "designator": designator,
                "layer": other.get("layer", ""),
                "bbox_basis": basis,
                "bbox": box,
            })

    _, target_basis = placement_bbox(target)
    return {
        "designator": target["designator"],
        "layer": target_layer,
        "same_side_filter": same_side_only,
        "bbox_basis": target_basis,
        "proposed": {"x": x, "y": y, "rotation": new_rot, "bbox": proposed,
                     "margin_mils": margin_mils},
        "colliding_count": len(colliding),
        "clear": not colliding,
        "colliding": colliding,
    }


def _centred(designator: str, cx: int, cy: int, w: int, h: int,
             layer: str = "TopLayer", rotation: float = 0.0,
             text_w: int | None = None, text_h: int | None = None) -> dict:
    """A component whose reference point sits at its body centre.

    Dimensions are kept even so the ``Div 2`` round trip is exact and the
    assertions can quote whole numbers.
    """
    def _box(bw: int, bh: int) -> tuple[int, int, int, int]:
        x1 = cx - bw // 2
        y1 = cy - bh // 2
        return (x1, y1, x1 + bw, y1 + bh)

    return {
        "designator": designator, "x": cx, "y": cy, "rotation": rotation,
        "layer": layer, "body": _box(w, h),
        "full_rect": _box(text_w if text_w is not None else w,
                          text_h if text_h is not None else h),
    }


# The reported scene: U2 is a BGA24 on top, R1021 a 0201 whose designator
# string measures 81 x 281 mil, U3 and U6 are on the bottom layer.
def _scene() -> tuple[dict, list[dict]]:
    u2 = _centred("U2", 6320, 8850, 236, 316)
    others = [
        # 0201 sitting 126 mil clear of U2's body edge. Its silkscreen text
        # box does reach into U2's box; its body comes nowhere near.
        _centred("R1021", 6320, 8560, 24, 12, text_w=81, text_h=282),
        # Bottom-layer parts that overlap U2 in plane. Cross-side parts can
        # never collide.
        _centred("U3", 6300, 8840, 200, 200, layer="BottomLayer"),
        _centred("U6", 6350, 8900, 200, 200, layer="BottomLayer"),
        # A genuine same-side neighbour, well clear.
        _centred("C14", 7200, 8850, 40, 20),
    ]
    return u2, others


class TestReportedFalsePositive:
    def test_bga_is_clear_of_its_real_neighbours(self):
        u2, others = _scene()
        res = check_placement_collision(u2, others, 6320, 8850,
                                        rotation=0, margin_mils=5)
        assert res["clear"] is True
        assert res["colliding"] == []

    def test_silkscreen_text_is_what_used_to_manufacture_the_collision(self):
        """Pin the mechanism, not just the symptom.

        Measuring the 0201 by its text-inflated rectangle -- what
        IPCB_Component.BoundingRectangle returns and what the collider side
        of the check used to call -- turns a 60 mil clearance into a hit.
        """
        u2, others = _scene()
        r1021 = next(o for o in others if o["designator"] == "R1021")
        proposed = predicted_bbox(u2, 6320, 8850, 0, 5)

        assert aabb_overlap(proposed, r1021["full_rect"]) is True
        assert aabb_overlap(proposed, r1021["body"]) is False

    def test_target_box_tracks_the_body_not_the_designator(self):
        u2, _ = _scene()
        x1, y1, x2, y2 = predicted_bbox(u2, 6320, 8850, 0, 5)
        # Body plus the 5 mil margin on each side, nothing else. The live
        # call returned 293 x 346 for this part.
        assert (x2 - x1, y2 - y1) == (236 + 10, 316 + 10)

    def test_cross_side_components_are_excluded(self):
        u2, others = _scene()
        res = check_placement_collision(u2, others, 6320, 8850, margin_mils=5)
        assert res["same_side_filter"] is True
        assert "U3" not in [c["designator"] for c in res["colliding"]]
        assert "U6" not in [c["designator"] for c in res["colliding"]]

    def test_cross_side_parts_would_collide_if_the_filter_were_dropped(self):
        """The bottom-layer parts really do overlap in plane.

        Without this the same-side assertion above would pass for the wrong
        reason -- because nothing overlapped at all.
        """
        u2, others = _scene()
        proposed = predicted_bbox(u2, 6320, 8850, 0, 5)
        for designator in ("U3", "U6"):
            other = next(o for o in others if o["designator"] == designator)
            assert aabb_overlap(proposed, other["body"]) is True


class TestColliderPairing:
    def test_each_reported_box_belongs_to_the_designator_it_is_under(self):
        u2 = _centred("U2", 1000, 1000, 200, 200)
        others = [
            _centred("R1", 1110, 1000, 40, 20),
            _centred("R2", 1000, 1105, 40, 20),
            _centred("R3", 5000, 5000, 40, 20),   # far away, must not appear
        ]
        res = check_placement_collision(u2, others, 1000, 1000)
        reported = {c["designator"]: c["bbox"] for c in res["colliding"]}

        assert set(reported) == {"R1", "R2"}
        for designator, box in reported.items():
            expected = next(o for o in others
                            if o["designator"] == designator)["body"]
            assert box == expected

    def test_basis_is_reported_per_collider(self):
        u2 = _centred("U2", 1000, 1000, 200, 200)
        textless = _centred("R1", 1110, 1000, 40, 20)
        # A footprint with no measurable non-text primitive falls back to the
        # text-inclusive rectangle, and has to admit it.
        textless["body"] = None
        res = check_placement_collision(u2, [textless], 1000, 1000)
        assert res["colliding"][0]["bbox_basis"] == "component_rect_including_text"

    def test_no_readable_target_layer_widens_the_search_visibly(self):
        u2 = _centred("U2", 1000, 1000, 200, 200, layer="")
        other = _centred("R1", 1110, 1000, 40, 20, layer="BottomLayer")
        res = check_placement_collision(u2, [other], 1000, 1000)
        assert res["same_side_filter"] is False
        assert res["colliding_count"] == 1


class TestQuarterTurn:
    def test_dimensions_swap(self):
        comp = _centred("U1", 1000, 1000, 400, 100)
        x1, y1, x2, y2 = predicted_bbox(comp, 1000, 1000, 90, 0)
        assert (x2 - x1, y2 - y1) == (100, 400)

    def test_offset_rotates_with_the_body(self):
        """A footprint whose origin is not its body centre.

        Leaving the reference-to-centre offset unrotated put the predicted
        box off by twice that offset on every quarter turn.
        """
        comp = {
            "designator": "U1", "x": 0, "y": 0, "rotation": 0,
            "layer": "TopLayer",
            # Body centred at (+50, 0), i.e. offset (50, 0) from the origin.
            "body": (0, -50, 100, 50),
            "full_rect": (0, -50, 100, 50),
        }
        # +90 CCW maps the offset (50, 0) -> (0, 50), and swaps 100 x 100
        # to itself, so the box must centre on (0, +50) from the new origin.
        x1, y1, x2, y2 = predicted_bbox(comp, 1000, 2000, 90, 0)
        assert (_div(x1 + x2, 2), _div(y1 + y2, 2)) == (1000, 2050)

        # -90 maps (50, 0) -> (0, -50).
        x1, y1, x2, y2 = predicted_bbox(comp, 1000, 2000, -90, 0)
        assert (_div(x1 + x2, 2), _div(y1 + y2, 2)) == (1000, 1950)

    def test_non_quarter_turn_leaves_the_offset_alone(self):
        comp = _centred("U1", 1000, 1000, 400, 100)
        x1, y1, x2, y2 = predicted_bbox(comp, 1000, 1000, 30, 0)
        assert (x2 - x1, y2 - y1) == (400, 100)


# ---------------------------------------------------------------------------
# Source-contract guards. These pin the parts of the fix that only exist in
# DelphiScript and cannot be exercised without a live Altium.
# ---------------------------------------------------------------------------


def _function_body(path: Path, name: str) -> str:
    src = path.read_text(encoding="utf-8", errors="replace")
    start = src.index("Function " + name)
    nxt = src.find("\nFunction ", start + 1)
    if nxt == -1:
        nxt = len(src)
    return src[start:nxt]


def _uncommented(body: str) -> str:
    """Drop ``{ ... }`` comments so prose about the old bug isn't matched.

    A plain regex would also eat the response payload: the JSON is built from
    Pascal string literals that are full of braces. Track string state so the
    braces inside ``'{"clear":...'`` survive.
    """
    out: list[str] = []
    in_string = False
    depth = 0
    for ch in body:
        if in_string:
            out.append(ch)
            if ch == "'":
                in_string = False
        elif depth:
            if ch == "}":
                depth -= 1
            out.append("\n" if ch == "\n" else " ")
        elif ch == "{":
            depth += 1
            out.append(" ")
        else:
            if ch == "'":
                in_string = True
            out.append(ch)
    return "".join(out)


@pytest.fixture(scope="module")
def collision_body() -> str:
    return _uncommented(_function_body(PCB_PAS, "PCB_CheckPlacementCollision"))


@pytest.fixture(scope="module")
def batch_delete_body() -> str:
    return _uncommented(_function_body(GENERIC_PAS, "Gen_BatchDelete"))


class TestCollisionSourceContract:
    def test_colliders_are_measured_like_the_target(self, collision_body):
        # Two calls: one for the target, one per candidate collider.
        assert collision_body.count("PCB_ComponentPlacementBBox(") == 2

    def test_component_bounding_rectangle_is_not_used_for_colliders(
        self, collision_body
    ):
        # IPCB_Component.BoundingRectangle includes designator and comment
        # text; only PCB_ComponentPlacementBBox may fall back to it.
        assert "Other.BoundingRectangle" not in collision_body

    def test_iterator_advances_in_exactly_one_place(self, collision_body):
        # The old loop advanced inside the layer-skip branch as well, then
        # relied on a Continue that did not always transfer control -- which
        # is how a skipped component's refdes ended up printed against the
        # next component's box.
        assert collision_body.count("Iterator.NextPCBObject") == 1

    def test_no_continue_in_the_candidate_loop(self, collision_body):
        assert "Continue" not in collision_body

    def test_layer_and_basis_are_reported(self, collision_body):
        assert '"bbox_basis"' in collision_body
        assert '"same_side_filter"' in collision_body
        assert '"bbox_includes"' in collision_body


class TestBatchDeleteSourceContract:
    """Bug 1 lives in Generic.pas and is likewise script-only."""

    def test_pcb_type_table_is_consulted(self, batch_delete_body):
        assert "ObjectTypeFromStringPCB(" in batch_delete_body

    def test_pcb_ops_reach_the_pcb_handler(self, batch_delete_body):
        assert "ProcessActivePCBDoc(" in batch_delete_body

    def test_unresolved_types_are_reported(self, batch_delete_body):
        assert '"unresolved":[' in batch_delete_body
        assert '"failures":[' in batch_delete_body
        assert "INVALID_TYPE" in batch_delete_body

    def test_existing_response_keys_are_preserved(self, batch_delete_body):
        assert '"operations_processed":' in batch_delete_body
        assert '"total":' in batch_delete_body

    def test_no_silent_skip_on_unresolved_type(self, batch_delete_body):
        # `If ObjTypeInt = -1 Then Continue;` was the whole bug.
        assert not re.search(r"ObjTypeInt\s*=\s*-1\s*Then\s*Continue",
                             batch_delete_body)
