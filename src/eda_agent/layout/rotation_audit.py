# SPDX-License-Identifier: Apache-2.0
"""Parts that would connect shorter at another right-angle rotation.

An advisory on a placed board, not a placer: every unlocked part with two
or more pads is tried at 0, 90, 180 and 270 degrees about its own origin, every
other part held where it is, and the rotation that scores lowest is
reported when it beats the current one by ``min_improvement_mils``.

Each connected net scores one term, moving all of the part's pads together:

* a routable net (``plane_net_pads`` pads or fewer): the airline length of
  the whole net, a minimum spanning tree over its pad centres, with this
  part's pads at their candidate positions. A pad that only slides along a chain
  (a bulk cap on a power path) costs almost nothing, a real detour costs
  its length;
* a plane net (more pads than that, a ground or a supply): the distance to
  the nearest pad on another part in that net, because a decoupling cap's return is
  local and closeness to the IC's ground or thermal pad is what matters.

Geometry only. It knows nothing of which nets are critical, so a pull-up or
a strap resistor can be told to turn for no electrical gain, and a
datasheet's recommended layout outranks it.

Candidate turns that overlap another known courtyard or 3D body are recorded
as blocked. Where either outline is unavailable, the collision check is
incomplete and the caller must still verify placement clearance.

Bottom-side parts ARE checked. They were skipped until the sign was
measured against Altium 26.11.1.5 on 2026-10-25: four mirrored parts,
flipped with ``pcb_flip_component`` and read back, turn their pads in
world coordinates by exactly the delta applied to ``Rotation``, the
same way a top-side part does, at 45 degrees as well as at right
angles. The scoring never needed a side term anyway -- it rotates the
pad's WORLD position about the component origin, and the mirroring is
already baked into the position the board reports.
"""

from __future__ import annotations

import math
from typing import Optional

from ..core.net_naming import is_ground_net, is_power_net
from . import geom
from .audit import _overlaps, body_outline
from .model import LayoutBoard, Pad

#: Nets with more pads than this are scored as planes (nearest pad).
PLANE_NET_PADS = 40

#: Smallest gain, in mils of score, worth reporting.
MIN_IMPROVEMENT_MILS = 25.0

ROTATIONS = (0.0, 90.0, 180.0, 270.0)


def mst_length(points: list[tuple[float, float]]) -> float:
    """Minimum spanning tree length over ``points`` (Prim, O(n^2))."""
    n = len(points)
    if n < 2:
        return 0.0
    in_tree = [False] * n
    best = [math.inf] * n
    best[0] = 0.0
    total = 0.0
    for _ in range(n):
        u = min((i for i in range(n) if not in_tree[i]), key=best.__getitem__)
        in_tree[u] = True
        total += best[u]
        ux, uy = points[u]
        for v in range(n):
            if not in_tree[v]:
                d = math.hypot(points[v][0] - ux, points[v][1] - uy)
                if d < best[v]:
                    best[v] = d
    return total


def _turn(x: float, y: float, ox: float, oy: float, deg: float) -> tuple[float, float]:
    """(x, y) turned anticlockwise by ``deg`` about (ox, oy)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    dx, dy = x - ox, y - oy
    return (ox + dx * c - dy * s, oy + dx * s + dy * c)


def _orthogonal(deg: float) -> bool:
    r = deg % 90.0
    return r < 0.5 or r > 89.5


def _plane_like(board: LayoutBoard, net: str, pad_count: int,
                threshold: int) -> bool:
    return (pad_count > threshold or is_ground_net(net) or is_power_net(net)
            or any(layer.plane_net == net for layer in board.layers))


def suggest_rotations(board: LayoutBoard, designators: Optional[list[str]] = None,
                      min_improvement_mils: float = MIN_IMPROVEMENT_MILS,
                      plane_net_pads: int = PLANE_NET_PADS) -> dict:
    """Score parts with two or more pads at the four right-angle rotations.

    Returns ``{"checked", "skipped", "suggestions", "blocked"}``: suggestions worst
    first, each with the current and suggested rotation, the gain in mils,
    ``bbox_changes`` (a quarter turn swaps the body's width and height, so
    clearance wants re-checking) and the per-net terms at both rotations.
    """
    wanted = {d.strip() for d in designators or [] if d.strip()}
    pads_of: dict[str, list[Pad]] = {}
    net_pads: dict[str, list[Pad]] = {}
    for p in board.pads:
        if p.comp:
            pads_of.setdefault(p.comp, []).append(p)
        if p.net:
            net_pads.setdefault(p.net, []).append(p)

    checked = 0
    skipped: list[dict] = []
    blocked: list[dict] = []
    outlines = {c.ref: body_outline(c) for c in board.components}
    outline_shapes = {ref: geom.polygon(points) for ref, points in outlines.items()
                      if points}
    suggestions: list[dict] = []
    for comp in board.components:
        if wanted and comp.ref not in wanted:
            continue
        pads = pads_of.get(comp.ref, [])
        if len(pads) < 2 or comp.locked:
            continue
        if not _orthogonal(comp.rotation):
            skipped.append({"designator": comp.ref,
                            "reason": f"rotation {comp.rotation:g} is not a right angle"})
            continue

        current = round(comp.rotation) % 360

        def score(rotation: float) -> Optional[tuple[float, list[dict]]]:
            total, terms = 0.0, []
            for net in sorted({p.net for p in pads if p.net}):
                own_pads = [p for p in pads if p.net == net]
                own = [_turn(p.x, p.y, comp.x, comp.y, rotation - current)
                       for p in own_pads]
                others = [(q.x, q.y) for q in net_pads[net]
                          if q.comp != comp.ref]
                if not others:
                    continue
                if _plane_like(board, net, len(net_pads[net]),
                               plane_net_pads):
                    value = sum(min(math.hypot(px - x, py - y)
                                    for x, y in others) for px, py in own)
                    metric = "nearest_return_mils"
                else:
                    value = mst_length(others + own)
                    metric = "net_airline_mils"
                total += value
                terms.append({"pad": own_pads[0].name if len(own_pads) == 1 else "*",
                              "net": net, metric: round(value, 1)})
            return (total, terms) if terms else None

        now = score(current)
        if now is None:
            continue
        checked += 1
        candidates = sorted(((int(r), value) for r in ROTATIONS
                             if r != current and (value := score(r)) is not None),
                            key=lambda item: item[1][0])
        for best_rot, best in candidates:
            gain = now[0] - best[0]
            if gain < min_improvement_mils:
                break
            entry = {
                "designator": comp.ref,
                "current_rotation": current,
                "suggested_rotation": best_rot,
                "improvement_mils": round(gain, 1),
                "bbox_changes": (best_rot - current) % 180 != 0,
                "courtyard_checked": bool(outlines.get(comp.ref)),
                "current_pads": now[1],
                "suggested_pads": best[1],
            }
            outline = outlines.get(comp.ref)
            if outline:
                turned = geom.polygon([_turn(x, y, comp.x, comp.y,
                                             best_rot - current)
                                       for x, y in outline])
                hit = next((other.ref for other in board.components
                            if other.ref != comp.ref and other.side == comp.side
                            and other.ref in outline_shapes
                            and _overlaps(turned, outline_shapes[other.ref])), None)
                if hit:
                    blocked.append({**entry, "collides_with": hit})
                    continue
            suggestions.append(entry)
            break
    suggestions.sort(key=lambda s: -s["improvement_mils"])
    blocked.sort(key=lambda s: -s["improvement_mils"])
    return {"checked": checked, "skipped": skipped,
            "suggestions": suggestions, "blocked": blocked}


def rotation_audit(board: LayoutBoard, limit: int = 200) -> dict:
    """Layout audit check: parts that would connect shorter turned.

    Advisory: ``pass`` stays True, since a shorter airline is not always the
    better layout."""
    found = suggest_rotations(board)
    return {
        "pass": True,
        "advisory": True,
        "counts": {"checked": found["checked"], "suggestions": len(found["suggestions"]),
                   "skipped": len(found["skipped"])},
        "suggestions": found["suggestions"][:limit],
        "blocked": found["blocked"][:limit],
        "skipped": found["skipped"][:limit],
        "note": ("Airline geometry only, pad centre to pad centre. Weigh each "
                 "suggestion: it matters for decoupling, snubber and filter parts, "
                 "rarely for pull-ups or straps. After a quarter turn "
                 "(bbox_changes) re-run placement_audit."),
    }


__all__ = ["mst_length", "rotation_audit", "suggest_rotations"]
