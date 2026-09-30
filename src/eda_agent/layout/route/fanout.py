# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""BGA fanout: a via for every ball that cannot leave on its own layer.

A person routing a BGA does not route ball by ball. The outer rings leave
on the BGA's own layer, as many rings as there is room for tracks between
the balls; every ball further in gets a via first, all in one pattern,
and the routing starts from those vias on the inner layers. Left to find
its own way, the router fought over the space between the balls for
every net at once, and most of the conflicts that never settled were
round the BGA.

A via goes between four balls (a dog-bone, with a short track to it) when
one fits there, else in the ball at its exact centre, the largest style
that clears everything either way. Dog-bones point away from the middle
of the part, so each ball has its own diagonal and no two share one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..model import LayoutBoard, Track, Via

EPS = 1e-6


@dataclass
class BGA:
    comp: str
    layer: str
    pitch: float
    ball: float                    # ball pad diameter
    pads: list[int]                # indices into board.pads
    ij: dict[int, tuple[int, int]] = field(default_factory=dict)
    ring: dict[int, int] = field(default_factory=dict)
    center: tuple[float, float] = (0.0, 0.0)


def find_bgas(board: LayoutBoard, min_balls: int = 16) -> list[BGA]:
    """Parts whose surface pads are round and sit on a square lattice."""
    by_comp: dict[tuple[str, str], list[int]] = {}
    for i, p in enumerate(board.pads):
        if not p.comp or not p.is_smd or len(p.copper) != 1:
            continue
        c = p.copper[0]
        if c.shape not in ("round", "roundrect") or abs(c.w - c.h) > 0.01 * max(c.w, 1):
            continue
        by_comp.setdefault((p.comp, c.layer), []).append(i)
    out = []
    for (comp, layer), idx in by_comp.items():
        if len(idx) < min_balls:
            continue
        xs = np.array([board.pads[i].x for i in idx])
        ys = np.array([board.pads[i].y for i in idx])
        rot = board.pads[idx[0]].rotation
        if abs((rot % 90.0)) > 0.01 and abs((rot % 90.0) - 90.0) > 0.01:
            continue    # a lattice at an angle: not handled yet
        ux = np.unique(np.round(xs, 2))
        uy = np.unique(np.round(ys, 2))
        steps = np.concatenate([np.diff(ux), np.diff(uy)])
        steps = steps[steps > 0.5]
        if not len(steps):
            continue
        pitch = float(np.min(steps))
        gi = (xs - xs.min()) / pitch
        gj = (ys - ys.min()) / pitch
        if np.max(np.abs(gi - np.round(gi))) > 0.05 or np.max(np.abs(gj - np.round(gj))) > 0.05:
            continue
        gi, gj = np.round(gi).astype(int), np.round(gj).astype(int)
        nx, ny = gi.max() + 1, gj.max() + 1
        # The step between rounded positions is only as good as the
        # rounding; the span over the lattice is exact.
        pitch = float((xs.max() - xs.min()) / (nx - 1)) if nx > 1 else pitch
        if nx < 4 or ny < 4:
            continue
        ball = float(np.median([board.pads[i].copper[0].w for i in idx]))
        bga = BGA(comp, layer, pitch, ball, list(idx),
                  center=(float(xs.mean()), float(ys.mean())))
        for k, i in enumerate(idx):
            a, b = int(gi[k]), int(gj[k])
            bga.ij[i] = (a, b)
            bga.ring[i] = min(a, b, nx - 1 - a, ny - 1 - b)
        out.append(bga)
    return out


@dataclass
class FanoutPlan:
    vias: list[Via] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)
    by_pad: dict[int, Via] = field(default_factory=dict)   # pad index -> its via


def plan_fanout(router, bgas: list[BGA]) -> FanoutPlan:
    """A via for each ball of a routed net that its layer cannot free.

    ``router`` supplies the grid's clearance fields, the rules and each
    net's via styles; it must be built on the board WITHOUT the fanout.
    """
    plan = FanoutPlan()
    board = router.board
    pads = board.pads
    by_net = {j.name: j for j in router.jobs}
    placed: list[tuple[float, float, float, str]] = []   # x, y, radius, net
    for bga in bgas:
        width = router.w_def
        c = router.c
        gap = bga.pitch - bga.ball
        between = max(0, int(math.floor((gap - c + EPS) / (width + c))))
        for i in bga.pads:
            p = pads[i]
            job = by_net.get(p.net)
            if job is None or bga.ring[i] <= between:
                continue
            via = _choose(router, job, bga, p, placed)
            if via is None:
                continue
            x, y, style, stub = via
            v = Via(x, y, style.diameter, style.hole, board.copper_layers()[0],
                    board.copper_layers()[-1], p.net)
            plan.vias.append(v)
            plan.by_pad[i] = v
            placed.append((x, y, style.diameter / 2, p.net))
            if stub:
                plan.tracks.append(Track(bga.layer, p.x, p.y, x, y, job.width, p.net))
    return plan


def _choose(router, job, bga: BGA, pad, placed):
    """Dog-bone if one fits, else in the pad; the largest style either way."""
    cx, cy = bga.center
    sx = 1.0 if pad.x >= cx else -1.0
    sy = 1.0 if pad.y >= cy else -1.0
    h = bga.pitch / 2.0
    spots = [(pad.x + sx * h, pad.y + sy * h, True), (pad.x, pad.y, False)]
    for x, y, stub in spots:
        room = _room(router, job, x, y)
        for style in job.vias:
            r = style.diameter / 2
            if room < r - EPS:
                continue
            if stub and room < r + 0.0:
                continue
            if any(math.hypot(x - px, y - py) < r + pr + router.c - EPS
                   for px, py, pr, net in placed if net != job.name):
                continue
            if not stub or _stub_clear(router, job, pad, x, y):
                return x, y, style, stub
    return None


def _room(router, job, x: float, y: float) -> float:
    """Room round a point for this net's copper on every routing layer:
    the nearest cell's room less the distance to it."""
    spec = router.grid.spec
    i, j = spec.cell(x, y)
    if not (0 <= i < spec.nx and 0 <= j < spec.ny):
        return -1.0
    off = math.hypot(float(spec.x(i)) - x, float(spec.y(j)) - y)
    row = router.rr.clearance_row(job.id)
    at = (slice(j, j + 1), slice(i, i + 1))
    return min(float(router._slack(job.id, l, at, row)[0, 0]) for l in range(router.L)) - off


def _stub_clear(router, job, pad, x: float, y: float) -> bool:
    """The short track from the ball to a dog-bone via clears foreign
    copper along its length, sampled at the grid's pitch."""
    n = max(2, int(math.ceil(math.hypot(x - pad.x, y - pad.y) / (router.pitch / 2))))
    li = router.grid.layer_index.get(pad.copper[0].layer)
    if li is None:
        return False
    spec = router.grid.spec
    row = router.rr.clearance_row(job.id)
    for k in range(n + 1):
        px = pad.x + (x - pad.x) * k / n
        py = pad.y + (y - pad.y) * k / n
        i, j = spec.cell(px, py)
        off = math.hypot(float(spec.x(i)) - px, float(spec.y(j)) - py)
        at = (slice(j, j + 1), slice(i, i + 1))
        if float(router._slack(job.id, li, at, row)[0, 0]) - off < job.width / 2 - EPS:
            return False
    return True
