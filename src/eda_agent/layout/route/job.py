# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""A routing run as a background job: board in, placeable copper out.

Pure: no bridge. The board comes from the live read (``read_altium``) or
a fixture; what comes back is the copper the router adds, in the item
shapes ``pcb_place_tracks`` and ``pcb_place_vias`` take, plus the exact
DRC's verdict on the routed board. Nothing is applied here.
"""

from __future__ import annotations

import time
from typing import Any

from ..bench import copy_board
from ..drc import run_drc
from ..model import LayoutBoard
from .router import route_adaptive


def route_job(params: dict[str, Any]) -> dict[str, Any]:
    board = params.get("board")
    if isinstance(board, dict):
        board = LayoutBoard.from_dict(board)
    if not isinstance(board, LayoutBoard):
        raise ValueError("layout_route job requires a 'board' (LayoutBoard or its dict)")
    nets = params.get("nets")
    board, old_pours = _without_old_pours(board)
    t0 = time.perf_counter()
    r = route_adaptive(board, nets=frozenset(nets) if nets else None,
                       planes=bool(params.get("planes", True)))
    out = r.apply()
    new_tracks = out.tracks[len(board.tracks):]
    new_vias = out.vias[len(board.vias):]
    drc = run_drc(out)
    rep = r.report
    wanted = set(nets) if nets else None
    unrouted = {n: k for n, k in drc.unrouted.items() if wanted is None or n in wanted}
    return {
        "board": board.name,
        "summary": {
            "completion": round(drc.completion, 4),
            "missing_connections": drc.missing_connections,
            "unrouted_nets": len(unrouted),
            "violations": len(drc.violations),
            "tracks": len(new_tracks),
            "vias": len(new_vias),
            "routing_layers": list(r.grid.layers),
            "planes": sorted({f"{p.layer}:{p.net}" for p in r.pour_planes}),
            "pours": sorted({f"{r.grid.layers[p.li]}:{p.net}" for p in r.pours}),
            "released_planes": sorted(r.released),
            "old_pours": old_pours,
            "iterations": rep.iterations,
            "seconds": round(time.perf_counter() - t0, 1),
        },
        "unrouted": unrouted,
        "violations": [v.as_dict() for v in drc.violations[:50]],
        "tracks": [{"x1": t.x1, "y1": t.y1, "x2": t.x2, "y2": t.y2, "width": t.width,
                    "layer": t.layer, "net_name": t.net} for t in new_tracks],
        "vias": [{"x": v.x, "y": v.y, "size": v.diameter, "hole_size": v.hole,
                  "low_layer": v.low_layer, "high_layer": v.high_layer, "net": v.net}
                 for v in new_vias],
        "notes": _notes(r),
    }


def _without_old_pours(board: LayoutBoard) -> tuple[LayoutBoard, list[str]]:
    """The board without its polygons' poured copper.

    A polygon's copper is where its last pour left it, round routing that
    may since have been taken up or moved. The router pours from the
    polygon's outline and the apply step repours, so the old copper is not
    something new routing has to clear. Kept, it was: on a public board,
    live, un-routed and re-placed, new vias found room on the inner layers only
    in the old vias' voids: 137 s and 76 violations. Without it the same
    board routed in 8 s with none.
    """
    outlines = {(r.layer, r.source) for r in board.regions if r.kind == "pour_boundary"}
    old = [r for r in board.regions if r.kind == "pour" and (r.layer, r.source) in outlines]
    if not old:
        return board, []
    out = copy_board(board)
    out.regions = [r for r in board.regions if not any(r is o for o in old)]
    return out, sorted({f"{r.layer}:{r.net}" for r in old})


def _notes(r) -> list[str]:
    notes = []
    if r.pour_planes:
        notes.append(
            "The routes rely on these inner-layer pours as planes: "
            + ", ".join(sorted({f"{p.layer} ({p.net})" for p in r.pour_planes}))
            + ". Nothing was routed on them. Repour the polygons after "
              "applying (pcb_repour_polygons) so they clear the new vias.")
    if r.pours:
        notes.append(
            "These nets are joined by the board's own pours, poured round the "
            "routes; their tracks the pours make redundant were taken up: "
            + ", ".join(sorted({f"{r.grid.layers[p.li]} ({p.net})" for p in r.pours}))
            + ". Their connections hold once the polygons are repoured "
              "(pcb_autoroute_apply does it, or pcb_repour_polygons).")
    return notes
