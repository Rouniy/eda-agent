# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Scale invariance of the routing model, and loud failure at its limits.

The bug these guard against: ``route_plan`` reported valid, existing
nets in ``unknown_nets`` on a dense board, and whether it did so
depended on ``grid_pitch_mils`` -- the one knob that must never change
which nets exist. The board here mirrors the reported one (1090 pads,
bbox 5356..8899 x 8044..9619 mils, a 0.8 mm BGA cluster, plus the
tracks and vias that were added between a working and a failing run) so
the sweep exercises the same node counts: ~709x315 cells at 5 mils
against ~178x79 at 20.
"""

from __future__ import annotations

import pytest

from eda_agent.route import GridTooFineError, RouterOptions, RoutingProblem
from eda_agent.route.router import route_geometry

# Board extents of the reported STM32H7 + 2x LR2021 layout, mils.
BX1, BY1, BX2, BY2 = 5356, 8044, 8899, 9619
PAD_COUNT = 1090

OCTOSPI = tuple(f"OCTOSPI_IO{i}" for i in range(8)) + (
    "OCTOSPI_NCS", "OCTOSPI_CLK", "OCTOSPI_DQS")

RULES = {
    "clearance_mils": 4,
    "track_width_mils": 5,
    "via_size_mils": 18,
    "via_drill_mils": 10,
    "layers": ["TopLayer", "SIG-L03"],
}


def _board(with_copper: bool) -> dict:
    """1090 pads over the reported bbox; the OCTOSPI nets sit in a 0.8 mm
    BGA cluster. ``with_copper`` adds the ~64 tracks / ~31 vias that were
    on the board for the failing runs but not the passing one."""
    pads = []
    for i, net in enumerate(OCTOSPI):
        # Two pads per net, one in the BGA field, one at the flash.
        pads.append({"x": 7000 + (i % 6) * 31, "y": 8500 + (i // 6) * 31,
                     "x_size": 16, "y_size": 16, "rotation": 0,
                     "layer": "TopLayer", "net": net})
        pads.append({"x": 7600 + i * 40, "y": 9200, "x_size": 20,
                     "y_size": 30, "rotation": 0, "layer": "TopLayer",
                     "net": net})
    filler = 0
    while len(pads) < PAD_COUNT:
        filler += 1
        # Deterministic spread across the board, no RNG: the point of the
        # sweep is that the SAME input survives every pitch.
        x = BX1 + 20 + (filler * 137) % (BX2 - BX1 - 40)
        y = BY1 + 20 + (filler * 71) % (BY2 - BY1 - 40)
        pads.append({"x": x, "y": y, "x_size": 16, "y_size": 16,
                     "rotation": 0,
                     "layer": ("MultiLayer" if filler % 3 == 0
                               else "TopLayer"),
                     "net": f"N{filler % 300}"})

    tracks, vias = [], []
    if with_copper:
        for k in range(64):
            x = BX1 + 50 + (k * 53) % (BX2 - BX1 - 100)
            y = BY1 + 50 + (k * 97) % (BY2 - BY1 - 100)
            tracks.append({"x1": x, "y1": y, "x2": x + 120, "y2": y,
                           "width": 8,
                           "layer": "TopLayer" if k % 2 else "SIG-L03",
                           "net": OCTOSPI[k % len(OCTOSPI)]})
        for k in range(31):
            vias.append({"x": BX1 + 80 + (k * 113) % (BX2 - BX1 - 160),
                         "y": BY1 + 80 + (k * 41) % (BY2 - BY1 - 160),
                         "size": 18,
                         "net": OCTOSPI[k % len(OCTOSPI)]})
    return {
        "bbox": {"x1": BX1, "y1": BY1, "x2": BX2, "y2": BY2},
        "counts": {"pads": len(pads), "tracks": len(tracks),
                   "vias": len(vias), "arcs": 0, "regions": 0,
                   "components": 0},
        "pads": pads, "tracks": tracks, "vias": vias,
    }


# ---------------------------------------------------------------------------
# Scale invariance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("with_copper", [False, True])
def test_terminals_are_identical_at_every_grid_pitch(with_copper):
    """The netlist the router sees must not move with the grid.

    Pitch changes the obstacle map's resolution and nothing else; if the
    set of nets with terminals differs between 5 and 20 mils, some
    resource limit is silently reclassifying real nets as unknown.
    """
    geom = _board(with_copper)
    seen = {}
    for pitch in (5, 10, 20, 25):
        prob = RoutingProblem.from_geometry(geom, RULES,
                                            grid_pitch_mils=pitch)
        seen[pitch] = (frozenset(prob.terminals),
                       prob.pads_seen, prob.pads_used)
        assert prob.pads_seen == PAD_COUNT

    baseline = seen[25]
    for pitch, got in seen.items():
        assert got == baseline, f"grid pitch {pitch} changed the netlist"
    assert set(OCTOSPI) <= baseline[0]


@pytest.mark.parametrize("with_copper", [False, True])
def test_grid_scale_actually_changes_between_the_swept_pitches(with_copper):
    """Guard the guard: if the sweep above ever stopped changing the grid
    it would pass vacuously."""
    geom = _board(with_copper)
    fine = RoutingProblem.from_geometry(geom, RULES, grid_pitch_mils=5)
    coarse = RoutingProblem.from_geometry(geom, RULES, grid_pitch_mils=20)
    assert fine.grid_info()["grid_nodes"] > 400_000
    assert fine.grid_info()["grid_nodes"] > (
        10 * coarse.grid_info()["grid_nodes"])


def test_adding_copper_does_not_make_nets_unknown():
    """Routed copper is an obstacle, never a reason to forget a net."""
    bare = RoutingProblem.from_geometry(_board(False), RULES,
                                        grid_pitch_mils=5)
    copper = RoutingProblem.from_geometry(_board(True), RULES,
                                          grid_pitch_mils=5)
    assert set(bare.terminals) == set(copper.terminals)
    assert set(OCTOSPI) <= set(copper.terminals)


# ---------------------------------------------------------------------------
# Loud failure at the resource bound
# ---------------------------------------------------------------------------


def test_grid_too_fine_raises_with_numbers_instead_of_degrading():
    geom = _board(False)
    with pytest.raises(GridTooFineError) as exc:
        RoutingProblem.from_geometry(
            geom, {**RULES, "layers": ["TopLayer", "SIG-L03", "SIG-L06"]},
            grid_pitch_mils=1)
    err = exc.value
    d = err.as_dict()
    assert d["reason_code"] == "grid_too_fine"
    assert d["grid_nodes"] > d["grid_node_limit"]
    assert d["suggested_grid_pitch_mils"] > 1
    assert str(d["grid_nodes"]) in str(err)
    assert str(d["grid_node_limit"]) in str(err)
    # A ValueError subclass, so existing callers keep catching it.
    assert isinstance(err, ValueError)


def test_node_budget_counts_layers():
    """A 6-layer stack costs three times a 2-layer one at the same pitch;
    a cells-only cap under-reads the allocation by exactly that factor."""
    geom = _board(False)
    two = RoutingProblem.from_geometry(geom, RULES, grid_pitch_mils=5)
    six_layers = [f"L{i}" for i in range(6)]
    six = RoutingProblem.from_geometry(
        geom, {**RULES, "layers": six_layers}, grid_pitch_mils=5)
    assert six.grid_info()["grid_cells"] == two.grid_info()["grid_cells"]
    assert six.grid_info()["grid_nodes"] == 3 * two.grid_info()["grid_nodes"]


# ---------------------------------------------------------------------------
# Failure diagnosis
# ---------------------------------------------------------------------------


def _bga(pitch_mils=31, pad=16, n=9, clearance=2, width=4):
    """n x n BGA field at ``pitch_mils``, two pads of net S buried in it."""
    pads = [{"x": 400 + i * pitch_mils, "y": 400 + j * pitch_mils,
             "x_size": pad, "y_size": pad, "rotation": 0,
             "layer": "TopLayer",
             "net": "S" if (i, j) in ((3, 3), (5, 5)) else f"F{i}{j}"}
            for i in range(n) for j in range(n)]
    geom = {"bbox": {"x1": 300, "y1": 300, "x2": 1000, "y2": 1000},
            "pads": pads}
    rules = {"clearance_mils": clearance, "track_width_mils": width,
             "via_size_mils": 20, "via_drill_mils": 10,
             "layers": ["TopLayer"]}
    return geom, rules


def test_coarse_grid_failure_names_the_limiting_pad_pitch():
    geom, rules = _bga()
    sol = route_geometry(geom, rules, grid_pitch_mils=25)
    net = sol["nets"]["S"]
    assert net["status"] == "failed"
    assert net["hint"] == "grid_too_coarse"
    assert net["limiting_pad_pitch_mils"] == pytest.approx(31.0)
    # gap 15, corridor = width + 2*clearance = 8, so 7 mils of band.
    assert net["escape_band_mils"] == pytest.approx(7.0)
    assert net["suggested_grid_pitch_mils"] == 7
    assert sol["summary"]["failed_hints"] == {"grid_too_coarse": 1}


def test_impossible_corridor_is_not_blamed_on_the_grid():
    # 12 mil track + 2 x 10 mil clearance needs 32 mils; the pads leave 15.
    geom, rules = _bga(clearance=10, width=12)
    sol = route_geometry(geom, rules, grid_pitch_mils=5)
    net = sol["nets"]["S"]
    assert net["status"] == "failed"
    assert net["hint"] == "no_corridor_at_any_pitch"
    assert net["corridor_needed_mils"] == pytest.approx(32.0)
    assert net["escape_band_mils"] < 0
    assert "suggested_grid_pitch_mils" not in net


def test_expansion_budget_exhaustion_is_not_reported_as_no_path():
    """A search-budget verdict must say so. Halving the pitch quadruples
    the flood, so the default budget silently turns routable nets into
    'no path' on any fine grid."""
    wall = [{"x": 1000, "y": y, "x_size": 16, "y_size": 40, "rotation": 0,
             "layer": "TopLayer", "net": "W"} for y in range(0, 2001, 30)]
    geom = {"bbox": {"x1": 0, "y1": 0, "x2": 2000, "y2": 2000},
            "pads": [{"x": 100, "y": 100, "x_size": 16, "y_size": 16,
                      "rotation": 0, "layer": "TopLayer", "net": "S"},
                     {"x": 1900, "y": 1900, "x_size": 16, "y_size": 16,
                      "rotation": 0, "layer": "TopLayer", "net": "S"},
                     *wall]}
    rules = {"clearance_mils": 5, "track_width_mils": 5, "via_size_mils": 20,
             "via_drill_mils": 10, "layers": ["TopLayer"]}
    sol = route_geometry(geom, rules, grid_pitch_mils=5,
                         options=RouterOptions(max_expansions=500))
    net = sol["nets"]["S"]
    assert net["status"] == "failed"
    assert net["hint"] == "expansion_budget_exhausted"
    assert net["expansion_budget"] == 500
    assert net["expansions_used"] >= 500
    assert "NOT proof that no route exists" in net["detail"]
    assert sol["summary"]["failed_hints"] == {"expansion_budget_exhausted": 1}


def test_exhaustive_search_is_not_mislabelled_as_budget_exhaustion():
    """A genuinely sealed-in pad must NOT claim the budget ran out."""
    ring = [{"x": 500 + dx, "y": 500 + dy, "x_size": 20, "y_size": 20,
             "rotation": 0, "layer": "TopLayer", "net": "F"}
            for dx in (-30, -15, 0, 15, 30) for dy in (-30, -15, 0, 15, 30)
            if (dx, dy) != (0, 0)]
    geom = {"bbox": {"x1": 300, "y1": 300, "x2": 900, "y2": 900},
            "pads": [{"x": 500, "y": 500, "x_size": 16, "y_size": 16,
                      "rotation": 0, "layer": "TopLayer", "net": "S"},
                     {"x": 850, "y": 850, "x_size": 16, "y_size": 16,
                      "rotation": 0, "layer": "TopLayer", "net": "S"},
                     *ring]}
    rules = {"clearance_mils": 8, "track_width_mils": 8, "via_size_mils": 20,
             "via_drill_mils": 10, "layers": ["TopLayer"]}
    sol = route_geometry(geom, rules, grid_pitch_mils=5,
                         options=RouterOptions(max_expansions=200_000))
    net = sol["nets"]["S"]
    assert net["status"] == "failed"
    assert net["hint"] != "expansion_budget_exhausted"
    assert net["expansions_used"] < 200_000
