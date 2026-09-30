# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The placement job: place a board read from the EDA, report the moves.

Runs the placer on a copy of the board, rounds each moved part to the whole
mil the EDA's move command takes, and judges the rounded result with the
exact DRC, so what is reported is what applying the moves would give.
"""

from __future__ import annotations

import time
from typing import Any

from ..bench import copy_board, hpwl, overlaps, strip_routing
from ..drc import run_drc
from ..model import LayoutBoard
from .placer import Placer
from .transform import set_pose


def place_job(params: dict[str, Any]) -> dict[str, Any]:
    board = params.get("board")
    if isinstance(board, dict):
        board = LayoutBoard.from_dict(board)
    if not isinstance(board, LayoutBoard):
        raise ValueError("layout_place job requires a 'board' (LayoutBoard or its dict)")
    parts = params.get("parts")
    t0 = time.perf_counter()
    placer = Placer(copy_board(board), movable=set(parts) if parts else None,
                    decap_pull=float(params.get("decap_pull") or 0.0),
                    spread_density=float(params.get("spread_density") or 0.0))
    rep = placer.run()
    out = copy_board(board)
    before = {c.ref: c for c in board.components}
    moves = []
    for part in placer.parts:
        if part.fixed:
            continue
        x, y, rot = round(part.x), round(part.y), part.rot % 360.0
        old = before.get(part.ref)
        if old is not None and abs(old.x - x) < 1e-6 and abs(old.y - y) < 1e-6 \
                and abs((old.rotation - rot) % 360.0) < 1e-6:
            continue
        set_pose(out, part.ref, x=x, y=y, rotation=rot)
        moves.append({"designator": part.ref, "x": x, "y": y, "rotation": rot})
    # Judged unrouted: the board's own routing does not move with its
    # parts, and its tracks would be counted against the new places.
    placed = strip_routing(out)
    drc = run_drc(placed)
    moved = {m["designator"] for m in moves}
    return {
        "board": board.name,
        "summary": {
            "parts_moved": len(moves),
            "parts_fixed": sum(1 for p in placer.parts if p.fixed),
            "failed": rep["failed"],
            "body_overlaps": rep["body_overlaps"],
            "hpwl_before": round(hpwl(strip_routing(copy_board(board))), 1),
            "hpwl_after": round(hpwl(placed), 1),
            "overlaps": [list(o) for o in overlaps(placed) if moved & set(o)],
            "violations": len(drc.violations),
            "seconds": round(time.perf_counter() - t0, 1),
        },
        "violations": [v.as_dict() for v in drc.violations[:50]],
        "moves": moves,
        "notes": _notes(board, moves, rep),
    }


def _notes(board: LayoutBoard, moves, rep) -> list[str]:
    notes = ["Parts keep their side. Parts whose designator starts like a "
             "connector, mounting hole, fiducial, test point, switch or "
             "battery (J, P, CN, USB, H, MH, FID, TP, T, BTN, SW, K, BT, ANT), "
             "and locked parts, stay where they are unless listed in parts."]
    # Routing is copper with a net: an outline drawn on a mechanical layer
    # was counted here as the board's routing.
    copper = set(board.copper_layers())
    routed = [t for t in board.tracks
              if not t.comp and not t.keepout and t.net and t.layer in copper]
    vias = [v for v in board.vias if not v.comp]
    if (routed or vias) and moves:
        notes.append(f"The board has {len(routed)} tracks and {len(vias)} vias of "
                     "its own; moving parts leaves "
                     "them where they are. Take it up first with pcb_unroute (all nets, "
                     "or the moved parts' nets), then place.")
    if rep["failed"]:
        notes.append("These parts found no free spot and were left where spreading put "
                     "them, overlapping others: " + ", ".join(rep["failed"]))
    if rep["body_overlaps"]:
        notes.append("These parts fit only with their bodies over another part's body, "
                     "their copper clear: " + ", ".join(rep["body_overlaps"])
                     + ". Check the heights.")
    return notes
