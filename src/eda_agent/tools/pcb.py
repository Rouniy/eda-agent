# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""PCB-specific tools for Altium Designer MCP Server.

Provides high-level PCB operations: net classes, design rules, DRC,
component placement, trace lengths, layer stackup, board outline, etc.
"""

import json
import hashlib
import math
import re
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import ValidationError

from ..bridge import get_bridge
from ..bridge.exceptions import AltiumError
from ..design import fab_library
from ..placement import (
    BoardRegion,
    PlaceComp,
    PlaceNet,
    PlaceOptions,
    PlacePin,
    hpwl,
    overlap_pair_count,
    plan_placement,
    rotate_offset,
)
from .bulk_hints import BulkHintTracker
from .datasheet_hints import tag_response
from .editor_options import run_options
from .library import _angle_text, _edge_arc, _mils
from ..bridge.payload import payload_safe
from ..units import MILS_PER_MM, format_length, length_in, normalise_units

#: The dump and the apply pass of pcb_apply_geometry_map each walk every
#: free primitive of a board, tens of thousands on a large one.
_GEOMETRY_MAP_TIMEOUT = 1800.0


def _fab_board_facts(reply: dict[str, Any], expected_path: str) -> dict[str, Any]:
    """Accept only a complete, internally consistent exact-board snapshot."""
    if not isinstance(reply, dict) or reply.get("board_path", "").casefold() != expected_path.casefold():
        raise ValueError("native fab facts did not identify the requested board")
    for key in ("copper_layers", "pad_holes", "via_holes", "hole_count"):
        if type(reply.get(key)) is not int or reply[key] < 0:
            raise ValueError(f"native fab facts lack a valid {key}")
    if reply["copper_layers"] == 0 or reply["hole_count"] != reply["pad_holes"] + reply["via_holes"]:
        raise ValueError("native fab layer or hole totals are inconsistent")
    outline = reply.get("outline_mm")
    if not isinstance(outline, dict):
        raise ValueError("native fab facts lack an outline")
    for axis in ("width", "height"):
        value = outline.get(axis)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"native fab outline has no valid {axis}")
    return {key: reply[key] for key in ("copper_layers", "outline_mm", "hole_count")}


def _drill_pairs_snapshot(reply: dict[str, Any], board_path: str) -> list[dict[str, Any]]:
    """Refuse a partial drill-pair read before it can authorize a write."""
    if not isinstance(reply, dict) or not isinstance(reply.get("board_path"), str):
        raise ValueError("drill pair read lacks board identity")
    if reply["board_path"].casefold() != board_path.casefold():
        raise ValueError("drill pair read came from another board")
    pairs = reply.get("pairs")
    count = reply.get("count")
    if (not isinstance(pairs, list) or type(count) is not int
            or count < 0 or len(pairs) != count
            or reply.get("reported_count") != count
            or reply.get("unreadable_count") != 0):
        raise ValueError("drill pair read is incomplete")
    for i, pair in enumerate(pairs):
        if (not isinstance(pair, dict) or pair.get("index") != i
                or type(pair.get("low_layer_id")) is not int
                or type(pair.get("high_layer_id")) is not int
                or any(type(pair.get(field)) is not bool for field in
                       ("backdrill", "plot_drill_drawing", "plot_drill_guide"))):
            raise ValueError("drill pair entry is incomplete")
    return pairs


def _pair_impedance_snapshot(reply: Any, board_path: str,
                             rule_name: str) -> dict[str, Any]:
    if (not isinstance(reply, dict)
            or not isinstance(reply.get("board_path"), str)
            or reply["board_path"].casefold() != board_path.casefold()
            or str(reply.get("rule_name", "")).casefold() != rule_name.casefold()
            or reply.get("rule_kind") != 51
            or not isinstance(reply.get("after"), dict)):
        raise ValueError("pair impedance read is incomplete or from another rule")
    state = reply["after"]
    if type(state.get("impedance_driven")) is not bool:
        raise ValueError("pair impedance mode is missing")
    for field in ("min_ohms", "max_ohms", "preferred_ohms"):
        value = state.get(field)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"pair impedance {field} is missing")
    return state


def _offset_pair_polyline(
    points: list[tuple[float, float]],
    center_offset: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return positive/negative parallel polylines around a centerline.

    Interior vertices use a miter intersection, so the pair spacing remains
    constant through ordinary corners instead of opening at every bend.
    """
    if len(points) < 2:
        raise ValueError("at least two centerline points are required")
    normals: list[tuple[float, float]] = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            raise ValueError("centerline contains a zero-length segment")
        normals.append((-dy / length, dx / length))

    offsets: list[tuple[float, float]] = []
    for index in range(len(points)):
        if index == 0:
            ox, oy = normals[0]
        elif index == len(points) - 1:
            ox, oy = normals[-1]
        else:
            ax, ay = normals[index - 1]
            bx, by = normals[index]
            denom = 1.0 + ax * bx + ay * by
            if denom <= 1e-6:
                raise ValueError("centerline contains a 180-degree reversal")
            ox, oy = (ax + bx) / denom, (ay + by) / denom
        offsets.append((ox * center_offset, oy * center_offset))

    positive = [(x + ox, y + oy) for (x, y), (ox, oy) in zip(points, offsets)]
    negative = [(x - ox, y - oy) for (x, y), (ox, oy) in zip(points, offsets)]
    return positive, negative


def _build_objective_report(
    place_comps: list,
    positions: dict[str, tuple],
    rotations: dict[str, float],
    place_nets: list,
    region_obj,
    grid_mils: float,
    clearance_mils: float,
) -> dict[str, Any]:
    """Score a proposed placement on the full multi-term objective.

    Pure Python; reuses the scorer in ``design.pcb_placement`` so both
    auto-placement cores report the same un-weighted term breakdown
    (wirelength, layer-change proxy, congestion, overlap, board-edge,
    decoupling proximity, connector banding, thermal) plus the weighted
    total, a legality flag, and the achieved utilization. Components all
    sit on the top side here, so the via term is structurally zero.
    """
    from ..design import pcb_placement as _construct

    rules = _construct.DesignRules(
        grid=float(grid_mils),
        component_clr=float(clearance_mils),
    )
    pos = {r: [float(c[0]), float(c[1])] for r, c in positions.items()}
    rot = {c.ref: float(rotations.get(c.ref, c.rotation)) for c in place_comps}
    sides = {c.ref: 1 for c in place_comps}
    report = _construct.score(
        place_comps, pos, rot, sides, place_nets, region_obj,
        rules, _construct.ObjectiveWeights(),
    )
    out = report.as_dict()
    out["weighted_total"] = round(report.weighted_total, 3)
    out["legal"] = bool(report.legal)
    out["utilization"] = round(report.utilization, 4)
    for key in list(out):
        if isinstance(out[key], float):
            out[key] = round(out[key], 3)
    return out


def _build_net_length_report(
    place_comps: list,
    positions: dict[str, tuple],
    rotations: dict[str, float],
    place_nets: list,
    critical: set,
    top: int = 8,
) -> dict[str, Any]:
    """Per-net physical bounding span (mils) of the proposed placement.

    Reuses ``design.pcb_placement.net_spans`` so the diagnostic matches the
    same pin geometry the scorer sees. Returns the ``top`` longest nets
    (the routing risk / candidates to mark critical) plus the achieved span
    of every net the caller already flagged critical.
    """
    from ..design import pcb_placement as _construct

    pos = {r: [float(c[0]), float(c[1])] for r, c in positions.items()}
    rot = {c.ref: float(rotations.get(c.ref, c.rotation)) for c in place_comps}
    sides = {c.ref: 1 for c in place_comps}
    spans = _construct.net_spans(place_comps, pos, rot, sides, place_nets)
    ordered = sorted(spans.items(), key=lambda kv: (-kv[1], kv[0]))
    report: dict[str, Any] = {
        "longest_nets": [
            {"net": n, "span_mils": round(v, 1)} for n, v in ordered[:top]
        ],
    }
    if critical:
        report["critical_net_spans"] = {
            n: round(spans[n], 1) for n, _ in ordered if n.upper() in critical
        }
    return report


def _build_decoupling_report(
    place_comps: list,
    positions: dict[str, tuple],
    rotations: dict[str, float],
    place_nets: list,
) -> list:
    """Structural decoupling analysis of the proposed placement.

    Reuses ``design.pcb_placement.decoupling_report`` to surface which cap
    decouples which IC (found on the connectivity graph, never by name) and
    the achieved centre-to-power-pin distance in mils, worst first -- so the
    caller can confirm decaps landed tight against their ICs.
    """
    from ..design import pcb_placement as _construct

    pos = {r: [float(c[0]), float(c[1])] for r, c in positions.items()}
    rot = {c.ref: float(rotations.get(c.ref, c.rotation)) for c in place_comps}
    sides = {c.ref: 1 for c in place_comps}
    return _construct.decoupling_report(place_comps, pos, rot, sides, place_nets)


# A net touching more than this many parts is treated as a power/ground rail
# (routed as a plane/pour) and excluded from the SIGNAL ratsnest count, since
# its crossings do not become signal vias.
_RATSNEST_SIGNAL_FANOUT = 4


def _build_ratsnest_report(
    place_comps: list,
    positions: dict[str, tuple],
    rotations: dict[str, float],
    place_nets: list,
) -> dict[str, Any]:
    """Ratsnest crossing counts as a routability / via-pressure indicator.

    ``signal_crossings`` excludes high-fanout rails (planes carry no signal
    via) and is the figure that predicts routing difficulty; ``total_crossings``
    is the conservative all-net count (power assumed routed as traces).
    """
    from ..design import pcb_placement as _construct

    pos = {r: [float(c[0]), float(c[1])] for r, c in positions.items()}
    rot = {c.ref: float(rotations.get(c.ref, c.rotation)) for c in place_comps}
    sides = {c.ref: 1 for c in place_comps}
    return {
        "signal_crossings": _construct.ratsnest_crossings(
            place_comps, pos, rot, sides, place_nets,
            max_fanout=_RATSNEST_SIGNAL_FANOUT),
        "total_crossings": _construct.ratsnest_crossings(
            place_comps, pos, rot, sides, place_nets),
        "signal_fanout_cap": _RATSNEST_SIGNAL_FANOUT,
    }


def _build_placement_summary(
    objective_report: dict[str, Any],
    ratsnest: dict[str, Any],
    decoupling: list,
    suggested_board: Optional[dict[str, Any]],
) -> str:
    """One-line, human/LLM-readable assessment of the placement, synthesising
    the detailed reports so a caller can judge quality at a glance."""
    parts: list[str] = []
    parts.append("legal" if objective_report.get("legal")
                 else "ILLEGAL (courtyard overlap)")
    util = objective_report.get("utilization")
    if util is not None:
        parts.append(f"{round(float(util) * 100)}% board utilization")
    sx = ratsnest.get("signal_crossings")
    if sx is not None:
        tag = "routable" if sx <= 2 else "review routability"
        parts.append(f"{sx} signal-net ratsnest crossing(s) ({tag})")
    if decoupling:
        worst = max(d["distance_mils"] for d in decoupling)
        parts.append(f"{len(decoupling)} decap(s) detected, worst "
                     f"{worst:.0f} mils from its IC power pin")
    if suggested_board:
        parts.append(f"suggested board {suggested_board['width']:.0f}x"
                     f"{suggested_board['height']:.0f} mils")
    return "; ".join(parts) + "."


NETLIST_CSV_HEADER = ("component", "pin", "pin_name", "net")

# The fitted-classes pcb_filter_variant_components can select. Validated
# in Python because the Pascal cannot: PCB_FilterVariantComponents tests
# 'all_fitted', 'fitted_original' and 'alternate' in an If chain whose
# implicit else is not_fitted, so an unrecognised word silently selects
# the not-fitted parts. It then echoes the caller's own string back as
# "select", so the reply CONFIRMS the class that was not selected.
#
# A typo of "alternate" therefore selects the opposite class and says it
# did what was asked. Anything acting on that selection, a delete, a
# component class, a variant review, acts on the wrong components.
FILTER_VARIANT_SELECT = (
    "not_fitted", "fitted_original", "alternate", "all_fitted")


def parse_tabular_netlist(text: str) -> dict[str, Any]:
    """Parse the tabular netlist CSV that ``proj_export_netlist`` writes.

    One ``component,pin,pin_name,net`` row per pin-net node, header row
    first. Pure Python (no Altium round-trip), so the SCH->PCB bridge
    derivation is unit-testable offline.

    Returns ``{"ok": True, "nodes": [(component, pin, pin_name, net), ...],
    "skipped_rows": N}`` -- nodes in file order, rows with a missing
    component/pin/net or a wrong field count counted in ``skipped_rows`` --
    or ``{"ok": False, "reason": ...}`` when the text is empty or the
    header is not the tabular-netlist header.
    """
    import csv
    import io

    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if not rows:
        return {"ok": False, "reason": "empty netlist text"}
    header = tuple(c.strip().lower() for c in rows[0])
    if header != NETLIST_CSV_HEADER:
        return {
            "ok": False,
            "reason": (
                "not a tabular netlist (expected header "
                f"'{','.join(NETLIST_CSV_HEADER)}', got "
                f"'{','.join(rows[0])}'); export with "
                "proj_export_netlist(net_format='tabular')"
            ),
        }
    nodes: list[tuple[str, str, str, str]] = []
    skipped = 0
    for row in rows[1:]:
        if len(row) != 4:
            skipped += 1
            continue
        comp, pin, pin_name, net = (c.strip() for c in row)
        if not comp or not pin or not net:
            skipped += 1
            continue
        nodes.append((comp, pin, pin_name, net))
    return {"ok": True, "nodes": nodes, "skipped_rows": skipped}


def derive_netlist_build(
    nodes: list[tuple[str, str, str, str]],
) -> dict[str, Any]:
    """Derive the net-creation and pad-binding work lists from netlist nodes.

    Input: ``(component, pin, pin_name, net)`` tuples (the shape
    ``parse_tabular_netlist`` returns). Output dict:

    - ``nets``: distinct net names, sorted (deterministic input for
      ``pcb_create_nets_from_list``).
    - ``bindings``: one ``{"designator", "pin", "net"}`` dict per node,
      grouped by designator (the Pascal handler caches the component
      lookup per consecutive designator run). Duplicate
      (designator, pin) rows collapse to the first occurrence.
    - ``components``: distinct designators, sorted.
    """
    nets: set[str] = set()
    components: set[str] = set()
    seen_pads: set[tuple[str, str]] = set()
    by_comp: dict[str, list[dict[str, str]]] = {}
    for comp, pin, _pin_name, net in nodes:
        nets.add(net)
        components.add(comp)
        if (comp, pin) in seen_pads:
            continue
        seen_pads.add((comp, pin))
        by_comp.setdefault(comp, []).append(
            {"designator": comp, "pin": pin, "net": net}
        )
    bindings = [b for comp in sorted(by_comp) for b in by_comp[comp]]
    return {
        "nets": sorted(nets),
        "bindings": bindings,
        "components": sorted(components),
    }


def _encode_bindings_param(bindings: list[dict[str, Any]]) -> str:
    """Encode binding dicts into the ``~~``-op / ``;``-field wire grammar
    the Pascal ``NextBatchOp``/``GetBatchField`` helpers parse. Entries
    missing designator/pin/net are dropped (the caller reports counts)."""
    ops: list[str] = []
    for b in bindings:
        desig = str(b.get("designator", "")).strip()
        pin = str(b.get("pin", "")).strip()
        net = str(b.get("net", "")).strip()
        if not desig or not pin or not net:
            continue
        ops.append(f"designator={desig};pin={pin};net={net}")
    return "~~".join(ops)


#: The signature defaults of pcb_calc_termination's unit-suffixed
#: arguments, kept here so the alias handling can tell "the caller did
#: not pass this" from "the caller passed exactly the default". Without
#: that distinction a conflicting alias cannot be detected at all, and
#: the choice is between silently preferring one value and refusing
#: every call that supplies a terse spelling.
_TERMINATION_DEFAULTS = {
    "z0_ohms": 50.0,
    "dielectric_constant": 4.2,
    "driver_impedance_ohms": 0.0,
    "dielectric_height_mils": 0.0,
}


# ---------------------------------------------------------------------------
# Rule scope queries.
#
# A scope reaches Altium as Scope1Expression / Scope2Expression, assigned
# as a property: it is never written into script text, so there is nothing
# to escape. Altium's own query engine compiles it. Its precedence puts
# And, Or, Xor and Not ABOVE the comparisons (Query Language Reference
# TR0110, "Brackets and Order of Precedence"), so "IsPad AND HoleSize > 3"
# reads as "(IsPad AND HoleSize) > 3". Reported: that scope raised
# "; expected at Line:2, Char:76. Continue execution?" on every call, the
# rule was created anyway, and the Rules editor later said some rules had
# incorrect definitions. && and || bind after the comparisons.
# ---------------------------------------------------------------------------

_SCOPE_TOKEN = re.compile(
    r"'(?:''|[^'])*'|&&|\|\||<>|<=|>=|[=<>()]|[A-Za-z_][A-Za-z0-9_.]*|\S")
_SCOPE_LOGIC = {"and", "or", "xor", "not"}
_SCOPE_COMPARE = {"=", "<>", "<", ">", "<=", ">=", "like"}


def _scope_wraps(expr: str) -> list[tuple[int, int]]:
    """Spans of comparisons sharing a bracket level with And/Or/Xor/Not.

    Each span is one operand of the logical operator at that level, as
    ``(start, end)`` offsets into ``expr``. The And of ``Between a And b``
    is read as a logical And too, which changes nothing: neither side of
    it holds a comparison.
    """
    def level():
        return {"logic": False, "segments": [],
                "current": {"compare": False, "start": None, "end": None}}

    def extend(lev, start, end):
        seg = lev["current"]
        if seg["start"] is None:
            seg["start"] = start
        seg["end"] = end

    wraps: list[tuple[int, int]] = []

    def close(lev):
        segments = lev["segments"] + [lev["current"]]
        if lev["logic"] and any(s["compare"] for s in segments):
            wraps.extend((s["start"], s["end"]) for s in segments
                         if s["compare"] and s["start"] is not None)

    stack = [level()]
    for m in _SCOPE_TOKEN.finditer(expr):
        tok, start, end = m.group(0), m.start(), m.end()
        low = tok.lower()
        lev = stack[-1]
        if tok == "(":
            extend(lev, start, end)
            stack.append(level())
        elif tok == ")":
            if len(stack) > 1:
                close(stack.pop())
            extend(stack[-1], start, end)
        elif low in _SCOPE_LOGIC:
            lev["logic"] = True
            lev["segments"].append(lev["current"])
            lev["current"] = {"compare": False, "start": None, "end": None}
        else:
            if low in _SCOPE_COMPARE:
                lev["current"]["compare"] = True
            extend(lev, start, end)
    while stack:
        close(stack.pop())
    return wraps


def scope_problem(expr: str) -> tuple[str, str]:
    """``(reason, bracketed form)`` when Altium would misread a scope, else ('', '')."""
    text = str(expr or "")
    wraps = _scope_wraps(text)
    if not wraps:
        return "", ""
    inserts = sorted([(s, "(") for s, _ in wraps] + [(e, ")") for _, e in wraps],
                     key=lambda p: p[0], reverse=True)
    fixed = text
    for pos, ch in inserts:
        fixed = fixed[:pos] + ch + fixed[pos:]
    return (
        f"The scope {text!r} has a comparison next to And, Or, Xor or Not "
        f"at the same bracket level. Altium's query language binds And, "
        f"Or, Xor and Not tighter than =, <>, <, >, <= and >=, so it reads "
        f"the comparison against the result of the And rather than as "
        f"written, and the engine raises a script error dialog that stops "
        f"the bridge. Write it as {fixed!r}, or join the terms with && or "
        f"||, which bind after comparisons. Nothing was sent."), fixed


def _scope_refusal(expr: str, **extra: Any) -> Optional[dict[str, Any]]:
    """The reply for a scope Altium would misread, or None to go ahead."""
    reason, fixed = scope_problem(expr)
    if not reason:
        return None
    return {"success": False, "error": "BAD_SCOPE", "reason": reason,
            "suggested_scope": fixed, **extra}


def _outline_ring(outline: Any, step_deg: float = 5.0) -> list[tuple[float, float]]:
    """Turn the board outline, including arc edges, into a polygon in mils."""
    if not isinstance(outline, dict):
        return []
    vertices = outline.get("vertices") or []
    if len(vertices) < 3:
        return []
    ring: list[tuple[float, float]] = []
    for i, vertex in enumerate(vertices):
        try:
            x, y = float(vertex["x"]), float(vertex["y"])
            ring.append((x, y))
            if vertex.get("kind") != "arc":
                continue
            nxt = vertices[(i + 1) % len(vertices)]
            cx, cy = float(vertex["cx"]), float(vertex["cy"])
            radius = math.hypot(x - cx, y - cy)
            start = math.degrees(math.atan2(y - cy, x - cx)) % 360
            angle1 = float(vertex["angle1"]) % 360
            angle2 = float(vertex["angle2"]) % 360
            end = math.degrees(math.atan2(float(nxt["y"]) - cy,
                                               float(nxt["x"]) - cx)) % 360
        except (KeyError, TypeError, ValueError):
            return []

        def near(left: float, right: float) -> bool:
            return abs((left - right + 180) % 360 - 180) < 1.0

        sweep = (angle2 - angle1) % 360 or 360.0
        if near(start, angle2) and not near(start, angle1):
            sweep = -sweep
        if not near(start + sweep, end):
            sweep = ((end - start + 180) % 360) - 180
        segments = max(1, int(abs(sweep) // step_deg))
        for k in range(1, segments):
            angle = math.radians(start + sweep * k / segments)
            ring.append((cx + radius * math.cos(angle),
                         cy + radius * math.sin(angle)))
    return ring


def _grid_points(x1: float, y1: float, x2: float, y2: float,
                 spacing: float) -> list[tuple[float, float]]:
    """Inclusive rectangular grid, regardless of corner ordering."""
    low_x, high_x = sorted((x1, x2))
    low_y, high_y = sorted((y1, y2))
    spacing = spacing if spacing > 0 else 50
    points = []
    row = 0
    y = low_y
    while y <= high_y + 0.000001:
        col = 0
        x = low_x
        while x <= high_x + 0.000001:
            points.append((x, y))
            col += 1
            x = low_x + col * spacing
        row += 1
        y = low_y + row * spacing
    return points


def _inside_ring(point: tuple[float, float], ring: list[tuple[float, float]],
                 margin: float) -> bool:
    """Check polygon membership and distance from every outline edge."""
    x, y = point
    inside = False
    nearest = math.inf
    for i, (ax, ay) in enumerate(ring):
        bx, by = ring[(i + 1) % len(ring)]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < cross:
                inside = not inside
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        fraction = (0.0 if length2 == 0 else
                    max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2)))
        nearest = min(nearest, math.hypot(x - ax - fraction * dx,
                                         y - ay - fraction * dy))
    return inside and nearest >= margin


def _layer_names(layer: str, layers: Any) -> list[str]:
    """Accept a single layer or a list supplied by a client."""
    if isinstance(layers, str):
        source = layers.strip()
        try:
            layers = json.loads(source) if source.startswith("[") else [
                part for part in (item.strip() for item in source.split(",")) if part]
        except ValueError:
            layers = [source]
    names = [str(item).strip() for item in (layers or []) if str(item).strip()]
    if not names and layer:
        names = [layer.strip()]
    return names


_TEXT_ANCHORS = (
    "manual", "top_left", "center_left", "bottom_left", "top_center",
    "center", "bottom_center", "top_right", "center_right", "bottom_right",
)


def _text_anchor(value: Any) -> Optional[int]:
    """Translate an anchor name or number to Altium's enum value."""
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text in _TEXT_ANCHORS:
        return _TEXT_ANCHORS.index(text)
    if text.isdigit() and int(text) < len(_TEXT_ANCHORS):
        return int(text)
    return None


_COORDS_PER_MIL = 10000


def _outline_vertices(points: list) -> tuple[str, str]:
    """Encode outline vertices for pcb.set_board_shape: ``(text, problem)``.

    A vertex is ``[x, y]`` or a dict with ``x``, ``y`` and optionally
    ``arc_center`` and ``clockwise``; an arc runs from its vertex to the
    next one, so both must lie on its circle. Coordinates go in Altium's
    internal units so an arc's ends meet the neighbouring vertices
    exactly.
    """
    import math

    verts: list[tuple[float, float, Optional[tuple[float, float]], bool]] = []
    for i, p in enumerate(points):
        try:
            if isinstance(p, dict):
                c = p.get("arc_center")
                centre = (float(c[0]), float(c[1])) if c is not None else None
                verts.append((float(p["x"]), float(p["y"]), centre,
                              bool(p.get("clockwise", False))))
            else:
                verts.append((float(p[0]), float(p[1]), None, False))
        except (KeyError, IndexError, TypeError, ValueError):
            return "", f"vertex {i} is not [x, y] or {{x, y, arc_center}}"
    if len(verts) > 1 and verts[0][:2] == verts[-1][:2] and verts[-1][2] is None:
        verts = verts[:-1]
    if len(verts) < 3:
        return "", "a polygon needs three points or more"

    def coord(v: float) -> int:
        return int(round(v * _COORDS_PER_MIL))

    out = []
    for i, (x, y, centre, cw) in enumerate(verts):
        if centre is None:
            out.append(f"{coord(x)},{coord(y)}")
            continue
        nx, ny = verts[(i + 1) % len(verts)][:2]
        cx, cy = centre
        r = math.hypot(x - cx, y - cy)
        r_next = math.hypot(nx - cx, ny - cy)
        if r <= 0 or abs(r - r_next) > 1.0:
            return "", (f"vertex {i}: the arc's ends are {r:.1f} and "
                        f"{r_next:.1f} mil from its centre; both must lie "
                        f"on one circle")
        a_start = math.degrees(math.atan2(y - cy, x - cx)) % 360
        a_end = math.degrees(math.atan2(ny - cy, nx - cx)) % 360
        # Altium draws an arc counter-clockwise from Angle1 to Angle2, both
        # in 0..360, and an Angle2 below Angle1 wraps through 0; an end at
        # 0 is written 360, as Altium writes a quarter ending there.
        a1, a2 = (a_end, a_start) if cw else (a_start, a_end)
        if abs(a2) < 1e-9:
            a2 = 360.0
        out.append(f"{coord(x)},{coord(y)},{coord(cx)},{coord(cy)},"
                   f"{coord(r)},{a1:.6f},{a2:.6f}")
    return ";".join(out), ""


def _mils(value: Any) -> str:
    """A length in mils for the wire: whole numbers as integers, the rest
    to 1e-4 mil, which is one Altium internal unit."""
    v = float(value)
    if v.is_integer():
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _encode_bindings_param(bindings: list[dict[str, Any]]) -> str:
    """Encode binding dicts into the ``~~``-op / ``;``-field wire grammar
    the Pascal ``NextBatchOp``/``GetBatchField`` helpers parse. Entries
    missing designator/pin/net are dropped (the caller reports counts)."""
    ops: list[str] = []
    for b in bindings:
        desig = str(b.get("designator", "")).strip()
        pin = str(b.get("pin", "")).strip()
        net = str(b.get("net", "")).strip()
        if not desig or not pin or not net:
            continue
        ops.append(f"designator={desig};pin={pin};net={net}")
    return "~~".join(ops)


#: The signature defaults of pcb_calc_termination's unit-suffixed
#: arguments, kept here so the alias handling can tell "the caller did
#: not pass this" from "the caller passed exactly the default". Without
#: that distinction a conflicting alias cannot be detected at all, and
#: the choice is between silently preferring one value and refusing
#: every call that supplies a terse spelling.
_TERMINATION_DEFAULTS = {
    "z0_ohms": 50.0,
    "dielectric_constant": 4.2,
    "driver_impedance_ohms": 0.0,
    "dielectric_height_mils": 0.0,
}


_PCB_VIEW_OPTIONS = {
    "show_pad_nets": "ShowPadNets", "show_pad_numbers": "ShowPadNumbers",
    "show_via_nets": "ShowViaNets", "show_test_points": "ShowTestPoints",
    "single_layer_mode": "SingleLayerMode",
    "show_special_strings": "DisplaySpecialStrings",
    "highlight_in_net_color": "UseNetColorForHighlight",
    "highlight_full": "HighlightFull",
    "highlight_whole_net": "ShowAllPrimitivesInHighlightedNets",
    "show_component_reference_point": "ShowComponentRefPoint",
    "plane_draw_mode": "PlaneDrawMode", "pad_types_display": "PadTypesDisplayMode",
    "from_tos_display": "FromTosDisplayMode",
    "layer_name_display": "LayerNameDisplayMode",
    "draft_track_threshold_mils": "DraftTrackThreshold",
    "show_invisible_objects": "ShowInvisibleObjects",
    "transparent_layers": "UseTransparent",
    "clean_redraw": "CleanRedraw",
    "redraw_layer_on_toggle": "RedrawLayerOnToggle",
    "text_as_box_below": "TextToRectSize",
    "pad_net_font": "PadViaFontName",
    "pad_net_min_font_size": "PadViaMinFontSize",
    "pad_net_font_color": "PadViaFontColor",
    "pad_net_font_background": "PadViaFontBkColor",
    "default_truetype_font": "DefaultTTFont",
    "board_area_color": "BoardAreaColor",
    "board_line_color": "BoardLineColor",
    "sheet_area_color": "SheetAreaColor",
    "sheet_line_color": "SheetLineColor",
}
_PCB_EDIT_OPTIONS = {
    "rotation_step": "RotationStep", "undo_levels": "UndoRedoStackSize",
    "protect_locked": "ProtectLockedPrimitives",
    "select_only_visible": "OnlySelectVisible",
    "click_clears_selection": "ClickClearsSelection",
    "double_click_runs_inspector": "DoubleClickRunsInspector",
    "snap_to_centre": "SnapToCentre",
    "allow_duplicate_designators": "DuplicateDesignatorsAllowed",
    "auto_pan": "AutoPan", "drag_mode": "DragMode",
    "component_move": "ComponentMoveKind",
    "confirm_delete": "QuestionDelete",
    "confirm_global_edit": "QuestionGlobalChange",
    "confirm_drag": "QuestionDrag",
    "confirm_selection_memory_clear": "ConfirmSelectionMemoryClear",
    "shift_to_select": "MustHoldShiftToSelect",
    "global_edit_includes_arcs": "GlobalEditIncludeArcsWithTracks",
    "pick_nearest_component": "NearestComponent",
    "defaults_permanent": "DefaultPrimsPermanent",
    "check_board_on_load": "ValidateOnLoad",
    "netlist_remove_unconnected_parts": "DeleteUnconnectedComps",
    "netlist_remove_unconnected_objects": "DeleteUnconnectedPrims",
    "netlist_check_footprints": "CheckPatterns",
    "netlist_check_comments": "CheckComments",
    "auto_pan_mode": "AutoPanMode",
    "auto_pan_step": "AutoPanSmallStep",
    "auto_pan_big_step": "AutoPanLargeStep",
    "auto_pan_speed": "AutoPanSpeed",
    "pour_redraw_threshold": "PolygonThreshold",
}
_PCB_ROUTE_OPTIONS = {
    "route_mode": "InteractiveRouteMode",
    "plow_through_pours": "PlowThroughPolygons", "auto_via": "AutoVia",
    "shove_depth": "PlaceShoveDepth", "lock_pre_routes": "LockPreRoutes",
    "delete_dead_ends": "DeleteDeadEnds", "smart_track_ends": "UseSmartTrackEnds",
}
_PCB_OPTION_FLOATS = {"rotation_step", "draft_track_threshold_mils",
                      "repeat_angle", "repeat_x_mils", "repeat_y_mils"}
_PCB_OPTION_SIGNED = {"repeat_x_mils", "repeat_y_mils"}
_PCB_OPTION_INTS = {"plane_draw_mode", "pad_types_display", "from_tos_display",
                    "layer_name_display", "drag_mode", "component_move",
                    "route_mode", "shove_depth", "text_as_box_below",
                    "pad_net_min_font_size", "pad_net_font_color",
                    "pad_net_font_background", "board_area_color",
                    "board_line_color", "sheet_area_color", "sheet_line_color",
                    "auto_pan_mode", "auto_pan_step", "auto_pan_big_step",
                    "auto_pan_speed", "pour_redraw_threshold", "repeat_count"}
_PCB_OPTION_COLORS = {"pad_net_font_color", "pad_net_font_background",
                      "board_area_color", "board_line_color", "sheet_area_color",
                      "sheet_line_color"}
_PCB_OPTION_TEXTS = {"pad_net_font", "default_truetype_font",
                     "repeat_increment"}


def _pcb_option_text(value: bool | int | float) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


async def _pcb_editor_options(board_path: str, names: dict[str, str],
                              values: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    """Exact-board read, old-value preflight and native readback for preferences."""
    if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
        return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
    updates = {key: value for key, value in values.items() if value is not None}
    for key, value in updates.items():
        if key in _PCB_OPTION_FLOATS:
            valid = (not isinstance(value, bool) and isinstance(value, (int, float))
                     and math.isfinite(value)
                     and (key in _PCB_OPTION_SIGNED or value >= 0))
        elif key in _PCB_OPTION_INTS:
            valid = (type(value) is int and value >= 0
                     and (key not in _PCB_OPTION_COLORS or value <= 0xFFFFFF))
        elif key in _PCB_OPTION_TEXTS:
            valid = (isinstance(value, str) and bool(value.strip())
                     and all(ch not in value for ch in "|\r\n"))
        else:
            valid = type(value) is bool
        if not valid:
            return {"ok": False, "reason": f"invalid value for {key}"}
    bridge = get_bridge()
    base = {"board_path": board_path, "names": ",".join(names.values())}
    snapshot = await bridge.send_command_async("pcb.editor_options", base, timeout=120.0)
    raw = snapshot.get("options") if isinstance(snapshot, dict) else None
    if (not isinstance(snapshot, dict) or not isinstance(snapshot.get("board_path"), str)
            or snapshot["board_path"].casefold() != board_path.casefold()
            or not isinstance(raw, dict) or set(raw) != set(names.values())
            or snapshot.get("refused") != [] or snapshot.get("unknown") != []):
        return {"ok": False, "reason": "PCB preference read is incomplete",
                "native_reply": snapshot}
    old = {key: raw[native] for key, native in names.items()}
    if not updates:
        return {**snapshot, "options": old}
    if dry_run:
        return {"ok": True, "dry_run": True, "board_path": board_path,
                "before": old, "would_set": updates}
    params = {**base,
              "expect": "|".join(f"{native}={_pcb_option_text(raw[native])}"
                                  for native in names.values()),
              "set": "|".join(f"{names[key]}={_pcb_option_text(value)}"
                              for key, value in updates.items())}
    reply = await bridge.send_command_async("pcb.editor_options", params, timeout=120.0)
    after = reply.get("options") if isinstance(reply, dict) else None
    if (not isinstance(reply, dict) or not isinstance(reply.get("board_path"), str)
            or reply["board_path"].casefold() != board_path.casefold()
            or not isinstance(after, dict) or set(after) != set(names.values())
            or reply.get("refused") != [] or reply.get("unknown") != []
            or reply.get("not_applied") != []):
        return {"ok": False, "reason": "PCB preference write was not fully verified",
                "native_reply": reply}
    for key, value in updates.items():
        actual = after[names[key]]
        if key in _PCB_OPTION_FLOATS:
            matches = type(actual) in (int, float) and math.isclose(
                actual, value, abs_tol=0.0001)
        else:
            matches = actual == value and type(actual) is type(value)
        if not matches:
            return {"ok": False, "reason": f"{key} did not read back",
                    "native_reply": reply}
    reply["options"] = {key: after[native] for key, native in names.items()}
    return reply


async def _pcb_export_component_step(board_path: str, designator: str,
                                     out_path: str, mode: str) -> dict[str, Any]:
    """Export one placed model and verify the exact new STEP file on disk."""
    if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
        return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
    target = Path(out_path)
    if not target.is_absolute() or target.suffix.casefold() not in (".step", ".stp"):
        return {"ok": False, "reason": "out_path must be an absolute .step or .stp path"}
    if not designator.strip():
        return {"ok": False, "reason": "designator is required"}
    if target.exists():
        return {"ok": False, "reason": "out_path already exists; choose a new filename"}
    target.parent.mkdir(parents=True, exist_ok=True)
    reply = await get_bridge().send_command_async(
        "pcb.export_component_step",
        {"board_path": board_path, "designator": designator.strip(),
         "out_path": str(target), "mode": mode}, timeout=120.0,
    )
    identity = (isinstance(reply, dict)
                and isinstance(reply.get("board_path"), str)
                and reply["board_path"].casefold() == board_path.casefold()
                and reply.get("designator", "").casefold() == designator.strip().casefold()
                and isinstance(reply.get("out_path"), str)
                and reply["out_path"].casefold() == str(target).casefold()
                and reply.get("mode") == mode)
    if not identity:
        return {"ok": False, "reason": "export answer does not identify the requested target",
                "native_reply": reply}
    if not target.is_file() or target.stat().st_size < 30:
        return {"ok": False, "reason": "Altium did not write a STEP file",
                "native_reply": reply}
    with target.open("rb") as stream:
        header = stream.read(256).lstrip()
    if not header.startswith(b"ISO-10303-21"):
        return {"ok": False, "reason": "output is not a STEP file",
                "native_reply": reply}
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {**reply, "written": True, "bytes": target.stat().st_size,
            "sha256": digest}


def _option_number_refusal(counts: dict[str, Any],
                           colors: dict[str, Any]) -> Optional[dict[str, Any]]:
    """A refusal for a whole number below 0 or a colour outside 0 to
    16777215 (Altium's colour number), else None."""
    for key, value in counts.items():
        if value is not None and value < 0:
            return {"ok": False, "reason": f"{key} is 0 or more"}
    for key, value in colors.items():
        if value is not None and not 0 <= value <= 0xFFFFFF:
            return {"ok": False, "reason": f"{key} is a colour from 0 to 16777215"}
    return None


#: Paste and paste-array preferences: argument name to Altium's.
_PCB_PASTE_OPTIONS = {
    "paste_same_net": "Paste_InSameNet",
    "paste_same_class": "Paste_InSameClass",
    "paste_same_layer": "Paste_OnSameLayer",
    "paste_same_designator": "Paste_HasSameDesignator",
    "repeat_count": "RepeatCountDefault",
    "repeat_increment": "RepeatInc",
    "repeat_circular": "RepeatCircular",
    "repeat_angle": "RepeatDegrees",
    "repeat_rotate": "RepeatRotateItem",
    "repeat_x_mils": "RepeatX",
    "repeat_y_mils": "RepeatY",
}

#: The board's Gerber settings: argument name to Altium's.
_GERBER_OPTIONS = {
    "units": "GerberUnits",
    "decimals": "GerberDecs",
    "sort_output": "SortOutput",
    "software_arcs": "UseSoftwareArcs",
    "centre_on_film": "CenterPhotoPlots",
    "embed_apertures": "EmbedApertures",
    "panelize": "Panelize",
    "g54": "G54",
    "relief_shapes_allowed": "ReliefShapesAllowed",
    "flash_pads_only": "PadsFlashOnly",
    "flash_all_fills": "FlashAllFills",
    "plus_tolerance_mils": "PlusTol",
    "minus_tolerance_mils": "MinusTol",
    "film_x_mils": "FilmSizeX",
    "film_y_mils": "FilmSizeY",
    "border_mils": "BorderSize",
    "max_aperture_mils": "MaxAperSize",
}

#: The board's print settings: argument name to Altium's.
_PRINT_OPTIONS = {
    "scale": "Scale",
    "scale_to_fit_page": "ScaleToFitPage",
    "x_correction": "XCorrect",
    "y_correction": "YCorrect",
    "show_holes": "ShowHoles",
    "printer_fonts": "UsePrinterFonts",
    "software_arcs": "UseSoftwareArcs",
    "pad_nets": "PlotPadNets",
    "pad_numbers": "PlotPadNumbers",
    "border_mils": "cBorderSize",
    "composite_type": "CompositeType",
    "batch_type": "BatchType",
}

#: The Testpoint Style rule settings pcb_set_rule_properties takes, and
#: whether each is a switch (else a length in mils).
_TESTPOINT_SETTINGS = {
    "min_size_mils": False, "max_size_mils": False, "preferred_size_mils": False,
    "min_hole_mils": False, "max_hole_mils": False, "preferred_hole_mils": False,
    "grid_mils": False, "grid_tolerance_mils": False, "min_spacing_mils": False,
    "body_clearance_mils": False, "edge_clearance_mils": False,
    "under_component": True, "use_grid": True,
}


def register_pcb_tools(mcp):
    """Register PCB tools with the MCP server."""

    @mcp.tool()
    async def pcb_get_nets(board_path: str = "") -> dict[str, Any]:
        """Get all unique net names from the active or specified PCB board.

        Returns:
            Dictionary with "nets" array of net name strings and "count"
        """
        params: dict[str, Any] = {}
        if board_path:
            if (not Path(board_path).is_absolute()
                    or Path(board_path).suffix.casefold() != ".pcbdoc"):
                return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
            params["board_path"] = board_path
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_nets", params)
        if board_path and (not isinstance(result, dict)
                           or not isinstance(result.get("board_path"), str)
                           or result["board_path"].casefold() != board_path.casefold()):
            return {"ok": False, "reason": "net inventory came from another board",
                    "native_reply": result}
        return result

    @mcp.tool()
    async def pcb_focus_board(board_path: str) -> dict[str, Any]:
        """Make a specific PCB the focused/current board.

        When several PcbDocs are open, the other PCB tools
        (`pcb_get_components`, `pcb_delete_object`, `pcb_delete_net`,
        `pcb_plan_placement`, `design_visual_review`, …) operate on the
        *focused* board, and `app_set_active_document` does NOT reliably set
        that for a PcbDoc. Call this first to point them all at the board
        you mean. (`pcb_place_components` already accepts `board_path`
        directly.)

        Args:
            board_path: Absolute path to the .PcbDoc to focus.

        Returns:
            Dict with ``focused`` and the resolved ``board`` file name.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.focus_board", {"board_path": board_path}
        )

    @mcp.tool()
    async def pcb_set_view_configuration(name: str = "",
                                         board_path: str = "") -> dict[str, Any]:
        """Switch a board's view configuration, e.g. "Altium 3D Black".

        Sets the PCB Standard toolbar's view configuration combo, the
        one showing "Altium Standard 2D" by default. No API route exists:
        PCB:ChangeViewConfiguration ignores its parameters. The combo is
        read back afterwards, so a pick that did not take is reported.
        It lives here rather than with the app_ tools because it uses the
        bridge to focus the board and to check which board is in front.

        Args:
            name: The configuration as the combo lists it. Omit it to
                read the current one; a name not on the list is refused
                with the names that are.
            board_path: Focus this .PcbDoc first. Omit it to act on the
                board already in front.
        """
        import os

        from ..ui import menu
        from .uiauto import _altium_pid

        pid, problem = _altium_pid(reads_only=not name)
        if problem is not None:
            return problem
        bridge = get_bridge()
        if board_path:
            focused = await bridge.send_command_async(
                "pcb.focus_board", {"board_path": board_path})
            if not (focused or {}).get("focused", True):
                return {"ok": False, "reason": "could not focus that board",
                        "focus": focused}

        async def front() -> str:
            doc = await bridge.send_command_async(
                "application.get_active_document", {"front": "true"})
            return (doc or {}).get("file_path") or ""

        def same(a: str, b: str) -> bool:
            return (os.path.normcase(os.path.normpath(a))
                    == os.path.normcase(os.path.normpath(b)))

        # The combo belongs to whichever board is in front, and another
        # session can bring a different one forward between the focus and
        # the click: measured, a switch meant for a scratch board landed
        # on another session's board. So the front board is checked just
        # before and named afterwards.
        before = await front()
        if board_path and not same(before, board_path):
            return {"ok": False, "front_document": before, "reason": (
                f"{board_path} is not the board in front, so the toolbar "
                "would change another one. Nothing was changed")}
        result = menu.set_view_configuration(pid, name)
        after = await front()
        result["front_document"] = before
        if after and not same(after, before):
            result["ok"] = False
            result["warning"] = (
                f"the board in front changed from {before} to {after} "
                "during the switch, so the change may have landed on "
                f"{after}. Read it with no name to see")
        return result

    @mcp.tool()
    async def pcb_delete_net(
        nets: Optional[list[str]] = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete nets from the active PCB.

        By default only empty nets go, e.g. strays left after deleting
        components. A net with connections is skipped unless
        ``force=True``, which orphans its pads and tracks.

        Args:
            nets: Specific net names to delete. Omit (or pass an empty
                list) to sweep ALL empty nets on the board.
            force: Also delete nets that still have connected primitives
                (orphans them). Default False.

        A net name with a comma is refused, since the list travels comma
        separated and ``VCC,GND`` would delete VCC and GND.

        Returns:
            Dict with ``deleted`` (count removed), ``skipped_connected``
            (count), and ``skipped_nets`` (names skipped because still
            connected). Or ``{"ok": False, "reason": ...}`` if a name
            contains a comma, in which case nothing is sent.
        """
        wanted = [str(n).strip() for n in (nets or []) if str(n).strip()]
        unsendable = [n for n in wanted if "," in n]
        if unsendable:
            return {
                "ok": False,
                "reason": (
                    f"these net names contain a comma and cannot be sent: "
                    f"{unsendable}. The list travels as one "
                    "comma-separated field, so each would arrive as two "
                    "names, and a fragment can match a real net: "
                    "'VCC,GND' becomes 'VCC' and 'GND'. Delete them "
                    "individually through the Altium UI."
                ),
            }
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.delete_nets",
            {
                "nets": ",".join(payload_safe(n) for n in wanted),
                "force": "true" if force else "false",
            },
        )

    @mcp.tool()
    async def pcb_get_net_classes(members: bool = True) -> dict[str, Any]:
        """Get all net classes on the active PCB, with the nets in each.

        Altium's script host does not expose a class's member list, so
        each class is asked about every net in turn. That is one call per
        class and net, so on a big board ``members=False`` is quicker when
        only the names are needed.

        Args:
            members: Read each class's nets (default). False returns the
                class names only.

        Returns:
            Dictionary with "net_classes" (each with name, super_class and,
            when members are read, "nets", "member_count" and
            "probe_errors"), "count" and "members_read". A class with
            probe_errors above 0 may have more nets than listed.
        """
        bridge = get_bridge()
        params = {} if members else {"members": False}
        return await bridge.send_command_async(
            "pcb.get_net_classes", params, timeout=90.0)

    @mcp.tool()
    async def pcb_get_object_classes() -> dict[str, Any]:
        """Get every object class on the active PCB, with resolved membership.

        Answers what pcb_get_net_classes cannot: whether a differential-pair or
        component class exists and what is actually in it. Membership is probed
        with IPCB_ObjectClass.IsMember against nets, components and differential
        pairs, because MemberCount/MemberName[] are not exposed in DelphiScript.

        The declared MemberKind is reported only as "is_net_class": the
        component and differential-pair kind constants are undeclared in this
        DelphiScript host, and referencing one is a compile-time failure. Class
        membership is therefore reported from what probing actually returned,
        not from the declared kind.

        Returns:
            Dictionary with "object_classes" (each with name, super_class,
            is_net_class, per-kind counts and member name arrays), "count",
            and "member_names_truncated" when a class exceeded the name cap.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_object_classes", {})
        return result

    @mcp.tool()
    async def pcb_create_net_class(
        name: str,
        nets: str,
    ) -> dict[str, Any]:
        """Create a net class (or add nets to an existing one) on the active PCB.

        Args:
            name: Name for the net class (e.g., "PowerNets", "HighSpeed")
            nets: Comma-separated list of net names to add
                  (e.g., "VCC,GND,3V3")

        Returns:
            Dictionary with class_name, class_created (bool), nets_added count
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.create_net_class",
            {"name": name, "nets": nets},
        )
        return result

    @mcp.tool()
    async def pcb_create_nets_from_list(nets: list[str]) -> dict[str, Any]:
        """Create net objects on the active PCB for names not already there.

        First leg of the netlist-driven SCH->PCB bridge (Altium's ECO is
        not scriptable): place footprints with `pcb_place_components`,
        create the nets here, bind pads with `pcb_bind_pad_nets`, then
        verify with `proj_compare_sch_pcb`. The whole list is one IPC
        round-trip; names already on the board are counted, not duplicated.

        Args:
            nets: Net names to ensure exist (e.g. from the compiled
                netlist). Duplicates and empty strings are ignored.

        Returns:
            Dict with ``created`` and ``existing`` counts.
        """
        names: list[str] = []
        seen: set[str] = set()
        for n in nets:
            s = str(n).strip()
            if s and s not in seen:
                seen.add(s)
                names.append(s)
        if not names:
            return {"error": "No valid net names", "created": 0}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.create_nets_from_list", {"nets": "|".join(names)}
        )

    @mcp.tool()
    async def pcb_bind_pad_nets(bindings: list[dict[str, Any]]) -> dict[str, Any]:
        """Assign component pads to existing board nets, batch in ONE call.

        Second leg of the netlist-driven SCH->PCB bridge: after
        `pcb_create_nets_from_list`, feed every (designator, pin, net)
        row of the compiled netlist here. Each binding finds the placed
        component, matches the pad by name, and sets its net. Nets must
        already exist on the board -- a binding to a missing net fails
        (it does not create the net).

        Bindings are processed in order; keep rows for the same
        designator adjacent (the handler caches the component lookup per
        consecutive run -- `pcb_build_from_project` orders them this way
        automatically).

        Args:
            bindings: List of dicts, each with ``designator`` (e.g. "U1"),
                ``pin`` (pad name, e.g. "3" or "A1"), ``net``.

        Returns:
            Dict with ``bound`` / ``failed`` counts plus
            ``missing_components`` / ``missing_pads`` / ``missing_nets``
            name lists. Each list stops at 50 entries and carries its
            own ``*_total`` and ``*_truncated`` fields -- read those
            before treating a list as the complete set of failures.
        """
        encoded = _encode_bindings_param(bindings)
        if not encoded:
            return {"error": "No valid bindings (need designator + pin "
                    "+ net)", "bound": 0}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.bind_pad_nets", {"bindings": encoded}
        )

    @mcp.tool()
    async def pcb_build_from_project(
        netlist_csv_path: str = "",
    ) -> dict[str, Any]:
        """Build the PCB's net set and pad connectivity from the netlist.

        The SCH->PCB bridge orchestrator (replaces the unscriptable ECO
        netlist transfer): derives the distinct net list and every
        (designator, pin, net) binding from the compiled netlist, creates
        the missing nets (`pcb_create_nets_from_list`) and binds every
        pad (`pcb_bind_pad_nets`) in two IPC round-trips.

        It does NOT place footprints -- `pcb_place_components` exists for
        that. Intended sequence: place components, then run this to build
        nets and bind pads, then verify with `proj_compare_sch_pcb`.

        Args:
            netlist_csv_path: Optional path to a tabular netlist CSV
                written by ``proj_export_netlist(net_format="tabular")``
                (``component,pin,pin_name,net`` rows). Empty (default) =
                pull the compiled netlist from the open project directly.

        Returns:
            Dict with ``components`` (distinct designators in the
            netlist), ``nets_created``, ``nets_existing``, ``pads_bound``,
            ``failed``, plus the ``missing_components`` /
            ``missing_pads`` / ``missing_nets`` lists from the bind step.
        """
        from pathlib import Path

        if netlist_csv_path:
            p = Path(netlist_csv_path)
            if not p.is_file():
                return {"error": f"netlist CSV not found: {netlist_csv_path}",
                        "pads_bound": 0}
            parsed = parse_tabular_netlist(p.read_text(encoding="utf-8-sig"))
            if not parsed["ok"]:
                return {"error": parsed["reason"], "pads_bound": 0}
            nodes = parsed["nodes"]
        else:
            bridge = get_bridge()
            data = await bridge.send_command_async(
                "project.get_nets", {"limit": "100000"}
            )
            pins = data.get("pins", []) if isinstance(data, dict) else []
            nodes = []
            for pin_rec in pins:
                comp = str(pin_rec.get("component", "")).strip()
                pin = str(pin_rec.get("pin", "")).strip()
                pin_name = str(pin_rec.get("pin_name", "")).strip()
                net = str(pin_rec.get("net", "")).strip()
                if comp and pin and net:
                    nodes.append((comp, pin, pin_name, net))

        if not nodes:
            return {"error": "netlist has no pin-net nodes (is the "
                    "project compiled / the CSV non-empty?)",
                    "pads_bound": 0}

        work = derive_netlist_build(nodes)
        bridge = get_bridge()
        net_result = await bridge.send_command_async(
            "pcb.create_nets_from_list", {"nets": "|".join(work["nets"])}
        )
        bind_result = await bridge.send_command_async(
            "pcb.bind_pad_nets",
            {"bindings": _encode_bindings_param(work["bindings"])},
        )
        return {
            "components": len(work["components"]),
            "nets_created": net_result.get("created", 0),
            "nets_existing": net_result.get("existing", 0),
            "pads_bound": bind_result.get("bound", 0),
            "failed": bind_result.get("failed", 0),
            "missing_components": bind_result.get("missing_components", []),
            "missing_pads": bind_result.get("missing_pads", []),
            "missing_nets": bind_result.get("missing_nets", []),
        }



    @mcp.tool()
    async def pcb_clean_net(net: str) -> dict[str, Any]:
        """Run Altium's own clean-up on one net's routing.

        Altium's own tidy of a net's routing. Measured on AD 26.11 it
        split tracks where others meet them (a net went from 21 to 23
        pieces), with nothing removed. Reports the net's track, arc and
        via count before and after. The board is saved by the next
        obj_modify or save, as usual; there is no script undo.

        Args:
            net: The net name.

        Returns:
            ``routing_before`` and ``routing_after``.
        """
        if not net.strip():
            return {"ok": False, "reason": "net is required"}
        return await get_bridge().send_command_async("pcb.clean_net", {"net": net.strip()})







    @mcp.tool()
    async def pcb_auto_position_text(
        designators: Optional[list[str]] = None,
        name_position: Optional[str] = None,
        comment_position: Optional[str] = None,
    ) -> dict[str, Any]:
        """Put parts' designator and comment back in Altium's automatic
        positions, or at a chosen anchor.

        With no position given, Altium re-places both texts at each
        part's current anchor (a part set to manual stays). Altium moves
        only text that is shown: a hidden designator or comment takes
        the anchor and keeps its place (``name_shown`` /
        ``comment_shown`` in the reply). Unlike pcb_autoplace_silkscreen,
        this does not look for clearance.

        Args:
            designators: The parts. ``None`` means every part.
            name_position, comment_position: One of manual, top_left,
                center_left, bottom_left, top_center, center,
                bottom_center, top_right, center_right, bottom_right
                (the part's own frame, so a rotated part turns them),
                or Altium's number 0 to 9.

        Returns:
            ``parts``, ``not_found`` and ``changed`` (each part's
            anchors, shown flags and text positions ``before`` and
            ``after``, the first 200).
        """
        params: dict[str, Any] = {}
        items = [d.strip() for d in (designators or []) if d and d.strip()]
        if designators is not None and not items:
            return {"ok": False, "reason": "designators is empty"}
        if items:
            params["designators"] = "\t".join(items)
        for key, value in (("name_position", name_position),
                           ("comment_position", comment_position)):
            if value is None:
                continue
            anchor = _text_anchor(value)
            if anchor is None:
                return {"ok": False, "reason": f"{key} is one of "
                        + ", ".join(_TEXT_ANCHORS) + " or 0 to 9"}
            params[key] = str(anchor)
        return await get_bridge().send_command_async(
            "pcb.auto_position_text", params, timeout=120.0)










    async def _board_regions(params: dict[str, Any]) -> dict[str, Any]:
        return await get_bridge().send_command_async("pcb.board_regions", params)

    def _points(x1: float, y1: float, x2: float, y2: float) -> dict[str, str]:
        return {"x1": repr(float(x1)), "y1": repr(float(y1)),
                "x2": repr(float(x2)), "y2": repr(float(y2))}


    @mcp.tool()
    async def pcb_split_board(x1: float, y1: float, x2: float, y2: float) -> dict[str, Any]:
        """Divide the board into layer stack regions along a split line
        from (x1, y1) to (x2, y2), in mils from the board origin, as
        Board Planning Mode's Define Split Line does. Draw it across the
        board, past the outline at both ends.

        Both halves may come back with the same name: tell them apart by
        index and give each its own (pcb_set_board_region), then a layer
        stack (pcb_layer_stacks assign).

        Returns:
            The rigid-flex setup afterwards, with ``changed`` true when a
            split line was added.
        """
        return await _board_regions({"action": "split", **_points(x1, y1, x2, y2)})

    @mcp.tool()
    async def pcb_remove_split_line(index: int) -> dict[str, Any]:
        """Remove a split line (its index from pcb_get_board_regions); the
        regions on either side join again.
        """
        if index < 0:
            return {"ok": False, "reason": "index is 0 or more"}
        return await _board_regions({"action": "unsplit", "index": str(index)})

    @mcp.tool()
    async def pcb_add_bend_line(
        region: str,
        x1: float, y1: float, x2: float, y2: float,
        radius_mils: float, angle: float, fold_index: int = 0,
    ) -> dict[str, Any]:
        """Add a bend line across a flex board region, from (x1, y1) to
        (x2, y2) in mils from the board origin, with its bend radius, bend
        angle in degrees and fold order (the order bends are folded in 3D).
        The region is named as pcb_get_board_regions lists it, or
        "#<index>". Altium stretches the line to the region's edges; a
        line that does not cross the region is refused.

        Returns:
            The rigid-flex setup afterwards, the new line in
            ``bend_lines``.
        """
        if radius_mils < 0:
            return {"ok": False, "reason": "radius_mils is 0 or more"}
        if not -360 <= angle <= 360:
            return {"ok": False, "reason": "angle is from -360 to 360 degrees"}
        if fold_index < 0:
            return {"ok": False, "reason": "fold_index is 0 or more"}
        if not region.strip():
            return {"ok": False, "reason": "region is required"}
        return await _board_regions({
            "action": "add_bend", "region": region.strip(), **_points(x1, y1, x2, y2),
            "radius_mils": repr(float(radius_mils)), "angle": repr(float(angle)),
            "fold_index": str(fold_index)})

    @mcp.tool()
    async def pcb_modify_bend_line(
        region: str,
        index: int,
        radius_mils: Optional[float] = None,
        angle: Optional[float] = None,
        fold_index: Optional[int] = None,
    ) -> dict[str, Any]:
        """Change a bend line's radius, angle or fold order: the region it
        belongs to and its index there, as pcb_get_board_regions lists
        them. Read back in the region's ``bend_lines``.
        """
        if index < 0:
            return {"ok": False, "reason": "index is 0 or more"}
        if not region.strip():
            return {"ok": False, "reason": "region is required"}
        params: dict[str, Any] = {"action": "modify_bend", "region": region.strip(),
                                  "index": str(index)}
        if radius_mils is not None:
            if radius_mils < 0:
                return {"ok": False, "reason": "radius_mils is 0 or more"}
            params["radius_mils"] = repr(float(radius_mils))
        if angle is not None:
            if not -360 <= angle <= 360:
                return {"ok": False, "reason": "angle is from -360 to 360 degrees"}
            params["angle"] = repr(float(angle))
        if fold_index is not None:
            if fold_index < 0:
                return {"ok": False, "reason": "fold_index is 0 or more"}
            params["fold_index"] = str(fold_index)
        if len(params) == 3:
            return {"ok": False, "reason": "give radius_mils, angle or fold_index"}
        return await _board_regions(params)

    @mcp.tool()
    async def pcb_delete_bend_line(region: str, index: int) -> dict[str, Any]:
        """Delete a bend line: the region it belongs to and its index there,
        as pcb_get_board_regions lists them."""
        if index < 0:
            return {"ok": False, "reason": "index is 0 or more"}
        if not region.strip():
            return {"ok": False, "reason": "region is required"}
        return await _board_regions({"action": "delete_bend", "region": region.strip(),
                                     "index": str(index)})

    @mcp.tool()
    async def pcb_set_board_region(
        region: str,
        name: str = "",
        locked_3d: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Rename a board region, or lock it in 3D (folding the board then
        moves the other regions around it) or unlock it.

        Args:
            region: The region, by name or "#<index>" (pcb_get_board_regions).
            name: Its new name.
            locked_3d: Lock (True) or unlock (False).
        """
        if not region.strip():
            return {"ok": False, "reason": "region is required"}
        if not name.strip() and locked_3d is None:
            return {"ok": False, "reason": "give name or locked_3d"}
        reply: dict[str, Any] = {}
        if name.strip():
            reply = await _board_regions({"action": "rename", "region": region.strip(),
                                          "name": name.strip()})
            if not (isinstance(reply, dict) and "regions" in reply):
                return reply
            region = name.strip()
        if locked_3d is not None:
            reply = await _board_regions({"action": "lock_3d", "region": region.strip(),
                                          "locked": "true" if locked_3d else "false"})
        return reply

    @mcp.tool()
    async def pcb_layer_stacks(
        action: str = "list",
        stack: str = "",
        name: str = "",
        flex: Optional[bool] = None,
        layer: str = "",
        region: str = "",
    ) -> dict[str, Any]:
        """List or change the board's layer stacks for rigid-flex: each
        region uses one stack, and a flex region a stack with fewer
        copper layers.

        Args:
            action: list, create (name, flex), rename (stack, name),
                remove (stack), set_flex (stack, flex), enable_layer /
                disable_layer (stack, layer: a copper layer of the board),
                or assign (stack, region: give a board region this stack).
            stack: The stack to act on, by name.
            name: The new stack's name, or the new name.
            flex: Whether the stack is flex.
            layer: A copper layer name, e.g. "Top Layer".
            region: A board region's name.

        Returns:
            The rigid-flex setup afterwards (see pcb_get_board_regions).
        """
        action = action.strip().lower()
        needs = {"list": (), "create": (), "rename": ("stack", "name"),
                 "remove": ("stack",), "set_flex": ("stack", "flex"),
                 "enable_layer": ("stack", "layer"),
                 "disable_layer": ("stack", "layer"),
                 "assign": ("stack", "region")}
        if action not in needs:
            return {"ok": False, "reason": "action is one of " + ", ".join(needs)}
        given = {"stack": stack.strip(), "name": name.strip(),
                 "flex": "" if flex is None else ("true" if flex else "false"),
                 "layer": layer.strip(), "region": region.strip()}
        missing = [k for k in needs[action] if not given[k]]
        if missing:
            return {"ok": False, "reason": f"{action} needs " + ", ".join(missing)}
        params: dict[str, Any] = {"action": action}
        params.update({k: v for k, v in given.items() if v})
        return await get_bridge().send_command_async("pcb.layer_stacks", params)

    @mcp.tool()
    async def pcb_gloss(nets: list[str], mode: str = "gloss") -> dict[str, Any]:
        """Run Altium's Gloss (smooth and shorten the routing) or Retrace
        (re-run it at the current width and clearance rules) on the
        routing of the given nets, and report each net's track count and
        routed length before and after.

        Only these nets' tracks and arcs are touched: they are selected,
        the command runs on the selection, and the selection is cleared.
        Gloss can reshape copper routed by hand: check the result.

        Args:
            nets: Net names.
            mode: "gloss" or "retrace".

        Returns:
            ``mode``, ``selected`` and ``nets`` (``tracks_before`` /
            ``tracks_after``, ``length_before_mils`` /
            ``length_after_mils``).
        """
        items = [n.strip() for n in (nets or []) if n and n.strip()]
        if not items:
            return {"ok": False, "reason": "nets is required"}
        if any("\t" in n for n in items):
            return {"ok": False, "reason": "a net name cannot hold a tab"}
        mode = mode.strip().lower()
        if mode not in ("gloss", "retrace"):
            return {"ok": False, "reason": "mode is gloss or retrace"}
        return await get_bridge().send_command_async(
            "pcb.gloss", {"nets": "\t".join(items), "mode": mode}, timeout=300.0)









    @mcp.tool()
    async def pcb_get_design_rules() -> dict[str, Any]:
        """Get all design rules from the active PCB.

        Every rule kind. ``rule_kind`` is a raw enum ordinal that differs
        between builds; read ``descriptor``, which names the kind and its
        values. Clearance-family rules also carry ``gap_mm``; trust it
        over the descriptor for Board Outline Clearance, whose descriptor
        always says ``Gap=0mil`` (measured, AD 26.10). That rule's
        per-object table is not readable from scripts. ``from_schematic``
        is true for a rule defined by a directive or parameter on the
        schematic: the next update from the schematic rewrites it, so
        change it there.

        Returns:
            Dictionary with "rules" array (each with name, rule_kind,
            enabled, priority, scope_1, scope_2, comment, descriptor,
            from_schematic, and
            gap_mm for clearance, component, hole-to-hole and board
            outline clearance rules) and "count".
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_design_rules", {})
        return result

    @mcp.tool()
    async def pcb_find_dominant_rule(
        board_path: str,
        object1: str,
        object2: str = "",
        rule_name: str = "",
        rule_kind: Optional[int] = None,
    ) -> dict[str, Any]:
        """Ask Altium which rule applies to a component, pad or net.

        Object syntax: U1, U1.3 or net:GND. Give a rule name or its
        Altium rule-kind integer from pcb_get_design_rules.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not object1.strip():
            return {"ok": False, "reason": "object1 is required"}
        if not rule_name.strip() and (type(rule_kind) is not int or rule_kind < 0):
            return {"ok": False, "reason": "give rule_name or a nonnegative rule_kind"}
        params = {"board_path": board_path, "object1": object1.strip()}
        if object2.strip():
            params["object2"] = object2.strip()
        if rule_name.strip():
            params["rule_name"] = rule_name.strip()
        else:
            params["rule_kind"] = str(rule_kind)
        reply = await get_bridge().send_command_async(
            "pcb.find_dominant_rule", params, timeout=120.0,
        )
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or type(reply.get("found")) is not bool
                or type(reply.get("rule_kind")) is not int
                or (reply["found"] and not isinstance(reply.get("rule"), dict))):
            return {"ok": False, "reason": "dominant-rule answer is incomplete",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_check_rule_scope(
        board_path: str,
        rule_name: str,
        object1: str,
        object2: str = "",
    ) -> dict[str, Any]:
        """Ask Altium whether a rule's scopes include real PCB objects."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not rule_name.strip() or not object1.strip():
            return {"ok": False, "reason": "rule_name and object1 are required"}
        params = {"board_path": board_path, "rule_name": rule_name.strip(),
                  "object1": object1.strip()}
        if object2.strip():
            params["object2"] = object2.strip()
        reply = await get_bridge().send_command_async(
            "pcb.rule_scope_check", params, timeout=120.0,
        )
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or not isinstance(reply.get("rule"), dict)
                or any(type(reply.get(field)) is not bool for field in
                       ("unary", "scope1_includes_object1",
                        "scope2_includes_object2", "applies"))):
            return {"ok": False, "reason": "rule-scope answer is incomplete",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_set_rules_enabled(
        names: list[str],
        enabled: bool,
        match: str = "name",
    ) -> dict[str, Any]:
        """Bulk-toggle the DRC-enabled flag on design rules by name.

        For example, silence Silk-to-Silk while sweeping Clearance. It
        flips ``DRCEnabled`` (whether DRC checks the rule), not
        ``Enabled``.

        Args:
            names: Rule names to toggle. With ``match="name"`` (default)
                each entry is matched case-insensitively against
                ``Rule.Name``; a trailing ``*`` wildcards the suffix
                (``"Clearance*"``). With ``match="kind"`` each entry is
                a TRuleKind ordinal as a string (look up via
                ``pcb_get_design_rules``).
            enabled: New value for ``DRCEnabled``. True turns the rule
                ON in DRC; False disables it for this run.
            match: ``"name"`` (default) or ``"kind"``.

        Returns:
            Dict with:
              - ``matched``: rules that matched any pattern
              - ``updated``: how many actually changed value
              - ``enabled``: the requested target value (for confirmation)
              - ``items``: per-matched ``{name, kind, prev_enabled, new_enabled}``
        """
        if not names:
            return {"ok": False, "reason": "names list is empty"}
        # The list rides a pipe-separated field, and this tool MUTATES
        # rule state: 'A|B' would arrive as two patterns, and with the
        # trailing-* wildcard a fragment can plausibly match real rules.
        # Refuse rather than strip: stripping produces a different
        # valid pattern.
        bad = [n for n in names if "|" in str(n)]
        if bad:
            return {"ok": False, "reason":
                    f"rule names {bad} contain '|', which is the "
                    "wire-format separator; fragments could match other "
                    "rules, so the call is refused"}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.set_rules_enabled",
            {
                "names": "|".join(str(n) for n in names),
                "enabled": "true" if enabled else "false",
                "match": match,
            },
        )

    @mcp.tool()
    async def pcb_get_clearance_violations(
        net: str = "",
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Read the violations ALREADY on the board, optionally filtered
        to one net. Does NOT run DRC.

        Reads the violation records the last DRC left; opens no dialog.
        ``violation_count: 0`` means none are STORED, not that the board
        passes: with no DRC run this session it is 0 either way (see
        ``note``). ``pcb_run_drc`` runs a fresh check, with no dialog.

        It used to trigger ``PCB:DesignRuleCheck`` first, which raises
        Altium's MODAL "Design Rule Checker" setup dialog: on a
        241-component board that wedged the whole bridge for 30+ min
        until the client timed out. A "get" tool must not do that, so
        the trigger is gone. ``pcb_run_drc()`` runs a fresh batch check;
        ``allow_modal=True`` opens the interactive dialog instead.

        CAVEAT -- ``violation_count: 0`` means "no violations are
        stored on this board", NOT "the board passes". If DRC has
        never been run in this Altium session, there is nothing to
        read and the answer is 0 either way. The response carries
        ``drc_triggered: false`` and a ``note`` saying so. To get
        fresh data, call ``pcb_run_drc()`` and verify that its report was
        written.

        Filter is substring-matched against the violation's Description
        and Name, so it catches both "Net USB_DP and Net GND" clearance
        warnings and net-named via antennas.

        Each violation carries ``x_mils`` / ``y_mils`` / ``layer`` for
        the agent to navigate to, plus ``primitive1`` / ``primitive2``
        objects with ``{detail, type, net, layer, x_mils, y_mils}``.

        Args:
            net: Substring matched against each violation's description
                and name. Empty returns all.
            offset: How many matching violations to skip, for paging.
            limit: How many to return, 200 by default.

        Returns:
            ``violation_count`` (all matches), ``offset``, ``limit``,
            ``returned``, ``has_more`` (page on by ``returned``),
            ``drc_triggered``, ``note``, ``violations``.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {"net": net} if net else {}
        if offset:
            params["offset"] = max(0, int(offset))
        if limit != 200:
            params["limit"] = max(1, int(limit))
        return await bridge.send_command_async(
            "pcb.get_clearance_violations", params, timeout=90.0)

    @mcp.tool()
    async def pcb_run_drc(allow_modal: bool = False) -> dict[str, Any]:
        """Run the active PCB's batch DRC and report its saved result.

        By default this calls Altium's board batch DRC API without opening
        the Design Rule Checker dialog. It writes a per-request report in
        the bridge workspace and confirms the run only when that report
        appears. The returned violations contain locations and primitives.
        Check board statistics first: a large unrouted board can take a
        long time to check.

        With ``allow_modal=True``, use the interactive Design Rule Checker
        instead. That dialog blocks the bridge until someone answers it.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.run_drc", {"allow_modal": "true" if allow_modal else "false"})

    @mcp.tool()
    async def pcb_get_components() -> dict[str, Any]:
        """Get all components from the active PCB with position and properties.

        DATASHEET DISCIPLINE: The response carries a `_datasheet_guidance`
        block. Before drawing any conclusion about a listed part's
        electrical behavior, pin function, or voltage rating, fetch its
        manufacturer datasheet (use WebSearch + WebFetch if you don't
        already have it). Library metadata here is NOT authoritative.

        Returns:
            Dictionary with "components" array (each with designator, x, y,
            rotation, layer, footprint) and "count", plus
            `_datasheet_guidance` + `_datasheet_parts`.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_components", {})
        return tag_response(result, components=result, context="pcb_get_components")

    @mcp.tool()
    async def pcb_recenter_component_origins(
        board_path: str,
        min_offset_mils: float = 100,
        designator: str = "",
        apply: bool = False,
        expected_plan: str = "",
    ) -> dict[str, Any]:
        """Plan or fix component origins far from their pad centroids.

        The origin moves while pads and artwork stay in place. Use the
        dry run first; pass its exact ``plan`` as ``expected_plan`` with
        ``apply=True``. Give ``designator`` to limit work to one component.
        ``board_path`` must be the exact focused PcbDoc. This repairs
        imported footprints whose remote origin breaks Fit Document.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "error": "BAD_BOARD_PATH"}
        if not math.isfinite(min_offset_mils) or min_offset_mils < 0:
            return {"ok": False, "error": "BAD_MIN_OFFSET"}
        if apply and not expected_plan:
            return {"ok": False, "error": "PLAN_REQUIRED"}
        params = {"board_path": board_path,
                  "min_offset_mils": str(min_offset_mils),
                  "designator": designator,
                  "apply": "true" if apply else "false"}
        if apply:
            params["expected_plan"] = expected_plan
        result = await get_bridge().send_command_async(
            "pcb.recenter_component_origins", params, timeout=120.0)
        if not isinstance(result, dict) or str(result.get("board_path", "")).casefold() != board_path.casefold():
            return {"ok": False, "error": "BOARD_MISMATCH", "native_reply": result}
        return result

    @mcp.tool()
    async def pcb_move_components(
        moves: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Move and/or rotate MANY PCB components in ONE IPC round-trip.

        PREFER THIS over moving one component per call. Each singular
        move is a full LLM turn (5-15 s); one call to this tool
        repositions every component in the list in a single Altium
        transaction.

        Typical uses: applying a full layout pass, running an
        auto-placement result, undoing and redoing a placement set,
        adjusting a row of components relative to each other.

        Args:
            moves: List of move dicts. Each dict supports:
                designator (required) , target component
                x        (optional)   , new X in mils
                y        (optional)   , new Y in mils
                rotation (optional)   , new rotation in degrees

            Example:
                [
                  {"designator": "U1", "x": 5000, "y": 5000, "rotation": 0},
                  {"designator": "R1", "x": 5200, "y": 4800},
                  {"designator": "C1", "rotation": 90},
                ]

        Returns:
            Dictionary with per-designator results and a count.
        """
        # Pack each move as comma-separated fields: designator,x,y,rotation
        # (empty field = leave that property unchanged). Moves joined by '|'.
        # This format is unambiguous and matches PCB_PlaceTracks.
        ops: list[str] = []
        for m in moves:
            desig = str(m.get("designator", "")).strip()
            if not desig:
                continue
            # Moves are comma-packed then pipe-joined, and this MOVES
            # components: a designator carrying either delimiter would
            # re-shape into a different move whose fragment can match a
            # real part. Refuse rather than strip ('R|1' stripped is
            # 'R1', a real component).
            if "," in desig or "|" in desig:
                return {"ok": False, "reason":
                        f"designator {desig!r} contains ',' or '|', "
                        "which are the wire-format separators; a "
                        "fragment could move another component, so the "
                        "call is refused", "moves_applied": 0}
            x_str = (
                _mils(m["x"]) if "x" in m and m["x"] is not None else ""
            )
            y_str = (
                _mils(m["y"]) if "y" in m and m["y"] is not None else ""
            )
            rot_str = (
                str(m["rotation"])
                if "rotation" in m and m["rotation"] is not None
                else ""
            )
            if x_str == "" and y_str == "" and rot_str == "":
                continue
            ops.append(f"{desig},{x_str},{y_str},{rot_str}")

        if not ops:
            return {"error": "No valid moves provided", "moves_applied": 0}

        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.batch_move_components",
            {"moves": "|".join(ops)},
        )
        return result

    @mcp.tool()
    async def pcb_place_ring(
        designators: list[str],
        center_x: float,
        center_y: float,
        radius: float,
        start_angle: float = 90.0,
        clockwise: bool = True,
        span: float = 360.0,
        rotation: Optional[float] = None,
        rotation_offset: float = 0.0,
        side: str = "",
    ) -> dict[str, Any]:
        """Place parts evenly round a circle (or an arc of one), in order.

        For rings of LEDs, buttons or mounting features: the first part at
        ``start_angle`` (degrees, 0 = +X, 90 = +Y), the rest every
        ``span / n`` degrees (``span / (n - 1)`` for an arc short of a full
        turn, so both ends are used), clockwise by default. Each part
        faces the centre the same way (its rotation follows its angle plus
        ``rotation_offset``), unless ``rotation`` fixes one rotation for
        all. Placed with the exact batch placement of pcb_move_components
        (side, then turn, then origin) and read back.

        Args:
            designators: the parts, in ring order.
            center_x, center_y: the circle's centre, mils.
            radius: mils.
            start_angle: the first part's angle, degrees.
            clockwise: direction round the ring.
            span: degrees covered (360 for a full ring).
            rotation: one rotation for every part, instead of following
                the ring.
            rotation_offset: added to each part's angle when following
                the ring (0 turns a part's +X outward).
            side: "top" or "bottom" for every part; empty keeps each.

        Returns:
            The batch placement reply, plus ``positions`` [{designator, x,
            y, rotation}] as sent.
        """
        import math

        refs = [str(d).strip() for d in designators if str(d).strip()]
        if not refs:
            return {"error": "no designators", "applied": 0}
        n = len(refs)
        full = abs(span) >= 360.0 - 1e-9
        step = span / n if full or n == 1 else span / (n - 1)
        sign = -1.0 if clockwise else 1.0
        positions = []
        for k, ref in enumerate(refs):
            a = start_angle + sign * step * k
            x = center_x + radius * math.cos(math.radians(a))
            y = center_y + radius * math.sin(math.radians(a))
            rot = rotation if rotation is not None else (a + rotation_offset)
            positions.append({"designator": ref, "x": round(x, 3), "y": round(y, 3),
                              "rotation": round(rot % 360.0, 3)})
        ops = []
        layer = {"top": "TopLayer", "bottom": "BottomLayer"}.get(side.strip().lower(), "")
        for p in positions:
            ops.append(f"{p['designator']},{round(p['x'])},{round(p['y'])},"
                       f"{p['rotation']:g},{layer}")
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.import_placement", {"placements": "|".join(ops)})
        if isinstance(result, dict):
            result["positions"] = positions
        return result

    @mcp.tool()
    async def pcb_import_placement(
        placements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Position components from a coordinate list (pick-and-place import).

        The inverse of `pcb_export_coordinates`. Each entry repositions a
        component already on the board, by designator. Absolute coordinates in
        mils, rotation in degrees; supplying `side`/`layer` flips the component
        to that side (a part already there is left alone).

        Applied in the order that gives an exact result: the side first, then
        the rotation, then the move. ``rotation`` is the FINAL rotation as
        Altium shows it, after any flip, and x/y are the component origin
        exactly, whatever the flip and the turn did to it (both move an
        asymmetric part). A part given only a side or a rotation keeps its
        origin. Every part is read back.

        A FLIP MIRRORS THE PART LEFT-RIGHT, as seen from the top, about its
        origin, and Altium changes the rotation it reports. Measured on a
        USB-C at 180 on the bottom: flipped to the top it read 0, every
        pad's x mirrored about the origin, every y unchanged. So a part
        whose opening faces +Y in its library faces +Y on either side at
        the same reported rotation, while one facing +X faces -X on the
        bottom. Work out the facing from the final reported rotation and
        the mirror, and read the pads back (pcb_get_component_pads) for a
        connector: two takes put the USB-C facing into the board.

        Args:
            placements: list of dicts, each supporting:
                designator (required)
                x        (optional) , X in mils
                y        (optional) , Y in mils
                rotation (optional) , degrees
                side     (optional) , "top" or "bottom"
                layer    (optional) , "TopLayer" / "BottomLayer" (overrides side)

        Returns:
            ``applied``, ``failed``, ``unknown_layers``, and ``mismatched``
            with ``mismatches`` (the first 20: designator, what is wrong,
            and the read-back x, y, rotation and layer).
        """
        ops: list[str] = []
        for p in placements:
            desig = str(p.get("designator", "")).strip()
            if not desig:
                continue
            x_str = _mils(p["x"]) if p.get("x") is not None else ""
            y_str = _mils(p["y"]) if p.get("y") is not None else ""
            rot_str = str(p["rotation"]) if p.get("rotation") is not None else ""
            layer = p.get("layer")
            if not layer and p.get("side") is not None:
                side = str(p["side"]).strip().lower()
                layer = "BottomLayer" if side in ("bottom", "bot", "b") else "TopLayer"
            layer_str = str(layer) if layer else ""
            ops.append(f"{desig},{x_str},{y_str},{rot_str},{layer_str}")
        if not ops:
            return {"error": "No valid placements provided", "applied": 0}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.import_placement", {"placements": "|".join(ops)}
        )

    @mcp.tool()
    async def pcb_add_teardrops() -> dict[str, Any]:
        """Add teardrops with Altium's own Teardrops command.

        Opens Altium's modal Teardrop dialog, which no script parameter
        suppresses: choose Add, the scope and the settings there, then OK.
        The reply comes when the dialog closes, and the bridge waits until
        then; app_set_dialog_control and app_press_dialog_button can answer
        it meanwhile. The selection is not changed. A later repour can
        delete teardrops, so count them after it.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.teardrops", {})

    @mcp.tool()
    async def pcb_remove_teardrops() -> dict[str, Any]:
        """Remove teardrops board-wide.

        Opens the same modal Teardrop dialog as `pcb_add_teardrops`; choose
        Remove and confirm it in Altium.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.teardrops", {})

    @mcp.tool()
    async def pcb_apply_silk_clip_plan(
        board_path: str, plan_path: str, apply: bool = False,
    ) -> dict[str, Any]:
        """Validate or apply a reviewed JSONL plan of overlay track changes."""
        return await get_bridge().send_command_async(
            "pcb.apply_silk_clip_plan",
            {"board_path": board_path, "plan_path": plan_path, "apply": str(apply).lower()},
            timeout=240.0,
        )

    @mcp.tool()
    async def pcb_clone_silk_track_fragment(
        board_path: str, address: str,
        x1_mm: float, y1_mm: float, x2_mm: float, y2_mm: float,
    ) -> dict[str, Any]:
        """Clone an overlay track segment while preserving its component."""
        coords = dict(zip(("x1", "y1", "x2", "y2"), (x1_mm, y1_mm, x2_mm, y2_mm)))
        if not all(math.isfinite(value) for value in coords.values()):
            raise ValueError("fragment coordinates must be finite")
        params = {"board_path": board_path, "address": address}
        params.update({key: str(round(value / .00000254)) for key, value in coords.items()})
        return await get_bridge().send_command_async("pcb.clone_silk_track_fragment", params)

    @mcp.tool()
    async def pcb_autoplace_silkscreen(
        silk_clearance_mils: float | None = None,
        mask_clearance_mils: float | None = None,
        mask_expansion_mils: float = 4,
        designators: list[str] | None = None,
    ) -> dict[str, Any]:
        """Move designators that break silk clearance to a clear position.

        A visible designator that is closer than the silk clearance to
        anything else on its overlay layer (component outlines, texts,
        fills), closer than the mask clearance to a pad's mask opening on
        its side, or off the board, is tried at a ring of auto-position
        anchors and left on the first that clears. A designator that is
        already clear is not touched, and one no anchor clears goes back
        where it was and is listed in ``unplaced_designators`` for a
        person. First-fit on bounding rectangles, so it errs towards
        "blocked"; run DRC after.

        Args:
            silk_clearance_mils: Silk to silk clearance. ``None`` reads the
                board's Silk To Silk rule.
            mask_clearance_mils: Silk to solder mask clearance. ``None``
                reads the board's Silk To Solder Mask rule.
            mask_expansion_mils: How far a pad's mask opening extends past
                its copper (default 4, Altium's default).
            designators: Only these components. ``None`` means all.

        Refused with NO_CLEARANCE, moving nothing, when a clearance is
        neither given nor readable from an enabled rule.

        Returns:
            ``placed``, ``already_clear``, ``unplaced``, ``hidden``,
            ``total``, the placed and unplaced designators, and each
            clearance used with its source (``argument`` or the rule's
            name). ``skipped`` is ``unplaced + hidden``.
        """
        params: dict[str, str] = {"mask_expansion_mils": str(float(mask_expansion_mils))}
        for name, val in (("silk_clearance_mils", silk_clearance_mils),
                          ("mask_clearance_mils", mask_clearance_mils)):
            if val is not None:
                if val < 0:
                    return {"ok": False, "reason": f"{name} cannot be negative"}
                params[name] = str(float(val))
        if mask_expansion_mils < 0:
            return {"ok": False, "reason": "mask_expansion_mils cannot be negative"}
        if designators:
            bad = [d for d in designators if "|" in str(d)]
            if bad:
                return {"ok": False,
                        "reason": f"a designator cannot contain |: {bad[0]}"}
            params["designators"] = "|".join(str(d) for d in designators)
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.autoplace_silkscreen", params)

    @mcp.tool()
    async def pcb_tune_length(
        net: str,
        add_length_mils: float,
        x_mils: float,
        y_mils: float,
        layer: str = "TopLayer",
        amplitude_mils: float = 40,
        width_mils: float = 6,
    ) -> dict[str, Any]:
        """Add approximate routed length to a net with a square serpentine.

        Lays a square meander on `net` at (x_mils, y_mils) sized to add about
        `add_length_mils`, then reports the net's routed length before and
        after.

        Open-loop and NOT DRC-checked: you choose where the meander goes and
        verify clearance afterward (`pcb_run_drc`). Use it to get a net close to
        a target, then finish in Altium's interactive tuner if needed. There is
        no scriptable interactive tuner in Altium, so this is the available
        approximation.

        Args:
            net: net name.
            add_length_mils: target length to add (mils).
            x_mils, y_mils: anchor point of the meander (mils).
            layer: routing layer (default TopLayer).
            amplitude_mils: meander height; bump count = add_length / (2*amplitude).
            width_mils: track width.

        Returns:
            {"length_before_mils", "length_after_mils", "added_mils", "bumps",
             "drc_checked": false}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.tune_length",
            {
                "net": net,
                "add_length_mils": add_length_mils,
                "x_mils": x_mils,
                "y_mils": y_mils,
                "layer": layer,
                "amplitude_mils": amplitude_mils,
                "width_mils": width_mils,
            },
        )

    @mcp.tool()
    async def pcb_panelize(
        child_path: str,
        board_width_mils: int,
        board_height_mils: int,
        rows: int = 2,
        cols: int = 2,
        col_gap_mils: int = 100,
        row_gap_mils: int = 100,
        border_mils: int = 200,
        tooling_holes: bool = True,
        fiducials: bool = True,
    ) -> dict[str, Any]:
        """Build a production panel on the CURRENT (blank) PCB document.

        Open a new empty .PcbDoc and run this on it. Creates an embedded-board
        array of `child_path`, a rectangular panel outline, corner tooling
        holes, and fiducials. Supply the source board size
        (`board_width_mils` / `board_height_mils`).

        Args:
            child_path: path to the source .PcbDoc to array.
            board_width_mils, board_height_mils: source board size (mils).
            rows, cols: array dimensions.
            col_gap_mils, row_gap_mils: spacing between adjacent boards.
            border_mils: rail width around the array (also half the tooling inset).
            tooling_holes, fiducials: whether to add them.

        Returns:
            {"panel_width_mils", "panel_height_mils", "rows", "cols",
             "tooling_holes", "fiducials"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.panelize",
            {
                "child_path": child_path,
                "board_width_mils": board_width_mils,
                "board_height_mils": board_height_mils,
                "rows": rows,
                "cols": cols,
                "col_gap_mils": col_gap_mils,
                "row_gap_mils": row_gap_mils,
                "border_mils": border_mils,
                "tooling_holes": tooling_holes,
                "fiducials": fiducials,
            },
        )

    @mcp.tool()
    async def pcb_delete_invalid_objects() -> dict[str, Any]:
        """Remove degenerate primitives from the active PCB.

        Deletes zero-length tracks and zero-area regions (board hygiene that
        accumulates from edits and imports). Returns the count removed.

        Returns:
            {"removed": N}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.delete_invalid_objects", {})

    @mcp.tool()
    async def pcb_audit_pad_center_connected() -> dict[str, Any]:
        """Find pads whose center has no copper entering it (acid-pad check).

        For every netted pad, checks that a track / arc / via on the same net
        reaches the pad centroid. A pad connected only at its edge (an "acid
        pad") can fail in fab. Read-only; reports offenders with designator,
        pad, net, and location.

        Returns:
            {"checked": N, "offenders": M, "items": [...]}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.audit_pad_center_connected", {})

    @mcp.tool()
    async def pcb_auto_size_board_outline(margin_mils: int = 100) -> dict[str, Any]:
        """Fit the board outline around the embedded-board array(s) plus a margin.

        Use after `pcb_panelize` (or any embedded-board layout) to size the
        panel outline to its content. Unions the embedded boards' extents, adds
        `margin_mils` on every side, and converts the result to the board
        outline.

        Args:
            margin_mils: border added on each side (default 100).

        Returns:
            {"width_mils", "height_mils"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.auto_size_board_outline", {"margin_mils": margin_mils}
        )

    @mcp.tool()
    async def pcb_normalize_vias(
        size_mils: float | None = None,
        hole_mils: float | None = None,
        net: str = "",
        from_size_mils: float | None = None,
        from_hole_mils: float | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Set free vias to their Routing Via rule's sizes, or to given ones.

        Without ``size_mils``/``hole_mils``, each via takes its dominant
        Routing Via rule's preferred diameter and hole. A rule in template
        mode ("Templates Used To Check Via") is refused for its vias: its
        size fields are not what it checks, and reading them once set nearly
        every via on a board to a pad no larger than its hole. Use ``pcb_apply_via_template``
        for a template rule. Any target without an annular ring is refused.
        Refused vias are left as they were.

        Args:
            size_mils, hole_mils: An explicit diameter and hole, together.
            net: Only vias on this net.
            from_size_mils, from_hole_mils: Only vias at this size now
                (within 0.05 mil), e.g. to fix one group.
            dry_run: Report what would change and change nothing.

        Returns:
            ``changed``, ``unchanged``, ``failed`` (did not read back), the
            refusal counts, and ``before``/``after``: vias counted by
            "diameter/hole" in mils. ``success`` is false when any via was
            refused or failed.
        """
        if (size_mils is None) != (hole_mils is None):
            return {"ok": False,
                    "reason": "give size_mils and hole_mils together, or neither"}
        params: dict[str, str] = {"dry_run": "true" if dry_run else "false"}
        for key, val in (("size_mils", size_mils), ("hole_mils", hole_mils),
                         ("from_size_mils", from_size_mils),
                         ("from_hole_mils", from_hole_mils)):
            if val is not None:
                if not val > 0:
                    return {"ok": False, "reason": f"{key} must be above zero"}
                params[key] = str(float(val))
        if size_mils is not None and not size_mils > hole_mils:
            return {"ok": False,
                    "reason": "size_mils must be larger than hole_mils (annular ring)"}
        if net:
            params["net"] = net
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.normalize_vias", params)

    @mcp.tool()
    async def pcb_apply_via_template(
        source_x: float,
        source_y: float,
        net: str = "",
        from_size_mils: float | None = None,
        from_hole_mils: float | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Make free vias match a source via: its via template, hole and diameter.

        Point at a via using the wanted template; every other free via, or
        those matching the filters, takes its template link, mode, hole
        and diameter, e.g. to meet a template-mode Routing Via rule
        (AD22+). Diameter and hole are read back, the link cannot be, so
        check one via in Properties. Larger vias can break clearance: run
        DRC.

        Args:
            source_x, source_y: A point on the source via, in mils.
            net: Only vias on this net.
            from_size_mils, from_hole_mils: Only vias at this size now.
            dry_run: Report what would change and change nothing.

        Returns:
            ``source`` (position, size, hole, net), ``changed``, ``failed``,
            ``before``/``after`` counted by "diameter/hole" in mils.
            Refused with LOCAL_STACK for a source with a per-layer stack
            and NO_ANNULAR_RING for a source without a ring.
        """
        params: dict[str, str] = {
            "source_x": str(float(source_x)),
            "source_y": str(float(source_y)),
            "dry_run": "true" if dry_run else "false",
        }
        for key, val in (("from_size_mils", from_size_mils),
                         ("from_hole_mils", from_hole_mils)):
            if val is not None:
                if not val > 0:
                    return {"ok": False, "reason": f"{key} must be above zero"}
                params[key] = str(float(val))
        if net:
            params["net"] = net
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.apply_via_template", params)

    @mcp.tool()
    async def pcb_copy_designators_to_mech(layer: str = "Mechanical1") -> dict[str, Any]:
        """Copy each component designator onto a mechanical layer (assembly prep).

        Places a `.Designator` special-string text on `layer` over every
        component, for an assembly drawing that survives silkscreen edits.

        Args:
            layer: target mechanical layer (default Mechanical1).

        Returns:
            {"copied": N, "layer": "..."}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.copy_designators_to_mech", {"layer": layer}
        )

    @mcp.tool()
    async def pcb_trim_extend_track(
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        tolerance_mils: int = 5,
    ) -> dict[str, Any]:
        """Trim or extend one track endpoint along the track's own slope.

        Finds the track endpoint nearest (from_x, from_y), then slides it to
        the perpendicular projection of (to_x, to_y) onto that track's line.
        The track stays collinear (no bend introduced) and the opposite end
        stays put, so this cleanly lengthens a track up to a target or pulls
        it back. All coordinates in mils.

        Args:
            from_x, from_y: Picks which endpoint moves (nearest one wins).
            to_x, to_y: Target the moving end is projected toward.
            tolerance_mils: How close (from_x, from_y) must be to a real
                endpoint (default 5).

        Returns:
            {"moved_end", "old_x", "old_y", "new_x", "new_y", "layer"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.trim_extend_track",
            {
                "from_x": str(from_x),
                "from_y": str(from_y),
                "to_x": str(to_x),
                "to_y": str(to_y),
                "tolerance_mils": str(tolerance_mils),
            },
        )

    @mcp.tool()
    async def pcb_cleanup_tracks(
        mode: str = "slivers",
        min_length_mils: int = 1,
    ) -> dict[str, Any]:
        """Tidy stray track geometry: delete slivers and/or merge collinear runs.

        Modes:
        - "slivers" (default): delete every track shorter than
          min_length_mils. Catches the zero/near-zero stubs left behind by
          editing.
        - "merge": join two collinear, same-layer, same-width, same-net tracks
          that meet end to end into a single track. The merge only fires when
          the shared point is a clean degree-2 junction (exactly those two
          track ends, with no via, pad, arc, or third track present), so it is
          safe to run on routed copper without breaking connectivity.
        - "both": slivers pass, then merge pass.

        Args:
            mode: "slivers", "merge", or "both" (default "slivers").
            min_length_mils: Sliver threshold (default 1).

        Returns:
            {"slivers_deleted", "merged", "mode"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.cleanup_tracks",
            {"mode": mode, "min_length_mils": str(min_length_mils)},
            timeout=120.0,
        )

    @mcp.tool()
    async def pcb_unroute(
        expect_file: str,
        nets: Optional[list[str]] = None,
        include_locked: bool = False,
        checkpoint: bool = True,
    ) -> dict[str, Any]:
        """Take up the focused board's routing: its tracks, arcs and vias.

        Removes the free tracks and arcs on signal layers, and the free
        vias, that carry a net. Never removes a footprint's own copper,
        polygons or their hatching, dimensions, keepouts, or copper with
        no net (an antenna, a logo, a heat spreader): those are drawn,
        not routed. Locked routing stays unless ``include_locked``, since
        locking is how a designer keeps a route. Polygons are not
        repoured; ``pcb_repour_polygons`` does that.

        Refuses unless the focused board is ``expect_file``. With
        ``checkpoint`` (default), first snapshots the board's folder as it
        is ON DISK, so it can be restored with ``app_restore_checkpoint``;
        unsaved edits in the editor are not in it, so save first if there
        are any.

        For other selections of board copper, ``obj_delete`` and
        ``obj_batch_delete`` take a board type with a filter, e.g.
        ``eTrackObject`` with ``Layer=TopLayer|InComponent=false``.

        Args:
            expect_file: full path of the board to un-route.
            nets: take up only these nets' routing. None takes every
                net's. A name that is not a net on the board refuses the
                whole call and nothing is removed.
            include_locked: take locked routing as well (default False).
            checkpoint: take a checkpoint first (default True).

        Returns:
            ``{"tracks", "arcs", "vias", "nets", "kept_locked", "failed",
            "checkpoint"}``: how many of each were removed, how many nets
            they were on, and how many locked primitives stayed. Or
            ``{"error": ...}``.
        """
        from pathlib import Path

        from ..layout.read_altium import _same_file

        if nets is not None and not nets:
            return {"error": "nets is empty; pass None to take up every net's routing"}
        bad = [n for n in (nets or []) if "," in n]
        if bad:
            return {"error": f"a net name with a comma cannot be sent: {bad}"}
        bridge = get_bridge()
        head = await bridge.send_command_async("pcb.get_layout_model", {"section": "board"},
                                                timeout=120.0)
        focused = str((head or {}).get("file", ""))
        if not _same_file(focused, expect_file):
            return {"error": f"the focused board is {focused or '(none)'}, not {expect_file}; "
                             "nothing was removed"}
        out: dict[str, Any] = {}
        if checkpoint:
            from ..checkpoint import CheckpointStore
            from ..config import get_config
            cp = CheckpointStore(get_config().workspace_dir / "checkpoints")
            info = cp.create(Path(expect_file).parent, label="before pcb_unroute")
            out["checkpoint"] = info.summary()
        # The board's own spelling of its path, so the script's check
        # compares like with like.
        res = await bridge.send_command_async(
            "pcb.unroute",
            {"expect_file": focused, "nets": ",".join(nets or []),
             "include_locked": "true" if include_locked else "false"},
            timeout=600.0,
        )
        if isinstance(res, dict):
            out.update(res)
        return out

    @mcp.tool()
    async def pcb_place_thieving_pads(
        layer: str = "TopLayer",
        pad_size_mils: int = 20,
        pitch_mils: int = 50,
        clearance_mils: int = 15,
        margin_mils: int = 100,
    ) -> dict[str, Any]:
        """Fill bare copper area with a grid of isolated thieving pads.

        Drops a regular grid of small round pads on `layer`, inside the board
        outline minus `margin_mils`. A grid point is skipped whenever any
        existing primitive (track, arc, via, pad, fill, region, polygon, or
        component body) sits within half-pad + clearance of it, so pads land
        only in genuinely empty regions. Pads carry no net. Evens out plating
        current on sparse boards. Capped at 5000 pads per run.

        Args:
            layer: Copper layer to populate (default TopLayer).
            pad_size_mils: Pad diameter (default 20).
            pitch_mils: Grid spacing (default 50).
            clearance_mils: Keep-out from existing copper (default 15).
            margin_mils: Inset from board edge (default 100).

        Returns:
            {"placed", "scanned", "layer"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.place_thieving_pads",
            {
                "layer": layer,
                "pad_size_mils": str(pad_size_mils),
                "pitch_mils": str(pitch_mils),
                "clearance_mils": str(clearance_mils),
                "margin_mils": str(margin_mils),
            },
            timeout=180.0,
        )

    @mcp.tool()
    async def pcb_move_tracks_to_layer(
        net_name: str,
        target_layer: str,
        via_size_mils: int = 50,
        via_hole_mils: int = 28,
    ) -> dict[str, Any]:
        """Move all tracks of a net to one layer, adding vias where needed.

        Relayers every track of `net_name` onto `target_layer`, then drops a
        via at each same-net single-layer (SMD) pad that is NOT on the target
        layer, since that pad can now only connect through a layer change.
        Multilayer (through-hole) pads need no via. This flattens a net's
        routing onto one layer, so use it deliberately.

        Args:
            net_name: Net whose tracks move.
            target_layer: Destination signal layer (e.g. "BottomLayer").
            via_size_mils: Via pad diameter for added vias (default 50).
            via_hole_mils: Via hole diameter (default 28).

        Returns:
            {"net", "target_layer", "moved", "vias_added"}.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.move_tracks_to_layer",
            {
                "net_name": net_name,
                "target_layer": target_layer,
                "via_size_mils": str(via_size_mils),
                "via_hole_mils": str(via_hole_mils),
            },
            timeout=120.0,
        )

    @mcp.tool()
    async def pcb_bevel_polygon_corners(
        index: int = 0,
        net_name: str = "",
        bevel_mils: int = 25,
    ) -> dict[str, Any]:
        """Chamfer the corners of a copper polygon pour.

        Replaces each sharp vertex with two points set back along its edges by
        bevel_mils (auto-clamped so neighbouring bevels never overlap), giving
        every corner a straight 45-style cut. Only straight-outline polygons
        are handled, a polygon containing arc segments is left untouched. The
        polygon is repoured after the edit.

        Args:
            index: Which polygon to bevel (0-based, in board iteration order).
            net_name: If set, count only polygons on this net when applying
                index.
            bevel_mils: Set-back distance per edge (default 25).

        Returns:
            {"beveled", "index", "orig_vertices", "new_vertices", "bevel_mils"},
            or an error code (NOT_FOUND / BAD_POLYGON / HAS_ARC).
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.bevel_polygon_corners",
            {"index": str(index), "net_name": net_name, "bevel_mils": str(bevel_mils)},
        )

    @mcp.tool()
    async def pcb_plan_placement(
        designators: Optional[list[str]] = None,
        fixed: Optional[list[str]] = None,
        region: Optional[dict[str, float]] = None,
        iterations: int = 400,
        grid_mils: float = 5.0,
        clearance_mils: float = 15.0,
        max_net_fanout: int = 0,
        exclude_nets: Optional[list[str]] = None,
        critical_nets: Optional[list[str]] = None,
        critical_weight: float = 3.0,
        edge_parts: Optional[dict[str, str]] = None,
        keepout_groups: Optional[dict[str, str]] = None,
        match_groups: Optional[dict[str, str]] = None,
        match_roles: Optional[dict[str, str]] = None,
        plan_json: Optional[Union[str, dict]] = None,
        reseed_grid: bool = False,
        optimize_rotation: bool = True,
        engine: str = "refine",
        restarts: int = 1,
        render_png: Optional[str] = None,
        apply: bool = False,
    ) -> dict[str, Any]:
        """Auto-place components to shorten wirelength, legally. Dry-run by
        default: returns proposed moves and metrics, changes nothing.

        Reads the netlist and each footprint's real bounding box, then
        minimises half-perimeter wirelength (HPWL) inside the outline with
        no same-layer overlaps. Parts on opposite layers may overlap.
        Workflow: run with apply=False, check ``summary``,
        ``hpwl_improvement_pct``, ``overlap_pairs_after`` and ``moves``,
        then run again with apply=True to commit in one transaction.

        Args:
            designators: Only these move; the rest stay put but still pull
                their nets and block overlaps. Default: all but ``fixed``.
            fixed: Designators held in place. You choose them; nothing is
                guessed from prefixes.
            region: Bounds {x1, y1, x2, y2} in mils. Default: the board
                outline's bounding box.
            iterations: Relaxation steps (default 400).
            grid_mils: Snap grid for final positions (default 5).
            clearance_mils: Extra spacing between parts (default 15).
            max_net_fanout: Ignore nets on more components than this
                (0 = keep all; ~20 drops power planes).
            exclude_nets: Net names to ignore, e.g. ["GND"].
            critical_nets: Nets whose pull is multiplied by
                ``critical_weight`` so they come out shortest.
            critical_weight: Multiplier for critical nets (default 3,
                clamped to 1..20).
            edge_parts: {refdes: "L"|"R"|"T"|"B"}: seat a part against that
                board edge (connectors, mounting holes).
            keepout_groups: {refdes: group}: parts in different groups are
                pushed apart, e.g. switching vs analog. construct only.
            match_groups: {refdes: group}: parts in one group are kept
                adjacent even without a shared net (matched pairs).
                construct only.
            match_roles: {refdes: role} within a match group (e.g. A/B):
                drives each role's centroid together for a common-centroid
                (ABBA) layout. Needs match_groups; construct only.
            plan_json: Your DesignPlan (JSON or dict). Adds match groups
                from differential nets and keepout groups from analog vs
                digital roles; explicit groups win. Echoed in
                ``auto_constraints``.
            reseed_grid: Re-place from scratch instead of refining current
                positions (unplaced or scrambled boards only).
            optimize_rotation: Also pick 0/90/180/270 per top-side part to
                point pins at their nets (default True).
            engine: "refine" (default) nudges current positions;
                "construct" places from scratch with a multi-term objective
                (wirelength, overlap, edge, decoupling, connectors,
                thermal) and sizes the board.
            restarts: construct only: run this many seeded restarts and
                keep the best legal result (default 1).
            render_png: Path for a preview image of the proposal, returned
                as ``preview_png`` (``preview_error`` on failure).
            apply: Commit the moves (default False).

        Returns:
            ``dry_run``, ``engine``, counts (component, movable, fixed,
            net, pin), ``summary`` (read first), ``hpwl_before/after`` and
            ``hpwl_improvement_pct``, ``overlap_pairs_before/after``,
            ``objective_report`` (each term unweighted plus
            ``weighted_total``, ``legal``, ``utilization``),
            ``net_length_report`` (``longest_nets``,
            ``critical_net_spans``), ``ratsnest`` (``signal_crossings``
            predicts layer changes), ``decoupling_report`` ([{decap, ic,
            distance_mils}], worst first, found from connectivity),
            ``suggested_board`` (construct only), ``moved_count``,
            ``rotated_count``, ``moves`` [{designator, from, to}] in
            mils/degrees, ``region``, ``notes``, and ``apply_result`` when
            applied.
        """
        bridge = get_bridge()

        comp_resp = await bridge.send_command_async("pcb.get_components", {})
        raw_comps = comp_resp.get("components") if isinstance(comp_resp, dict) else None
        if not raw_comps:
            return {
                "error": "NO_COMPONENTS",
                "reason": "pcb.get_components returned no components",
                "raw": comp_resp,
            }

        approximate = [
            str(c.get("designator", "")) for c in raw_comps
            if c.get("placement_bbox_fallback")
        ]
        if approximate:
            return {
                "error": "PHYSICAL_BBOX_UNAVAILABLE",
                "reason": (
                    "The bridge returned component boxes that may include "
                    "designator or comment text. Placement planning requires "
                    "physical footprint bounds."
                ),
                "affected_count": len(approximate),
                "affected_designators": approximate[:20],
            }

        # Resolve placement region from the board outline if not given.
        region_used: dict[str, float]
        if region and all(k in region for k in ("x1", "y1", "x2", "y2")):
            region_used = {k: float(region[k]) for k in ("x1", "y1", "x2", "y2")}
        else:
            outline = await bridge.send_command_async("pcb.get_board_outline", {})
            br = outline.get("bounding_rect") if isinstance(outline, dict) else None
            if not br:
                return {
                    "error": "NO_BOARD_OUTLINE",
                    "reason": "No board outline; pass an explicit region "
                    "{x1, y1, x2, y2} in mils.",
                    "raw": outline,
                }
            region_used = {
                "x1": float(br.get("left", 0)),
                "y1": float(br.get("bottom", 0)),
                "x2": float(br.get("right", 0)),
                "y2": float(br.get("top", 0)),
            }

        # Build the solver's component list. Capture each part's centroid,
        # origin, current rotation, bbox (for the pad->component spatial
        # join), and C0 = the centroid's offset from the origin at
        # rotation 0 -- needed to convert a solved (centroid, rotation)
        # back to an Altium move (which sets the origin and rotates about
        # it).
        def _is_orthogonal(deg: float) -> bool:
            return abs((deg % 90.0)) < 0.5 or abs((deg % 90.0) - 90.0) < 0.5

        fixed_set = {str(d).strip() for d in (fixed or []) if str(d).strip()}
        selected = {str(d).strip() for d in (designators or []) if str(d).strip()}
        geom: dict[str, dict[str, Any]] = {}
        place_comps: list[PlaceComp] = []
        comp_by_ref: dict[str, PlaceComp] = {}
        all_designators: list[str] = []
        for c in raw_comps:
            ref = str(c.get("designator", "")).strip()
            if not ref:
                continue
            all_designators.append(ref)
            # The fallback flag above prevents visual text bounds from being
            # treated as physical footprint bounds by the solver.
            bbox = c.get("placement_bbox") or c.get("bbox") or {}
            try:
                w = max(1.0, float(bbox.get("width", 0)))
                h = max(1.0, float(bbox.get("height", 0)))
                x1 = float(bbox.get("x1", 0))
                y1 = float(bbox.get("y1", 0))
                x2 = float(bbox.get("x2", 0))
                y2 = float(bbox.get("y2", 0))
                ox = float(c.get("x", 0))
                oy = float(c.get("y", 0))
                rot = float(c.get("rotation", 0) or 0)
            except (TypeError, ValueError):
                continue
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            layer = str(c.get("layer", "Top")) or "Top"
            # C0 = back-rotated centroid-from-origin vector (rotation 0).
            c0 = rotate_offset(cx - ox, cy - oy, -rot)
            geom[ref] = {
                "cx": cx, "cy": cy, "ox": ox, "oy": oy, "rot": rot,
                "c0": c0,
                "bbox": (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)),
                "layer": layer,
            }
            # Fixed if explicitly pinned, or (when a selection is given)
            # not part of the selected set.
            is_fixed = ref in fixed_set or (bool(selected) and ref not in selected)
            pc = PlaceComp(
                ref=ref,
                w=w,
                h=h,
                cx=cx,
                cy=cy,
                layer=layer,
                fixed=is_fixed,
                rotation=rot,
            )
            place_comps.append(pc)
            comp_by_ref[ref] = pc

        if not place_comps:
            return {"error": "NO_PLACEABLE_COMPONENTS", "raw": comp_resp}

        # Build the net graph from the compiled netlist. One batch IPC.
        net_resp = await bridge.send_command_async(
            "project.get_connectivity_batch",
            {"designators": "~~".join(all_designators)},
            timeout=180.0,
        )
        exclude = {str(n).strip().upper() for n in (exclude_nets or [])}
        critical = {str(n).strip().upper() for n in (critical_nets or [])}
        crit_w = max(1.0, min(float(critical_weight), 20.0))
        # refdes -> edge band, validated to the four sides. Tag the matching
        # placed component so the solver seats it against that board edge.
        edge_band_of = {
            str(r).strip(): str(b).strip().upper()[:1]
            for r, b in (edge_parts or {}).items()
            if str(b).strip().upper()[:1] in ("L", "R", "T", "B")
        }
        for ref, band in edge_band_of.items():
            pc = comp_by_ref.get(ref)
            if pc is not None:
                pc.edge = True
                pc.edge_band = band
        # Role-driven auto-constraints: when the planner hands us its plan, we
        # derive the matched-pair (differential) match_groups and the
        # mixed-signal (analog/digital) keepout_groups from the plan's net
        # roles and MERGE them under the explicit args. Explicit tags win on a
        # per-refdes conflict, so the planner can always override. No-op when
        # plan_json is absent or the plan has no differential / mixed-signal
        # structure, so existing callers are unaffected.
        auto_constraints: dict[str, Any] = {}
        if plan_json is not None:
            try:
                from ..design.placement_constraints import (
                    infer_placement_constraints,
                    merge_groups,
                )
                from ..design.plan import DesignPlan
                _payload = (plan_json if isinstance(plan_json, dict)
                            else json.loads(plan_json))
                _plan = DesignPlan.model_validate(_payload)
                _c = infer_placement_constraints(_plan)
                match_groups = merge_groups(_c.match_groups, match_groups)
                keepout_groups = merge_groups(_c.keepout_groups, keepout_groups)
                auto_constraints = {
                    "match_groups_inferred": _c.match_groups,
                    "keepout_groups_inferred": _c.keepout_groups,
                }
            except (ValueError, json.JSONDecodeError, ValidationError) as exc:
                auto_constraints = {"plan_json_error": str(exc)}
        # Mixed-signal keep-apart tags: parts in DIFFERENT groups are pushed
        # apart by the separation term (construct engine only). The planner
        # supplies the grouping semantically (e.g. analog vs digital vs RF);
        # the tag string itself is opaque, only equality matters.
        for ref, grp in (keepout_groups or {}).items():
            pc = comp_by_ref.get(str(ref).strip())
            tag = str(grp).strip()
            if pc is not None and tag:
                pc.keepout_group = tag
        # Matched-pair keep-together tags: parts in the SAME group are pulled
        # adjacent even with no shared net (diff pair, current mirror, matched
        # array). Construct engine only.
        for ref, grp in (match_groups or {}).items():
            pc = comp_by_ref.get(str(ref).strip())
            tag = str(grp).strip()
            if pc is not None and tag:
                pc.match_group = tag
        # Common-centroid sub-device roles: within a match_group, parts sharing
        # a role form one matched half (the 'A' transistors vs the 'B' ones of
        # a cross-quad / interdigitated array). Drives the two halves' centroids
        # to coincide so a process/thermal gradient cancels. Needs match_group
        # too -- a role with no group is inert.
        for ref, role in (match_roles or {}).items():
            pc = comp_by_ref.get(str(ref).strip())
            tag = str(role).strip()
            if pc is not None and tag:
                pc.match_role = tag

        def _net_weight(net_name: str) -> float:
            return crit_w if net_name.upper() in critical else 1.0
        net_members: dict[str, list[str]] = {}
        comps_conn = net_resp.get("components") if isinstance(net_resp, dict) else None
        for c in comps_conn or []:
            ref = str(c.get("designator", "")).strip()
            if not ref:
                continue
            for pin in c.get("pins") or []:
                net = str(pin.get("net", "")).strip()
                if not net or net.upper() in exclude:
                    continue
                members = net_members.setdefault(net, [])
                if ref not in members:
                    members.append(ref)

        place_nets: list[PlaceNet] = []
        for net, members in net_members.items():
            if len(members) < 2:
                continue
            if max_net_fanout and len(members) > max_net_fanout:
                continue
            place_nets.append(
                PlaceNet(tuple(members), name=net, weight=_net_weight(net))
            )

        # Pin geometry: one board-wide pad query, then a spatial join (pad
        # center -> smallest containing component bbox) + back-rotation to
        # recover rotation-0 local offsets. Needed for rotation
        # optimization AND -- crucially -- to derive the net graph when
        # there is no compiled schematic netlist (a PCB-only / synced-
        # placement board, where connectivity lives on the pads, not in a
        # schematic). Only top-side, orthogonally-placed parts are made
        # rotatable.
        pin_count = 0
        netgraph_from_pads = False
        if optimize_rotation or not net_members:
            pad_resp = await bridge.send_command_async(
                "generic.query_objects",
                {"object_type": "ePadObject", "properties": "X,Y,Net",
                 "scope": "active_doc", "filter": ""},
                timeout=120.0,
            )
            pads = pad_resp.get("objects") if isinstance(pad_resp, dict) else None
            bbox_list = [(ref, geom[ref]["bbox"]) for ref in geom]
            pins_by_ref: dict[str, list[PlacePin]] = {}
            pad_net_members: dict[str, list[str]] = {}
            for pad in pads or []:
                try:
                    px = float(pad.get("X"))
                    py = float(pad.get("Y"))
                except (TypeError, ValueError):
                    continue
                net = str(pad.get("Net", "")).strip()
                if not net or net.upper() in exclude:
                    continue
                owner = None
                owner_area = None
                for ref, (bx1, by1, bx2, by2) in bbox_list:
                    if bx1 <= px <= bx2 and by1 <= py <= by2:
                        area = (bx2 - bx1) * (by2 - by1)
                        if owner_area is None or area < owner_area:
                            owner_area = area
                            owner = ref
                if owner is None:
                    continue
                g = geom[owner]
                lx, ly = rotate_offset(px - g["cx"], py - g["cy"], -g["rot"])
                pins_by_ref.setdefault(owner, []).append(PlacePin(lx, ly, net))
                m = pad_net_members.setdefault(net, [])
                if owner not in m:
                    m.append(owner)
            if optimize_rotation:
                for ref, pins in pins_by_ref.items():
                    pc = comp_by_ref[ref]
                    pc.pins = tuple(pins)
                    pc.rotatable = (
                        pc.layer.lower().startswith("top")
                        and _is_orthogonal(geom[ref]["rot"])
                    )
                    pin_count += len(pins)
            # No schematic netlist -> build the net graph from PCB pad nets
            # so the spring placement (and rotation) actually optimize.
            if not net_members and pad_net_members:
                net_members = pad_net_members
                netgraph_from_pads = True
                place_nets = []
                for net, members in net_members.items():
                    if len(members) < 2:
                        continue
                    if max_net_fanout and len(members) > max_net_fanout:
                        continue
                    place_nets.append(
                        PlaceNet(tuple(members), name=net, weight=_net_weight(net))
                    )

        region_obj = BoardRegion(
            region_used["x1"], region_used["y1"],
            region_used["x2"], region_used["y2"],
        )

        engine_norm = str(engine or "refine").strip().lower()
        if engine_norm not in ("refine", "construct"):
            return {
                "error": "BAD_ENGINE",
                "reason": "engine must be 'refine' or 'construct'",
            }

        # Seed positions / rotations of the input, for before-metrics.
        in_pos = {ref: (g["cx"], g["cy"]) for ref, g in geom.items()}
        in_rot = {ref: g["rot"] for ref, g in geom.items()}

        if engine_norm == "construct":
            # From-scratch placement core (sizes, seeds, legalizes, polishes
            # a full multi-term objective). Imported lazily so the tool
            # module stays cheap to import.
            from ..design import pcb_placement as _construct

            rules = _construct.DesignRules(
                grid=float(grid_mils),
                component_clr=float(clearance_mils),
            )
            # Auto-group each crystal/resonator with its two load caps so the
            # keep-together term clusters the oscillator tight at the MCU's
            # crystal pins (critical for short, symmetric, low-noise traces).
            # Structural + naming-agnostic; an explicit planner match_group
            # always wins.
            for ref, grp in _construct._infer_crystal_groups(
                place_comps, place_nets
            ).items():
                pc = comp_by_ref.get(ref)
                if pc is not None and not getattr(pc, "match_group", ""):
                    pc.match_group = grp
            # Auto-group a switching regulator's switch-node parts (inductor +
            # catch diode / sync FET + bootstrap cap) so keep-together keeps the
            # high-di/dt loop compact -- the dominant EMI rule for any
            # buck/boost. Structural; an explicit planner match_group wins.
            for ref, grp in _construct._infer_switch_node_groups(
                place_comps, place_nets
            ).items():
                pc = comp_by_ref.get(ref)
                if pc is not None and not getattr(pc, "match_group", ""):
                    pc.match_group = grp
            cons_opts = _construct.ConstructOptions()
            n_restarts = max(1, int(restarts))
            if n_restarts > 1:
                # Several seeded restarts; keep the lowest-objective legal one.
                cres = _construct.construct_placement_best_of(
                    place_comps, place_nets, rules,
                    seeds=tuple(range(n_restarts)), base_opts=cons_opts,
                )
            else:
                cres = _construct.construct_placement(
                    place_comps, place_nets, rules, cons_opts
                )
            # Visual repair: tighten any keep-together cluster (crystal + load
            # caps, matched pair) the analytic objective left scattered. Reads
            # the perceptual compactness metric and relocates the cluster tight
            # against the IC it serves, gated to never regress the combined
            # analytic-plus-visual objective. A no-op when nothing is scattered.
            cres = _construct.tighten_match_clusters(
                place_comps, place_nets, rules, cres)
            # The construct engine sizes (and tightens) its own board; surface
            # that as the recommended outline -- the "best PCB size" answer.
            suggested_board = {
                "x1": round(cres.region.x1, 1), "y1": round(cres.region.y1, 1),
                "x2": round(cres.region.x2, 1), "y2": round(cres.region.y2, 1),
                "width": round(cres.region.width, 1),
                "height": round(cres.region.height, 1),
            }
            result_positions = {r: (c[0], c[1]) for r, c in cres.centroids.items()}
            result_rotations = dict(cres.rotations)
            result_rotated = {
                r: result_rotations[r]
                for r in result_rotations
                if abs(result_rotations.get(r, 0.0) - in_rot.get(r, 0.0)) > 1e-6
            }
            hpwl_before = hpwl(in_pos, place_nets)
            hpwl_after = hpwl(result_positions, place_nets)
            overlap_before = overlap_pair_count(
                place_comps, in_pos, float(clearance_mils), in_rot
            )
            overlap_after = overlap_pair_count(
                place_comps, result_positions, float(clearance_mils),
                result_rotations,
            )
            solver_notes = list(cres.notes)
        else:
            # The refine engine nudges the board's CURRENT positions inside the
            # given outline; it does not propose a new board size.
            suggested_board = None
            options = PlaceOptions(
                iterations=max(0, int(iterations)),
                grid_mils=float(grid_mils),
                clearance_mils=float(clearance_mils),
                reseed_grid=bool(reseed_grid),
                optimize_rotation=bool(optimize_rotation),
            )
            result = plan_placement(place_comps, place_nets, region_obj, options)
            result_positions = dict(result.positions)
            result_rotations = dict(result.rotations)
            result_rotated = dict(result.rotated)
            hpwl_before = result.hpwl_before
            hpwl_after = result.hpwl_after
            overlap_before = result.overlap_pairs_before
            overlap_after = result.overlap_pairs_after
            solver_notes = list(result.notes)

        # Full per-term objective report on the proposed layout. Computed
        # for both engines from the same pure-Python scorer so the caller
        # always sees the trade-off, not just a single HPWL number.
        objective_report = _build_objective_report(
            place_comps, result_positions, result_rotations,
            place_nets, region_obj, float(grid_mils), float(clearance_mils),
        )

        # Per-net wirelength diagnostic: the longest nets are the routing
        # risk, and the candidates the caller may want to mark critical and
        # re-place. Also echoes the achieved span of any flagged critical net.
        net_length_report = _build_net_length_report(
            place_comps, result_positions, result_rotations,
            place_nets, critical,
        )

        # Structural decoupling analysis: which cap decouples which IC and how
        # close it landed -- confirms decaps sit tight against their ICs.
        decoupling = _build_decoupling_report(
            place_comps, result_positions, result_rotations, place_nets,
        )

        # Ratsnest crossings: a routability / via-pressure indicator. The
        # signal figure excludes high-fanout rails (planes/pours carry no
        # signal via); the total is the conservative all-net count.
        ratsnest = _build_ratsnest_report(
            place_comps, result_positions, result_rotations, place_nets,
        )

        # Convert each solved (centroid, rotation) back to an Altium move.
        # Altium sets the origin (Comp.x/y) and rotates the body about it,
        # so new_origin = target_centroid - R(newRot) * C0, where C0 is
        # the centroid's offset from the origin at rotation 0. Emit a move
        # when the part shifted past half the snap grid OR was re-oriented.
        threshold = max(1.0, float(grid_mils) / 2.0)
        moves: list[dict[str, Any]] = []
        for ref, (ncx, ncy) in result_positions.items():
            comp = comp_by_ref.get(ref)
            if comp is None or comp.fixed:
                continue
            g = geom[ref]
            new_rot = float(result_rotations.get(ref, g["rot"]))
            rotated = ref in result_rotated
            c0x, c0y = g["c0"]
            r0x, r0y = rotate_offset(c0x, c0y, new_rot)
            new_ox = int(round(ncx - r0x))
            new_oy = int(round(ncy - r0y))
            old_ox = int(round(g["ox"]))
            old_oy = int(round(g["oy"]))
            moved_xy = (abs(new_ox - old_ox) >= threshold
                        or abs(new_oy - old_oy) >= threshold)
            if not moved_xy and not rotated:
                continue
            moves.append({
                "designator": ref,
                "from": {"x": old_ox, "y": old_oy, "rotation": g["rot"]},
                "to": {"x": new_ox, "y": new_oy,
                       "rotation": new_rot if rotated else None},
            })

        improvement = (
            round((hpwl_before - hpwl_after) / hpwl_before * 100.0, 2)
            if hpwl_before > 0 else 0.0
        )
        movable_count = sum(1 for c in place_comps if not c.fixed)
        rotated_count = sum(1 for m in moves if m["to"]["rotation"] is not None)
        summary: dict[str, Any] = {
            "dry_run": True,
            "engine": engine_norm,
            "component_count": len(place_comps),
            "movable_count": movable_count,
            "fixed_count": len(place_comps) - movable_count,
            "net_count": len(place_nets),
            "net_graph_source": "pcb_pads" if netgraph_from_pads else "schematic",
            "pin_count": pin_count,
            "hpwl_before": round(hpwl_before, 1),
            "hpwl_after": round(hpwl_after, 1),
            "hpwl_improvement_pct": improvement,
            "overlap_pairs_before": overlap_before,
            "overlap_pairs_after": overlap_after,
            "summary": _build_placement_summary(
                objective_report, ratsnest, decoupling, suggested_board),
            "objective_report": objective_report,
            "net_length_report": net_length_report,
            "ratsnest": ratsnest,
            "decoupling_report": decoupling,
            "suggested_board": suggested_board,
            "moved_count": len(moves),
            "rotated_count": rotated_count,
            "moves": moves,
            "region": region_used,
            "notes": solver_notes,
        }
        if auto_constraints:
            summary["auto_constraints"] = auto_constraints

        if apply and moves:
            # Pack as designator,x,y,rotation (empty rotation field leaves
            # the orientation unchanged).
            ops = []
            for m in moves:
                rot = m["to"]["rotation"]
                rot_str = "" if rot is None else str(rot)
                ops.append(
                    f"{m['designator']},{m['to']['x']},{m['to']['y']},{rot_str}"
                )
            apply_result = await bridge.send_command_async(
                "pcb.batch_move_components",
                {"moves": "|".join(ops)},
            )
            summary["dry_run"] = False
            summary["apply_result"] = apply_result
        elif apply and not moves:
            summary["apply_result"] = {"moves_applied": 0,
                                       "reason": "no moves to apply"}

        if render_png:
            try:
                from pathlib import Path
                from ..design.illustrate import placement_png
                out = Path(render_png)
                out.parent.mkdir(parents=True, exist_ok=True)
                title = (f"PCB placement ({engine_norm})  "
                         f"HPWL {objective_report.get('hpwl', 0.0):.0f}  "
                         f"legal={objective_report.get('legal')}")
                placement_png(place_comps, result_positions, region_obj,
                              place_nets, str(out), title=title,
                              rotations=result_rotations)
                summary["preview_png"] = str(out)
            except Exception as exc:  # rendering must never break the move data
                summary["preview_error"] = str(exc)

        return summary

    @mcp.tool()
    async def pcb_copy_component_placement(
        mapping: dict[str, str],
        include_designator: bool = True,
        include_comment: bool = True,
    ) -> dict[str, Any]:
        """Clone placement from source components onto destination components.

        Copies layer, X, Y and rotation, and optionally the designator
        and comment text placement. For repeated channels: lay out one,
        then map it onto the next, e.g. ``{"R1": "R11", "U1": "U2"}``.

        Args:
            mapping: ``{source_designator: dest_designator}``. Each
                source must already be placed somewhere; each dest gets
                overwritten with the source's placement.
            include_designator: Also copy designator-text placement
                (offset, rotation, size, layer, visibility). Default
                True.
            include_comment: Also copy comment-text placement. Default
                True.

        Returns:
            Dict with:
              - ``applied``: pairs that succeeded
              - ``failed``: pairs that failed (src/dst missing or apply
                exception)
              - ``items``: per-pair ``{src, dst, ok, error}``
        """
        if not mapping:
            return {"applied": 0, "failed": 0, "items": [],
                    "error": "mapping is empty"}
        pairs = "|".join(f"{s}={d}" for s, d in mapping.items())
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.copy_component_placement",
            {
                "mapping": pairs,
                "include_designator": "true" if include_designator else "false",
                "include_comment": "true" if include_comment else "false",
            },
        )

    @mcp.tool()
    async def pcb_replicate_layout(
        mapping: dict[str, str],
        nets: Optional[list[str]] = None,
        move_components: bool = False,
    ) -> dict[str, Any]:
        """Copy one channel's routing onto a matching channel.

        Copies the source group's tracks, arcs, vias, polygons, regions
        and fills onto the destination group, remapping each net to the
        matching destination net. One rigid transform comes from the
        FIRST mapping pair. Only nets internal to the source group are
        copied (every pad on the net belongs to a mapped part), so shared
        GND or power nets are left alone; ``nets`` overrides that.

        The destination parts must already sit like the source (run
        ``pcb_copy_component_placement`` first, or pass
        ``move_components=True``); ``congruence_warnings`` counts those
        that don't.

        Args:
            mapping: ``{source_designator: dest_designator}``; include
                every part in the channel.
            nets: Source net names to copy instead of the internal ones.
            move_components: Also move the destination parts onto the
                transform (default False).

        Returns:
            ``copied``, ``net_assigned``, ``internal_nets``,
            ``shared_nets_skipped``, ``congruence_warnings``, ``notes``.
        """
        if not mapping:
            return {"copied": 0, "error": "mapping is empty"}
        pairs = "|".join(f"{s}={d}" for s, d in mapping.items())
        args = {"mapping": pairs}
        if nets:
            args["nets"] = "|".join(nets)
        if move_components:
            args["move_components"] = "true"
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.replicate_layout", args)

    @mcp.tool()
    async def pcb_filter_variant_components(
        variant_name: str,
        select: str = "not_fitted",
    ) -> dict[str, Any]:
        """Select a variant's components of one fitted-class on the board.

        Classifies every component under ``variant_name`` (fitted original /
        alternate / not fitted) and selects exactly the chosen class on the
        active PCB, deselecting the rest -- so, e.g., the not-fitted parts of a
        variant stand out for review or for building a component class. The
        agent-callable equivalent of the community VariantFilter script;
        selection uses the deterministic component API, not a query process.

        Args:
            variant_name: The project variant to classify against.
            select: Which class to select -- ``not_fitted`` (default),
                ``fitted_original``, ``alternate``, or ``all_fitted``
                (fitted_original + alternate).

        An unrecognised ``select`` is REJECTED rather than guessed. The
        handler's If chain falls through to not-fitted for any word it
        does not know, and the reply echoes back the word you sent, so a
        typo would select the opposite class and report success.

        Returns:
            {"variant", "select", "matched", "designators"}, or
            ``{"ok": False, "reason": ...}`` if ``select`` is not one of
            the four classes, in which case nothing is sent or selected.
        """
        if select not in FILTER_VARIANT_SELECT:
            return {
                "ok": False,
                "reason": (
                    f"select must be one of "
                    f"{', '.join(FILTER_VARIANT_SELECT)}, not "
                    f"{select!r}. Unknown values are not rejected by the "
                    "board handler: they fall through to not_fitted, and "
                    "the reply echoes the word you sent, so a typo would "
                    "select the opposite class and look like it worked."
                ),
            }
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.filter_variant_components",
            {"variant_name": variant_name, "select": select},
        )

    @mcp.tool()
    async def pcb_renumber_pads(
        order: str = "lr_tb",
        start: int = 1,
        increment: int = 1,
        prefix: str = "",
    ) -> dict[str, Any]:
        """Renumber the current PcbLib footprint's pads in spatial order.

        The non-interactive form of the community RenumberPads tool: instead
        of clicking each pad in order, the footprint's pads are sorted by
        position and assigned sequential designators. Rows/columns are banded
        by a small tolerance so a grid numbers cleanly. Operates on the active
        PCB library's current footprint.

        Args:
            order: ``lr_tb`` (default) numbers rows top-to-bottom,
                left-to-right within a row; ``tb_lr`` numbers columns
                left-to-right, top-to-bottom within a column.
            start: First designator number (default 1).
            increment: Step between successive pads (default 1).
            prefix: Optional string prefixed to each number (e.g. ``A`` ->
                ``A1``, ``A2``).

        Returns:
            {"renumbered", "order", "mapping": [{old, new}, ...]} or an error.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.renumber_pads",
            {
                "order": order,
                "start": str(start),
                "increment": str(increment),
                "prefix": prefix,
            },
        )

    @mcp.tool()
    async def pcb_copy_tracks_radial(
        center_x: int,
        center_y: int,
        count: int,
        angle_step: Optional[float] = None,
    ) -> dict[str, Any]:
        """Array the selected tracks/arcs/vias radially about a center point.

        Replicates the current selection ``count - 1`` more times, each rotated
        a further ``angle_step`` degrees about ``(center_x, center_y)`` -- a
        circular/radial copy. Reuses the same verified Replicate +
        RotateAroundXY transform as ``pcb_replicate_layout``. Copies are added
        unselected so the source set stays put.

        Args:
            center_x: Rotation-center X in mils.
            center_y: Rotation-center Y in mils.
            count: Total instances including the original (>= 2).
            angle_step: Degrees between instances. Defaults to ``360 / count``
                (a full even ring).

        Returns:
            {"copied", "count", "angle_step"} or an error.
        """
        bridge = get_bridge()
        args: dict[str, Any] = {
            "center_x": str(center_x),
            "center_y": str(center_y),
            "count": str(count),
        }
        if angle_step is not None:
            args["angle_step"] = str(angle_step)
        return await bridge.send_command_async("pcb.copy_tracks_radial", args)

    @mcp.tool()
    async def pcb_scale(
        ratio: float,
        anchor: str = "selection_center",
    ) -> dict[str, Any]:
        """Scale the selected free primitives by a ratio about an anchor.

        Each coordinate maps ``P' = anchor + ratio*(P - anchor)`` and sizes
        scale by ``ratio``. Handles free tracks, arcs, vias, pads, fills and
        text. Primitives inside a component, dimension, or polygon are skipped
        (as are polygons/regions) -- so this scales free copper and artwork,
        not footprints. Grounded in the community PCBScale tool.

        Args:
            ratio: Scale factor (> 0). ``0.95`` shrinks 5%, ``1.05`` grows 5%.
            anchor: ``selection_center`` (default), ``board_center``, or
                ``origin``.

        Returns:
            {"scaled", "skipped", "ratio", "anchor_x", "anchor_y"} or an error.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.scale", {"ratio": str(ratio), "anchor": anchor}
        )

    @mcp.tool()
    async def pcb_save_copy_as(
        target_path: str,
        source_path: str = "",
        backup: bool = True,
    ) -> dict[str, Any]:
        """Write the open board to another path, as File > Save Copy As.

        The target gets the board as it is in Altium, unsaved edits
        included; the open document keeps its path, project and modified
        state. An existing target is overwritten, after a copy to
        ``<target>.bak`` with ``backup`` (default); a target open in
        Altium is refused. The copy joins no project.

        Args:
            target_path: Full path of the .PcbDoc to write.
            source_path: The open board to copy. Empty uses the focused
                board, or the only one open; several open with none
                focused is refused rather than guessed.
            backup: Keep the overwritten target as ``<target>.bak``.

        Returns:
            {"source", "target", "target_existed", "written",
            "open_board_path", "backup"} or an error. ``written`` is read
            from the target's file time, not assumed.
        """
        import shutil
        from pathlib import Path

        bridge = get_bridge()
        params = {"target_path": target_path}
        if source_path:
            params["board_path"] = source_path
        check = await bridge.send_command_async(
            "pcb.save_copy_as", {**params, "check_only": "true"})
        if not isinstance(check, dict) or "target_exists" not in check:
            return check
        backup_path = ""
        if backup and check.get("target_exists"):
            backup_path = target_path + ".bak"
            try:
                shutil.copy2(target_path, backup_path)
            except OSError as e:
                return {"success": False, "written": False,
                        "error": f"could not keep a backup at {backup_path}: {e}. "
                                 "Nothing was written; pass backup=False to "
                                 "overwrite without one."}
        # Altium will not write into a folder that does not exist, and said
        # only written:false. The folder is made, and the reply says so.
        folder = Path(target_path).parent
        created_folder = ""
        if not folder.is_dir():
            try:
                folder.mkdir(parents=True)
                created_folder = str(folder)
            except OSError as e:
                return {"success": False, "written": False,
                        "error": f"the folder {folder} does not exist and "
                                 f"could not be made: {e}. Nothing was written."}
        result = await bridge.send_command_async("pcb.save_copy_as", params)
        if isinstance(result, dict):
            result["backup"] = backup_path
            if backup_path and not Path(backup_path).is_file():
                result["backup"] = ""
            if created_folder:
                result["created_folder"] = created_folder
        return result

    @mcp.tool()
    async def pcb_apply_geometry_map(
        map_path: str,
        board_path: str,
        tolerance_mil: float = 0.01,
        angle_tolerance_deg: float = 1e-4,
        dry_run: bool = False,
        repour: bool = True,
        region_shape: str = "rebuild",
    ) -> dict[str, Any]:
        """Move and reshape thousands of free primitives in ONE pass, from a
        JSON map of each object's CURRENT geometry and its new one.

        Use it past a few hundred objects, where obj_batch_modify is slow.
        Each entry is matched to exactly one object within the tolerance;
        none, several, or one object named twice is reported, never
        guessed, and an object changed since the dump is left alone. Free
        primitives only (not in a component, pour or dimension): move
        components with pcb_move_components.

        The map (mils, absolute board coordinates, not origin-relative)::

            {"tracks":   [{"layer", "width", "key": [x1,y1,x2,y2],
                           "new": [x1,y1,x2,y2], "new_width"?}],
             "arcs":     [{"layer", "width", "key": [cx,cy,r,start,end],
                           "new": [cx,cy,r,start,end], "new_width"?}],
             "vias":     [{"key": [x,y], "new": [x,y]}],
             "texts":    [{"layer", "key": [x,y,text], "new": [x,y,text?]}],
             "fills":    [{"layer", "key": [x1,y1,x2,y2], "new": [...]}],
             "regions":  [{"layer", "key": {"n", "first": [x,y], "holes"},
                           "contour": [[x,y],...], "holes": [[[x,y],...],...]}],
             "polygons": [{"layer", "key_first": [vx,vy], "segments": [seg]}],
             "board_outline": [seg] or {"segments": [seg]},
             "delete":   [{"kind": "track"|"arc", "layer", "width", "key"}
                          | {"kind": "region", "layer", "key": {"n", "first", "holes"}}],
             "create":   [{"kind": "track"|"arc", "layer", "width",
                           "geom": [x1,y1,x2,y2] | [cx,cy,r,start,end],
                           "net"?, "keepout"? (default true on KeepOutLayer)}
                          | {"kind": "region", "layer", "contour": [[x,y],...],
                           "net"?, "teardrop"?, "keepout"?}
                          | {"kind": "via", "x", "y", "size", "hole", "net"?}
                          | {"kind": "polygon", "layer", "contour": [[x,y],...],
                           "net"?, "name"?, "order"?, "pour_over"? (true)}]}

        A seg is {"kind": 0, "vx", "vy"} (line) or {"kind": 1, "vx", "vy",
        "cx", "cy", "r", "sa", "ea"} (arc). Track ends match in either
        order. A region keeps its hole count and each hole its vertex
        count. The outline is replaced whole. Polygons match by layer and
        first vertex. A repour also deletes free regions lying in the pour,
        teardrops included, so create those after the last repour. ``components`` entries
        are counted and ignored. A delete is matched like a move (an
        object both moved and deleted is refused). Identical objects need
        one identical entry per copy; fewer entries than copies is
        ambiguous and deletes none. Creates are free, on
        the layer named, each with an optional ``net``; a net the board
        lacks creates nothing and is listed in ``apply.create_refused``
        with the map ``entry``. A via is a through via (TopLayer to
        BottomLayer). A polygon pour is made but NOT poured: pour many
        with pcb_repour_polygons afterwards (small ones first); ``order``
        sets its pour index (``pour_order_off`` counts any that did not
        take). Copper fills that are rotated or not rectangular are best
        sent as regions. A created region takes, with ``teardrop``,
        Altium's teardrop flag. THIS IS THE BULK COPPER CREATE: thousands of
        tracks, vias, regions and pours from one file, in one transaction,
        instead of sending them inline. A value past +/-214,748 mil (an arc's
        centre plus radius included) stops the whole apply before anything
        is sent, since Altium's coordinates cannot hold it; ``out_of_range``
        counts them per kind. Draw a near-straight arc as a line.

        Args:
            map_path: The JSON map.
            board_path: The .PcbDoc to change (required; refused unless
                that file is the board Altium opens).
            tolerance_mil: Allowed distance per coordinate and width.
            angle_tolerance_deg: The same for arc angles, modulo 360.
            dry_run: Dump and match only. Run this first.
            repour: Repour each reshaped polygon. False leaves pours for
                pcb_repour_polygons (small ones first, big hatched once).
            region_shape: For regions that carry shape segments (what
                Altium draws): "rebuild" (default) rewrites them from the
                new outline; "clear" drops them; "keep" leaves the OLD
                shape on screen.

        Returns:
            {"board", "dry_run", "match": {kind: {entries, matched,
            unmatched, ambiguous, refused, samples?}}, "apply": {applied,
            stale, missing, region_readback_off, track_arc_readback_off,
            region_bbox_off, region_shapes_changed, deleted, created,
            create_failed, create_readback_off, teardrops_created,
            by_kind}}. Any nonzero ``*_off`` means something did not read
            back as written (a track's or arc's ends, radius or width
            included); ``by_kind.O.open`` 1 means the
            outline's closing vertex did not read back on its first. A dry run keyed on the new
            geometry shows what landed.
        """
        import codecs
        import locale
        from pathlib import Path

        from ..atomicfile import replace_with_retry
        from ..geometry_map import build_edits, parse_dump

        try:
            geometry_map = json.loads(Path(map_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return {"success": False, "error": f"could not read the map: {e}"}
        if not isinstance(geometry_map, dict):
            return {"success": False, "error": "the map must be a JSON object"}

        bridge = get_bridge()
        workspace = Path(bridge.config.workspace_dir)
        dump_path = workspace / "geometry_dump.tsv"
        dumped = await bridge.send_command_async(
            "pcb.dump_free_primitives",
            {"out_path": str(dump_path), "board_path": board_path},
            timeout=_GEOMETRY_MAP_TIMEOUT)
        if not isinstance(dumped, dict) or "tracks" not in dumped:
            return dumped
        # TStringList.SaveToFile writes the ANSI code page.
        dump = parse_dump(dump_path.read_text(
            encoding=locale.getpreferredencoding(False), errors="replace"))

        lines, match = build_edits(geometry_map, dump, tolerance_mil,
                                   angle_tolerance_deg)
        result: dict[str, Any] = {"board": dumped.get("board", ""),
                                  "dry_run": dry_run, "dumped": dumped,
                                  "match": match}
        if dry_run or not lines:
            return result
        # One value Altium cannot hold means the map is wrong somewhere, and
        # applying the rest can leave a board half changed: the deletes of
        # an outline whose replacement was refused.
        out_of_range = {kind: rep["out_of_range"] for kind, rep in match.items()
                        if isinstance(rep, dict) and rep.get("out_of_range")}
        if out_of_range:
            result["success"] = False
            result["error"] = (
                "nothing applied: the map holds values outside Altium's "
                "coordinate range (+/-214,748 mil), listed in match[kind]."
                "samples. Fix them (draw a near-straight arc as a line) and "
                "run again.")
            result["out_of_range"] = out_of_range
            return result

        edits_path = workspace / "geometry_edits.tsv"
        tmp = edits_path.with_suffix(".tmp")
        # The mark is what makes LoadFromStream read UTF-8, for a new text.
        tmp.write_bytes(codecs.BOM_UTF8 + ("\n".join(lines) + "\n").encode("utf-8"))
        replace_with_retry(str(tmp), edits_path)
        apply_params = {"in_path": str(edits_path), "board_path": board_path,
                        "region_shape": region_shape}
        if not repour:
            apply_params["repour"] = "false"
        result["apply"] = await bridge.send_command_async(
            "pcb.apply_free_primitives", apply_params,
            timeout=_GEOMETRY_MAP_TIMEOUT)
        # Each refused create named by its entry in the map, not its line.
        order = (match.get("create") or {}).get("line_entries") or []
        applied = result["apply"]
        if isinstance(applied, dict) and applied.get("create_refused"):
            for item in applied["create_refused"]:
                n = item.get("create")
                if isinstance(n, int) and 0 <= n < len(order):
                    item["entry"] = order[n]
        return result

    @mcp.tool()
    async def pcb_place_stitching_vias(
        net: str,
        x1_mils: float = 0,
        y1_mils: float = 0,
        x2_mils: float = 0,
        y2_mils: float = 0,
        spacing_mils: float = 50,
        via_size_mils: float = 30,
        via_hole_mils: float = 14,
        clearance_mils: float = 10,
        dry_run: bool = True,
        within_board: bool = True,
        edge_clearance_mils: int = 30,
        avoid_parts: bool = True,
    ) -> dict[str, Any]:
        """Place a grid of stitching vias on a named net.

        The grid covers the rectangle, or the whole board when no
        rectangle is given. With ``within_board`` (default) only grid
        points inside the board outline, at least ``edge_clearance_mils``
        from its edge, are tried, so a round or flanged board gets vias
        only on the board. A point is skipped when any pad or via (any
        net: no via in a pad), a part's 3D body (``avoid_parts``), or a
        track, arc or keep-out of another net lies within
        ``via_size_mils/2 + clearance_mils``; the rest get a through via
        on the net. Dry run by default: check ``placed`` and
        ``skipped``, then call again with ``dry_run=False``.

        Args:
            net: Target net (must already exist on the board).
            x1_mils, y1_mils, x2_mils, y2_mils: Inclusive rectangle for
                the grid; all zero (default) uses the board's extent.
            spacing_mils: Grid spacing (default 50).
            via_size_mils: Via pad diameter (default 30).
            via_hole_mils: Via drill diameter (default 14).
            clearance_mils: Min gap to a blocking primitive (default 10).
            dry_run: When True (default), only count would-be
                placements without mutating the board.
            within_board: Keep to the board outline (default True).
            edge_clearance_mils: Minimum distance from a via centre to
                the board edge when ``within_board`` (default 30).
            avoid_parts: Keep out from under every part's 3D body
                (default True): a board-wide stitch put vias under the
                USB-C and debug connectors. False stitches under bodies
                too, as under a QFN's thermal area.

        Returns:
            Dict with ``{net, dry_run, placed, skipped, spacing_mils,
            clearance_mils}``, plus ``outside_board`` (grid points left out).
        """
        bridge = get_bridge()
        params = {
            "net": net,
            "x1_mils": _mils(x1_mils),
            "y1_mils": _mils(y1_mils),
            "x2_mils": _mils(x2_mils),
            "y2_mils": _mils(y2_mils),
            "spacing_mils": _mils(spacing_mils),
            "via_size_mils": _mils(via_size_mils),
            "via_hole_mils": _mils(via_hole_mils),
            "clearance_mils": _mils(clearance_mils),
            "dry_run": "true" if dry_run else "false",
            "avoid_parts": "1" if avoid_parts else "0",
        }
        no_rect = not any((x1_mils, y1_mils, x2_mils, y2_mils))
        outside = 0
        if within_board or no_rect:
            outline = await bridge.send_command_async("pcb.get_board_outline", {})
            ring = _outline_ring(outline)
            if not ring:
                return {"success": False, "error": "the board outline could not be read",
                        "outline": outline}
            if no_rect:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                x1_mils, y1_mils, x2_mils, y2_mils = min(xs), min(ys), max(xs), max(ys)
            grid = _grid_points(x1_mils, y1_mils, x2_mils, y2_mils, spacing_mils)
            inside = ([point for point in grid
                       if _inside_ring(point, ring, edge_clearance_mils)]
                      if within_board else grid)
            outside = len(grid) - len(inside)
            if not inside:
                return {"net": net, "dry_run": dry_run, "placed": 0,
                        "skipped": 0, "outside_board": outside,
                        "note": "no grid point lies inside the board"}
            params["points"] = ";".join(
                f"{_mils(x)},{_mils(y)}" for x, y in inside)
        result = await bridge.send_command_async(
            "pcb.place_stitching_vias", params, timeout=120.0)
        if isinstance(result, dict):
            result["outside_board"] = outside
        return result

    @mcp.tool()
    async def pcb_calc_impedance(
        geometry: str,
        width_mils: float,
        dielectric_height_mils: float,
        dielectric_constant: float = 4.2,
        copper_oz: float = 1.0,
        spacing_mils: float = 0.0,
    ) -> dict[str, Any]:
        """Characteristic impedance of a PCB trace (IPC-2141 microstrip and
        stripline, Wadell coupling for pairs). Pure math, about +/-10%:
        fine for choosing widths; the fab's field solver has the final
        word. Read real heights and Er with pcb_get_layer_stackup first
        rather than assuming FR-4.

        Args:
            geometry: "microstrip", "microstrip_diff", "stripline" or
                "stripline_diff".
            width_mils: Track width; for a pair, each conductor's.
            dielectric_height_mils: Microstrip: trace to plane below.
                Stripline: total between the two planes.
            dielectric_constant: Er (default 4.2, FR-4).
            copper_oz: Copper weight; 1 oz = 1.378 mil thick (default 1).
            spacing_mils: Edge-to-edge gap of a pair.

        Returns:
            Inputs echoed, ``thickness_mils``, ``z0_ohms``, ``zdiff_ohms``
            (pairs) and ``propagation_delay_ps_per_inch``.
        """
        import math
        geometry = geometry.strip().lower()
        valid = ("microstrip", "microstrip_diff",
                 "stripline", "stripline_diff")
        if geometry not in valid:
            return {"ok": False,
                    "reason": "geometry must be one of " + ", ".join(valid)}
        if width_mils <= 0 or dielectric_height_mils <= 0:
            return {"ok": False,
                    "reason": "width_mils and dielectric_height_mils must be > 0"}
        if dielectric_constant <= 0:
            return {"ok": False,
                    "reason": "dielectric_constant must be > 0"}
        is_diff = geometry.endswith("_diff")
        if is_diff and spacing_mils <= 0:
            return {"ok": False,
                    "reason": "spacing_mils must be > 0 for differential geometries"}

        # The two forward formulas live in design/impedance_sizing.py,
        # where trace_width_for_impedance already inverts them. They
        # were inlined here as well, character for character, so the
        # IPC-2141 constants were stated twice with nothing enforcing
        # agreement: the same defect as the mils-to-mm factor in task
        # #43, and the reason calc.py can now offer this tool without
        # becoming a third copy.
        from ..design.impedance_sizing import z0_microstrip, z0_stripline
        from ..units import OZ_TO_MILS

        w = float(width_mils)
        h = float(dielectric_height_mils)
        er = float(dielectric_constant)
        t = copper_oz * OZ_TO_MILS          # copper thickness, mils

        if geometry.startswith("microstrip"):
            z0 = z0_microstrip(w, h, er, copper_oz=copper_oz)
            er_eff = (er + 1.0) / 2.0
        else:
            # Symmetric stripline (trace centered between two planes,
            # h is the FULL dielectric thickness between planes).
            z0 = z0_stripline(w, h, er, copper_oz=copper_oz)
            er_eff = er

        # The same validity check the other copy of this tool applies.
        #
        # Shared rather than restated for the reason the constants above
        # are shared: this tool exists twice, here for Altium and in
        # tools/calc.py for KiCad and EasyEDA. Guarding only one of them
        # left this one still returning a NEGATIVE impedance as a
        # success, which is precisely the drift the comment above warns
        # about.
        from ..design.impedance_sizing import impedance_validity

        checked = impedance_validity(z0, w, h, er)
        if not checked["usable"]:
            return {
                "ok": False,
                "reason": checked["reason"],
                "geometry": geometry,
                "width_mils": w,
                "dielectric_height_mils": h,
                "width_to_height_ratio": checked["width_to_height_ratio"],
            }

        # Propagation delay: c0 = 11.8 in/ns in vacuum;
        # tpd = sqrt(er_eff) / c0 = sqrt(er_eff) * 1000 / 11.8 ps/in
        tpd = math.sqrt(er_eff) * 1000.0 / 11.8

        out: dict[str, Any] = {
            "ok": True,
            "geometry": geometry,
            "width_mils": w,
            "dielectric_height_mils": h,
            "dielectric_constant": er,
            "thickness_mils": round(t, 3),
            "z0_ohms": round(z0, 1),
            "propagation_delay_ps_per_inch": round(tpd, 2),
            "width_to_height_ratio": checked["width_to_height_ratio"],
        }
        if checked["outside_validity_range"]:
            out["outside_validity_range"] = True
            out["accuracy_warning"] = checked["warning"]
        if is_diff:
            # Same reasoning as the Z0 formulas above: the coupling
            # factor was stated here AND in impedance_sizing, where the
            # inverse solver uses it. Two copies of a Wadell
            # approximation is two chances to edit one of them.
            from ..design.impedance_sizing import diff_coupling_factor

            s = float(spacing_mils)
            out["spacing_mils"] = s
            out["zdiff_ohms"] = round(
                2.0 * z0 * diff_coupling_factor(geometry, s, h), 1)
        return out

    @mcp.tool()
    async def pcb_calc_trace_width_for_impedance(
        target_ohms: float,
        geometry: str,
        dielectric_height_mils: float,
        dielectric_constant: float = 4.2,
        copper_oz: float = 1.0,
        spacing_mils: float = 0.0,
    ) -> dict[str, Any]:
        """Trace WIDTH to hit a target impedance (inverse of pcb_calc_impedance).

        The design-time complement: instead of "what impedance does this width
        give?", it answers "I need 90 ohm USB / 100 ohm HDMI differential, or
        50 ohm single-ended; how wide?". Inverts the same IPC-2141 / Wadell
        closed forms, so it round-trips with the forward calc. Pure math, no
        Altium. Same +/-10 % caveat -- a fab field solver refines the stackup;
        read the real dielectric heights / er with ``pcb_get_layer_stackup``.

        Args:
            target_ohms: Single-ended Z0 for ``microstrip``/``stripline``, or
                the differential Zdiff for ``microstrip_diff``/
                ``stripline_diff``.
            geometry: One of microstrip, microstrip_diff, stripline,
                stripline_diff.
            dielectric_height_mils: Trace-to-plane height (microstrip) or full
                between-plane thickness (stripline).
            dielectric_constant: er (default 4.2 FR-4).
            copper_oz: Copper weight for trace thickness (default 1.0).
            spacing_mils: Edge-to-edge gap (required for ``*_diff``).

        Returns:
            ``{"ok": True, "width_mils", "single_ended_z0_ohms", "feasible",
            ...}`` (feasible False when the target needs a width <= 0: raise the
            dielectric height or lower the target), or ``{"ok": False, ...}``.
        """
        from ..design.impedance_sizing import trace_width_for_impedance
        try:
            r = trace_width_for_impedance(
                target_ohms, geometry, dielectric_height_mils,
                dielectric_constant=dielectric_constant, copper_oz=copper_oz,
                spacing_mils=spacing_mils)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        out: dict[str, Any] = {
            "ok": True,
            "geometry": r.geometry,
            "target_ohms": target_ohms,
            "feasible": r.feasible,
            "width_mils": round(r.width_mils, 2),
            "single_ended_z0_ohms": round(r.single_ended_z0_ohms, 1),
            "dielectric_height_mils": dielectric_height_mils,
            "dielectric_constant": dielectric_constant,
        }
        if r.geometry.endswith("_diff"):
            out["spacing_mils"] = spacing_mils
        out["summary"] = (
            f"{target_ohms:g} ohm {r.geometry}: "
            + (f"width {r.width_mils:.2f} mil" if r.feasible else
               "infeasible (target too high for this stackup)"))
        return out

    @mcp.tool()
    async def pcb_calc_termination(
        length_mils: float,
        rise_time_ns: float,
        z0_ohms: Optional[float] = None,
        dielectric_constant: Optional[float] = None,
        geometry: str = "microstrip",
        driver_impedance_ohms: Optional[float] = None,
        vcc: float = 0.0,
        width_mils: float = 0.0,
        dielectric_height_mils: Optional[float] = None,
        length_fraction: float = 1.0 / 6.0,
        multi_load: bool = False,
        z0: Optional[float] = None,
        er: Optional[float] = None,
        driver_impedance: Optional[float] = None,
        height_mils: Optional[float] = None,
    ) -> dict[str, Any]:
        """Decide if a net needs termination and size the resistor(s).

        Offline. A net is electrically long when its one-way flight time
        exceeds ``length_fraction`` of the rise time (Johnson & Graham's
        1/6 by default). Microstrip Er_eff is Hammerstad when width and
        height are given, else 0.475*Er+0.67.

        Args:
            length_mils: Routed (or estimated) net length.
            rise_time_ns: Signal edge rate (the driver's 10-90 % rise time).
            z0_ohms: Line characteristic impedance (size it with
                ``pcb_calc_impedance``; default 50).
            dielectric_constant: er (default 4.2 FR-4).
            geometry: ``microstrip`` or ``stripline``.
            driver_impedance_ohms: Driver output impedance, subtracted for the
                series value (``Rs = Z0 - Rdriver``).
            vcc: Supply rail; enables the Thevenin split option when > 0.
            width_mils, dielectric_height_mils: Microstrip geometry for the
                Hammerstad Er_eff (optional; falls back to the approximation).
            length_fraction: Electrically-long threshold (default 1/6).
            multi_load: True for a bus / multi-receiver net (recommends
                far-end Thevenin/parallel instead of source series).
            z0, er, driver_impedance, height_mils: the EasyEDA and KiCad
                spellings of the same four values; giving both spellings
                with different values is refused.

        Returns:
            ``ok``, ``needs_termination``, ``recommended``,
            ``critical_length_mils``, ``flight_time_ns``, ``options`` (ideal
            and nearest-E24 values per scheme), ``summary``.
        """
        from ..design.signal_integrity import recommend_termination
        try:
            # The terse spellings are what the EasyEDA and KiCad builds
            # take, so accepting both here means one call works on any
            # backend.
            #
            # Preferring the alias unconditionally was the first attempt
            # and it is wrong: a caller passing z0_ohms=75 and z0=50
            # would have silently been given 50 and told it succeeded.
            # These name ONE quantity, so disagreement is a mistake in
            # the call and the only safe answer is to say so.
            # The defaults moved OUT of the signature and into
            # _TERMINATION_DEFAULTS so that "not supplied" is
            # distinguishable from "supplied, and happens to equal the
            # default". Detecting the conflict any other way needs a
            # comparison against the default value, and that silently
            # misses the case where the caller passed exactly it: the
            # first version of this passed every test except the one
            # that supplied dielectric_constant=4.2 alongside a
            # disagreeing er, which is precisely the call a client
            # written for another backend makes. Behaviour is unchanged
            # for every caller; only the advertised default moves into
            # the docstring.
            resolved = {}
            for terse, terse_name, verbose, verbose_name in (
                    (z0, "z0", z0_ohms, "z0_ohms"),
                    (er, "er", dielectric_constant, "dielectric_constant"),
                    (driver_impedance, "driver_impedance",
                     driver_impedance_ohms, "driver_impedance_ohms"),
                    (height_mils, "height_mils",
                     dielectric_height_mils, "dielectric_height_mils")):
                if (terse is not None and verbose is not None
                        and terse != verbose):
                    return {"ok": False, "reason": (
                        f"{verbose_name}={verbose} and {terse_name}="
                        f"{terse} were both given and disagree; they are "
                        f"the same quantity, so pass one")}
                given = verbose if verbose is not None else terse
                resolved[verbose_name] = (
                    given if given is not None
                    else _TERMINATION_DEFAULTS[verbose_name])
            z0_ohms = resolved["z0_ohms"]
            dielectric_constant = resolved["dielectric_constant"]
            driver_impedance_ohms = resolved["driver_impedance_ohms"]
            dielectric_height_mils = resolved["dielectric_height_mils"]
            adv = recommend_termination(
                length_mils, rise_time_ns, z0_ohms, dielectric_constant,
                geometry=geometry,
                driver_impedance=driver_impedance_ohms or None,
                vcc=vcc or None,
                width_mils=width_mils or None,
                height_mils=dielectric_height_mils or None,
                fraction=length_fraction, multi_load=multi_load)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        options: dict[str, Any] = {}
        if adv.series is not None:
            options["series"] = {
                "r_ohms": round(adv.series.r_series, 2),
                "r_e24": adv.series.r_series_e24}
        if adv.parallel is not None:
            options["parallel"] = {
                "r_ohms": round(adv.parallel.r_parallel, 2),
                "r_e24": adv.parallel.r_parallel_e24}
        if adv.thevenin is not None:
            options["thevenin"] = {
                "r_pullup_ohms": round(adv.thevenin.r_pullup, 2),
                "r_pulldown_ohms": round(adv.thevenin.r_pulldown, 2),
                "r_pullup_e24": adv.thevenin.r_pullup_e24,
                "r_pulldown_e24": adv.thevenin.r_pulldown_e24,
                "v_bias": round(adv.thevenin.v_bias, 3),
                "static_power_w": round(adv.thevenin.static_power_w, 4)}
        if adv.ac is not None:
            options["ac"] = {
                "r_ohms": round(adv.ac.r_parallel, 2),
                "r_e24": adv.ac.r_parallel_e24,
                "capacitance_pf": round(adv.ac.capacitance_f * 1e12, 1)}
        return {
            "ok": True,
            "needs_termination": adv.needs_termination,
            "recommended": adv.recommended,
            "electrically_long": adv.electrical.electrically_long,
            "critical_length_mils": round(adv.electrical.critical_length_mils, 1),
            "flight_time_ns": round(adv.electrical.flight_time_ns, 4),
            "delay_ratio": round(adv.electrical.delay_ratio, 2),
            "options": options,
            "summary": adv.note,
        }

    @mcp.tool()
    async def pcb_calc_length_match(
        lengths: Optional[dict[str, float]] = None,
        skew_budget_ps: float = 0.0,
        rise_time_ns: float = 0.0,
        match_fraction: float = 0.1,
        dielectric_constant: float = 4.2,
        geometry: str = "stripline",
        width_mils: float = 0.0,
        dielectric_height_mils: float = 0.0,
    ) -> dict[str, Any]:
        """Length-match tolerance and serpentine compensation for a bus / pair.

        Turns a timing budget into the length-match window the routing must hold,
        and -- given the routed lengths -- the serpentine copper each net needs.
        The complement of Altium's ``pcb_tune_length`` (which executes the
        meander) and ``pcb_get_trace_lengths`` (which reads lengths back). Pure
        math, no Altium. Rests on the ns/in == ps/mil identity, so skew maps to
        length exactly; propagation speed uses the effective dielectric constant
        (stripline = Er, the usual inner-layer bus case; microstrip reduced).

        The skew budget is taken from ``skew_budget_ps`` if > 0, else from
        ``match_fraction * rise_time_ns`` (the "match to within 10-20 % of the
        edge" rule).

        Args:
            lengths: Optional ``{net: length_mils}`` of routed lengths; when
                given, returns a per-net match report targeting the longest net.
            skew_budget_ps: Allowed skew in ps (e.g. a DDR byte-lane budget).
            rise_time_ns: Edge rate, used with ``match_fraction`` if no ps budget.
            match_fraction: Fraction of the rise time allowed as skew (default 0.1).
            dielectric_constant: er (default 4.2 FR-4).
            geometry: ``stripline`` (default) or ``microstrip``.
            width_mils, dielectric_height_mils: Microstrip geometry for the
                Hammerstad Er_eff (optional).

        Returns:
            ``{"ok": True, "er_eff", "t_pd_ps_per_mil", "skew_budget_ps",
            "tolerance_mils", "members"?: [{net, length_mils, mismatch_mils,
            skew_ps, compensation_mils, within_tolerance}], "target_length_mils"?,
            "worst_skew_ps"?, "all_matched"?, "summary"}``.
        """
        from ..design.length_matching import assess_length_match
        try:
            res = assess_length_match(
                dielectric_constant=dielectric_constant, geometry=geometry,
                width_mils=width_mils or None,
                dielectric_height_mils=dielectric_height_mils or None,
                skew_budget_ps=skew_budget_ps or None,
                rise_time_ns=rise_time_ns or None,
                match_fraction=match_fraction,
                lengths=lengths or None)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        tol = res["tolerance_mils"]
        out: dict[str, Any] = {
            "ok": True,
            "er_eff": round(res["er_eff"], 3),
            "t_pd_ps_per_mil": round(res["t_pd_ps_per_mil"], 4),
            "skew_budget_ps": res["skew_budget_ps"],
            "tolerance_mils": round(tol, 2) if tol is not None else None,
            # Which geometry produced the delay. A stripline uses er
            # directly and a microstrip an effective er near half of it,
            # so the two differ by roughly a quarter on every length
            # converted here. This defaults to stripline while
            # pcb_calc_termination defaults to microstrip, and neither
            # reply used to say so.
            "geometry": geometry,
            "dielectric_constant": dielectric_constant,
            "geometry_note": (
                f"delay computed for {geometry}. A stripline uses er "
                f"directly and a microstrip uses an effective er near "
                f"half of it, so the two differ by roughly a quarter. "
                f"Pass geometry explicitly if this board is not "
                f"{geometry}."),
        }
        rep = res.get("report")
        if rep is not None:
            out["target_length_mils"] = rep.target_length_mils
            out["worst_skew_ps"] = round(rep.worst_skew_ps, 3)
            out["all_matched"] = rep.all_matched
            out["members"] = [
                {"net": m.name, "length_mils": m.length_mils,
                 "mismatch_mils": round(m.mismatch_mils, 2),
                 "skew_ps": round(m.skew_ps, 3),
                 "compensation_mils": round(m.compensation_mils, 2),
                 "within_tolerance": m.within_tolerance}
                for m in rep.members]
            n_bad = sum(1 for m in rep.members if not m.within_tolerance)
            out["summary"] = (
                f"target {rep.target_length_mils:.0f} mils, worst skew "
                f"{rep.worst_skew_ps:.1f} ps"
                + (f", {n_bad} net(s) over the {tol:.0f}-mil window"
                   if tol is not None and n_bad else
                   (", all matched" if tol is not None else "")))
        else:
            out["summary"] = (
                f"match window {tol:.1f} mils for a {res['skew_budget_ps']:.1f} ps "
                f"budget on {geometry}" if tol is not None else
                f"no budget given ({geometry}, {res['t_pd_ps_per_mil']:.3f} ps/mil)")
        return out

    @mcp.tool()
    async def pcb_calc_thermal_vias(
        drill_mm: float,
        board_thickness_mm: Optional[float] = None,
        length_mm: Optional[float] = None,
        plating_um: float = 25.0,
        filled_copper: bool = False,
        k_cu: float = 385.0,
        power_w: float = 0.0,
        delta_t_c: float = 0.0,
        target_k_per_w: float = 0.0,
        via_count: int = 0,
    ) -> dict[str, Any]:
        """Size a thermal-via field under a power pad, or score a given
        ``via_count``. Each barrel conducts ``R = L / (k * A)`` and the vias
        add in parallel. The target is ``target_k_per_w``, or ``power_w``
        with a ``delta_t_c`` budget. Pure math, no Altium; copper spreading
        in the pad and plane is assumed good.

        Args:
            drill_mm: Finished via drill diameter.
            board_thickness_mm: Conduction length, from the top layer to the
                heat-spreading plane (full thickness for a bottom plane).
                The EasyEDA and KiCad builds spell this ``length_mm``;
                either is accepted.
            length_mm: Alias for ``board_thickness_mm``.
            plating_um: Barrel plating thickness in microns.
            filled_copper: True for a copper-filled via (full-circle copper),
                False for an unfilled / resin-filled barrel (annulus only).
            k_cu: Copper thermal conductivity, W/(m.K) (default 385).
            power_w: Dissipation, for the target (with ``delta_t_c``) and the
                realized temperature rise.
            delta_t_c: Allowed rise across the via field.
            target_k_per_w: Explicit target array resistance.
            via_count: Score this exact count instead of solving one.

        Returns:
            ``{"ok": True, "via_count", "single_via_k_per_w", "array_k_per_w",
            "target_k_per_w", "temp_rise_c", "barrel_area_mm2", "summary"}``.
        """
        from ..design.thermal_vias import assess_thermal_vias
        from .calc import _either
        try:
            board_thickness_mm = _either(
                "board_thickness_mm", board_thickness_mm,
                "length_mm", length_mm)
            rep = assess_thermal_vias(
                drill_mm, plating_um, board_thickness_mm,
                filled_copper=filled_copper, k_cu=k_cu,
                power_w=power_w or None, delta_t_c=delta_t_c or None,
                target_k_per_w=target_k_per_w or None,
                via_count=via_count or None)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        rise = (f", {rep.temp_rise_c:.1f} C rise"
                if rep.temp_rise_c is not None else "")
        return {
            "ok": True,
            "via_count": rep.via_count,
            "single_via_k_per_w": round(rep.single_via_k_per_w, 1),
            "array_k_per_w": round(rep.array_k_per_w, 2),
            "target_k_per_w": (round(rep.target_k_per_w, 2)
                               if rep.target_k_per_w is not None else None),
            "temp_rise_c": (round(rep.temp_rise_c, 2)
                            if rep.temp_rise_c is not None else None),
            "barrel_area_mm2": round(rep.barrel_area_mm2, 4),
            "summary": (
                f"{rep.via_count} via(s) -> {rep.array_k_per_w:.1f} K/W"
                f" ({rep.single_via_k_per_w:.0f} K/W each){rise}"),
        }

    @mcp.tool()
    async def pcb_calc_track_current_capacity(
        width_mils: float,
        copper_oz: float = 1.0,
        layer: str = "external",
        length_mils: float = 0.0,
    ) -> dict[str, Any]:
        """IPC-2221 current-carrying capacity for a PCB track.

        Offline math. ``I = k (dT)^0.44 (h w)^0.725`` in mils and degrees
        C, with k 0.048 external and 0.024 internal, at rises of 1, 5,
        10, 20 and 30 C. A length adds DC resistance (annealed copper,
        20 C) and the voltage drop at each current.

        Args:
            width_mils: Track width in mils.
            copper_oz: Copper weight in oz/ft² (1 oz = 1.378 mil).
            layer: ``"external"`` (default) or ``"internal"``.
            length_mils: If > 0, also return resistance and voltage drop.

        Returns:
            ``width_mils``, ``copper_oz``, ``thickness_mils``, ``layer``,
            ``current_amps`` (keys ``1c`` ... ``30c``), and with a length
            ``resistance_mohm`` and ``voltage_drop_mv``.
        """
        if width_mils <= 0:
            return {"ok": False, "reason": "width_mils must be > 0"}
        if copper_oz <= 0:
            return {"ok": False, "reason": "copper_oz must be > 0"}
        layer_norm = layer.strip().lower()
        if layer_norm not in ("external", "internal"):
            return {"ok": False,
                    "reason": "layer must be 'external' or 'internal'"}

        from ..units import OZ_TO_MILS

        thickness_mils = copper_oz * OZ_TO_MILS
        k = 0.024 if layer_norm == "internal" else 0.048
        b = 0.44
        c = 0.725
        hw_c = (thickness_mils * width_mils) ** c

        rises = (1, 5, 10, 20, 30)
        current = {f"{t}c": round(k * (t ** b) * hw_c, 3) for t in rises}
        out: dict[str, Any] = {
            "ok": True,
            "width_mils": width_mils,
            "copper_oz": copper_oz,
            "thickness_mils": round(thickness_mils, 3),
            "layer": layer_norm,
            "current_amps": current,
        }
        if length_mils > 0:
            from ..design.trace_sizing import trace_resistance_mohm
            r_ohm = trace_resistance_mohm(
                width_mils, copper_oz, length_mils) / 1000.0
            out["resistance_mohm"] = round(r_ohm * 1000.0, 4)
            out["voltage_drop_mv"] = {
                k_: round(current[k_] * r_ohm * 1000.0, 3) for k_ in current
            }
        return out

    @mcp.tool()
    async def pcb_calc_trace_width_for_current(
        current_amps: Optional[float] = None,
        copper_oz: float = 1.0,
        delta_t_c: float = 10.0,
        layer: str = "external",
        margin: float = 0.2,
        length_mils: float = 0.0,
        current_a: Optional[float] = None,
    ) -> dict[str, Any]:
        """Minimum track WIDTH to carry a target current (inverse IPC-2221).

        The design-time complement of ``pcb_calc_track_current_capacity``:
        instead of "what current does this width carry?", it answers "I need N
        amps, how wide?". Pure math, no Altium hit.

        Solves ``I = k * dT^0.44 * (h*w)^0.725`` for ``w`` with the same
        constants as the forward tool (so they round-trip), ``k = 0.048``
        external / ``0.024`` internal, ``h = copper_oz * 1.378 mils``.

        Args:
            current_amps: Target current the track must carry. The
                EasyEDA and KiCad builds spell this ``current_a``;
                either is accepted here, so one call works on any
                backend.
            current_a: Alias for ``current_amps``.
            copper_oz: Copper weight, oz/ft^2 (0.5 / 1.0 / 2.0 / 3.0).
            delta_t_c: Allowed temperature rise above ambient (10 degC is a
                common conservative budget; 20-30 degC for tight boards).
            layer: ``"external"`` (top/bottom) or ``"internal"`` (inner; needs
                ~2.6x the width for the same rise).
            margin: Fractional widening above the bare IPC minimum for the
                recommendation (default 0.2 = 20 %).
            length_mils: If > 0, also returns DC resistance and voltage drop at
                the recommended width.

        Returns:
            ``{"ok": True, "min_width_mils", "recommended_width_mils",
            "copper_oz", "delta_t_c", "layer", ...optional resistance/drop}``
            or ``{"ok": False, "reason": ...}``.
        """
        from ..design.trace_sizing import trace_width_for_current
        from .calc import _either
        try:
            current_amps = _either("current_amps", current_amps,
                                   "current_a", current_a)
            r = trace_width_for_current(
                current_amps, copper_oz=copper_oz, delta_t_c=delta_t_c,
                layer=layer, margin=margin, length_mils=length_mils)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc)}
        out: dict[str, Any] = {
            "ok": True,
            "current_amps": current_amps,
            "min_width_mils": round(r.min_width_mils, 3),
            "recommended_width_mils": r.recommended_width_mils,
            "copper_oz": copper_oz,
            "delta_t_c": delta_t_c,
            "layer": r.layer,
            "summary": (
                f"{current_amps:g} A at {delta_t_c:g} degC rise ({r.layer}, "
                f"{copper_oz:g} oz): min {r.min_width_mils:.1f} mil, "
                f"use {r.recommended_width_mils:g} mil"),
        }
        if r.resistance_mohm is not None:
            out["resistance_mohm"] = round(r.resistance_mohm, 4)
            out["voltage_drop_mv"] = round(r.voltage_drop_mv, 3)
        return out

    @mcp.tool()
    async def pcb_add_testpoints_for_net_class(
        net_class: str,
        type: str = "smd",
        pad_size_mils: float = 40,
        hole_size_mils: float = 20,
        fab_top: bool = False,
        fab_bottom: bool = False,
        assy_top: bool = True,
        assy_bottom: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """For each net in a netclass with no testpoint yet, place a pad
        with the net and testpoint flags, in a row above the board, to be
        moved into place.

        A net counts as covered when any pad or via on it carries any of
        the four testpoint flags; ``force`` places anyway.

        Args:
            net_class: Netclass name to scan.
            type: ``"smd"`` (top-layer SMD pad, no hole) or
                ``"through_hole"`` (multi-layer pad with drill).
            pad_size_mils: Outer pad size in mils. Default 40.
            hole_size_mils: Drill diameter, only used for through-hole
                testpoints. Default 20.
            fab_top: Set ``IsTestpoint_Top`` (top-side bed-of-nails).
            fab_bottom: Set ``IsTestpoint_Bottom``.
            assy_top: Set ``IsAssyTestpoint_Top`` (top-side assembly
                probe). Default True.
            assy_bottom: Set ``IsAssyTestpoint_Bottom``.
            force: Ignore existing testpoint coverage and always
                place a new pad.

        Returns:
            Dict with ``{net_class, type, placed, skipped_already_covered,
            placed_nets[], skipped_nets[]}``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.add_testpoints_for_net_class",
            {
                "net_class": net_class,
                "type": type,
                "pad_size_mils": _mils(pad_size_mils),
                "hole_size_mils": _mils(hole_size_mils),
                "fab_top": "true" if fab_top else "false",
                "fab_bottom": "true" if fab_bottom else "false",
                "assy_top": "true" if assy_top else "false",
                "assy_bottom": "true" if assy_bottom else "false",
                "force": "true" if force else "false",
            },
            timeout=60.0,
        )

    @mcp.tool()
    async def pcb_apply_dnp_paste_exclusion(
        designators: Optional[list[str]] = None,
        restore: bool = False,
        dry_run: bool = False,
        use_current_variant: bool = False,
    ) -> dict[str, Any]:
        """Suppress stencil paste on Not-Fitted (DNP) components, so no
        paste lands on empty pads. Each surface pad's paste opening is
        disabled; through-hole pads are skipped.

        Apply with no ``designators`` uses the current variant's
        Not-Fitted list. RESTORE THE SAME LIST YOU APPLIED: restore
        refuses without ``designators``, because restoring from a
        different variant would silently leave a fitted part without
        paste. Pass back the ``items`` the apply returned.

        Args:
            designators: Components to treat (apply default: the current
                variant's Not-Fitted list; required for restore).
            restore: Remove the override so the design rules apply again.
            dry_run: Report what would change, change nothing (use first).
            use_current_variant: Let a restore with no designators use the
                current variant (you own that choice).

        Returns:
            ``restored``, ``components_requested`` vs
            ``components_matched``, ``pads_changed``,
            ``pads_skipped_through_hole``, ``items``; a dry run gives
            ``designators`` and ``source``; a refused restore gives
            {"ok": False, "reason"} and touches nothing.
        """
        bridge = get_bridge()

        source = "explicit"
        variant = ""
        names = [str(d).strip() for d in (designators or []) if str(d).strip()]

        # Refuse BEFORE asking the bridge anything. A restore that
        # resolves from whatever variant happens to be open is the one
        # way this tool can leave a fitted part with no paste, and the
        # result is indistinguishable from success.
        if restore and not names and not use_current_variant:
            return {
                "ok": False,
                "reason": (
                    "restore needs the designators that were excluded. "
                    "Resolving them from the variant open right now "
                    "would restore the wrong components if the variant "
                    "changed since the apply, leaving a fitted part "
                    "with no stencil aperture. Pass the designators "
                    "from the apply reply's 'items', or set "
                    "use_current_variant=True to accept that risk "
                    "deliberately."
                ),
            }

        if not names:
            source = "variant_not_fitted"
            found = await bridge.send_command_async(
                "audit.variant_not_fitted", {})
            items = (found or {}).get("items") or []
            names = [str(i.get("designator", "")).strip()
                     for i in items if isinstance(i, dict)]
            names = [n for n in names if n]
            variant = str((found or {}).get("variant", ""))
            if not names:
                return {
                    "ok": True,
                    "components_matched": 0,
                    "pads_changed": 0,
                    "source": source,
                    "variant": (found or {}).get("variant", ""),
                    "note": "no Not-Fitted components in the current "
                            "variant; nothing to exclude",
                }

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "restore": restore,
                "source": source,
                "variant": variant,
                "designators": names,
                "note": "nothing was changed; re-run with dry_run=False "
                        "to apply",
            }

        # The designator list rides ONE field, so a designator containing
        # the separator would silently split into two names and treat a
        # component nobody asked for. This used to STRIP the separator,
        # which prevents the split but can produce a DIFFERENT valid
        # name: 'R|1' became 'R1', a real component, whose paste this
        # tool then changes. Refusing tells the caller what happened.
        bad = [n for n in names if "|" in payload_safe(n)]
        if bad:
            return {"ok": False, "reason":
                    f"designators {bad} contain '|', which is the "
                    "wire-format separator; stripping it could target a "
                    "different real component, so the call is refused"}
        safe = [s for s in (payload_safe(n) for n in names) if s]
        result = await bridge.send_command_async(
            "pcb.apply_dnp_paste_exclusion",
            {
                "designators": "|".join(safe),
                "restore": "true" if restore else "false",
            },
        )
        # Report WHERE the list came from. An apply and a later restore
        # that resolved against different variants is the failure mode
        # that leaves a fitted part with no paste, and without these two
        # keys the two replies are indistinguishable.
        if isinstance(result, dict):
            result.setdefault("source", source)
            if variant:
                result.setdefault("variant", variant)
        return result

    @mcp.tool()
    async def pcb_make_paste_grid(
        designator: str,
        pad_name: str,
        min_grid_size_mils: float = 15,
        min_gap_mils: float = 5,
        min_coverage_pct: float = 60.0,
    ) -> dict[str, Any]:
        """Split one pad's solder-paste opening into a regular grid of
        smaller fills, typically for a QFN/DFN exposed pad. Use the
        stencil pattern from the IC's datasheet when it gives one;
        this tool only does a regular grid.

        Args:
            designator: Component designator, e.g. ``"U5"``.
            pad_name: Pad name on that component. Check the footprint
                for an exposed pad's name.
            min_grid_size_mils: Starting block size; raised in 5-mil
                steps until coverage is met.
            min_gap_mils: Minimum gap between blocks.
            min_coverage_pct: Target paste coverage, % of pad area.

        Returns:
            ``{designator, pad_name, grid_x, grid_y, grid_size_mils,
            gap_x_mils, gap_y_mils, fills_placed, coverage_pct}``. The
            pad's own paste opening is disabled before the fills go down.
            A pad with paste already disabled is refused, preventing a
            duplicate grid.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.make_paste_grid",
            {
                "designator": designator,
                "pad_name": pad_name,
                "min_grid_size_mils": _mils(min_grid_size_mils),
                "min_gap_mils": _mils(min_gap_mils),
                "min_coverage_pct": str(float(min_coverage_pct)),
            },
            timeout=30.0,
        )

    @mcp.tool()
    async def pcb_get_differential_pairs() -> dict[str, Any]:
        """Enumerate every ``IPCB_DifferentialPair`` on the active PCB
        and report each pair's two halves with length skew.

        Compare ``skew_mils`` with the limit in the interface's own
        specification or the part's datasheet. One row per pair:
          - ``name``: pair name (e.g. ``"USB_DATA"`` if the SCH had
            ``.DiffPair`` directives ``USB_DATA_P`` / ``USB_DATA_N``)
          - ``positive_net`` / ``negative_net``: the two member nets
          - ``pos_length_mils`` / ``neg_length_mils``: summed track +
            arc length for each half (signal layers only)
          - ``skew_mils``: absolute difference
          - ``both_routed``: false means a half is unrouted and the
            lengths mean little

        Returns:
            Dict with ``{count, pairs: [...]}``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.get_differential_pairs", {}, timeout=30.0,
        )

    @mcp.tool()
    async def pcb_clear_source_footprint_library(
        designator_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        """Clear ``Comp.SourceFootprintLibrary`` on board components.

        A component remembers the library it came from, so after that
        library is renamed or moved, updates fail with "library not
        found". Clearing it makes Altium re-match by name from the
        Available Libraries: install the new library, run this, then the
        ECO.

        Args:
            designator_filter: Restrict to these designators
                (e.g. ``["U1", "U5"]``). ``None`` / empty clears all
                components on the board. Match is case-sensitive
                whole-string.

        Returns:
            Dict with ``{total, cleared}``. ``total`` counts components
            inspected after filter; ``cleared`` counts ones that
            actually had a non-empty SourceFootprintLibrary cleared.
        """
        bridge = get_bridge()
        params: dict[str, str] = {}
        if designator_filter:
            # A '|' inside a designator splits into two filter entries,
            # and a fragment like 'R1' matches a real component whose
            # library pin this tool then clears. Refuse rather than
            # strip.
            bad = [d for d in designator_filter if "|" in str(d)]
            if bad:
                return {"ok": False, "reason":
                        f"designators {bad} contain '|', which is the "
                        "wire-format separator; fragments could match "
                        "other components, so the call is refused"}
            params["designator_filter"] = "|".join(
                str(d) for d in designator_filter)
        return await bridge.send_command_async(
            "pcb.clear_source_footprint_library", params, timeout=30.0,
        )

    @mcp.tool()
    async def pcb_update_footprints_from_library(
        designators: list[str],
        library_path: str = "",
        board_path: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Refresh placed parts from their edited PcbLib, with no ECO.

        For a footprint fixed in its library (silk, pads, 3D body) when
        the project ECO cannot be used because it also proposes every
        other schematic and board difference. Each part is replaced by a
        fresh copy from the library that keeps its side, rotation,
        position, designator and comment text as placed, locked state,
        pad nets by pad name, and its schematic link (SourceUniqueId and
        SourceHierarchicalPath, which multi-channel designs match on).

        A part is replaced only when the library holds its pattern and
        every pad that carried a net exists on the new footprint;
        otherwise it is left as it was and the reason is given. Routed
        copper is not touched, so check connectivity where pads moved.

        The part's PARAMETERS (LCSC number, manufacturer and the rest a
        schematic sync put on it) are not carried over: the scripting
        API exposes no way to read them on a board part. A follow-up take
        refreshed all 143 parts and the next change order offered to put
        every part's parameters back. That sync restores them, so run
        proj_sync_pcb after a refresh, before writing a BOM from the board.

        Args:
            designators: The parts to refresh, e.g. ``["C12", "J3"]``.
            library_path: The .PcbLib to load from. Empty uses each
                part's own SourceFootprintLibrary.
            board_path: Focus this .PcbDoc first. Omit for the board in
                front.
            dry_run: Report what would be refreshed and change nothing.

        Returns:
            ``updated``, ``failed`` and per part ``ok``, ``pattern``,
            ``library``, ``pads_before``/``pads_after``, ``nets_bound``
            and a ``reason`` when it was left alone.
        """
        bad = [d for d in designators if "|" in str(d) or not str(d).strip()]
        if not designators or bad:
            return {"ok": False, "reason": (
                "give one or more designators, none empty or containing "
                f"'|', the wire-format separator: {bad}")}
        import os

        bridge = get_bridge()
        if board_path:
            focused = await bridge.send_command_async(
                "pcb.focus_board", {"board_path": board_path})
            if not (focused or {}).get("focused", True):
                return {"ok": False, "reason": "could not focus that board",
                        "focus": focused}
        names = [str(d).strip() for d in designators]
        plan = await bridge.send_command_async(
            "pcb.update_footprints_from_library",
            {"designators": "|".join(names), "library_path": library_path,
             "dry_run": "true"}, timeout=120.0)
        if not isinstance(plan, dict) or "items" not in plan:
            return plan
        board = plan.get("board") or board_path

        # LoadFromLibrary does not fail on a library that lacks the
        # pattern. MEASURED: pointed at a .PcbLib that does not exist, it
        # loaded the footprint from elsewhere, most likely the board's own
        # copy, and the part "refreshed" to exactly what it was. So each
        # library is checked to exist and to hold the pattern first.
        held: dict[str, set] = {}
        refused: list[dict[str, Any]] = []
        passing: list[str] = []
        for item in plan["items"]:
            if not item.get("ok"):
                refused.append(item)
                continue
            lib = item.get("library") or ""
            if not os.path.isfile(lib):
                refused.append({**item, "ok": False, "reason": (
                    f"{lib!r} is not a library file on disk, so the "
                    "footprint would come from elsewhere; pass library_path")})
                continue
            if lib not in held:
                listing = await bridge.send_command_async(
                    "library.get_footprints", {"library_path": lib})
                held[lib] = {str(f.get("name", "")).upper()
                             for f in (listing or {}).get("footprints", [])}
            if str(item.get("pattern", "")).upper() not in held[lib]:
                refused.append({**item, "ok": False, "reason": (
                    f"{item.get('pattern')} is not in {lib}")})
                continue
            passing.append(item["designator"])
        if held and board:
            await bridge.send_command_async(
                "pcb.focus_board", {"board_path": board})

        if dry_run or not passing:
            items = [i for i in plan["items"]
                     if i["designator"] in passing] + refused
            return {"updated": 0, "would_update": len(passing),
                    "failed": len(refused), "dry_run": dry_run,
                    "board": board, "items": items}
        done = await bridge.send_command_async(
            "pcb.update_footprints_from_library",
            {"designators": "|".join(passing), "library_path": library_path,
             "dry_run": "false"}, timeout=300.0)
        if isinstance(done, dict) and "items" in done:
            done["items"] = done["items"] + refused
            done["failed"] = done.get("failed", 0) + len(refused)
        return done

    @mcp.tool()
    async def pcb_get_fab_stats() -> dict[str, Any]:
        """DFM (Design For Manufacturing) summary -- the numbers fab
        houses ask for on their quote forms.

        One IPC call returns:
          - ``board_width_mm``, ``board_height_mm``, ``board_area_mm2``
          - ``num_copper_layers``
          - ``vias_total``, ``vias_through``, ``vias_blind``,
            ``vias_buried``
          - ``pads_plated``, ``pads_unplated``, ``pads_slotted``
          - ``min_annular_ring_mils`` (plated holes, vias and pads)
          - ``min_track_width_mils`` (all copper layers)
          - ``smallest_hole_mils``, ``largest_hole_mils``,
            ``distinct_hole_count``

        Compare them with the chosen fab's published capabilities
        (``design_load_fab_profile``). Aspect ratio is not included; it
        needs ``pcb_get_layer_stackup``.

        Returns:
            Dict with all keys above. All linear measurements use the
            stated unit suffix (``_mm`` vs ``_mils``).
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.get_fab_stats", {})

    @mcp.tool()
    async def pcb_lock_net_routing(
        nets: list[str],
        lock: bool,
        lock_components: bool = False,
    ) -> dict[str, Any]:
        """Lock or unlock track / arc / via primitives on a list of nets.

        For example, lock hand-routed power and clock nets before an
        autoroute pass. Locking sets ``Moveable=False``, which the editor
        honours when "Protect Locked Objects" is on in the PCB
        preferences.

        Args:
            nets: Net names to lock / unlock (e.g. ``["VCC", "GND",
                "CLK_24M"]``). Case-sensitive.
            lock: True to lock (sets Moveable=False), False to unlock.
            lock_components: Also lock any component with at least one
                pad on a matched net. Useful to freeze the connectors /
                regulators that anchor a hand-routed power section.
                Default False.

        Returns:
            Dict with:
              - ``locked``: True / False mirror of the input
              - ``matched_primitives``: track + arc + via objects whose
                net matched
              - ``updated_primitives``: how many actually changed state
              - ``matched_components``: components touched (only filled
                when ``lock_components=True``)
              - ``updated_components``: components whose Moveable flipped
        """
        if not nets:
            return {"ok": False, "reason": "nets list is empty"}
        # A '|' inside a net name splits into two names, and net-name
        # fragments ('VCC', 'GND') are the most likely of all fragments
        # to match real objects; this tool then flips their Moveable
        # state. Refuse rather than strip.
        bad = [n for n in nets if "|" in str(n)]
        if bad:
            return {"ok": False, "reason":
                    f"net names {bad} contain '|', which is the "
                    "wire-format separator; fragments could match other "
                    "nets, so the call is refused"}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.lock_net_routing",
            {
                "nets": "|".join(str(n) for n in nets),
                "lock": "true" if lock else "false",
                "lock_components": "true" if lock_components else "false",
            },
        )

    @mcp.tool()
    async def pcb_set_text_visibility(
        designators: bool | None = None,
        comments: bool | None = None,
        filter: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bulk-toggle component designator and / or comment visibility.

        For the common workflows:
          - Hide all designators before generating an assembly PDF.
          - Show comments during a value-review pass.
          - Hide just the noisy 0402 designators while keeping IC labels.

        Args:
            designators: If True/False, set ``Component.NameOn`` for
                matched components. ``None`` leaves designator visibility
                alone.
            comments: If True/False, set ``Component.CommentOn``. ``None``
                leaves comment visibility alone.
            filter: Restrict to these designator names (e.g. ``["U1",
                "U2", "C5"]``). ``None`` applies to every component.
                Match is case-sensitive whole-string.

        At least one of ``designators`` / ``comments`` must be supplied.

        Returns:
            Dict with:
              - ``matched``: components inspected (after filter)
              - ``updated_names``: components whose NameOn flipped
              - ``updated_comments``: components whose CommentOn flipped
        """
        if designators is None and comments is None:
            return {"ok": False,
                    "reason": ("supply at least one of designators / "
                               "comments")}
        bridge = get_bridge()
        params: dict[str, str] = {}
        if designators is not None:
            params["designators"] = "true" if designators else "false"
        if comments is not None:
            params["comments"] = "true" if comments else "false"
        if filter:
            params["filter"] = "|".join(str(d) for d in filter)
        return await bridge.send_command_async(
            "pcb.set_text_visibility", params,
        )

    @mcp.tool()
    async def pcb_set_text_style(
        height_mils: float | None = None,
        stroke_mils: float | None = None,
        designators: list[str] | None = None,
        which: str = "designator",
    ) -> dict[str, Any]:
        """Set the height and stroke width of component designators or comments.

        Silkscreen text size is usually a fabrication requirement (for
        example 0.8 mm high with a 0.1 mm stroke: ``height_mils=31.5,
        stroke_mils=3.94``). Altium's stroke text has a height and a
        stroke width and no separate character width: the characters
        scale with the height.

        For free texts use ``obj_modify`` on ``eTextObject`` with
        ``Height`` and ``StrokeWidth`` (filter ``IsDesignator=false``).

        Args:
            height_mils: Text height in mils. ``None`` leaves it.
            stroke_mils: Stroke width in mils. ``None`` leaves it.
            designators: Only these components (e.g. ``["U1", "R5"]``).
                ``None`` applies to every component.
            which: ``"designator"`` (default), ``"comment"`` or ``"both"``.

        At least one of ``height_mils`` / ``stroke_mils`` must be given.

        Returns:
            Dict with ``matched`` components, ``changed`` and ``failed``
            texts, ``not_found`` designators, and ``texts``: each one's
            height and stroke as read back after the write. ``success``
            is false when any text did not take or a designator was not
            found.
        """
        if height_mils is None and stroke_mils is None:
            return {"ok": False,
                    "reason": "give height_mils, stroke_mils or both"}
        if which not in ("designator", "comment", "both"):
            return {"ok": False,
                    "reason": 'which is "designator", "comment" or "both"'}
        for name, val in (("height_mils", height_mils),
                          ("stroke_mils", stroke_mils)):
            if val is not None and not val > 0:
                return {"ok": False, "reason": f"{name} must be above zero"}
        bad = [d for d in designators or [] if "|" in str(d)]
        if bad:
            return {"ok": False,
                    "reason": f"a designator cannot contain |: {bad[0]}"}
        bridge = get_bridge()
        params: dict[str, str] = {"which": which}
        if height_mils is not None:
            params["height_mils"] = str(float(height_mils))
        if stroke_mils is not None:
            params["stroke_mils"] = str(float(stroke_mils))
        if designators:
            params["designators"] = "|".join(str(d) for d in designators)
        return await bridge.send_command_async("pcb.set_text_style", params)

    @mcp.tool()
    async def pcb_check_placement_collision(
        designator: str,
        x: float,
        y: float,
        rotation: Optional[float] = None,
        margin_mils: float = 0,
    ) -> dict[str, Any]:
        """Check, without moving it, whether a component at (x, y[,
        rotation]) would overlap another component on the same side.
        Use before ``pcb_move_components`` on a populated board.

        DOES NOT actually move the component. Computes the predicted
        axis-aligned bounding box at the proposed pose, then AABB-tests
        against every other same-side component. Use this BEFORE every
        `pcb_move_components` call when placing parts on a board that
        already has placed parts.

        What a bbox covers: the union of the footprint's pads, tracks,
        arcs, fills and regions on ALL layers. That includes the
        silkscreen OUTLINE and any mechanical courtyard shapes, and
        excludes every text primitive (designator, comment, free text).
        It is therefore a body/courtyard box, NOT the Altium component
        bounding rectangle, which is text-inflated and made 0201s look
        hundreds of mils tall. Target and colliders are measured
        identically; each result carries a `bbox_basis` field.

        Args:
            designator: Component to test.
            x, y: Proposed reference point in mils.
            rotation: Proposed rotation; default the current one.
            margin_mils: Extra clearance; at 0, touching boxes collide.

        Returns:
            Dict with:
              - designator: target.
              - layer: the target's side, e.g. "TopLayer".
              - same_side_filter: True when the side rule was applied.
                False means the target's layer was unreadable and the
                check fell back to comparing against every component.
              - bbox_basis: "footprint_body", or
                "component_rect_including_text" when the footprint had
                no measurable non-text primitive and the text-inflated
                rectangle had to be used as a fallback.
              - bbox_includes: plain-text description of the above.
              - proposed: {x, y, rotation, bbox:{x1,y1,x2,y2}, margin_mils}.
              - clear: True if no collisions, False otherwise.
              - colliding_count: number of collisions.
              - colliding: list of {designator, layer, bbox_basis,
                bbox:{...}} per collider. Each bbox is measured from the
                component named next to it.

        Caveats:
            - AABB only; rotated non-square footprints will report an
              inflated bbox.
            - Same-side check is automatic; the target's bbox is compared
              only against components on the same layer (Top vs Bottom).
            - The box is a body/courtyard box including silkscreen
              outline, not a pad-copper-only box, so it is slightly
              larger than the package body.
            - Does not detect courtyard violations or pad-to-pad clearances,
              only solid-box overlap. Use DRC for actual clearance rules.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "designator": designator,
            "x": _mils(x),
            "y": _mils(y),
            "margin_mils": _mils(margin_mils),
        }
        if rotation is not None:
            params["rotation"] = str(rotation)
        return await bridge.send_command_async(
            "pcb.check_placement_collision", params,
        )

    @mcp.tool()
    async def pcb_get_trace_lengths(
        net: str = "",
    ) -> dict[str, Any]:
        """Get total routed track length per net on the active PCB.

        Sums all track segment lengths for each net. Useful for length
        matching analysis and checking differential pair balance.

        Args:
            net: Optional net name filter. If provided, only returns the
                 length for that specific net. Empty = all nets.

        Returns:
            Dictionary with "trace_lengths" array (each with net name and
            length_mils) and "net_count"
        """
        bridge = get_bridge()
        params: dict[str, Any] = {}
        if net:
            params["net"] = net
        result = await bridge.send_command_async("pcb.get_trace_lengths", params)
        return result

    @mcp.tool()
    async def pcb_get_net_routing(net: str) -> dict[str, Any]:
        """Return every track, via and arc assigned to one exact PCB net.

        This is the authoritative structural getter for copying reference
        routing.  Unlike generic ``obj_query``, net filtering happens inside
        DelphiScript through ``primitive.Net.Name``.
        """
        if not net:
            return {"error": "net is required"}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.get_net_routing", {"net": net}, timeout=120.0,
        )

    @mcp.tool()
    async def pcb_get_layer_stackup() -> dict[str, Any]:
        """Get the full PCB layer stackup information.

        Returns copper layers with thickness, dielectric type/height/constant,
        and board name.

        Returns:
            Dictionary with "layers" array (each with name, order,
            copper_thickness_mils, dielectric_type, dielectric_height_mils,
            dielectric_constant), "layer_count", and "board_name"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_layer_stackup", {})
        return result

    @mcp.tool()
    async def pcb_physical_stack(board_path: str) -> dict[str, Any]:
        """Read Altium's physical layer stack in order for one exact PcbDoc.

        Includes copper, dielectric, mask, paste and overlay layers, Z
        positions and thicknesses in mils, plus dielectric material data.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.physical_stack", {"board_path": board_path}, timeout=120.0,
        )
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        layers = reply.get("layers")
        if (str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or type(reply.get("style")) is not int
                or type(reply.get("layer_count")) is not int
                or not isinstance(layers, list)
                or len(layers) != reply["layer_count"]
                or not isinstance(reply.get("total_thickness_mils"), (int, float))):
            return {"ok": False, "reason": "incomplete or wrong-board physical stack reply",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_plane_connections(
        board_path: str, designator: str, pad: str = "",
    ) -> dict[str, Any]:
        """Read each pad's internal-plane connection settings on one PcbDoc.

        Reports the native rule style, relief dimensions and clearance in mils.
        An optional pad name narrows the result to one pad.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not designator.strip():
            return {"ok": False, "reason": "designator is required"}
        reply = await get_bridge().send_command_async(
            "pcb.plane_connections",
            {"board_path": board_path, "designator": designator, "pad": pad},
            timeout=120.0,
        )
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        pads = reply.get("pads")
        if (str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or str(reply.get("designator", "")).casefold() != designator.casefold()
                or type(reply.get("plane_layers")) is not int
                or type(reply.get("pad_count")) is not int
                or not isinstance(pads, list)
                or len(pads) != reply["pad_count"]
                or (pad and (len(pads) != 1
                            or str(pads[0].get("pad", "")).casefold() != pad.casefold()))
                or any(not isinstance(item, dict)
                       or not all(key in item for key in (
                           "pad", "net", "rule_style", "relief_width_mils",
                           "relief_entries", "air_gap_mils", "relief_expansion_mils",
                           "plane_clearance_mils")) for item in pads)):
            return {"ok": False, "reason": "incomplete or wrong-board plane connection reply",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_get_board_regions(board_path: str) -> dict[str, Any]:
        """Read rigid-flex regions, split/bend lines and named layer stacks.

        Coordinates of bend endpoints are in mils from the board origin.
        The exact active PcbDoc path is required.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.flex_state", {"board_path": board_path}, timeout=120.0,
        )
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        if (str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or type(reply.get("split_line_count")) is not int
                or type(reply.get("layer_stack_count")) is not int
                or not isinstance(reply.get("regions"), list)
                or not isinstance(reply.get("split_lines"), list)
                or not isinstance(reply.get("layer_stacks"), list)
                or len(reply["split_lines"]) != reply["split_line_count"]
                or len(reply["layer_stacks"]) != reply["layer_stack_count"]
                or any(not isinstance(region, dict)
                       or not isinstance(region.get("bend_lines"), list)
                       for region in reply["regions"])
                or any(not isinstance(stack, dict)
                       or not isinstance(stack.get("copper_layers"), list)
                       or type(stack.get("flex")) is not bool
                       for stack in reply["layer_stacks"])):
            return {"ok": False, "reason": "incomplete or wrong-board rigid-flex snapshot",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_set_stack_style(
        board_path: str, style: int, dry_run: bool = True,
    ) -> dict[str, Any]:
        """Plan or set Altium's layer-stack style for one exact PcbDoc.

        Read the current style first with ``pcb_physical_stack``. Save the
        PcbDoc separately after inspecting the resulting physical stack.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if type(style) is not int or style < 0:
            return {"ok": False, "reason": "style must be a nonnegative integer"}
        before = await pcb_physical_stack(board_path)
        if not isinstance(before, dict) or type(before.get("style")) is not int:
            return {"ok": False, "reason": "could not read exact-board stack",
                    "native_reply": before}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "before_style": before["style"], "would_set_style": style,
                    "layer_count": before["layer_count"]}
        params = {"board_path": board_path, "style": str(style),
                  "expect_style": str(before["style"]),
                  "expect_layer_count": str(before["layer_count"])}
        reply = await get_bridge().send_command_async("pcb.set_stack_style", params,
                                                       timeout=120.0)
        if (not isinstance(reply, dict)
                or str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or reply.get("before_style") != before["style"]
                or reply.get("after_style") != style):
            return {"ok": False, "reason": "native stack style readback failed",
                    "native_reply": reply}
        after = await pcb_physical_stack(board_path)
        if not isinstance(after, dict) or after.get("style") != style:
            return {"ok": False, "reason": "independent stack style readback failed",
                    "native_reply": reply, "after": after}
        reply["save_required"] = bool(reply.get("changed"))
        return reply

    @mcp.tool()
    async def pcb_set_dielectric(
        board_path: str,
        layer: str,
        dielectric_type: Optional[int] = None,
        material: Optional[str] = None,
        constant: Optional[float] = None,
        loss_tangent: Optional[float] = None,
        thickness_mils: Optional[float] = None,
        stiffener: Optional[bool] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Plan or set a named dielectric or solder-mask layer.

        Requires an exact board path and old values. Save the PcbDoc
        separately after checking the result.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not layer.strip():
            return {"ok": False, "reason": "layer is required"}
        updates = {"dielectric_type": dielectric_type, "material": material,
                   "constant": constant, "loss_tangent": loss_tangent,
                   "thickness_mils": thickness_mils, "stiffener": stiffener}
        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            return {"ok": False, "reason": "give at least one dielectric setting"}
        if "stiffener" in updates:
            return {"ok": False, "reason":
                    "Altium 26.11 did not persist the stiffener flag after save/reopen"}
        if ("dielectric_type" in updates and
                (type(dielectric_type) is not int or dielectric_type < 0)):
            return {"ok": False, "reason": "dielectric_type must be a nonnegative integer"}
        if "material" in updates and (not isinstance(material, str) or not material.strip()):
            return {"ok": False, "reason": "material must be nonempty"}
        for key, minimum in (("constant", 1), ("loss_tangent", 0),
                             ("thickness_mils", 0)):
            if key in updates:
                value = updates[key]
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or value < minimum or (key == "thickness_mils" and value == 0)):
                    return {"ok": False, "reason": f"invalid {key}"}
        before_stack = await pcb_physical_stack(board_path)
        if not isinstance(before_stack.get("layers"), list):
            return {"ok": False, "reason": "could not read exact-board physical stack",
                    "native_reply": before_stack}
        matches = [item for item in before_stack["layers"]
                   if item.get("name", "").casefold() == layer.strip().casefold()]
        if len(matches) != 1 or matches[0].get("kind") not in ("dielectric", "solder_mask"):
            return {"ok": False, "reason": "named dielectric or solder mask layer not found"}
        old = {key: matches[0][key] for key in
               ("dielectric_type", "material", "constant", "loss_tangent",
                "thickness_mils", "stiffener")}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "layer": matches[0]["name"], "before": old, "would_set": updates}
        params = {"board_path": board_path, "layer": matches[0]["name"]}
        for key, value in old.items():
            params[f"expect_{key}"] = ("true" if value else "false") if key == "stiffener" else str(value)
        for key, value in updates.items():
            params[key] = ("true" if value else "false") if key == "stiffener" else str(value)
        reply = await get_bridge().send_command_async("pcb.set_dielectric", params,
                                                       timeout=120.0)
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        after_stack = await pcb_physical_stack(board_path)
        if not isinstance(after_stack.get("layers"), list):
            return {"ok": False, "reason": "could not verify dielectric readback",
                    "native_reply": reply}
        after = next((item for item in after_stack["layers"]
                      if item.get("name", "").casefold() == layer.strip().casefold()), None)
        if after is None:
            return {"ok": False, "reason": "dielectric vanished after write",
                    "native_reply": reply}
        for key, value in updates.items():
            actual = after.get(key)
            matched = (math.isclose(actual, value, abs_tol=0.01) if key in
                       ("constant", "loss_tangent", "thickness_mils") and
                       isinstance(actual, (int, float)) else actual == value)
            if not matched:
                return {"ok": False, "reason": f"{key} did not read back",
                        "after": after, "native_reply": reply}
        reply["save_required"] = bool(reply.get("changed"))
        return reply

    @mcp.tool()
    async def pcb_get_impedance_profiles(board_path: str = "") -> dict[str, Any]:
        """Read Altium's own layer-stack impedance profiles for the open board.

        Returns targets, tolerances, reference layers, solved widths and gaps,
        calculated impedance, and ``read_errors`` for unavailable fields.
        The reply names the board so the result can be checked against the
        intended design.
        """
        if board_path and (not Path(board_path).is_absolute()
                           or Path(board_path).suffix.casefold() != ".pcbdoc"):
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.get_impedance_profiles",
            {"board_path": board_path} if board_path else {},
        )
        if board_path and isinstance(reply, dict) and not reply.get("error"):
            if str(reply.get("board_path", "")).casefold() != board_path.casefold():
                return {"ok": False, "reason": "wrong-board impedance profile reply",
                        "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_impedance_profile(
        board_path: str,
        action: str,
        profile: str,
        name: str = "",
        target_ohms: Optional[float] = None,
        tolerance: Optional[float] = None,
        differential: Optional[bool] = None,
        coplanar: Optional[bool] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Plan, create, change or remove one exact-board impedance profile.

        Checks the current profile count and old values before any write.
        Saving the PcbDoc is a separate operation.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        action = action.strip().lower()
        profile = profile.strip()
        name = name.strip()
        if action not in ("create", "set", "remove") or not profile:
            return {"ok": False, "reason": "action must be create/set/remove and profile required"}
        updates = {"name": name or None, "target_ohms": target_ohms,
                   "tolerance": tolerance, "differential": differential,
                   "coplanar": coplanar}
        updates = {key: value for key, value in updates.items() if value is not None}
        if action == "create" and target_ohms is None:
            return {"ok": False, "reason": "target_ohms required for create"}
        if action == "set" and not updates:
            return {"ok": False, "reason": "give at least one profile setting"}
        if action == "remove" and updates:
            return {"ok": False, "reason": "remove accepts no profile settings"}
        if action == "create" and name:
            return {"ok": False, "reason": "use profile as the new name for create"}
        for key in ("target_ohms", "tolerance"):
            if key in updates:
                value = updates[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    return {"ok": False, "reason": f"{key} must be positive and finite"}
        for key in ("differential", "coplanar"):
            if key in updates and type(updates[key]) is not bool:
                return {"ok": False, "reason": f"{key} must be boolean"}
        before = await pcb_get_impedance_profiles(board_path)
        if (not isinstance(before, dict) or before.get("board_path", "").casefold() != board_path.casefold()
                or type(before.get("profile_count")) is not int
                or type(before.get("read_errors")) is not int
                or before["read_errors"] != 0
                or not isinstance(before.get("profiles"), list)
                or len(before["profiles"]) != before["profile_count"]):
            return {"ok": False, "reason": "incomplete profile preflight", "native_reply": before}
        found = [p for p in before["profiles"] if p.get("name", "").casefold() == profile.casefold()]
        if (action == "create" and found) or (action != "create" and len(found) != 1):
            return {"ok": False, "reason": "profile existence differs from action"}
        if name and any(p.get("name", "").casefold() == name.casefold()
                        for p in before["profiles"] if p not in found):
            return {"ok": False, "reason": "new profile name already exists"}
        old = found[0] if found else None
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "action": action, "profile": profile, "before": old,
                    "would_set": updates, "profile_count": before["profile_count"]}
        params = {"board_path": board_path, "action": action, "profile": profile,
                  "expect_count": str(before["profile_count"])}
        if old is not None:
            for key in ("name", "target_ohms", "tolerance", "differential", "coplanar"):
                value = old[key]
                params[f"expect_{key}"] = ("true" if value else "false") if isinstance(value, bool) else str(value)
        for key, value in updates.items():
            params[key] = ("true" if value else "false") if isinstance(value, bool) else str(value)
        reply = await get_bridge().send_command_async("pcb.impedance_profile", params,
                                                       timeout=120.0)
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        after = await pcb_get_impedance_profiles(board_path)
        expected_count = before["profile_count"] + (1 if action == "create" else -1 if action == "remove" else 0)
        if (not isinstance(after, dict) or after.get("board_path", "").casefold() != board_path.casefold()
                or after.get("profile_count") != expected_count
                or after.get("read_errors") != 0
                or not isinstance(after.get("profiles"), list)):
            return {"ok": False, "reason": "profile count/readback failed", "native_reply": reply,
                    "after": after}
        result_name = name or profile
        matches = [p for p in after["profiles"] if p.get("name", "").casefold() == result_name.casefold()]
        if (action == "remove" and matches) or (action != "remove" and len(matches) != 1):
            return {"ok": False, "reason": "profile identity readback failed", "after": after}
        if action != "remove":
            for key, value in updates.items():
                actual = matches[0].get(key)
                if key in ("target_ohms", "tolerance"):
                    matched = isinstance(actual, (int, float)) and math.isclose(actual, value, abs_tol=0.001)
                else:
                    matched = actual == value
                if not matched:
                    return {"ok": False, "reason": f"{key} did not read back", "after": after}
        reply["save_required"] = True
        return reply

    @mcp.tool()
    async def pcb_impedance_profile_layer(
        board_path: str,
        profile: str,
        layer: str,
        enabled: Optional[bool] = None,
        width_locked: Optional[bool] = None,
        gap_locked: Optional[bool] = None,
        width_mils: Optional[float] = None,
        min_width_mils: Optional[float] = None,
        max_width_mils: Optional[float] = None,
        gap_mils: Optional[float] = None,
        min_gap_mils: Optional[float] = None,
        max_gap_mils: Optional[float] = None,
        clearance_to_plane_mils: Optional[float] = None,
        use_solder_mask: Optional[bool] = None,
        mask_between_mils: Optional[float] = None,
        mask_on_top_mils: Optional[float] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read or plan/set one impedance profile's copper-layer settings.

        An absent profile-layer entry is reported as ``after=null`` and is
        created by a write. Save the exact PcbDoc separately.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not profile.strip() or not layer.strip():
            return {"ok": False, "reason": "profile and layer required"}
        updates = {"enabled": enabled, "width_locked": width_locked,
                   "gap_locked": gap_locked, "width_mils": width_mils,
                   "min_width_mils": min_width_mils,
                   "max_width_mils": max_width_mils, "gap_mils": gap_mils,
                   "min_gap_mils": min_gap_mils, "max_gap_mils": max_gap_mils,
                   "clearance_to_plane_mils": clearance_to_plane_mils,
                   "use_solder_mask": use_solder_mask,
                   "mask_between_mils": mask_between_mils,
                   "mask_on_top_mils": mask_on_top_mils}
        updates = {key: value for key, value in updates.items() if value is not None}
        bool_fields = {"enabled", "width_locked", "gap_locked", "use_solder_mask"}
        for key, value in updates.items():
            if key in bool_fields:
                if type(value) is not bool:
                    return {"ok": False, "reason": f"{key} must be boolean"}
            elif type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                return {"ok": False, "reason": f"{key} must be nonnegative and finite"}
        base = {"board_path": board_path, "profile": profile.strip(), "layer": layer.strip()}
        bridge = get_bridge()

        def checked(reply: Any) -> dict[str, Any]:
            if (not isinstance(reply, dict)
                    or str(reply.get("board_path", "")).casefold() != board_path.casefold()
                    or str(reply.get("profile", "")).casefold() != profile.strip().casefold()
                    or str(reply.get("layer", "")).casefold() != layer.strip().casefold()
                    or type(reply.get("profile_count")) is not int
                    or not isinstance(reply.get("profile_token"), str)
                    or not isinstance(reply.get("state_token"), str)
                    or reply.get("after") is not None and not isinstance(reply.get("after"), dict)):
                raise ValueError("incomplete or wrong-board profile-layer reply")
            return reply

        first = await bridge.send_command_async("pcb.impedance_profile_layer", base,
                                                timeout=120.0)
        try:
            old_reply = checked(first)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": first}
        if not updates:
            return old_reply
        if dry_run:
            return {"ok": True, "dry_run": True, **base,
                    "before": old_reply["after"], "would_set": updates,
                    "layer_would_be_added": old_reply["after"] is None}
        params = {**base, "expect_count": str(old_reply["profile_count"]),
                  "expect_profile_token": old_reply["profile_token"],
                  "expect_state_token": old_reply["state_token"]}
        for key, value in updates.items():
            params[key] = ("true" if value else "false") if key in bool_fields else str(value)
        reply = await bridge.send_command_async("pcb.impedance_profile_layer", params,
                                                timeout=120.0)
        try:
            changed = checked(reply)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reply}
        reread = await bridge.send_command_async("pcb.impedance_profile_layer", base,
                                                 timeout=120.0)
        try:
            confirmed = checked(reread)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reread}
        state = confirmed["after"]
        if state is None:
            return {"ok": False, "reason": "profile layer absent after write"}
        for key, value in updates.items():
            actual = state.get(key)
            matched = (actual is value if key in bool_fields else
                       type(actual) in (int, float) and math.isclose(actual, value, abs_tol=0.01))
            if not matched:
                return {"ok": False, "reason": f"{key} did not read back",
                        "after": state, "native_reply": reply}
        changed["save_required"] = bool(changed.get("changed"))
        return changed

    @mcp.tool()
    async def pcb_pours_at(
        x: float,
        y: float,
        expect_file: str = "",
    ) -> dict[str, Any]:
        """List pours whose outline contains a point in board-relative mils.

        The reply includes ``board_file`` and reports outline inclusion,
        including a gap where the poured copper itself is absent. Supply
        ``expect_file`` to refuse a read from a different focused board.
        """
        import math

        if not (math.isfinite(x) and math.isfinite(y)):
            return {"success": False, "error": "x and y must be finite"}
        reply = await get_bridge().send_command_async(
            "pcb.pours_at", {"x": repr(float(x)), "y": repr(float(y)),
                             "expect_file": expect_file})
        if expect_file and (not isinstance(reply, dict)
                            or not isinstance(reply.get("board_file"), str)
                            or reply["board_file"].casefold() != expect_file.casefold()):
            return {"ok": False, "reason": "pour read did not identify the requested board",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_board_options(
        polygon_name_template: Optional[int] = None,
        expect_file: str = "",
    ) -> dict[str, Any]:
        """Read board naming options, or set the new-pour name template.

        A write requires the exact focused ``expect_file``. The reply
        includes the actual board path, value readback and ``not_applied``.
        ``automatic_split_planes`` is read only.
        """
        params: dict[str, Any] = {"expect_file": expect_file}
        if polygon_name_template is not None:
            if polygon_name_template < 0:
                return {"success": False, "error":
                        "polygon_name_template must be nonnegative"}
            if not expect_file:
                return {"success": False, "error":
                        "expect_file is required to change board options"}
            params["polygon_name_template"] = str(polygon_name_template)
        reply = await get_bridge().send_command_async("pcb.board_options", params)
        if expect_file and (not isinstance(reply, dict)
                            or not isinstance(reply.get("board_file"), str)
                            or reply["board_file"].casefold() != expect_file.casefold()):
            return {"ok": False, "reason": "board options did not identify the requested board",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_query_region(
        object_type: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: str = "",
        properties: str = "ObjectId,X,Y,Layer,Net,Name",
        filter: str = "",
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Query PCB primitives intersecting a rectangular area.

        Uses ``IPCB_Board.SpatialIterator_Create`` and therefore avoids a
        whole-board scan. Group objects such as components and dimensions are
        not spatial-iterator primitives; query their children (pads, tracks,
        arcs, fills, regions) or use their dedicated getters instead.

        Args:
            object_type: PCB primitive constant such as ``eTrackObject``,
                ``ePadObject``, ``eViaObject``, ``eArcObject`` or
                ``eTextObject``.
            x1, y1, x2, y2: Opposite rectangle corners in mils.
            layer: Optional exact PCB layer; empty searches all layers.
            properties: Flat PCB property names accepted by ``obj_query``.
                ``Owner`` is an alias for the owning component designator
                (``Component``); it is empty for a free primitive.
            filter: Optional property=value filters joined with ``|``.
            limit: Maximum returned primitives (1..10000).

        Returns:
            Dict with objects, count, normalized bounds, layer, board path and
            an explicit truncation flag.
        """
        requested_properties = [name.strip() for name in properties.split(",")]
        wire_properties = ",".join(
            "Component" if name == "Owner" else name
            for name in requested_properties
        )
        wire_filter = "|".join(
            "Component=" + clause.split("=", 1)[1]
            if clause.startswith("Owner=") else clause
            for clause in filter.split("|")
        )
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.query_region",
            {
                "object_type": object_type,
                "x1": str(x1), "y1": str(y1),
                "x2": str(x2), "y2": str(y2),
                "layer": layer,
                "properties": wire_properties,
                "filter": wire_filter,
                "limit": str(limit),
            },
        )
        if "Owner" in requested_properties and isinstance(result, dict):
            for obj in result.get("objects", []):
                if isinstance(obj, dict):
                    obj["Owner"] = obj.get("Component", "")
                    if "Component" not in requested_properties:
                        obj.pop("Component", None)
        return result

    @mcp.tool()
    async def pcb_get_used_layers() -> dict[str, Any]:
        """Return PCB layers that actually contain design primitives.

        This reads ``IPCB_Board.LayerIsUsed``. It is intentionally different
        from ``pcb_get_layer_display``: a hidden layer can still contain
        fabrication or copper data, while a visible layer can be empty.

        Returns:
            Dict with ``layers`` (layer id, user name, displayed), ``count``,
            ``scanned_count``, ``unreadable_count`` and ``board_path``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.get_used_layers", {})

    @mcp.tool()
    async def pcb_get_drill_layer_pairs() -> dict[str, Any]:
        """Return every through/blind/buried drill span on the active PCB.

        Reads the documented ``DrillLayerPairsCount`` and
        ``LayerPair[index]`` interfaces. This is the authoritative way to
        check whether via drilling spans match the intended stackup.

        Returns:
            Dict with ``layer_pairs`` (index, low_layer, high_layer),
            ``count``, ``reported_count``, ``unreadable_count`` and board path.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.get_drill_layer_pairs", {})

    @mcp.tool()
    async def pcb_get_internal_planes() -> dict[str, Any]:
        """Return internal-plane layers and their assigned net names.

        Only planes physically present in the current layer stack are
        returned. ``net_read`` distinguishes an unassigned plane (empty name)
        from an Altium build that did not expose the net-name accessor.

        Returns:
            Dict with ``internal_planes`` (layer, name, net_name, net_read,
            displayed), ``count``, ``unreadable_net_count`` and board path.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.get_internal_planes", {})

    @mcp.tool()
    async def pcb_get_special_strings(limit: int = 1000) -> dict[str, Any]:
        """Read authored and rendered PCB special strings.

        For text such as ``.Designator``, ``.PCB_FILE_NAME`` or
        ``.LAYER_NAME``, returns both the raw token and Altium's
        ``ConvertedString`` used by output generation. This avoids mistaking
        rendered display text for the authored token.

        Args:
            limit: Maximum special strings returned (1..10000).

        Returns:
            Dict with ``special_strings`` (raw, converted, layer and location),
            ``count``, ``limit``, ``truncated`` and ``board_path``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.get_special_strings", {"limit": str(limit)},
        )

    @mcp.tool()
    async def pcb_export_stackup_csv(output_path: str = "") -> dict[str, Any]:
        """Write the layer stackup to a conventional fab CSV report.

        Fetches the structured stackup (``pcb_get_layer_stackup``) and writes
        it as the board-house stackup table: one row per physical layer,
        copper and dielectric interleaved top-to-bottom, thickness in mil and
        mm, dielectric constant where it applies. Columns: index, layer, type,
        material, thickness_mil, thickness_mm, dielectric_constant.

        Args:
            output_path: Destination .csv file. Defaults to
                ``workspace/<board>_stackup.csv``.

        Returns:
            {"output_path", "rows", "layer_count", "total_thickness_mils"} or
            an error dict if the board / stackup could not be read.
        """
        from pathlib import Path

        from ..config import get_config
        from ..export.stackup_csv import (
            format_stackup_csv,
            stackup_total_thickness_mils,
        )

        bridge = get_bridge()
        stackup = await bridge.send_command_async("pcb.get_layer_stackup", {})
        if not isinstance(stackup, dict) or "layers" not in stackup:
            return {"success": False,
                    "error": "could not read layer stackup (open a .PcbDoc)"}

        csv_text = format_stackup_csv(stackup)
        if output_path:
            out = Path(output_path)
        else:
            board = str(stackup.get("board_name") or "board").strip() or "board"
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in board)
            out = get_config().workspace_dir / f"{safe}_stackup.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(csv_text, encoding="utf-8")

        # rows = data rows (exclude the header line).
        rows = max(0, csv_text.count("\n") - 1)
        return {
            "success": True,
            "output_path": str(out),
            "rows": rows,
            "layer_count": stackup.get("layer_count", len(stackup.get("layers") or [])),
            "total_thickness_mils": round(stackup_total_thickness_mils(stackup), 3),
        }

    @mcp.tool()
    async def pcb_order_copper_layer(
        board_path: str,
        action: str = "list",
        layer: str = "",
        above: str = "",
        below: str = "",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """List, insert or move a copper layer relative to another layer.

        Insert accepts a free MidLayer1..30 or InternalPlane1..16 ID.
        Move accepts an existing layer. Changes require an exact board path
        and the complete old copper order; saving is separate.
        """
        import re

        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        action = action.strip().lower()
        layer, above, below = layer.strip(), above.strip(), below.strip()
        if action not in ("list", "insert", "move"):
            return {"ok": False, "reason": "action must be list, insert or move"}
        if action != "list" and not layer:
            return {"ok": False, "reason": "layer is required"}
        if above and below or action == "move" and not (above or below):
            return {"ok": False, "reason": "give exactly one above or below reference for move"}
        if action == "insert" and not re.fullmatch(
                r"(?i)(?:MidLayer(?:[1-9]|[12][0-9]|30)|InternalPlane(?:[1-9]|1[0-6]))",
                layer):
            return {"ok": False, "reason": "insert layer must be MidLayer1..30 or InternalPlane1..16"}
        bridge = get_bridge()
        base = {"board_path": board_path, "action": "list"}

        async def read_order() -> dict[str, Any]:
            result = await bridge.send_command_async("pcb.order_copper_layer", base,
                                                     timeout=120.0)
            if (not isinstance(result, dict)
                    or str(result.get("board_path", "")).casefold() != board_path.casefold()
                    or type(result.get("count")) is not int
                    or not isinstance(result.get("order"), list)
                    or not isinstance(result.get("canonical_order"), list)
                    or len(result["order"]) != result["count"]
                    or len(result["canonical_order"]) != result["count"]
                    or not isinstance(result.get("order_token"), str)):
                return {"ok": False, "reason": "incomplete or wrong-board copper order",
                        "native_reply": result}
            return result

        before = await read_order()
        if "order" not in before:
            return before
        if action == "list":
            return before
        names = [name.casefold() for name in before["order"]]
        canonical = [name.casefold() for name in before["canonical_order"]]
        target = layer.casefold()
        reference = (above or below).casefold()
        if action == "insert" and target in canonical:
            return {"ok": False, "reason": "layer ID already in stack under an existing name"}
        if action == "move" and target not in names:
            return {"ok": False, "reason": "layer not in stack"}
        if reference and (reference not in names or reference == target):
            return {"ok": False, "reason": "reference layer missing or same as target"}
        if action == "move":
            distance = names.index(target) - names.index(reference)
            if distance == (-1 if above else 1):
                return {"ok": True, "board_path": board_path, "action": action,
                        "changed": False, "save_required": False,
                        "order_before": before["order"], "order_after": before["order"]}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "action": action, "layer": layer, "above": above, "below": below,
                    "order_before": before["order"]}
        params = {"board_path": board_path, "action": action, "layer": layer,
                  "expect_order": before["order_token"]}
        if above:
            params["above"] = above
        if below:
            params["below"] = below
        reply = await bridge.send_command_async("pcb.order_copper_layer", params,
                                                timeout=120.0)
        if (not isinstance(reply, dict)
                or str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or not isinstance(reply.get("order_after"), list)
                or reply.get("order_before") != before["order"]):
            return {"ok": False, "reason": "native copper-order reply failed",
                    "native_reply": reply}
        after = await read_order()
        if "order" not in after or after["order"] != reply["order_after"]:
            return {"ok": False, "reason": "independent copper-order readback failed",
                    "native_reply": reply, "after": after}
        expected_count = before["count"] + (1 if action == "insert" else 0)
        order = [name.casefold() for name in after["order"]]
        result_name = str(reply.get("target_name", "")).casefold()
        if after["count"] != expected_count or order.count(result_name) != 1:
            return {"ok": False, "reason": "target layer count/readback failed",
                    "after": after}
        if reference:
            ref_name = str(reply.get("reference_name", "")).casefold()
            if ref_name not in order or ref_name != reference:
                return {"ok": False, "reason": "reference identity changed", "after": after}
            distance = order.index(result_name) - order.index(ref_name)
            if distance != (-1 if above else 1):
                return {"ok": False, "reason": "requested layer position did not take",
                        "after": after}
        reply["save_required"] = bool(reply.get("changed"))
        return reply

    @mcp.tool()
    async def pcb_add_layer(layer: str, above: str = "", below: str = "") -> dict[str, Any]:
        """Insert a copper layer into the PCB layer stack.

        Valid names include MidLayer1..MidLayer30 (signal layers) and
        InternalPlane1..InternalPlane16 (power / ground planes). Top / Bottom
        are always present, they cannot be added. With ``above`` or
        ``below`` (a layer already in the stack) it goes in at that place;
        otherwise Altium chooses.

        Args:
            layer: Layer name, e.g. "MidLayer1", "InternalPlane1"
            above: Put it directly above this layer.
            below: Put it directly below this layer.

        Returns:
            ``layer`` and ``stack_order``, the copper layers top down.
        """
        if above.strip() and below.strip():
            return {"ok": False, "reason": "give above or below, not both"}
        params: dict[str, Any] = {"layer": layer}
        if above.strip():
            params["above"] = above.strip()
        if below.strip():
            params["below"] = below.strip()
        return await get_bridge().send_command_async("pcb.add_layer", params)

    @mcp.tool()
    async def pcb_remove_layer(layer: str) -> dict[str, Any]:
        """Remove a copper layer from the PCB layer stack.

        Calls IPCB_LayerStack.RemoveFromStack on the requested layer.
        Does nothing if the layer is not currently in the stack.

        Args:
            layer: Layer name, e.g. "MidLayer1", "InternalPlane2"

        Returns:
            Dictionary confirming the layer was removed.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.remove_layer", {"layer": layer}
        )
        return result

    @mcp.tool()
    async def pcb_modify_layer(
        layer: str,
        name: str = "",
        copper_thickness_mils: float = 0.0,
        dielectric_type: str = "",
        dielectric_height_mils: float = 0.0,
        dielectric_constant: float = 0.0,
        dielectric_material: str = "",
    ) -> dict[str, Any]:
        """Tune properties on an existing copper layer.

        Every optional parameter is applied only if provided (non-empty
        string / non-zero number). Maps to:
          name                   IPCB_LayerObject.Name
          copper_thickness_mils  IPCB_LayerObject.CopperThickness
          dielectric_type        Dielectric.DielectricType
                                 (one of "none", "core", "prepreg", "surface")
          dielectric_height_mils Dielectric.DielectricHeight
          dielectric_constant    Dielectric.DielectricConstant
          dielectric_material    Dielectric.DielectricMaterial

        Args:
            layer: Target layer name, e.g. "MidLayer1"
            name: New layer name (optional)
            copper_thickness_mils: New copper thickness in mils, fractional
                (1 oz is 1.378) (optional)
            dielectric_type: "none" | "core" | "prepreg" | "surface" (optional)
            dielectric_height_mils: New dielectric height in mils, fractional
                (optional)
            dielectric_constant: New Dk value (optional)
            dielectric_material: New dielectric material string (optional)

        Returns:
            Dictionary confirming the changes.
        """
        bridge = get_bridge()
        params: dict[str, str] = {"layer": layer}
        if name:
            params["name"] = name
        if copper_thickness_mils:
            params["copper_thickness_mils"] = f"{copper_thickness_mils:g}"
        if dielectric_type:
            params["dielectric_type"] = dielectric_type
        if dielectric_height_mils:
            params["dielectric_height_mils"] = f"{dielectric_height_mils:g}"
        if dielectric_constant:
            params["dielectric_constant"] = str(dielectric_constant)
        if dielectric_material:
            params["dielectric_material"] = dielectric_material
        result = await bridge.send_command_async("pcb.modify_layer", params)
        return result

    @mcp.tool()
    async def pcb_configure_multilayer_stackup(
        operations: list[dict[str, Any]],
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Apply a validated sequence of multilayer stack operations.

        Each operation has ``action`` = ``add``, ``modify``, or ``remove``.
        Add/remove require ``layer``. Modify accepts the same fields as
        ``pcb_modify_layer``: name, copper thickness, dielectric type/height,
        dielectric constant, and material. Dry-run is the default because
        layer-stack changes can invalidate existing routing.
        """
        normalized = []
        for index, raw in enumerate(operations):
            op = dict(raw)
            action = str(op.pop("action", "modify")).lower()
            layer = str(op.get("layer", ""))
            if action not in {"add", "modify", "remove"} or not layer:
                return {"success": False, "reason": f"invalid operation {index}"}
            if action == "modify":
                dtype = str(op.get("dielectric_type", ""))
                if dtype and dtype.lower() not in {"none", "core", "prepreg", "surface"}:
                    return {"success": False, "reason": f"invalid dielectric_type in operation {index}"}
                for key in ("copper_thickness_mils", "dielectric_height_mils"):
                    if key in op and float(op[key]) < 0:
                        return {"success": False, "reason": f"negative {key} in operation {index}"}
                if "dielectric_constant" in op and float(op["dielectric_constant"]) <= 0:
                    return {"success": False, "reason": f"invalid dielectric_constant in operation {index}"}
            normalized.append({"action": action, **op})
        if dry_run:
            return {"success": True, "dry_run": True, "operations": normalized,
                    "warning": "Stack changes can invalidate existing routing."}
        bridge = get_bridge()
        results = []
        for op in normalized:
            action = op["action"]
            command = {"add": "pcb.add_layer", "modify": "pcb.modify_layer",
                       "remove": "pcb.remove_layer"}[action]
            params = {k: str(v) for k, v in op.items() if k != "action" and v != ""}
            result = await bridge.send_command_async(command, params)
            results.append({"operation": op, "result": result})
        return {"success": True, "dry_run": False, "results": results,
                "operations_applied": len(results)}

    @mcp.tool()
    async def pcb_apply_impedance_rules(
        rule_name: str,
        scope: str,
        target_ohms: float,
        geometry: str,
        dielectric_height_mils: float,
        dielectric_constant: float,
        copper_oz: float = 1.0,
        spacing_mils: float = 0.0,
        width_tolerance_mils: int = 1,
        gap_tolerance_mils: int = 1,
        max_uncoupled_length_mils: int = 100,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Size and optionally create controlled-impedance PCB rules.

        Creates a Width rule and, for ``*_diff`` geometries, a Differential
        Pairs Routing gap rule. Values come from the existing verified inverse
        impedance calculator. Closed-form sizing is an initial engineering
        value; fabrication-house field-solver values remain authoritative.
        """
        from ..design.impedance_sizing import trace_width_for_impedance

        try:
            sized = trace_width_for_impedance(
                target_ohms, geometry, dielectric_height_mils,
                dielectric_constant=dielectric_constant,
                copper_oz=copper_oz,
                spacing_mils=spacing_mils,
            )
        except (TypeError, ValueError) as exc:
            return {"success": False, "reason": str(exc)}
        if not sized.feasible:
            return {"success": False, "reason": "target impedance is infeasible",
                    "sizing": sized.__dict__}
        width = max(1, round(sized.width_mils))
        rules = [{
            "rule_type": "width", "name": f"{rule_name}_WIDTH",
            "value": max(1, width - width_tolerance_mils),
            "max_value": width + width_tolerance_mils,
            "favored_value": width, "scope": scope,
        }]
        is_diff = geometry.lower().endswith("_diff")
        if is_diff:
            if spacing_mils <= 0:
                return {"success": False, "reason": "spacing_mils is required for differential geometry"}
            gap = max(1, round(spacing_mils))
            rules.append({
                "rule_type": "differential_pairs",
                "name": f"{rule_name}_GAP",
                "value": max(1, gap - gap_tolerance_mils),
                "max_value": gap + gap_tolerance_mils,
                "favored_value": gap, "scope": scope,
                "max_uncoupled_length": max_uncoupled_length_mils,
            })
        plan = {"success": True, "dry_run": dry_run, "target_ohms": target_ohms,
                "geometry": geometry, "sizing": sized.__dict__, "rules": rules,
                "fab_field_solver_required": True}
        if dry_run:
            return plan
        bridge = get_bridge()
        plan["apply_results"] = [
            await bridge.send_command_async(
                "pcb.create_design_rule", {k: str(v) for k, v in rule.items()}
            ) for rule in rules
        ]
        return plan

    @mcp.tool()
    async def pcb_check_stackup(
        template: str,
        thickness_tol_pct: float = 5.0,
        er_tol: float = 0.05,
    ) -> dict[str, Any]:
        """Compare the active board's stack-up with a fab stack-up.

        Reads the board (``pcb_get_layer_stackup``) and compares copper
        thickness, the dielectric height under each copper layer and its
        Dk with the template (``design_list_stackups``). The board keeps
        one dielectric per copper gap; a template gap of several plies is
        summed (heights) and thickness-weighted (Dk) first, so a correct
        board is not reported wrong for having fewer entries. A different
        copper count is ONE finding. Read only.

        Args:
            template: stack-up name, e.g. "JLC04161H-7628"
            thickness_tol_pct: allowed difference in thickness, percent
            er_tol: allowed difference in Dk

        Returns:
            ``{"ok": True, "matches": bool, "findings": [...], "board":
            {...}}`` or the bridge's error.
        """
        bridge = get_bridge()
        board = await bridge.send_command_async("pcb.get_layer_stackup", {})
        if not isinstance(board, dict) or "layers" not in board:
            return {"ok": False, "reason": "could not read the board stack-up",
                    "board": board}
        got = fab_library.compare_stackup(board, template,
                                          thickness_tol_pct=thickness_tol_pct,
                                          er_tol=er_tol)
        got["board"] = board.get("board_name")
        return got

    @mcp.tool()
    async def pcb_apply_stackup_template(
        template: str, dry_run: bool = True,
    ) -> dict[str, Any]:
        """Give the active board a fab stack-up's thicknesses and Dk.

        A dry run by default: it returns the ``pcb_modify_layer`` calls it
        would make. With ``dry_run=False`` it makes them, each read back.
        Existing layers only: a board with a different copper count is
        refused (add or remove layers in Altium's Layer Stack Manager
        first; inventing a layer name on a routed board is worse than
        asking). If a call fails part way, the result says which layers
        changed and which did not, since a half-applied stack-up is worse
        than none and has to be finished or undone knowingly.

        Args:
            template: stack-up name, e.g. "JLC04161H-7628"
            dry_run: True to only plan (default)

        Returns:
            ``{"ok", "template", "calls", "dry_run"}``, plus per-layer
            ``results`` and ``changed`` / ``not_changed`` when applied.
        """
        bridge = get_bridge()
        board = await bridge.send_command_async("pcb.get_layer_stackup", {})
        if not isinstance(board, dict) or "layers" not in board:
            return {"ok": False, "reason": "could not read the board stack-up",
                    "board": board}
        plan = fab_library.plan_apply(board, template)
        if not plan["ok"] or dry_run:
            return {**plan, "dry_run": dry_run}
        results, changed, not_changed = [], [], []
        for call in plan["calls"]:
            params = {k: (f"{v:g}" if isinstance(v, float) else str(v))
                      for k, v in call.items()}
            try:
                res = await bridge.send_command_async("pcb.modify_layer", params)
            except Exception as exc:                        # noqa: BLE001
                res = {"success": False, "error": str(exc)}
            results.append({"layer": call["layer"], "result": res})
            ok = isinstance(res, dict) and res.get("success") is not False \
                and not res.get("rejected") and "error" not in res
            (changed if ok else not_changed).append(call["layer"])
        return {"ok": not not_changed, "template": plan["template"],
                "dry_run": False, "calls": plan["calls"], "results": results,
                "changed": changed, "not_changed": not_changed}

    @mcp.tool()
    async def pcb_set_plane_net(layer: str, net: str) -> dict[str, Any]:
        """Tie an internal plane layer to a net.

        A plane is a negative layer whose net belongs to the layer, so a
        polygon poured on it connects nothing. Use this rather than ``pcb_place_polygon_rect``
        to make a plane carry a net.

        The net must exist on the board. A signal layer is refused
        (``NOT_A_PLANE``) and a layer the board lacks is ``UNKNOWN_LAYER``;
        "Internal Plane 1" and "InternalPlane1" both work. The net is
        read back, and if it did not take the reply is ``success: false``,
        ``applied: false``, with the board left unmarked.

        Args:
            layer: Internal plane layer, e.g. "InternalPlane1" or the name
                the stackup reports for it
            net: Existing net name to tie the plane to, e.g. "PGND"

        Returns:
            Dictionary with "success", "layer" (the RESOLVED layer),
            "layer_name", "net", "net_readback", "applied", "route" (which
            write took) and "note".
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.set_plane_net", {"layer": layer, "net": net}
        )
        return result

    @mcp.tool()
    async def pcb_get_board_outline() -> dict[str, Any]:
        """Get the board outline vertices and bounding rectangle.

        Returns outline geometry as a list of vertices (line segments and
        arcs) plus the bounding rectangle dimensions.

        Returns:
            Dictionary with "point_count", "vertices" array (each with
            index, kind, x, y, and optionally cx, cy, angle1, angle2 for arcs),
            "closing" (the vertex saved after the last, which must equal
            the first) with "closed", and "bounding_rect" (left, bottom,
            right, top in mils)
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_board_outline", {})
        return result

    @mcp.tool()
    async def pcb_get_selected_objects(
        properties: str = "ObjectId,X,Y,Layer,Net",
    ) -> dict[str, Any]:
        """Get properties of currently selected objects on the active PCB.

        Args:
            properties: Comma-separated property names to return.
                Available: ObjectId, X, Y, X1, Y1, X2, Y2, Layer, Net,
                Width, Name, Rotation, HoleSize, TopXSize, TopYSize,
                Size, Pattern, SourceDesignator, Text, Descriptor, Selected

        Returns:
            Dictionary with "objects" array and "count"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.get_selected_objects",
            {"properties": properties},
        )
        return result

    @mcp.tool()
    async def pcb_set_layer_visibility(
        layer: str = "",
        visible: bool = True,
        layers: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Show or hide a PCB layer, or several.

        Args:
            layers: Several layer names to set at once (a list, or a JSON
                list as text), instead of ``layer``.
            layer: Layer name string, e.g.:
                Copper: "TopLayer", "BottomLayer", "MidLayer1"-"MidLayer30"
                Overlay: "TopOverlay", "BottomOverlay"
                Mask: "TopPaste", "BottomPaste", "TopSolder", "BottomSolder"
                Plane: "InternalPlane1"-"InternalPlane16"
                Other: "DrillGuide", "DrillDrawing", "MultiLayer",
                       "KeepOutLayer", "Mechanical1"-"Mechanical16"
            visible: True to show, False to hide

        Returns:
            Dictionary with layer name and visibility state
        """
        bridge = get_bridge()
        names = _layer_names(layer, layers)
        if not names:
            return {"success": False, "error": "give a layer, or layers"}
        if len(names) == 1:
            return await bridge.send_command_async(
                "pcb.set_layer_visibility",
                {"layer": names[0], "visible": "true" if visible else "false"})
        results = []
        for name in names:
            results.append(await bridge.send_command_async(
                "pcb.set_layer_visibility",
                {"layer": name, "visible": "true" if visible else "false"}))
        failed = [n for n, r in zip(names, results)
                  if isinstance(r, dict) and r.get("success") is False]
        return {"success": not failed, "visible": visible, "layers": names,
                "failed": failed, "results": results}

    @mcp.tool()
    async def pcb_repour_polygons(
        names: Optional[list[str]] = None,
        indices: Optional[list[int]] = None,
        exclude: Optional[list[str]] = None,
        board_path: str = "",
        timeout: float = 60.0,
        clean_first: bool = False,
        empty_only: bool = False,
    ) -> dict[str, Any]:
        """Repour poured polygons on the open PCB, in pour order.

        Each polygon is rebuilt through the API, so a changed clearance
        or board-edge rule takes effect. Shelved polygons stay shelved.
        ``repoured`` is true only when at least one polygon was rebuilt
        and none failed; each item reports its copper pieces and poured
        area before and after, so a repour that changed nothing shows.

        With no filter every polygon is repoured. ``names`` and
        ``indices`` (places in the board's polygon order, as
        pcb_modify_polygon counts them) pick polygons and add up;
        ``exclude`` drops names and wins. Use them to redo many small
        pours quickly and a slow hatched one once, at the end.

        A large hatched pour can take minutes. The call waits up to 30
        times ``timeout`` while Altium reports it is still working, so
        the default of 60 s allows 30 minutes.

        Args:
            names: Polygon names to repour (any case).
            indices: Polygon indices to repour.
            exclude: Polygon names to leave alone.
            board_path: The .PcbDoc to act on. Empty uses the open board;
                a path is refused unless that file is the board opened.
            timeout: Seconds per wait window, see above.
            clean_first: Empty every selected poured polygon before any
                is rebuilt. Use it after polygons were moved: otherwise
                an early pour flows around later pours' stale copper and
                a later one can then fill the space it left.
            empty_only: Empty the selected poured polygons and rebuild
                none, leaving them with no copper until the next repour.
                For a command that avoids pour copper, such as
                Teardrops, so that the pours are poured around its result.

        Returns:
            ``repoured``, counts of ``polygons`` (selected), ``skipped``,
            ``rebuilt``, ``shelved`` and ``failed``, ``clean``, ``empty``
            and ``cleared_primitives``, per-polygon ``items``, and
            ``not_found``: requested names no polygon has.
        """
        for name in (names or []) + (exclude or []):
            if "|" in str(name):
                return {"repoured": False,
                        "error": f"polygon name {name!r} holds '|', which the "
                                 "request cannot carry"}
        params: dict[str, Any] = {}
        if names:
            params["names"] = "|".join(str(n) for n in names)
        if indices:
            params["indices"] = "|".join(str(int(i)) for i in indices)
        if exclude:
            params["exclude"] = "|".join(str(n) for n in exclude)
        if board_path:
            params["board_path"] = board_path
        if clean_first:
            params["clean"] = "true"
        if empty_only:
            params["empty"] = "true"
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.repour_polygons", params,
                                                 timeout=timeout)
        if isinstance(result, dict) and names:
            found = {str(it.get("name", "")).upper() for it in result.get("items") or []}
            dropped = {str(n).upper() for n in exclude or []}
            result["not_found"] = [n for n in names if str(n).upper() not in found
                                   and str(n).upper() not in dropped]
        return result

    @mcp.tool()
    async def pcb_polygon_repour_mode(mode: str = "") -> dict[str, Any]:
        """Read or set Altium's "Repour Polygons After Modification" preference.

        With ``always``, editing anything a pour touches rebuilds that pour
        after the edit, and a large hatched pour (tens of thousands of
        pieces) can then take minutes per edit. Set ``never`` before a run
        of geometry edits and repour once at the end with
        pcb_repour_polygons, which rebuilds whatever this is set to. Put
        the user's setting back afterwards: it is an application
        preference, not a board property, and it stays until changed.

        Args:
            mode: "" reads only; "never", "threshold" or "always" sets it.

        Returns:
            {"mode_before", "mode", "before", "after"}: names and Altium's
            raw values (0 never, 1 threshold, 2 always).
        """
        names = {0: "never", 1: "threshold", 2: "always"}
        mode = (mode or "").strip().lower()
        if mode and mode not in names.values():
            return {"success": False,
                    "error": f"mode must be never, threshold or always; got {mode!r}"}
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.polygon_repour_mode", {"mode": mode} if mode else {})
        if isinstance(result, dict) and "after" in result:
            result["mode_before"] = names.get(result.get("before"), "unknown")
            result["mode"] = names.get(result.get("after"), "unknown")
        return result

    @mcp.tool()
    async def pcb_set_board_shape(
        x1: float = 0,
        y1: float = 0,
        x2: float = 0,
        y2: float = 0,
        shape: str = "rectangle",
        center_x: float = 0,
        center_y: float = 0,
        radius: float = 0,
        points: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        """Define the physical PCB board outline: a rectangle, a circle or
        a polygon.

        Overwrites the current board shape. Use this right after creating a
        new PCB document to establish the board size before placing parts.
        Coordinates are in mils.

        Args:
            x1: rectangle: first corner X.
            y1: rectangle: first corner Y.
            x2: rectangle: opposite corner X (corners in any order).
            y2: rectangle: opposite corner Y.
            shape: "rectangle" (default), "circle" or "polygon".
            center_x: circle: centre X.
            center_y: circle: centre Y.
            radius: circle: radius.
            points: polygon: the vertices in order, three or more, not
                repeating the first at the end. Each is ``[x, y]`` (a
                straight edge to the next vertex) or ``{"x", "y",
                "arc_center": [cx, cy], "clockwise": false}`` (an arc
                about that centre to the next vertex, counter-clockwise
                unless ``clockwise``). A round board with mounting tabs
                is arcs of the board circle between straight tab sides
                and an arc around each hole.

        Returns:
            ``success`` and the shape as written.
        """
        bridge = get_bridge()
        kind = str(shape or "rectangle").strip().lower()
        if kind == "circle":
            if radius <= 0:
                return {"success": False, "error": "a circle needs a positive radius"}
            return await bridge.send_command_async(
                "pcb.set_board_shape",
                {"shape": "circle", "cx": _mils(center_x),
                 "cy": _mils(center_y), "radius": _mils(radius)})
        if kind == "polygon":
            encoded, problem = _outline_vertices(points or [])
            if problem:
                return {"success": False, "error": problem}
            return await bridge.send_command_async(
                "pcb.set_board_shape",
                {"shape": "polygon", "points": encoded})
        if kind != "rectangle":
            return {"success": False,
                    "error": f"shape {shape!r} is not rectangle, circle or polygon"}
        result = await bridge.send_command_async(
            "pcb.set_board_shape",
            {"x1": _mils(x1), "y1": _mils(y1), "x2": _mils(x2), "y2": _mils(y2)},
        )
        return result

    @mcp.tool()
    async def pcb_place_polygon_rect(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        net: str = "",
        layer: str = "TopLayer",
        pour_over: bool = True,
        remove_dead: bool = True,
        pour: bool = True,
    ) -> dict[str, Any]:
        """Drop a copper polygon pour on a rectangular area.

        Useful for placing a ground plane or power plane: pass the board's
        corners, the layer, and the net name (typically "GND"). Set
        pour_over=False to force the pour around same-net tracks/pads
        instead of covering them.

        On a board that is not a rectangle (round, flanged), draw the
        outline as a keep-out first (pcb_keepout_board_outline) and make
        the rectangle larger than the board: the pour stops at the
        keep-out, and copper left outside it, joined to nothing, is
        removed as dead copper.

        Args:
            x1: First corner X in mils
            y1: First corner Y in mils
            x2: Opposite corner X in mils
            y2: Opposite corner Y in mils
            net: Net name to assign (empty = no-net fill, unusual)
            layer: Copper layer (default "TopLayer")
            pour_over: Pour over same-net objects (default True)
            remove_dead: Remove copper islands joined to nothing
                (default True).
            pour: Pour it now (default True). False skips the pour, so
                its hatch, grid or thresholds can be set first and it is
                poured once, with pcb_repour_polygons by the ``name`` in
                the reply; on a dense board a pour can take seconds to
                minutes. Some builds pour a new polygon anyway (AD 26.11
                did, whatever pcb_polygon_repour_mode said): ``poured``
                reports the copper that is there.

        Returns:
            Dictionary confirming the polygon placement, with
            ``pour_skipped``, ``poured``, ``repour_mode`` and ``name``.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_polygon_rect",
            {
                "x1": _mils(x1),
                "y1": _mils(y1),
                "x2": _mils(x2),
                "y2": _mils(y2),
                "net": net,
                "layer": layer,
                "pour_over": "true" if pour_over else "false",
                "remove_dead": "true" if remove_dead else "false",
                "pour": "true" if pour else "false",
            },
        )
        return result

    @mcp.tool()
    async def pcb_keepout_board_outline(width_mils: int = 20) -> dict[str, Any]:
        """Draw the board outline on the Keep-Out layer.

        Every outline edge, arcs included, becomes a keep-out track or arc
        of ``width_mils`` centred on the edge. Copper on every layer (a
        pour, a route) then stays half that width plus the clearance rule
        from the board edge, and a pour larger than the board stops there.
        Edges already drawn on the Keep-Out layer are left alone, so a
        second call adds nothing.

        Args:
            width_mils: Keep-out width (default 20, so copper keeps 10 mil
                plus clearance from the edge).

        Returns:
            ``edges``, ``added``, ``already_there`` and ``width_mils``.
        """
        if width_mils <= 0:
            return {"success": False, "error": "width_mils must be positive"}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.keepout_board_outline", {"width": str(int(width_mils))})

    @mcp.tool()
    async def pcb_place_polygon_board(
        net: str,
        layer: str = "TopLayer",
        edge_clearance_mils: int = 10,
        pour_over: bool = True,
        remove_dead: bool = True,
        pour: bool = True,
    ) -> dict[str, Any]:
        """Pour copper over the whole board shape, following its outline.

        The pour takes the board outline's own vertices, arcs included, so
        it fits a round or flanged board exactly. The outline is drawn on
        the Keep-Out layer first (pcb_keepout_board_outline, twice
        ``edge_clearance_mils`` wide), which keeps the copper that far
        plus the clearance rule from the edge. Pour every copper layer
        that wants it, then stitch them with pcb_place_stitching_vias.

        Args:
            net: Net of the pour, typically "GND". Must exist on the board.
            layer: Copper layer (default "TopLayer").
            edge_clearance_mils: Copper-free band inside the board edge
                (default 10; 0 draws no keep-out).
            pour_over: Pour over same-net objects (default True).
            remove_dead: Remove copper islands joined to nothing
                (default True).
            pour: Pour it now (default True); False skips the pour, to
                pour once with pcb_repour_polygons (by the ``name`` in the
                reply) after its settings are made. Some builds pour a new
                polygon anyway (AD 26.11 did): ``poured`` reports the
                copper that is there.

        Returns:
            The pour (``vertices``, ``name``, ``layer``, ``net``,
            ``remove_dead``, ``pour_skipped``, ``poured``,
            ``repour_mode``) and ``keepout`` (what the keep-out outline
            added).
        """
        bridge = get_bridge()
        keepout: Any = None
        if edge_clearance_mils > 0:
            keepout = await bridge.send_command_async(
                "pcb.keepout_board_outline",
                {"width": str(int(2 * edge_clearance_mils))})
            if isinstance(keepout, dict) and keepout.get("success") is False:
                return {"success": False, "error": "the keep-out outline failed",
                        "keepout": keepout}
        result = await bridge.send_command_async(
            "pcb.place_polygon_board",
            {"net": net, "layer": layer,
             "pour_over": "true" if pour_over else "false",
             "remove_dead": "true" if remove_dead else "false",
             "pour": "true" if pour else "false"})
        if isinstance(result, dict):
            result["keepout"] = keepout
        return result

    @mcp.tool()
    async def pcb_place_via_array(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        pitch: float = 50,
        net: str = "",
        size: float = 30,
        hole_size: float = 12,
        low_layer: str = "TopLayer",
        high_layer: str = "BottomLayer",
    ) -> dict[str, Any]:
        """Stitch vias in a regular grid across a rectangle.

        Typical use: GND stitching between top and bottom layer copper
        pours. Places vias at every (pitch × pitch) grid intersection
        inside the rectangle.

        Args:
            x1: First corner X in mils
            y1: First corner Y in mils
            x2: Opposite corner X in mils
            y2: Opposite corner Y in mils
            pitch: Grid spacing in mils (default 50)
            net: Net to assign (typically "GND"; empty = no net)
            size: Via pad diameter in mils (default 30)
            hole_size: Drill hole diameter in mils (default 12)
            low_layer: Start layer (default "TopLayer")
            high_layer: End layer (default "BottomLayer")

        Returns:
            Dictionary with count of vias placed and rectangle/pitch echo
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_via_array",
            {
                "x1": _mils(x1),
                "y1": _mils(y1),
                "x2": _mils(x2),
                "y2": _mils(y2),
                "pitch": _mils(pitch),
                "net": net,
                "size": _mils(size),
                "hole_size": _mils(hole_size),
                "low_layer": low_layer,
                "high_layer": high_layer,
            },
        )
        return result

    @mcp.tool()
    async def pcb_place_via(
        x: float,
        y: float,
        net: str = "",
        size: float = 50,
        hole_size: float = 28,
        low_layer: str = "TopLayer",
        high_layer: str = "BottomLayer",
        size_mm: float | None = None,
        hole_size_mm: float | None = None,
    ) -> dict[str, Any]:
        """Place a via at specific coordinates on the active PCB.

        Sizes take fractions of a mil, or millimetres through ``size_mm``
        and ``hole_size_mm``, so a 1.2/0.6 mm via is exactly that and
        matches a metric Routing Via rule. Whole mils made it
        1.194/0.610 mm. A hole as wide as the pad is refused.

        Args:
            x: Via X position in mils
            y: Via Y position in mils
            net: Net name to assign (optional, empty = no net)
            size: Via pad diameter in mils (default 50)
            hole_size: Drill hole diameter in mils (default 28)
            low_layer: Start layer (default "TopLayer")
            high_layer: End layer (default "BottomLayer")
            size_mm: pad diameter in mm, used instead of ``size``
            hole_size_mm: hole diameter in mm, used instead of
                ``hole_size``

        Returns:
            Dictionary with placed via position and size (mils)
        """
        if size_mm is not None:
            size = float(size_mm) * MILS_PER_MM
        if hole_size_mm is not None:
            hole_size = float(hole_size_mm) * MILS_PER_MM
        bridge = get_bridge()
        params: dict[str, Any] = {
            "x": _mils(x),
            "y": _mils(y),
            "size": _mils(size),
            "hole_size": _mils(hole_size),
            "low_layer": low_layer,
            "high_layer": high_layer,
        }
        if net:
            params["net"] = net
        result = await bridge.send_command_async("pcb.place_via", params)
        return result

    @mcp.tool()
    async def pcb_place_tracks(
        tracks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Place many track segments on the active PCB in ONE IPC round-trip.

        PREFER THIS over placing one segment at a time whenever you have
        more than one segment to place. The whole batch is wrapped in
        a single PreProcess/PostProcess and a single save, so 50
        tracks take roughly the same wall time as 1. Typical uses:
        routing a full net, laying down a whole stitch pattern,
        replicating a motif, drawing a keepout rectangle.

        Args:
            tracks: List of track dicts. Each dict supports:
                x1, y1, x2, y2 (required, mils; decimals are kept)
                width (default 10, mils; decimals are kept, so a 0.1 mm
                rule stays 3.937), layer (default "TopLayer"),
                net_name (optional, empty = no net)

            Example:
                [
                  {"x1": 5010, "y1": 4785, "x2": 5070, "y2": 4785,
                   "width": 10, "net_name": "NetC8_2"},
                  {"x1": 5070, "y1": 4785, "x2": 5070, "y2": 4862,
                   "width": 10, "net_name": "NetC8_2"},
                ]

        Connectivity: each segment is registered with the board
        individually and, when it names a net, joined to that net's
        primitive list; the batch then triggers a connectivity rebuild
        so ``pcb_get_unrouted_nets`` is trustworthy immediately after.
        A net name that does not exist on the board is NOT created --
        the segment is placed netless and counted in ``nets_not_found``.

        Returns:
            Dictionary with:
              - placed, skipped_existing (exact direction-insensitive
                duplicates), failed: segment counts.
              - nets_not_found: segments whose ``net_name`` matched no
                net on the board, so they carry no net. Non-zero here
                is the usual reason a net still looks unrouted.
              - connectivity_rebuilt: the rebuild was issued (only when
                something was actually placed).
        """
        parts = []
        for t in tracks:
            x1 = _mils(t["x1"])
            y1 = _mils(t["y1"])
            x2 = _mils(t["x2"])
            y2 = _mils(t["y2"])
            width = _mils(t.get("width", 10))
            layer = str(t.get("layer", "TopLayer"))
            net = str(t.get("net_name", ""))
            parts.append(f"{x1},{y1},{x2},{y2},{width},{layer},{net}")
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_tracks", {"tracks": "|".join(parts)}
        )
        return result

    @mcp.tool()
    async def pcb_plan_bga_fanout(
        pads: list[dict[str, Any]],
        center_x: float,
        center_y: float,
        escape_mils: float = 20,
        track_width_mils: float = 4,
        via_size_mils: float = 18,
        via_hole_mils: float = 8,
        layer: str = "TopLayer",
        apply: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Plan radial BGA dog-bone escapes; optionally place them.

        Defaults to an offline dry run. Applying requires ``confirm=True``.
        Collision/DRC validation remains a separate mandatory audit step.
        """
        from eda_agent.design.pcb_planning import plan_bga_fanout
        if not pads:
            return {"ok": False, "reason": "pads must not be empty"}
        plan = plan_bga_fanout(
            pads, center_x, center_y, escape_mils, track_width_mils,
            via_size_mils, via_hole_mils, layer,
        )
        plan["applied"] = False
        if not apply:
            return plan
        if not confirm:
            raise ValueError("confirm=True is required when apply=True")
        bridge = get_bridge()
        track_parts = [
            f"{t['x1']},{t['y1']},{t['x2']},{t['y2']},{t['width']},{t['layer']},{t['net_name']}"
            for t in plan["tracks"]
        ]
        plan["track_result"] = await bridge.send_command_async(
            "pcb.place_tracks", {"tracks": "|".join(track_parts)}
        )
        plan["via_results"] = [
            await bridge.send_command_async("pcb.place_via", {
                "x": str(v["x"]), "y": str(v["y"]), "net": v["net"],
                "size": str(v["size"]), "hole_size": str(v["hole_size"]),
                "low_layer": "TopLayer", "high_layer": "BottomLayer",
            }) for v in plan["vias"]
        ]
        plan["applied"] = True
        return plan

    @mcp.tool()
    async def pcb_render_route_plan_svg(
        plan: dict[str, Any],
        output_path: str,
    ) -> dict[str, Any]:
        """Render planned tracks/vias/obstacles to SVG without using Altium."""
        from pathlib import Path
        from eda_agent.render.route_plan_svg import write_route_plan_svg
        if not any(plan.get(key) for key in ("tracks", "vias", "obstacles")):
            return {"ok": False, "reason": "route plan contains no geometry"}
        target = Path(output_path).expanduser().resolve()
        if target.suffix.lower() != ".svg":
            target = target.with_suffix(".svg")
        return write_route_plan_svg(plan, target)

    @mcp.tool()
    async def pcb_plan_return_vias(
        transitions: list[dict[str, Any]],
        reference_net: str = "GND",
        offset_mils: float = 40,
        via_size_mils: float = 30,
        via_hole_mils: float = 14,
        apply: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Plan nearby reference vias for signal layer transitions."""
        from eda_agent.design.pcb_planning import plan_return_vias
        vias = plan_return_vias(
            transitions, reference_net, offset_mils,
            via_size_mils, via_hole_mils,
        )
        result: dict[str, Any] = {
            "vias": vias, "count": len(vias), "applied": False,
            "reference_net": reference_net,
        }
        if not apply:
            return result
        if not confirm:
            raise ValueError("confirm=True is required when apply=True")
        bridge = get_bridge()
        result["via_results"] = [
            await bridge.send_command_async("pcb.place_via", {
                "x": str(v["x"]), "y": str(v["y"]), "net": v["net"],
                "size": str(v["size"]), "hole_size": str(v["hole_size"]),
                "low_layer": "TopLayer", "high_layer": "BottomLayer",
            }) for v in vias
        ]
        result["applied"] = True
        return result

    @mcp.tool()
    async def pcb_place_vias(
        vias: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Place many vias on the active PCB in ONE IPC round-trip.

        PREFER THIS over ``pcb_place_via`` whenever there is more than one
        via: the batch is one PreProcess/PostProcess and one broadcast.
        Coordinates and sizes keep their decimals, so a via laid by a
        router on a sub-mil grid lands where the router put it.

        Args:
            vias: List of via dicts. Each dict supports:
                x, y (required, mils), size (default 50), hole_size
                (default 28), low_layer (default "TopLayer"), high_layer
                (default "BottomLayer"), net (optional, empty = no net)

        Returns:
            Dictionary with "placed" and "failed" counts and
            "unknown_layers" naming any layer pair that did not resolve.
        """
        parts = []
        for v in vias:
            parts.append(",".join([
                _mils(v["x"]), _mils(v["y"]),
                _mils(v.get("size", 50)), _mils(v.get("hole_size", 28)),
                str(v.get("low_layer", "TopLayer")),
                str(v.get("high_layer", "BottomLayer")),
                str(v.get("net", "")),
            ]))
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.place_vias", {"vias": "|".join(parts)})

    @mcp.tool()
    async def pcb_audit_placement_plan(
        components: list[dict[str, Any]],
        board: dict[str, float],
        decoupling_max_mils: float = 200,
        termination_max_mils: float = 300,
        connector_edge_max_mils: float = 150,
        courtyard_mils: float = 10,
    ) -> dict[str, Any]:
        """Offline placement acceptance: bounds, overlaps and role proximity."""
        from eda_agent.design.placement_audit import audit_placement
        try:
            return audit_placement(
                components, board, decoupling_max_mils,
                termination_max_mils, connector_edge_max_mils,
                courtyard_mils,
            )
        except (ValueError, TypeError, KeyError) as exc:
            return {"ok": False, "reason": str(exc), "findings": []}

    @mcp.tool()
    async def pcb_place_arc(
        x_center: float,
        y_center: float,
        radius: float,
        start_angle: float = 0,
        end_angle: float = 360,
        width: float = 10,
        layer: str = "TopLayer",
        keepout: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Place an arc on the active PCB.

        Creates a circular arc segment defined by center, radius, and
        angular range.

        Args:
            x_center: Arc center X position in mils
            y_center: Arc center Y position in mils
            radius: Arc radius in mils
            start_angle: Start angle in degrees (default 0)
            end_angle: End angle in degrees (default 360 = full circle)
            width: Arc line width in mils (default 10)
            layer: PCB layer name (default "TopLayer")
            keepout: Mark the arc a keep-out, which routing and pours
                keep clear of. Omitted: on for "KeepOutLayer", off
                elsewhere; True on a copper layer keeps that layer
                clear only.

        Returns:
            Dictionary with placed arc geometry, layer and ``keepout``
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "x_center": str(x_center),
            "y_center": str(y_center),
            "radius": str(radius),
            "start_angle": str(start_angle),
            "end_angle": str(end_angle),
            "width": str(width),
            "layer": layer,
        }
        if keepout is not None:
            params["keepout"] = "1" if keepout else "0"
        result = await bridge.send_command_async("pcb.place_arc", params)
        return result

    @mcp.tool()
    async def pcb_place_text(
        text: str,
        x: int,
        y: int,
        layer: str = "TopOverlay",
        height: float = 60,
        rotation: float = 0,
        stroke: float = 0,
    ) -> dict[str, Any]:
        """Place a text string on the active PCB.

        Args:
            text: Text content to place
            x: Text X position in mils
            y: Text Y position in mils
            layer: PCB layer name (default "TopOverlay"). Common choices:
                "TopOverlay", "BottomOverlay", "TopLayer", "BottomLayer",
                "Mechanical1"-"Mechanical16"
            height: Text height in mils (default 60), decimals allowed
            rotation: Rotation angle in degrees (default 0)
            stroke: Stroke width in mils; 0 keeps Altium's default.
                To resize existing designators use ``pcb_set_text_style``.

        Returns:
            Dictionary with placed text properties, height and stroke as
            read back from the placed text
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "text": text,
            "x": str(x),
            "y": str(y),
            "layer": layer,
            "height": str(height),
            "rotation": str(rotation),
        }
        if stroke:
            params["stroke"] = str(stroke)
        result = await bridge.send_command_async("pcb.place_text", params)
        return result

    @mcp.tool()
    async def pcb_place_fill(
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: str = "TopLayer",
        net_name: str = "",
    ) -> dict[str, Any]:
        """Place a rectangular copper fill on the active PCB.

        Creates a solid copper rectangle. Useful for thermal pads,
        ground planes, and copper pours in specific areas.

        Args:
            x1: First corner X in mils
            y1: First corner Y in mils
            x2: Second corner X in mils
            y2: Second corner Y in mils
            layer: PCB layer name (default "TopLayer")
            net_name: Net name to assign (optional, empty = no net)

        Returns:
            Dictionary with placed fill coordinates and layer
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "layer": layer,
        }
        if net_name:
            params["net_name"] = net_name
        result = await bridge.send_command_async("pcb.place_fill", params)
        return result

    @mcp.tool()
    async def pcb_start_polygon_placement(
        layer: str = "TopLayer",
        net_name: str = "",
    ) -> dict[str, Any]:
        """Start INTERACTIVE polygon pour placement on the active PCB.

        This is an interactive command, it launches Altium's polygon
        placement mode. The user must then draw the polygon boundary
        interactively in Altium Designer (clicks define vertices, right-click
        or Escape completes). It does NOT create a polygon programmatically
        from coordinates.

        Args:
            layer: Target copper layer (default "TopLayer")
            net_name: Net to assign to the polygon pour (optional)

        Returns:
            Dictionary confirming polygon placement mode was initiated
        """
        bridge = get_bridge()
        params: dict[str, Any] = {"layer": layer}
        if net_name:
            params["net_name"] = net_name
        result = await bridge.send_command_async("pcb.start_polygon_placement", params)
        return result

    @mcp.tool()
    async def pcb_create_design_rule(
        name: str,
        rule_type: str = "clearance",
        value: int = 10,
        max_value: Optional[int] = None,
        favored_value: Optional[int] = None,
        max_uncoupled_length: Optional[int] = None,
        scope: str = "",
        net_scope: str = "different_nets",
        allowed: Optional[bool] = None,
        connect_style: str = "direct",
    ) -> dict[str, Any]:
        """Create a new design rule on the active PCB.

        Args:
            name: Rule name (e.g., "Min Clearance 6mil").
            rule_type: "polygon_connect" / "plane_connect" (no value:
                connect_style decides, e.g. scope "IsVia" with "direct"
                so vias never get thermal reliefs; set relief widths
                and gaps afterwards with pcb_set_rule_properties),
            rule_type: "clearance" (value = gap), "width" (value = min,
                max_value/favored_value optional), "via_size" (value = min
                hole), "differential_pairs" (value = min gap, max_value,
                favored_value, max_uncoupled_length),
                "solder_mask_expansion" / "paste_mask_expansion" (value =
                SIGNED radial expansion; negative with scope "IsVia" tents
                vias), "vias_under_smd" (set ``allowed``, not value).
            value: Primary value in mils (the MIN for ranged kinds).
            max_value: MAX for ranged kinds (default 5x value).
            favored_value: Preferred value (default value).
            max_uncoupled_length: differential_pairs only, mils
                (default 1000).
            scope: Query for Scope1, matching the kind: "InNet('GND')",
                "InNetClass('Power')" or "All" for net rules;
                "InDifferentialPair('USB')" or "IsDifferentialPair" for
                pairs (InNet on a pair rule never matches). Bracket
                comparisons: "IsPad And (HoleSize > 3)"; the unbracketed
                form is refused with ``suggested_scope``.
            net_scope: "different_nets" (default), "any_net" or
                "same_net"; ignored by pair, mask and via-in-pad rules.
            allowed: vias_under_smd only: False forbids via-in-pad.
                Omitted means True, Altium's default.

        Returns:
            Dictionary with created rule details.

        Component, hole-to-hole and board-outline clearance rules cannot
        be created on this Altium build; existing ones can be changed
        with pcb_set_rule_properties.
        """
        if scope:
            refusal = _scope_refusal(scope, created=False)
            if refusal:
                return refusal
        bridge = get_bridge()
        params: dict[str, Any] = {
            "name": name,
            "rule_type": rule_type,
            "value": str(value),
            "net_scope": net_scope,
        }
        if max_value is not None:
            params["max_value"] = str(max_value)
        if favored_value is not None:
            params["favored_value"] = str(favored_value)
        if max_uncoupled_length is not None:
            params["max_uncoupled_length"] = str(max_uncoupled_length)
        if scope:
            params["scope"] = scope
        if allowed is not None:
            params["allowed"] = "true" if allowed else "false"
        if rule_type in ("polygon_connect", "plane_connect"):
            params["connect_style"] = connect_style
        result = await bridge.send_command_async("pcb.create_design_rule", params)
        return result

    @mcp.tool()
    async def pcb_delete_design_rule(
        name: str,
    ) -> dict[str, Any]:
        """Delete a design rule by name from the active PCB.

        Args:
            name: Exact name of the design rule to delete

        Returns:
            Dictionary confirming deletion
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.delete_design_rule",
            {"name": name},
        )
        return result

    @mcp.tool()
    async def pcb_get_component_pads(
        designator: str,
    ) -> dict[str, Any]:
        """Get all pads of a specific PCB component.

        Returns detailed pad information including pin name, position,
        net assignment, size, and hole information.

        DATASHEET DISCIPLINE: Pad name -> pin function mapping comes
        from the footprint, which can be wrong (especially the thermal
        pad on QFN/DFN, which is rarely numbered consistently across
        vendors). Before stating which pin a pad corresponds to,
        cross-check the manufacturer datasheet's mechanical /
        recommended-land-pattern section. The response carries
        `_datasheet_guidance` + `_datasheet_parts`.

        Args:
            designator: Component reference designator (e.g., "U1", "J3")

        Returns:
            Dictionary with "designator", "pads" array (each with name,
            x, y, net, layer, hole_size, top_x_size, top_y_size,
            rotation), "pad_count", plus `_datasheet_guidance` +
            `_datasheet_parts`.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.get_component_pads",
            {"designator": designator},
        )
        if isinstance(result, dict):
            explicit = [{
                "manufacturer": "",
                "part_number": "",
                "designators": designator,
            }]
            return tag_response(
                result,
                explicit_parts=explicit,
                context="pcb_get_component_pads",
            )
        return result

    @mcp.tool()
    async def pcb_flip_component(
        designator: str,
    ) -> dict[str, Any]:
        """Flip a component to the other side of the board (top to bottom
        or bottom to top).

        The part is mirrored left-right about its origin, as seen from the
        top, and Altium changes the rotation it reports (a USB-C at 180 on
        the bottom read 0 once flipped to the top). To end at an exact
        place and rotation, use pcb_move_components with ``side``, which
        sets the rotation after the flip.

        Args:
            designator: Component reference designator (e.g., "U1", "R5")

        Returns:
            Dictionary with designator, old_layer, and new_layer
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.flip_component",
            {"designator": designator},
        )
        return result

    @mcp.tool()
    async def pcb_set_component_side(
        designators: list[str],
        side: str,
    ) -> dict[str, Any]:
        """Put many components deterministically on Top or Bottom in one call.

        Unlike repeatedly calling ``pcb_flip_component``, this operation is
        idempotent: components already on the requested side are not toggled.
        Use it after the user chooses single- or double-sided assembly and
        before auto-placement so the placer legalizes each side separately.

        Args:
            designators: Component reference designators to assign.
            side: ``"top"`` or ``"bottom"``.
        """
        normalized = side.strip().lower()
        if normalized not in {"top", "bottom"}:
            return {"ok": False, "reason": "side must be 'top' or 'bottom'"}
        refs = [str(x).strip() for x in designators if str(x).strip()]
        if not refs:
            return {"side": normalized, "requested": 0, "changed": 0,
                    "already": 0, "missing": 0}
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.batch_set_component_side",
            {"designators": "~~".join(refs), "side": normalized},
        )

    @mcp.tool()
    async def pcb_align_components(
        designators: str,
        alignment: str = "left",
    ) -> dict[str, Any]:
        """Align multiple PCB components along a common edge or center.

        Args:
            designators: Comma-separated component reference designators
                (e.g., "R1,R2,R3,R4")
            alignment: Alignment mode. Options:
                "left" - Align to leftmost X
                "right" - Align to rightmost X
                "top" - Align to topmost Y
                "bottom" - Align to bottommost Y
                "center_x" - Center horizontally
                "center_y" - Center vertically

        Returns:
            Dictionary with alignment result and component count
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.align_components",
            {"designators": designators, "alignment": alignment},
        )
        return result

    @mcp.tool()
    async def pcb_snap_to_grid(
        designator: str,
        grid_size: float = 50,
    ) -> dict[str, Any]:
        """Snap a component to the nearest grid point.

        Rounds the component's X and Y position to the nearest multiple
        of the specified grid size.

        Args:
            designator: Component reference designator (e.g., "U1", "R5")
            grid_size: Grid spacing in mils (default 50)

        Returns:
            Dictionary with designator, old and new positions, and grid_size
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.snap_to_grid",
            {"designator": designator, "grid_size": _mils(grid_size)},
        )
        return result

    @mcp.tool()
    async def pcb_get_diff_pair_rules() -> dict[str, Any]:
        """Get all differential pair routing rules from PCB design rules.

        Returns design rules of kind eRule_DifferentialPairsRouting, these
        are routing rules, NOT IPCB_DifferentialPair pair objects on the board.

        Returns:
            Dictionary with "diff_pair_rules" array (each with name, enabled,
            scope_1, scope_2, comment, descriptor) and "count"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_diff_pair_rules", {})
        return result

    @mcp.tool()
    async def pcb_get_vias() -> dict[str, Any]:
        """Get all vias on the active PCB board.

        Returns via position, pad size, hole size, net assignment, and
        start/end layer for every via on the board.

        Returns:
            Dictionary with "vias" array (each with x, y, size, hole_size,
            net, low_layer, high_layer) and "count". Legacy size/hole_size
            values are rounded integer mils. size_mm and hole_size_mm
            retain sub-mil precision and are explicitly in millimeters.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_vias", {})
        return result

    @mcp.tool()
    async def pcb_via_structures(board_path: str, limit: int = 200) -> dict[str, Any]:
        """Count via structure, protection and back-drill configurations.

        The exact PcbDoc path is required. ``truncated`` and
        ``omitted_vias`` show whether the distinct-kind limit hid entries.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if type(limit) is not int or not 1 <= limit <= 2000:
            return {"ok": False, "reason": "limit must be an integer from 1 to 2000"}
        reply = await get_bridge().send_command_async(
            "pcb.via_structures", {"board_path": board_path, "limit": str(limit)},
            timeout=120.0,
        )
        if not isinstance(reply, dict) or reply.get("error"):
            return reply
        if (str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or type(reply.get("vias")) is not int
                or type(reply.get("omitted_vias")) is not int
                or type(reply.get("truncated")) is not bool
                or not isinstance(reply.get("structures"), list)):
            return {"ok": False, "reason": "incomplete or wrong-board via structure reply",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_get_tracks(
        net: str = "",
        layer: str = "",
        offset: int = 0,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Get routed copper tracks and arcs on the active PCB board, one page at a time.

        Copper layers only; primitives inside components, polygons and
        dimensions are left out (they are not routing). Arcs are included
        because corners routed with arcs are part of the path. Coordinates
        and widths are RAW Altium units (TCoord, 10000 per mil) so a
        0.15 mm gap keeps full precision; the response says so.

        Args:
            net: Only primitives on this exact net (optional).
            layer: Only this copper layer: TopLayer, MidLayerN or BottomLayer
                (optional; default all copper).
            offset: First matching primitive to return (default 0).
            limit: Rows per page, 1..2000 (default 500).

        Returns:
            Dict with ``tracks`` (each: kind "track" with x1/y1/x2/y2, or
            kind "arc" with xc/yc/radius/start_angle/end_angle; plus net,
            layer, width and teardrop), ``count`` (rows in this page),
            ``total`` (matching primitives), ``offset``, ``limit``,
            ``units`` ("coord") and ``coord_per_mil`` (10000).
        """
        bridge = get_bridge()
        params: dict[str, Any] = {"offset": str(max(0, int(offset))),
                                  "limit": str(min(2000, max(1, int(limit))))}
        if net:
            params["net"] = net
        if layer:
            params["layer"] = layer
        result = await bridge.send_command_async("pcb.get_tracks", params)
        return result

    @mcp.tool()
    async def pcb_calc_polygon_area(
        net: str = "",
        layer: str = "",
    ) -> dict[str, Any]:
        """Report the area of each copper polygon on the active board.

        Returns each polygon's overall boundary area in square mils and
        square millimetres, optionally filtered by net and/or layer.
        Useful for estimating copper coverage / plane area.

        Args:
            net: Only polygons on this net (optional).
            layer: Only polygons on this layer name (optional).

        Returns:
            Dict with ``polygons`` (each: name, net, layer, area_sq_mils,
            area_sq_mm) and ``count``.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {}
        if net:
            params["net"] = net
        if layer:
            params["layer"] = layer
        return await bridge.send_command_async("pcb.calc_polygon_area", params)

    @mcp.tool()
    async def pcb_set_via_soldermask_relief(
        expansion_mils: int = 4,
        net: str = "",
    ) -> dict[str, Any]:
        """REFUSED on this Altium build: the write crashes the engine.

        Setting a via's soldermask expansion from script raises an access
        violation inside ScriptingSystem.DLL on AD 26.10.1.6, measured
        twice on a scratch board with three vias and nothing else, once
        through BeginModify and once through SendMessageToRobots. The
        engine shows a modal before any handler guard can run, so the
        polling loop stops and the session needs a manual restart. The
        handler refuses rather than attempt it: every caller who tried
        lost their session and changed nothing on the board.

        TENT VIAS WITH A RULE INSTEAD. Altium's own route is a Solder
        Mask Expansion rule, which covers every via at once and survives
        a repour, where a per-via write would not. Create it with
        ``pcb_create_design_rule(rule_type="solder_mask_expansion",
        scope="IsVia", value=<negative mils>)``. A negative expansion
        contracts the mask opening; the rule is also editable by hand in
        Design > Rules > Mask.

        REFUSED HERE, NOT AT THE BRIDGE, on purpose. The handler refuses
        too, but reaching it means sending the command, and a session
        running a deployed script older than 2026.09.10.3 still has the
        write in it. Sending would take down exactly the session this
        exists to protect. Nothing is sent.

        Args:
            expansion_mils: accepted and unused.
            net: accepted and unused.

        Returns:
            An error dict with `NOT_SCRIPTABLE` and the rule route.
        """
        return {
            "success": False,
            "error": "NOT_SCRIPTABLE",
            "reason": (
                "Writing a via soldermask expansion crashes the Altium "
                "scripting engine on this build (access violation in "
                "ScriptingSystem.DLL), which stops the polling loop and "
                "needs a manual restart, so nothing was sent."
            ),
            "instead": (
                "Tent vias with a Solder Mask Expansion rule scoped IsVia, "
                "in Design > Rules > Mask. pcb_create_design_rule cannot "
                "author that rule kind; app_run_menu opens the dialog and "
                "app_drive_dialogs fills it in."
            ),
            "requested": {"expansion_mils": expansion_mils, "net": net},
        }

    @mcp.tool()
    async def pcb_set_via_tenting(
        points: Optional[list[dict[str, float]]] = None,
        net: str = "",
        top: Optional[bool] = None,
        bottom: Optional[bool] = None,
        board_path: str = "",
        dry_run: bool = True,
        expected_plan: str = "",
    ) -> dict[str, Any]:
        """Set a board via's own Tenting Top / Bottom flags.

        Altium keeps the tenting flag only while the via's solder mask
        expansion is manual; on a rule-driven via the write is accepted
        and dropped. So a rule-driven via is switched to a manual mask at
        the values it already has, and each via says so in
        ``mask_made_manual``. Every flag is read back. Vias inside
        footprints are skipped: use ``lib_set_via_properties`` in the
        PcbLib.

        Args:
            board_path: Exact loaded PcbDoc path. Required for reads and writes.
            points: ``[{x, y}]`` in mils; each picks the via whose pad
                covers that point (nearest centre wins).
            net: Without points, every free via on this net; with points,
                only vias on this net are considered.
            top, bottom: True tents that side, False opens it; leave one
                out to keep it as it is.
            dry_run: True by default. Return the selected vias and a plan token.
            expected_plan: The token from that dry run, required for a write.

        Returns:
            ``matched``, ``changed``, ``failed``, ``points_without_a_via``,
            ``footprint_vias_skipped`` and ``vias`` [{x_mils, y_mils, net,
            tenting_top, tenting_bottom, mask_made_manual, ok}].
        """
        if (not board_path or not Path(board_path).is_absolute()
                or Path(board_path).suffix.casefold() != ".pcbdoc"):
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if (top is not None and type(top) is not bool) or (bottom is not None and type(bottom) is not bool):
            return {"ok": False, "reason": "top and bottom must be booleans"}
        if top is None and bottom is None:
            return {"ok": False, "reason": "top and/or bottom say what to set"}
        if not points and not net.strip():
            return {"ok": False, "reason": "points or net say which vias"}
        params: dict[str, Any] = {"board_path": board_path, "dry_run": "true"}
        if points:
            try:
                coords = [(float(p["x"]), float(p["y"])) for p in points]
                if any(not math.isfinite(v) or abs(v) > 1_000_000
                       for pair in coords for v in pair):
                    raise ValueError("point coordinate outside board range")
                params["points"] = ";".join(
                    f"{x:.6f},{y:.6f}" for x, y in coords)
            except (KeyError, TypeError, ValueError):
                return {"ok": False, "reason": "each point needs finite {x, y} in mils"}
        if net.strip():
            params["net"] = net.strip()
        if top is not None:
            params["top"] = "true" if top else "false"
        if bottom is not None:
            params["bottom"] = "true" if bottom else "false"
        bridge = get_bridge()
        plan = await bridge.send_command_async("pcb.set_via_tenting", params)
        if (not isinstance(plan, dict) or plan.get("dry_run") is not True
                or str(plan.get("board_path", "")).casefold() != board_path.casefold()
                or type(plan.get("matched")) is not int
                or not isinstance(plan.get("plan_token"), str)):
            return {"ok": False, "reason": "via tenting plan was incomplete or targeted another board",
                    "native_reply": plan}
        if dry_run or plan.get("success") is not True:
            return plan
        if not expected_plan or expected_plan != plan["plan_token"]:
            return {"ok": False, "reason": "expected_plan differs from the current via selection",
                    "current_plan": plan}
        reply = await bridge.send_command_async(
            "pcb.set_via_tenting",
            {**params, "dry_run": "false", "expected_plan": expected_plan})
        if (not isinstance(reply, dict) or reply.get("success") is not True
                or reply.get("dry_run") is not False
                or str(reply.get("board_path", "")).casefold() != board_path.casefold()
                or reply.get("matched") != plan["matched"]
                or reply.get("failed") != 0):
            return {"ok": False, "reason": "via tenting write was not fully verified",
                    "native_reply": reply, "plan": plan}
        reply["ok"] = True
        reply["save_required"] = bool(reply.get("changed"))
        return reply

    @mcp.tool()
    async def pcb_get_mech_layer_names(
        count_primitives: bool = True,
    ) -> dict[str, Any]:
        """Every enabled mechanical layer on the board, and what is on it.

        WHAT IS ON THE LAYER IS THE PART YOU CANNOT GET ELSEWHERE. A
        PcbLib header carries USEDBYPRIMS; a PcbDoc does not, so on a
        board there is no way to ask which mechanical layers the
        geometry occupies. This counts, because moving kinds around on a
        board you cannot inspect is how an assembly drawing gets
        orphaned. ``primitive_count`` of 0 is a layer that is genuinely
        spare; -1 means the count was not attempted or failed.

        ENABLED, NOT DISPLAYED. This used to list only layers the view
        happened to be showing, so a layer carrying the whole fab
        drawing was missing from the answer whenever it was toggled off.
        Display is a view setting and is reported separately as
        ``displayed``.

        Each entry carries its ``kind``, which is what the layer is FOR
        rather than what it is called. Read it before setting one: a
        kind belongs to a single layer, so assigning it moves it, and a
        PAIRED kind is held by the layer pair. ``kind_id`` of -1 means
        this Altium build has no mechanical layer kinds.

        Args:
            count_primitives: Count what sits on each layer. The board is
                walked once per enabled layer, so pass False when only
                the names are wanted.

        Returns:
            Dict with ``mechanical_layers`` (each: layer, number, name,
            enabled, displayed, kind, kind_id, primitive_count),
            ``count``, ``occupied_count``, ``counted_primitives`` and
            ``scanned_to``, the layer number the scan stopped at.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.get_mech_layer_names",
            {"count_primitives": "true" if count_primitives else "false"})

    @mcp.tool()
    async def pcb_set_mech_layers(
        layers: list[dict[str, Any]],
        tidy_pairs: bool = False,
        timeout: float = 180.0,
    ) -> dict[str, Any]:
        """Name, enable and kind the mechanical layers of the open BOARD.

        The board counterpart of ``lib_set_mech_layers`` (which refuses
        a PcbDoc). Every change is read back, and one that did not take
        is reported against its layer.

        A kind ending in Top or Bottom belongs to the layer PAIR, stored
        without the side ("Courtyard Top" is pair kind "Courtyard"):
        give both sides in one call and they are paired and given the
        kind. Single kinds such as "Fab Notes" need no partner.

        Read ``pcb_get_mech_layer_names`` first: moving a kind off a
        layer whose ``primitive_count`` is not 0 orphans that geometry
        from anything that finds the layer by purpose.

        Args:
            layers: One dict per layer. Keys: ``layer`` (required, e.g.
                "Mechanical13"), and any of ``name``, ``enabled``
                (bool), ``kind`` (e.g. "Courtyard Top"). A layer with
                none of the three is reported as nothing asked for.
            tidy_pairs: Remove layer pairs no kind justifies. Off by
                default, because it REMOVES pairs.
            timeout: Seconds.

        Returns:
            Dict with ``document``, ``layers`` (each: layer, changed,
            problem), ``changed``, ``failed``, ``kinds_displaced``,
            ``pairs_removed``, ``pairs_tidied`` and ``pairs_scanned_to``.
        """
        from .library import _encode_layer_ops

        encoded = _encode_layer_ops(layers)
        if isinstance(encoded, dict):
            return encoded

        params: dict[str, Any] = {"layers": encoded}
        if tidy_pairs:
            params["tidy_pairs"] = "true"

        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.set_mech_layers", params, timeout=timeout,
        )
        return result or {}

    @mcp.tool()
    async def pcb_get_layer_display() -> dict[str, Any]:
        """Visibility and colour for every layer on the active board.

        Covers signal, plane, mechanical, mask, paste, silk, keepout and
        multilayer. Each entry gives the internal ``layer`` id, the user's
        ``name`` for it, whether it is ``visible``, and its colour both as
        Altium's raw integer and as ``color_hex``.

        Read this before recolouring: Altium stores a colour as a Windows
        TColor, which is byte-reversed against the #RRGGBB people write,
        and getting that backwards produces a plausible wrong colour
        rather than an error.

        Returns:
            Dict with ``layers``, ``count`` and ``visible_count``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.get_layer_display", {})

    @mcp.tool()
    async def pcb_set_layer_color(layer: str, color: str) -> dict[str, Any]:
        """Recolour one layer.

        The colour is given as ``#RRGGBB``. Altium holds it internally as
        a byte-reversed TColor, and that conversion happens on the Altium
        side so no caller has to know about it.

        The write is READ BACK before reporting success, because a
        refused assignment raises nothing and would otherwise be reported
        as having worked.

        Colour is a display setting rather than a property of the board,
        so it follows the installation rather than travelling with the
        file.

        Args:
            layer: Layer name, e.g. "TopOverlay" or "Mechanical13".
            color: Colour as "#RRGGBB".

        Returns:
            Dict with ``layer``, ``color`` and ``color_hex``.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.set_layer_color", {"layer": layer, "color": color}
        )

    @mcp.tool()
    async def pcb_set_mech_layer_kind(
        layer: str, kind: str, partner_layer: str = ""
    ) -> dict[str, Any]:
        """Set what a mechanical layer is FOR, not what it is called.

        Naming a layer "Courtyard Top" does not make it one: courtyard
        checks, assembly drawings, 3D bodies and via treatments read the
        KIND. A single kind ("Fab Notes") moves off any layer holding it
        (``cleared_from``). A kind ending in Top or Bottom belongs to a
        layer PAIR and needs ``partner_layer``. The write is read back.

        Args:
            layer: Mechanical layer, e.g. "Mechanical13".
            kind: e.g. "Courtyard Top", "Assembly Top", "3D Body Top",
                "Fab Notes", "Not Set", or a bare number. Read the
                current kinds with ``pcb_get_mech_layer_names``.
            partner_layer: The layer for the other side; required for a
                Top or Bottom kind.

        Returns:
            Dict with ``layer``, ``kind``, ``kind_id``, ``paired``,
            ``pair_kind``, ``partner_layer`` and ``cleared_from``.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {"layer": layer, "kind": kind}
        if partner_layer:
            params["partner_layer"] = partner_layer
        return await bridge.send_command_async(
            "pcb.set_mech_layer_kind", params
        )

    @mcp.tool()
    async def pcb_delete_object(
        x: float,
        y: float,
        layer: str = "",
        object_type: str = "track",
    ) -> dict[str, Any]:
        """Delete a PCB object closest to specific coordinates on a layer.

        Finds the nearest matching object within 100 mils of the given
        coordinates and removes it from the board. Distance is to the
        object itself: a track by its segment less half its width, an arc
        by its curve, a via by its centre less its radius, anything else
        by its bounding rectangle (0 inside it). A point anywhere on a
        track finds that track.

        Args:
            x: Target X position in mils
            y: Target Y position in mils
            layer: PCB layer name to search; empty searches every layer,
                which is where a through via, a through-hole pad or a part
                is found (they sit on the multi-layer).
            object_type: Type of object to delete. Options:
                "track" - Track segment
                "via" - Via
                "fill" - Copper fill
                "text" - Text string
                "pad" - Free pad
                "arc" - Arc
                "polygon" - Copper polygon pour
                "region" - Region / split-plane
                "component" - Placed component
                (for bulk/filter-based deletes use ``obj_delete``)

        Connectivity is rebuilt afterwards, because removing copper
        changes the net topology and the ratsnest would otherwise stay
        stale.

        Returns:
            Dictionary with deleted status, object_type, distance_mils,
            the deleted object's net, layer and bbox_mils, and others_as_close:
            how many other objects were exactly as near, so a pick among
            equals is visible.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.delete_object",
            {"x": _mils(x), "y": _mils(y), "layer": layer, "object_type": object_type},
        )
        return result

    @mcp.tool()
    async def pcb_get_pad_properties(
        net: str = "",
        designator: str = "",
        offset: int = 0,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Get detailed pad information filtered by net or component.

        Returns pad shape, size, hole, thermal relief, and solder/paste
        mask expansion details.

        THE RESULT IS A WINDOW, NOT THE WHOLE BOARD. At most `limit` pad
        records come back (default 500, hard ceiling 5000). Always read
        `truncated` before drawing any conclusion: `truncated:true` means
        pads matching your filter were NOT returned, so a component
        missing from `pads` may simply sit past the window rather than
        being absent or netless. Either narrow with `designator` (the
        cheap, preferred route) or page with `next_offset`.

        Args:
            net: Filter by net name, or a comma-separated list
                (e.g., "GND", "GND,VCC"). Empty means all nets.
            designator: Filter by component designator, or a
                comma-separated list (e.g., "U15", "U14,U15"). Empty
                means all components.
            offset: Skip this many matching pads before collecting.
                Feed the previous response's `next_offset` to page.
            limit: Maximum pad records to return. <=0 or >5000 is
                clamped to 5000; an unbounded dump is not offered
                because it breaks the file transport on dense boards.

        Returns:
            Dictionary with:
              - pads: array (each with name, component, x, y, net,
                layer, shape, top_x_size, top_y_size, hole_size,
                rotation, is_smd, solder_mask_expansion,
                paste_mask_expansion).
              - count / returned: records in `pads` (identical; `count`
                is kept for backwards compatibility).
              - total_matching: pads matching the filter across the
                WHOLE board, counted independently of the window.
              - total_pads_on_board: every pad the iterator saw.
              - offset, limit: the window that was applied.
              - truncated: True when total_matching > offset + returned.
              - next_offset: offset to pass for the next page.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "offset": str(int(offset)),
            "limit": str(int(limit)),
        }
        if net:
            params["net"] = net
        if designator:
            params["designator"] = designator
        result = await bridge.send_command_async("pcb.get_pad_properties", params)
        return result

    @mcp.tool()
    async def pcb_set_track_width(
        net_name: str,
        width_mils: int,
    ) -> dict[str, Any]:
        """Modify track width for all tracks on a specific net.

        Changes the width of every routed track segment assigned to
        the given net. Useful for adjusting power or signal trace widths.

        Args:
            net_name: Name of the net whose tracks to modify (e.g., "VCC")
            width_mils: New track width in mils (e.g., 10, 20, 50)

        Returns:
            Dictionary with net_name, width_mils, and tracks_modified count
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.set_track_width",
            {"net_name": net_name, "width_mils": str(width_mils)},
        )
        return result

    @mcp.tool()
    async def pcb_get_unrouted_nets(reanalyze: bool = True) -> dict[str, Any]:
        """Get list of nets with unrouted connections (ratsnest lines).

        Identifies nets that still have ratsnest lines, meaning they are
        not fully routed. Useful for checking routing completion status.

        The count is of the connection lines stored on the board, and
        those go out of date: boards whose nets were all joined have been
        reported with open connections, and moved parts kept lines to
        their old places. So by default Altium first re-derives the lines
        of every net that has one, as it does after an edit.
        ``obj_query`` on ``eConnectionObject`` lists each line with its
        ends, layers, ``IsRedundant`` and ``Mode``.

        Args:
            reanalyze: re-derive the ratsnest before counting (default
                True). False reads the stored lines as they are, faster
                on a large board.

        Returns:
            Dictionary with "unrouted_nets" array (each with net name and
            unrouted_connections count), "net_count", "total_unrouted" and
            "reanalyzed"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.get_unrouted_nets", {"reanalyze": "true" if reanalyze else "false"})
        return result

    @mcp.tool()
    async def pcb_rebuild_connectivity() -> dict[str, Any]:
        """Recompute the board's net topology and ratsnest.

        Adding or removing copper through the API does not by itself
        refresh Altium's connectivity model, and the ratsnest lines that
        ``pcb_get_unrouted_nets`` counts are generated from that model.
        ``pcb_place_tracks``, ``pcb_delete_object`` and
        ``obj_batch_delete`` already call this at the end of their own
        work; use this tool directly after a sequence of other mutations
        (vias, pads, polygons, net binding) or when a routing result
        looks stale.

        ``obj_refresh_document`` is NOT a substitute -- it issues a Zoom
        Redraw, which repaints the view without recomputing anything.

        Returns:
            Dictionary with "rebuilt" and an explanatory "note".
            ``rebuilt`` means the connectivity process was issued without
            raising, NOT that Altium is confirmed to have recomputed;
            verify with ``pcb_get_unrouted_nets``.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.rebuild_connectivity", {})
        return result

    @mcp.tool()
    async def pcb_get_net_object_ids(net: str) -> dict[str, Any]:
        """Inspect the internal net-object address used by every primitive.

        Use this diagnostic when pads and copper have the same visible net
        name but Altium still treats them as disconnected. Different
        ``net_address`` values reveal duplicate internal net objects.
        """
        if not net.strip():
            return {"success": False, "reason": "net is required"}
        return await get_bridge().send_command_async(
            "pcb.get_net_object_ids", {"net": net.strip()}
        )

    @mcp.tool()
    async def pcb_get_connections_detail(net: str) -> dict[str, Any]:
        """Return the live ratsnest connection endpoints for one net."""
        if not net.strip():
            return {"success": False, "reason": "net is required"}
        return await get_bridge().send_command_async(
            "pcb.get_connections_detail", {"net": net.strip()}
        )

    @mcp.tool()
    async def pcb_delete_connections_for_net(
        net: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Remove stale ratsnest objects for one independently verified net.

        This is a repair escape hatch, not a routing operation. Confirm only
        after independently proving that the copper graph connects every pad;
        otherwise the removal can hide a genuine unrouted connection.
        """
        if not net.strip():
            return {"success": False, "reason": "net is required"}
        if not confirm:
            return {
                "success": False,
                "reason": (
                    "refusing to remove ratsnest objects without confirm=true; "
                    "first prove that the copper graph connects every endpoint"
                ),
            }
        return await get_bridge().send_command_async(
            "pcb.delete_connections_for_net", {"net": net.strip()}
        )

    @mcp.tool()
    async def pcb_rebind_vias() -> dict[str, Any]:
        """Re-register every net-associated via and rebuild connectivity."""
        return await get_bridge().send_command_async("pcb.rebind_vias", {})

    @mcp.tool()
    async def pcb_rebind_copper_to_pad_nets() -> dict[str, Any]:
        """Canonicalize copper net objects against pad nets, then rebuild."""
        return await get_bridge().send_command_async(
            "pcb.rebind_copper_to_pad_nets", {}
        )

    @mcp.tool()
    async def pcb_get_polygons() -> dict[str, Any]:
        """Get all polygon pours on the active PCB with copper area.

        Each row: ``index``, ``name``, ``net``, ``layer``,
        ``hatch_style``, ``pour_over``, ``poured`` (false when shelved),
        ``vertex_count``, ``bbox_mm2``, and:
          - ``area_sqmils`` / ``area_mm2``: the OUTLINE's area, unchanged
            by the pour and including copper cut away by clearances.
          - ``copper_area_mm2``: copper actually poured (regions minus
            their holes). A hatched pour is tracks, so its region area
            is 0.
          - ``copper_area_exact``: false when holes could not be read;
            the area then overstates the copper.
          - ``copper_pieces``: 0 on a poured polygon means nothing
            poured.

        Returns:
            Dict with ``{polygons: [...], count: N}``.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_polygons", {})
        return result

    @mcp.tool()
    async def pcb_grow_pour(
        board_path: str, index: int, expected_name: str, expected_layer: str,
        distance_mils: float, expected_bounds: Optional[dict[str, float]] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Preview or grow one polygon outline on an exact PcbDoc.

        Use the index, name and layer reported by ``pcb_get_polygons``.
        Read with dry_run first, then pass its ``bounds_before`` as
        ``expected_bounds`` for a write. Polygon indices may reorder after
        Altium saves and reloads a PcbDoc.
        Repour the polygon separately after the outline change.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if (type(index) is not int or index < 0 or not expected_name.strip()
                or not expected_layer.strip() or type(distance_mils) not in (int, float)
                or not math.isfinite(distance_mils) or distance_mils == 0
                or abs(distance_mils) > 1000):
            return {"ok": False, "reason": "invalid polygon selector or distance_mils"}
        bridge = get_bridge()
        params = {"board_path": board_path, "index": index,
                  "expected_name": expected_name, "expected_layer": expected_layer,
                  "distance_mils": distance_mils, "dry_run": True}
        preview = await bridge.send_command_async("pcb.grow_pour", params, timeout=120.0)
        if not isinstance(preview, dict) or preview.get("error"):
            return preview
        bounds = preview.get("bounds_before")
        if (str(preview.get("board_path", "")).casefold() != board_path.casefold()
                or preview.get("index") != index
                or str(preview.get("name", "")).casefold() != expected_name.casefold()
                or str(preview.get("layer", "")).casefold() != expected_layer.casefold()
                or type(preview.get("point_count_before")) is not int
                or preview["point_count_before"] < 3
                or preview.get("dry_run") is not True
                or not isinstance(bounds, dict)
                or any(type(bounds.get(side)) not in (int, float)
                       or not math.isfinite(bounds[side])
                       for side in ("left", "bottom", "right", "top"))):
            return {"ok": False, "reason": "incomplete or wrong-board pour preview",
                    "native_reply": preview}
        if expected_bounds is not None:
            if (not isinstance(expected_bounds, dict)
                    or any(type(expected_bounds.get(side)) not in (int, float)
                           or not math.isfinite(expected_bounds[side])
                           or not math.isclose(expected_bounds[side], bounds[side],
                                               abs_tol=0.01, rel_tol=0)
                           for side in ("left", "bottom", "right", "top"))):
                return {"ok": False, "reason": "polygon bounds differ from reviewed plan",
                        "current_bounds": bounds}
        if dry_run:
            return preview
        if expected_bounds is None:
            return {"ok": False, "reason": "expected_bounds from a reviewed dry-run is required for writes"}
        params.update({"dry_run": False, "expected_points": preview["point_count_before"],
                       **{f"expected_{side}": bounds[side]
                          for side in ("left", "bottom", "right", "top")}})
        result = await bridge.send_command_async("pcb.grow_pour", params, timeout=120.0)
        if not isinstance(result, dict) or result.get("error"):
            return result
        if (str(result.get("board_path", "")).casefold() != board_path.casefold()
                or result.get("index") != index or result.get("dry_run") is not False
                or result.get("bounds_before") != bounds
                or not isinstance(result.get("bounds_after"), dict)):
            return {"ok": False, "reason": "incomplete or wrong-board pour write reply",
                    "native_reply": result}
        return result

    @mcp.tool()
    async def pcb_modify_polygon(
        index: int,
        net: str = "",
        layer: str = "",
        hatch_style: str = "",
        remove_dead: Optional[bool] = None,
        remove_narrow_necks: Optional[bool] = None,
        remove_islands_by_area: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Modify a polygon pour's properties and its pour options.

        Index from ``pcb_get_polygons``. Nothing here repours: run
        ``pcb_repour_polygons`` after (``repour_needed`` says so).

        Args:
            index: Polygon index (from pcb_get_polygons output)
            net: New net; an unknown name goes to ``not_applied``.
            layer: New layer name.
            hatch_style: "Solid", "NoHatch", "45Degree" or "90Degree".
            remove_dead: Remove copper islands off the net. None leaves
                it unchanged, as for the next two.
            remove_narrow_necks: Remove necks under the threshold.
            remove_islands_by_area: Remove islands under the area
                threshold.

        Returns:
            ``modified`` (something changed), ``success``, ``index``,
            ``name``, ``changed``, ``not_applied``, ``repour_needed``,
            ``note``.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {"index": str(index)}
        if net:
            params["net"] = net
        if layer:
            params["layer"] = layer
        if hatch_style:
            params["hatch_style"] = hatch_style
        # Sent as words rather than omitted-when-false: False is a real
        # request to clear the flag, and `if remove_dead:` would drop it.
        if remove_dead is not None:
            params["remove_dead"] = "true" if remove_dead else "false"
        if remove_narrow_necks is not None:
            params["remove_narrow_necks"] = "true" if remove_narrow_necks else "false"
        if remove_islands_by_area is not None:
            params["remove_islands_by_area"] = (
                "true" if remove_islands_by_area else "false")
        result = await bridge.send_command_async("pcb.modify_polygon", params)
        return result

    @mcp.tool()
    async def pcb_place_3d_body(
        model_path: str,
        x: float = 0,
        y: float = 0,
        layer: str = "TopLayer",
        standoff_height: float = 0,
    ) -> dict[str, Any]:
        """Place a STEP model on the open PCB as a free 3D body (Place >
        3D Body > Generic STEP Model), not inside a component, e.g. a
        fixture, enclosure or device under test.
        Use this rather than ``lib_link_3d_model``, which writes into a
        library footprint, unless the model belongs to a part.

        Rotation cannot be set from here (``rotation_applied: false``);
        rotate in the editor.

        Args:
            model_path: absolute path to the .step / .stp file.
            x: X of the model's own origin in mils; where the body lands
                depends on how the STEP was authored, so check it against
                a known feature.
            y: Y of the model's origin in mils.
            layer: board layer to attach it to.
            standoff_height: underside height above the board, mils.

        Returns:
            ``{"success", "model_path", "x", "y", "layer",
            "standoff_height", "standoff_applied", "rotation_applied",
            "note"}``; x and y are read back from the placed body.
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "model_path": model_path,
            "x": _mils(x),
            "y": _mils(y),
            "layer": layer,
            "standoff_height": _mils(standoff_height),
        }
        return await bridge.send_command_async("pcb.place_3d_body", params)

    @mcp.tool()
    async def pcb_place_extruded_body(
        overall_height: float,
        points: Optional[list[Any]] = None,
        x1: float = 0,
        y1: float = 0,
        x2: float = 0,
        y2: float = 0,
        standoff_height: float = 0,
        layer: str = "TopLayer",
        identifier: str = "",
        color: Optional[int] = None,
        opacity: Optional[float] = None,
    ) -> dict[str, Any]:
        """Place an extruded 3D body on the open PCB: an outline lifted
        from ``standoff_height`` to ``overall_height``.

        A clearance or keep-in volume, an enclosure feature, or the body
        of a part with no STEP model. A STEP model (``pcb_place_3d_body``)
        is the accurate body and comes first; this is the fallback.

        Args:
            overall_height: top of the body above the board, mils.
            points: outline ``[{x, y}]`` or ``[[x, y]]`` in mils, three or
                more vertices, decimals kept; or leave it out and give the
                rectangle x1, y1, x2, y2.
            x1, y1, x2, y2: opposite corners in mils when no points.
            standoff_height: underside above the board, mils (default 0).
            layer: the layer the body belongs to; a bottom layer makes it
                project from the bottom side.
            identifier: a name to find the body again by.
            color: Altium TColor integer.
            opacity: 0 (clear) to 1 (solid).

        Returns:
            ``placed``, ``outline``, ``standoff_height``,
            ``overall_height``, ``identifier`` and ``layer`` read back
            from the body, and ``*_applied`` for each optional property.
        """
        if not 0 <= standoff_height < overall_height:
            return {"ok": False,
                    "reason": "need 0 <= standoff_height < overall_height"}
        params: dict[str, Any] = {
            "overall_height": str(float(overall_height)),
            "standoff_height": str(float(standoff_height)),
            "layer": layer,
        }
        if points:
            try:
                pairs = [(float(p["x"]), float(p["y"])) if isinstance(p, dict)
                         else (float(p[0]), float(p[1])) for p in points]
            except (KeyError, IndexError, TypeError, ValueError):
                return {"ok": False,
                        "reason": "each point is {x, y} or [x, y] in mils"}
            if len(pairs) < 3:
                return {"ok": False,
                        "reason": "an outline needs three or more points"}
            params["points"] = "/".join(f"{x},{y}" for x, y in pairs)
        else:
            if x1 == x2 or y1 == y2:
                return {"ok": False,
                        "reason": "give points, or a rectangle with an area"}
            params.update({"x1": str(float(x1)), "y1": str(float(y1)),
                           "x2": str(float(x2)), "y2": str(float(y2))})
        if identifier:
            params["identifier"] = identifier
        if color is not None:
            params["color"] = str(int(color))
        if opacity is not None:
            params["opacity"] = str(min(max(float(opacity), 0.0), 1.0))
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.place_extruded_body", params)

    @mcp.tool()
    async def pcb_get_room_rules() -> dict[str, Any]:
        """Get all room-like rules (confinement constraint design rules).

        Returns design rules of kind eRule_ConfinementConstraint, these are
        NOT physical IPCB_Room objects on the board. The rule bounding rect
        is reported as x1/y1/x2/y2 in mils.

        Returns:
            Dictionary with "room_rules" array (each with name, enabled, kind,
            scope_1, comment, x1, y1, x2, y2) and "count"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_room_rules", {})
        return result

    @mcp.tool()
    async def pcb_create_room(
        name: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        components: str = "",
    ) -> dict[str, Any]:
        """Create a room for component grouping on the active PCB.

        Creates a confinement constraint rule that defines a rectangular
        region. Components can be assigned via scope expression.

        Args:
            name: Room name (e.g., "Power Section", "USB Block")
            x1: First corner X in mils
            y1: First corner Y in mils
            x2: Second corner X in mils
            y2: Second corner Y in mils
            components: Comma-separated component designators to confine
                (e.g., "U1,U2,R1,R2"). Optional; empty = applies to all.

        Returns:
            Dictionary with created status, name, coordinates, and scope
        """
        bridge = get_bridge()
        params: dict[str, Any] = {
            "name": name,
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
        }
        if components:
            params["components"] = components
        result = await bridge.send_command_async("pcb.create_room", params)
        return result

    @mcp.tool()
    async def pcb_get_board_statistics() -> dict[str, Any]:
        """Get comprehensive statistics for the active PCB board.

        Returns counts of all object types, total trace length, board
        dimensions, and layer count. Useful for design reviews and
        progress tracking.

        Returns:
            Dictionary with track_count, via_count, pad_count,
            component_count, fill_count, text_count, polygon_count,
            unrouted_connections, total_trace_length_mils,
            board_width_mils, board_height_mils, board_area_sq_mils,
            layer_count, and board_name. ``unrouted_connections``
            counts the ratsnest lines stored on the board, not a
            connectivity verdict, and stored lines can be out of date,
            so it can disagree with the DRC's un-routed net check.
            pcb_get_unrouted_nets with reanalyze=True re-derives them
            first.
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.get_board_statistics", {})
        return result

    @mcp.tool()
    async def pcb_export_coordinates() -> dict[str, Any]:
        """Export component placement coordinates formatted for pick-and-place (like `pcb_get_components`, but the pick-and-place shape: adds side, omits bbox detail).

        Returns designator, footprint, comment, position (x, y),
        rotation, layer, and side (Top/Bottom) for every component.
        Useful for manufacturing pick-and-place machine programming.

        Returns:
            Dictionary with "placements" array (each with designator,
            footprint, comment, x, y, rotation, layer, side) and "count"
        """
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.export_coordinates", {})
        return result

    @mcp.tool()
    async def pcb_create_diff_pair(
        positive_net: str,
        negative_net: str,
        name: str = "",
    ) -> dict[str, Any]:
        """Create a differential pair object from two existing nets.

        The two nets must already exist on the board (typically present
        after update_pcb / ECO). The diff-pair object lets Altium apply
        differential routing constraints and the interactive router to
        honour impedance / matched-length rules between the pair.

        A PAIR MADE ONLY ON THE BOARD IS REMOVED BY THE NEXT SCHEMATIC
        SYNC: the change order deletes board objects the schematic does
        not define (a follow-up take lost both USB pairs that way). To
        keep it, define the pair in the schematic too: net names ending
        _P/_N and a DifferentialPair directive on them (sch_add_directive),
        then sync.

        Args:
            positive_net: Positive-side net name (e.g. "USB_DP")
            negative_net: Negative-side net name (e.g. "USB_DM")
            name: Optional diff-pair name (defaults to "<pos>_<neg>")

        Returns:
            Dictionary confirming creation with name, positive_net, negative_net
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.create_diff_pair",
            {
                "positive_net": positive_net,
                "negative_net": negative_net,
                "name": name,
            },
        )
        if isinstance(result, dict) and result.get("success", True) is not False:
            result.setdefault("note", (
                "board-only: the next schematic sync removes this pair unless "
                "the schematic defines it too (DifferentialPair directive on "
                "_P/_N nets)"))
        return result

    @mcp.tool()
    async def pcb_route_diff_pair(
        positive_net: str,
        negative_net: str,
        centerline: list[dict[str, float]],
        width_mils: float,
        gap_mils: float,
        layer: str = "TopLayer",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Route two matched parallel tracks from one centerline polyline.

        The edge-to-edge gap is held through corners with mitered parallel
        offsets. Both conductors receive the same number and length pattern
        of segments. This is a deterministic geometry operation, not an
        obstacle-avoiding autorouter; run DRC after applying it.

        Args:
            positive_net / negative_net: Existing board net names.
            centerline: Ordered ``[{"x": mils, "y": mils}, ...]`` points.
            width_mils: Width of each conductor.
            gap_mils: Edge-to-edge pair gap.
            layer: Copper routing layer, including inner signal layers.
            dry_run: Return generated geometry without modifying PCB.
        """
        if width_mils <= 0 or gap_mils <= 0:
            return {"success": False, "reason": "width_mils and gap_mils must be > 0"}
        try:
            points = [(float(p["x"]), float(p["y"])) for p in centerline]
            separation = float(width_mils) + float(gap_mils)
            pos, neg = _offset_pair_polyline(points, separation / 2.0)
        except (KeyError, TypeError, ValueError) as exc:
            return {"success": False, "reason": str(exc)}

        tracks: list[dict[str, Any]] = []
        for net, vertices in ((positive_net, pos), (negative_net, neg)):
            for start, end in zip(vertices, vertices[1:]):
                tracks.append({
                    "x1": round(start[0]), "y1": round(start[1]),
                    "x2": round(end[0]), "y2": round(end[1]),
                    "width": round(width_mils), "layer": layer,
                    "net_name": net,
                })
        result: dict[str, Any] = {
            "success": True, "dry_run": dry_run,
            "positive_net": positive_net, "negative_net": negative_net,
            "width_mils": width_mils, "gap_mils": gap_mils,
            "center_separation_mils": separation, "layer": layer,
            "tracks": tracks, "drc_checked": False,
        }
        if dry_run:
            return result
        parts = [
            f"{t['x1']},{t['y1']},{t['x2']},{t['y2']},{t['width']},{t['layer']},{t['net_name']}"
            for t in tracks
        ]
        applied = await get_bridge().send_command_async(
            "pcb.place_tracks", {"tracks": "|".join(parts)}
        )
        result["apply_result"] = applied
        return result

    @mcp.tool()
    async def pcb_place_diff_pair_vias(
        positive_net: str,
        negative_net: str,
        center_x_mils: float,
        center_y_mils: float,
        pair_axis_degrees: float,
        center_separation_mils: float,
        size_mils: int = 24,
        hole_size_mils: int = 10,
        low_layer: str = "TopLayer",
        high_layer: str = "BottomLayer",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Place a symmetric via pair for a differential layer transition.

        Supports through, blind, buried, and microvia spans through the
        existing ``low_layer``/``high_layer`` via API. The two via centers are
        symmetric about the requested point and preserve pair separation.
        """
        if center_separation_mils <= 0 or size_mils <= hole_size_mils:
            return {"success": False, "reason": "invalid separation or via geometry"}
        angle = math.radians(pair_axis_degrees)
        dx = math.cos(angle) * center_separation_mils / 2.0
        dy = math.sin(angle) * center_separation_mils / 2.0
        vias = [
            {"net": positive_net, "x": round(center_x_mils + dx),
             "y": round(center_y_mils + dy)},
            {"net": negative_net, "x": round(center_x_mils - dx),
             "y": round(center_y_mils - dy)},
        ]
        out: dict[str, Any] = {
            "success": True, "dry_run": dry_run, "vias": vias,
            "center_separation_mils": center_separation_mils,
            "low_layer": low_layer, "high_layer": high_layer,
            "size_mils": size_mils, "hole_size_mils": hole_size_mils,
            "drc_checked": False,
        }
        if dry_run:
            return out
        results = []
        for via in vias:
            results.append(await get_bridge().send_command_async(
                "pcb.place_via",
                {"x": str(via["x"]), "y": str(via["y"]),
                 "net": via["net"], "size": str(size_mils),
                 "hole_size": str(hole_size_mils),
                 "low_layer": low_layer, "high_layer": high_layer},
            ))
        out["apply_results"] = results
        return out

    @mcp.tool()
    async def pcb_audit_diff_pair(
        positive_net: str,
        negative_net: str,
        max_skew_mils: float = 10.0,
        require_same_via_count: bool = True,
    ) -> dict[str, Any]:
        """Audit routed length skew and layer-transition symmetry of a pair."""
        bridge = get_bridge()
        lengths = await bridge.send_command_async("pcb.get_trace_lengths", {})
        vias = await bridge.send_command_async("pcb.get_vias", {})
        by_net = {
            str(item.get("net")): float(item.get("length_mils") or 0)
            for item in (lengths.get("trace_lengths") or [])
        }
        p_len, n_len = by_net.get(positive_net, 0.0), by_net.get(negative_net, 0.0)
        p_vias = [v for v in (vias.get("vias") or []) if v.get("net") == positive_net]
        n_vias = [v for v in (vias.get("vias") or []) if v.get("net") == negative_net]
        skew = abs(p_len - n_len)
        violations = []
        if skew > max_skew_mils:
            violations.append("length_skew")
        if require_same_via_count and len(p_vias) != len(n_vias):
            violations.append("via_count_mismatch")
        return {
            "success": True, "positive_net": positive_net,
            "negative_net": negative_net, "positive_length_mils": p_len,
            "negative_length_mils": n_len, "skew_mils": skew,
            "max_skew_mils": max_skew_mils,
            "positive_via_count": len(p_vias),
            "negative_via_count": len(n_vias),
            "violations": violations, "passed": not violations,
            "note": "Track/arc length only; package pin delay is not included.",
        }

    @mcp.tool()
    async def pcb_place_region(
        x1: int = 0,
        y1: int = 0,
        x2: int = 0,
        y2: int = 0,
        layer: str = "TopLayer",
        net: str = "",
        points: Optional[list[Any]] = None,
        name: str = "",
    ) -> dict[str, Any]:
        """Place a solid copper region on a rectangle or a polygon outline.

        Regions are solid primitives; unlike polygons, they don't participate
        in the connectivity engine unless you assign a net. Use for
        mechanical copper zones, thermal pads, or solder-mask openings.
        For a true ground plane with ratsnest tracking, prefer
        pcb_place_polygon_rect.

        Args:
            x1, y1, x2, y2: Opposite corners in mils (any order); not used
                when points is given
            layer: Copper or mech layer (default "TopLayer")
            net: Optional net assignment
            points: Optional outline, ``[{x, y}]`` (or ``[[x, y]]``) in
                mils, three or more vertices in order, decimals kept; the
                outline closes by itself. A vertex given as ``{x, y, sweep}``
                (or ``[x, y, sweep]``) makes the edge from it to the next a
                true arc of ``sweep`` degrees, counterclockwise when
                positive, as in lib_add_footprint_regions
            name: Optional region Name, a tag to find the region again by
                (``obj_query`` filter ``Name=...``); avoid ``=`` and ``|``,
                which split a filter

        Returns:
            Dictionary confirming the region placement, with the ``name``
            read back from the region; with points, also ``vertices`` and
            ``points``, the outline read back from the placed region in mils;
            with arcs, ``arc_edges`` and ``shape``, ``[x, y, sweep]`` per
            vertex read back
        """
        params: dict[str, Any] = {
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "layer": layer,
            "net": net,
        }
        if points:
            try:
                verts = [(float(p["x"]), float(p["y"]), float(p.get("sweep") or 0))
                         if isinstance(p, dict)
                         else (float(p[0]), float(p[1]),
                               float(p[2]) if len(p) > 2 else 0.0)
                         for p in points]
            except (KeyError, IndexError, TypeError, ValueError):
                return {"ok": False,
                        "reason": "each point is {x, y} or [x, y] in mils, "
                                  "with an optional sweep"}
            if len(verts) < 3:
                return {"ok": False,
                        "reason": "an outline needs three or more points"}
            params["points"] = "/".join(f"{x},{y}" for x, y, _ in verts)
            # The same arc form lib_add_footprint_regions sends (#119).
            arcs: list[str] = []
            for k, (x, y, sweep) in enumerate(verts):
                if not sweep:
                    continue
                nx, ny, _ = verts[(k + 1) % len(verts)]
                arc = _edge_arc(x, y, nx, ny, sweep)
                if isinstance(arc, str):
                    return {"ok": False, "reason": f"point {k}: {arc}"}
                cx, cy, r, a1, a2 = arc
                arcs.append(f"{k + 1},{format_length(cx)},{format_length(cy)},"
                            f"{format_length(r)},{_angle_text(a1)},{_angle_text(a2)}")
            if arcs:
                params["arcs"] = "/".join(arcs)
        if name:
            params["name"] = name
        bridge = get_bridge()
        return await bridge.send_command_async("pcb.place_region", params)

    @mcp.tool()
    async def pcb_place_region_poly(
        vertices: list[dict[str, float]],
        layer: str = "TopLayer",
        net: str = "",
        name: str = "",
    ) -> dict[str, Any]:
        """Place a copper region from three or more polygon vertices.

        Args:
            vertices: Ordered ``{"x": ..., "y": ...}`` points in mils.
            layer: Target layer.
            net: Optional net assignment.
            name: Optional region name for later lookup with ``Name=...``.
        """
        if len(vertices) < 3:
            return {"success": False, "reason": "at least 3 vertices required"}
        try:
            pts = ";".join(
                f"{float(point['x']):.15g}:{float(point['y']):.15g}"
                for point in vertices
            )
        except (KeyError, TypeError, ValueError) as exc:
            return {"success": False, "reason": f"invalid vertex: {exc}"}
        return await get_bridge().send_command_async(
            "pcb.place_region_poly",
            {"pts": pts, "layer": layer, "net": net, "name": name},
        )

    @mcp.tool()
    async def pcb_place_image(
        image_path: str,
        x: float,
        y: float,
        width: float,
        units: str = "mil",
        layer: str = "TopOverlay",
        threshold: int = 128,
        invert: bool = False,
        dry_run: bool = True,
        max_regions: int = 2000,
    ) -> dict[str, Any]:
        """Draw a raster image (logo, QR code, artwork) as PCB regions.

        Verified on a live board (2026-10-15): an asymmetric test glyph
        placed at a known origin was read back with pcb_query_region,
        confirming the scale, the bottom-left origin corner, the layer,
        and that the art is neither mirrored nor flipped. Still worth a
        dry_run first on anything real, for the primitive count.

        Putting a logo on silkscreen has no API of its own; this converts
        the image to region primitives and places them. The image is
        decomposed into non-overlapping RECTANGLES rather than traced
        outlines, which is exact (nothing is approximated away from the
        source art) and needs no special handling for holes, at the cost
        of primitive COUNT.

        That count is the thing to look at, which is why **dry_run
        defaults to True**: it returns the plan (how many regions, the
        area covered, the scale) and touches nothing. Anti-aliased or
        dithered artwork can decompose into thousands of pieces, and
        raising ``threshold`` or supplying cleaner two-colour art fixes
        that far better than undoing a placement. Call again with
        dry_run=False to commit.

        Args:
            image_path: PNG/BMP/JPG etc. Any format Pillow reads.
            x, y: Where the image's BOTTOM-LEFT corner sits on the board.
            width: Target width on the board; height follows the image's
                aspect ratio.
            units: "mil" (default) or "mm", for x, y and width.
            layer: Target layer, default "TopOverlay" (silkscreen). Any
                copper or mechanical layer works too.
            threshold: A pixel is ink when its luminance is below this
                (0-255). Raise it to catch more of a washed-out image,
                lower it to drop anti-aliasing fringes.
            invert: For artwork drawn light-on-dark.
            dry_run: True (default) plans without placing.
            max_regions: Refuse rather than place more than this many
                primitives. A photograph will blow straight through it,
                which is the point.

        Returns:
            The plan (region_count, bounds, scale, image) and, when
            committed, how many regions were placed.
        """
        from ..design.image_regions import plan_image_regions

        if normalise_units(units) is None:
            return {"error": f"units must be 'mil' or 'mm', not {units!r}"}
        if normalise_units(units) == "mm":
            x, y, width = (v * MILS_PER_MM for v in (x, y, width))

        plan = plan_image_regions(image_path, origin_x=x, origin_y=y,
                                  target_width_mils=width,
                                  threshold=threshold, invert=invert)
        if not plan["ok"]:
            return {"success": False, "reason": plan["reason"]}

        regions = plan.pop("regions")
        summary = {**plan, "layer": layer, "dry_run": dry_run}

        if dry_run:
            summary["note"] = (
                f"planned {plan['region_count']} region(s); nothing placed. "
                f"Call again with dry_run=False to commit.")
            return summary

        if plan["region_count"] > max_regions:
            return {"success": False, "reason":
                    f"{plan['region_count']} regions exceeds max_regions "
                    f"({max_regions}). Raise the cap deliberately, raise "
                    f"threshold, or use cleaner two-colour artwork: this "
                    f"many primitives is slow to place and slow to edit.",
                    **{k: plan[k] for k in ("scale", "bounds", "image")}}

        bridge = get_bridge()
        placed = 0
        for region in regions:
            pts = ";".join(f"{v['x']:g}:{v['y']:g}" for v in region["vertices"])
            result = await bridge.send_command_async(
                "pcb.place_region_poly",
                {"pts": pts, "layer": layer, "net": ""},
            )
            # Stop at the first refusal rather than pressing on: a wrong
            # layer name fails identically every time, and finishing the
            # run would leave a thousand of them to undo.
            if isinstance(result, dict) and result.get("success") is False:
                return {"success": False, "placed": placed,
                        "reason": f"region {placed + 1} failed: "
                                  f"{result.get('reason', result)}",
                        **{k: plan[k] for k in ("scale", "bounds", "image")}}
            placed += 1

        return {"success": True, "placed": placed, **summary}

    @mcp.tool()
    async def pcb_place_dimension(
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: str = "TopOverlay",
        orientation: str = "",
    ) -> dict[str, Any]:
        """Place a linear dimension between two points.

        Horizontal dimension measures delta-X, vertical measures delta-Y.
        Orientation auto-detects from the larger axis delta if not given.

        Args:
            x1, y1: First reference point in mils
            x2, y2: Second reference point in mils
            layer: Layer to draw the dimension on (default "TopOverlay")
            orientation: "horizontal" or "vertical" ("" = auto)

        Returns:
            Dictionary confirming the dimension placement
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_dimension",
            {
                "x1": str(x1),
                "y1": str(y1),
                "x2": str(x2),
                "y2": str(y2),
                "layer": layer,
                "orientation": orientation,
            },
        )
        return result

    @mcp.tool()
    async def pcb_place_pad(
        x: float,
        y: float,
        name: str = "",
        net: str = "",
        shape: str = "round",
        x_size: Optional[float] = None,
        y_size: Optional[float] = None,
        hole_size: float = 0,
        layer: str = "TopLayer",
        units: str = "mil",
    ) -> dict[str, Any]:
        """Place a standalone pad on the active PCB.

        Not part of any component. Use for fiducials, test points,
        mounting holes. Set hole_size=0 for surface-mount pads,
        nonzero for through-hole.

        Args:
            x, y: Position in mils
            name: Pad designator / label (optional)
            net: Net to connect to (optional)
            shape: "round" (default) / "rect" / "oct", or spelled out as
                the library tools take them ("rectangular", "octagonal").
                Any other word is refused; it used to become a round pad.
            x_size, y_size: Pad dimensions (default 60 mil)
            hole_size: Drill diameter (0 = SMD)
            layer: Copper layer (default "TopLayer")
            units: "mil" (default) or "mm", for the position and every
                size, kept exact rather than rounded to whole mils.

        Returns:
            Dictionary confirming pad placement
        """
        if normalise_units(units) is None:
            return {"error": f"units must be 'mil' or 'mm', not {units!r}"}
        params: dict[str, Any] = {
            "x": format_length(x),
            "y": format_length(y),
            "name": name,
            "net": net,
            "shape": shape,
            "x_size": format_length(
                length_in(units, 60) if x_size is None else x_size),
            "y_size": format_length(
                length_in(units, 60) if y_size is None else y_size),
            "hole_size": format_length(hole_size),
            "layer": layer,
        }
        if normalise_units(units) == "mm":
            params["units"] = "mm"
        bridge = get_bridge()
        result = await bridge.send_command_async("pcb.place_pad", params)
        return result

    @mcp.tool()
    async def pcb_place_components(
        placements: list[dict[str, Any]],
        board_path: str = "",
    ) -> dict[str, Any]:
        """Place one or many footprints from PcbLibs onto the board in ONE call.

        The scriptable substitute for ECO / *Design ▸ Update PCB Document*:
        Altium's ECO always raises a modal, so for unattended population this
        drops footprints straight onto the board. It resolves the board once
        and places every footprint in a single Altium transaction (one IPC
        round-trip). Pass a single-element list to place just one.

        Two modes per component: **geometry only** (omit ``unique_id`` /
        ``pad_nets``) leaves pads unconnected (DRC flags them), good for
        artwork / panelization / fiducials / placement studies; **synced**
        (pass both) stamps the PCB SourceUniqueId so a later ECO matches the
        part and creates+assigns each pad's net for real connectivity. In a
        hierarchical project ``unique_id`` normally has the form
        ``\\SHEET_UNIQUE_ID\\COMPONENT_UNIQUE_ID``; the short schematic
        UniqueId alone is insufficient. Derive the prefix from a known matched
        component on the same sheet (``pcb_get_components`` returns
        ``source_unique_id``) or compiled mappings. Read ``pad_nets`` from the
        compiled
        netlist (``proj_get_connectivity_many`` → pad number → net).

        ``board_path``: target a specific .PcbDoc when several are open
        (resolved once for the whole batch). Otherwise the focused board
        is used.

        Args:
            placements: List of placement dicts, each with:
                footprint (required), library_path (required, .PcbLib),
                x, y (mils), designator, lib_reference, comment,
                rotation, layer, unique_id, and pad_nets
                (``{pad_name: net_name}``); omit unique_id/pad_nets for
                geometry-only, include them for a synced placement.

                A bottom layer is placed on top first, then flipped in a
                separate Altium transaction so its pads are mirrored.
            board_path: Absolute .PcbDoc path to place onto (optional).

        Returns:
            Dict with ``placed`` (count), ``failed`` (count), ``total``.

        After placement, save and force a project recompile, then require no
        unmatched components on either side. Equal counts alone do not prove
        that the SourceUniqueId link is valid.
        """
        recs: list[str] = []
        wanted_bottom: list[str] = []
        for p in placements:
            fp = str(p.get("footprint", "")).strip()
            lib = str(p.get("library_path", "")).strip()
            if not fp or not lib:
                continue
            bottom = "bottom" in str(p.get("layer") or "").strip().lower()
            designator = str(p.get("designator") or "").strip()
            if bottom and not designator:
                return {"ok": False, "placed": 0,
                        "reason": "bottom-side placement requires a designator for the flip"}
            fields = [f"footprint=={fp}", f"library_path=={lib}"]
            for key in ("lib_reference", "designator", "comment",
                        "layer", "unique_id"):
                v = str(p.get(key, "") or "").strip()
                if v:
                    fields.append(f"{key}=={v}")
            fields.append(f"x=={_mils(p.get('x', 0))}")
            fields.append(f"y=={_mils(p.get('y', 0))}")
            if p.get("rotation") is not None:
                rotation = p.get("rotation")
                if bottom:
                    try:
                        rotation = (180.0 - float(rotation)) % 360
                        if rotation.is_integer():
                            rotation = int(rotation)
                    except (TypeError, ValueError):
                        pass
                fields.append(f"rotation=={rotation}")
            pn = p.get("pad_nets")
            if pn:
                pn_str = "|".join(
                    f"{str(k).strip()}={str(v).strip()}"
                    for k, v in pn.items()
                    if str(k).strip() and str(v).strip()
                )
                if pn_str:
                    fields.append(f"pad_nets=={pn_str}")
            recs.append(";;".join(fields))
            if bottom:
                wanted_bottom.append(designator)

        if not recs:
            return {"error": "No valid placements (need footprint + "
                    "library_path)", "placed": 0}

        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_components",
            {"placements": "~~".join(recs), "board_path": board_path},
        )
        if not wanted_bottom or not isinstance(result, dict):
            return result
        if result.get("success") is False or result.get("ok") is False:
            return result
        exact_board = str(result.get("board_path") or board_path)
        if not exact_board:
            result["flip_failed"] = {d: "placement did not report its board path"
                                     for d in wanted_bottom}
            result["success"] = False
            return result
        flipped: list[str] = []
        failed: dict[str, str] = {}
        for designator in wanted_bottom:
            try:
                reply = await bridge.send_command_async(
                    "pcb.flip_component",
                    {"designator": designator, "board_path": exact_board})
                if isinstance(reply, dict) and (
                        reply.get("success") is False or reply.get("ok") is False):
                    failed[designator] = str(reply.get("error") or reply)
                else:
                    flipped.append(designator)
            except Exception as exc:  # noqa: BLE001 - report partial placement
                failed[designator] = str(exc)
        result["flipped_to_bottom"] = flipped
        if failed:
            result["flip_failed"] = failed
            result["success"] = False
            result["warning"] = "placed, but these parts remain on top: " + ", ".join(sorted(failed))
        return result

    @mcp.tool()
    async def pcb_place_angular_dimension(
        center_x: float,
        center_y: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float = 100,
        layer: str = "TopOverlay",
    ) -> dict[str, Any]:
        """Place an angular dimension (angle between two reference directions).

        Args:
            center_x, center_y: Vertex of the angle in mils
            x1, y1: First reference direction endpoint in mils
            x2, y2: Second reference direction endpoint in mils
            radius: Arc radius at which to draw the dimension in mils
            layer: Layer (default "TopOverlay")

        Returns:
            Dictionary confirming the angular dimension
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_angular_dimension",
            {
                "center_x": _mils(center_x),
                "center_y": _mils(center_y),
                "x1": _mils(x1),
                "y1": _mils(y1),
                "x2": _mils(x2),
                "y2": _mils(y2),
                "radius": _mils(radius),
                "layer": layer,
            },
        )
        return result

    @mcp.tool()
    async def pcb_place_radial_dimension(
        center_x: int,
        center_y: int,
        radius: int,
        layer: str = "TopOverlay",
    ) -> dict[str, Any]:
        """Place a radial dimension around a center point with a given radius.

        Args:
            center_x, center_y: Center point in mils
            radius: Radius to dimension in mils
            layer: Layer (default "TopOverlay")

        Returns:
            Dictionary confirming the radial dimension
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.place_radial_dimension",
            {
                "center_x": str(center_x),
                "center_y": str(center_y),
                "radius": str(radius),
                "layer": layer,
            },
        )
        return result

    @mcp.tool()
    async def pcb_distribute_components(
        designators: str,
        axis: str = "x",
        start: float = 0,
        end: float = 1000,
    ) -> dict[str, Any]:
        """Evenly space components along an axis.

        Moves each named component so its X (or Y) coordinate lands at
        equally-spaced stops from `start` to `end`. Order follows the
        designators list, designators="R1,R2,R3" with start=0 end=200
        places R1 at 0, R2 at 100, R3 at 200 on the chosen axis. Y (or X)
        is untouched.

        Args:
            designators: Comma-separated list of component designators
            axis: "x" or "y" (default "x")
            start: First position in mils
            end: Last position in mils

        Returns:
            Dictionary with distribution result
        """
        bridge = get_bridge()
        result = await bridge.send_command_async(
            "pcb.distribute_components",
            {
                "designators": designators,
                "axis": axis,
                "start": _mils(start),
                "end": _mils(end),
            },
        )
        return result

    @mcp.tool()
    async def pcb_get_pair_impedance_rule(
        board_path: str, rule_name: str,
    ) -> dict[str, Any]:
        """Read numeric impedance limits of one Differential Pairs Routing rule."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not rule_name.strip():
            return {"ok": False, "reason": "rule_name is required"}
        reply = await get_bridge().send_command_async(
            "pcb.pair_impedance_rule",
            {"board_path": board_path, "rule_name": rule_name.strip()}, timeout=120.0,
        )
        try:
            _pair_impedance_snapshot(reply, board_path, rule_name.strip())
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_set_pair_impedance_rule(
        board_path: str,
        rule_name: str,
        impedance_driven: Optional[bool] = None,
        min_ohms: Optional[float] = None,
        max_ohms: Optional[float] = None,
        preferred_ohms: Optional[float] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Plan or set the pair impedance-driven flag with exact-board checks.

        Numeric fields remain readable but Altium 26.11 did not persist their
        direct SDK writes across an exact save and reopen. Saving is separate.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not rule_name.strip():
            return {"ok": False, "reason": "rule_name is required"}
        updates = {"impedance_driven": impedance_driven,
                   "min_ohms": min_ohms, "max_ohms": max_ohms,
                   "preferred_ohms": preferred_ohms}
        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            return {"ok": False, "reason": "give at least one impedance setting"}
        if any(key in updates for key in ("min_ohms", "max_ohms", "preferred_ohms")):
            return {"ok": False, "reason":
                    "numeric pair impedance fields did not persist after Altium 26.11 save/reopen"}
        if ("impedance_driven" in updates
                and type(updates["impedance_driven"]) is not bool):
            return {"ok": False, "reason": "impedance_driven must be boolean"}
        bridge = get_bridge()
        base = {"board_path": board_path, "rule_name": rule_name.strip()}
        snapshot = await bridge.send_command_async(
            "pcb.pair_impedance_rule", base, timeout=120.0,
        )
        try:
            old = _pair_impedance_snapshot(snapshot, board_path, rule_name.strip())
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": snapshot}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "rule_name": rule_name.strip(), "before": old,
                    "would_set": updates}
        params = {**base,
                  "expect_impedance_driven": "true" if old["impedance_driven"] else "false",
                  "expect_min_ohms": str(old["min_ohms"]),
                  "expect_max_ohms": str(old["max_ohms"]),
                  "expect_preferred_ohms": str(old["preferred_ohms"])}
        for key, value in updates.items():
            params[key] = ("true" if value else "false") if key == "impedance_driven" else str(value)
        reply = await bridge.send_command_async("pcb.pair_impedance_rule", params, timeout=120.0)
        try:
            after = _pair_impedance_snapshot(reply, board_path, rule_name.strip())
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reply}
        for key, value in updates.items():
            actual = after[key]
            matched = (actual is value if key == "impedance_driven" else
                       math.isclose(actual, value, abs_tol=0.001))
            if not matched:
                return {"ok": False, "reason": f"{key} did not read back",
                        "native_reply": reply}
        reread = await bridge.send_command_async("pcb.pair_impedance_rule", base, timeout=120.0)
        try:
            confirmed = _pair_impedance_snapshot(reread, board_path, rule_name.strip())
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reread}
        if any((confirmed[key] is not value if key == "impedance_driven" else
                not math.isclose(confirmed[key], value, abs_tol=0.001))
               for key, value in updates.items()):
            return {"ok": False, "reason": "independent impedance readback disagrees",
                    "native_reply": reread}
        reply["save_required"] = bool(reply.get("changed"))
        return reply

    @mcp.tool()
    async def pcb_get_rule_properties(name: str) -> dict[str, Any]:
        """Read a named PCB design rule: name, rule_kind, enabled,
        priority, and a ``descriptor`` string holding the constraint
        values as Altium words them, e.g.
        ``"Clearance Constraint (Gap=0.127mm) (All),(All)"``. Parse it
        for numbers.

        The descriptor is a limit of this read, not of the API: to
        CHANGE a constraint use ``pcb_set_rule_properties``, which
        reaches the values. ``obj_modify`` does not; it reports a match
        and changes nothing.

        A clearance-family rule also returns ``gap_mm`` from the rule
        itself; for Board Outline Clearance the descriptor says
        ``Gap=0mil`` whatever the rule holds, so read ``gap_mm``.

        Args:
            name: Design rule name (e.g., "Clearance", "Width", "RoutingVias").

        Returns:
            Dict with name, rule_kind, enabled, priority, descriptor, and
            gap_mm for a clearance-family rule.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.get_rule_properties", {"name": name}
        )

    @mcp.tool()
    async def pcb_set_rule_properties(
        name: str,
        enabled: bool | None = None,
        scope1: str | None = None,
        scope2: str | None = None,
        comment: str | None = None,
        gap_mils: int | None = None,
        gap_mm: float | None = None,
        min_width_mils: float | None = None,
        max_width_mils: float | None = None,
        favored_width_mils: float | None = None,
        min_width_mm: float | None = None,
        max_width_mm: float | None = None,
        favored_width_mm: float | None = None,
        connect_style: str | None = None,
        relief_width_mils: float | None = None,
        relief_width_mm: float | None = None,
        air_gap_mils: float | None = None,
        air_gap_mm: float | None = None,
        entries: int | None = None,
        relief_angle: int | None = None,
        relief_expansion_mils: float | None = None,
        dp_min_gap_mils: float | None = None,
        dp_max_gap_mils: float | None = None,
        dp_preferred_gap_mils: float | None = None,
        dp_min_gap_mm: float | None = None,
        dp_max_gap_mm: float | None = None,
        dp_preferred_gap_mm: float | None = None,
        dp_impedance_driven: bool | None = None,
        dp_min_impedance: float | None = None,
        dp_max_impedance: float | None = None,
        dp_preferred_impedance: float | None = None,
        height_min_mils: float | None = None,
        height_max_mils: float | None = None,
        height_preferred_mils: float | None = None,
        vertical_gap_mils: float | None = None,
        show_distances: bool | None = None,
        collision_check_mode: int | None = None,
        corner_min_setback_mils: float | None = None,
        corner_max_setback_mils: float | None = None,
        antenna_tolerance_mils: float | None = None,
        fanout_style: int | None = None,
        fanout_direction: int | None = None,
        bga_fanout_direction: int | None = None,
        bga_via_mode: int | None = None,
        fanout_via_grid_mils: float | None = None,
        width_impedance_driven: bool | None = None,
        width_min_impedance: float | None = None,
        width_max_impedance: float | None = None,
        width_preferred_impedance: float | None = None,
        check_connected_copper: bool | None = None,
        min_hole_size_mils: int | None = None,
        max_hole_size_mils: int | None = None,
        min_via_size_mils: float | None = None,
        max_via_size_mils: float | None = None,
        preferred_via_size_mils: float | None = None,
        min_via_hole_mils: float | None = None,
        max_via_hole_mils: float | None = None,
        preferred_via_hole_mils: float | None = None,
        testpoint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update metadata AND constraint values of a named PCB design rule.

        Metadata fields always apply. Constraint fields are dispatched
        by the rule's underlying RuleKind:

        - Clearance (kind 0), ComponentClearance (kind 24),
          HoleToHoleClearance (kind 52), MinimumSolderMaskSliver
          (kind 53), SilkToSolderMaskClearance (kind 54),
          SilkToSilkClearance (kind 55), and BoardOutlineClearance
          (kind 63): ``gap_mils``, or ``gap_mm`` when the value is
          metric. An integer mil field cannot express 0.2mm; it lands
          on 8 mils, which is 0.2032mm. Pass one or the other.
        - Width (kind 2): ``min_width_mils`` / ``max_width_mils`` /
          ``favored_width_mils`` (applied to every layer).
        - HoleSize (kind 42): ``min_hole_size_mils`` / ``max_hole_size_mils``.
        - Routing Via: ``min_via_size_mils`` / ``max_via_size_mils`` /
          ``preferred_via_size_mils`` and the three ``*_via_hole_mils``.
          Checked as a set first (minimum <= preferred <= maximum, every
          diameter larger than its hole) and each read back; the reply
          carries ``via_sizes_mils`` and ``via_sizes_written``. A rule in
          template mode keeps checking its templates, and ``via_note``
          says so; this cannot switch a rule between modes.

        THE GAP WRITE IS READ BACK, not assumed. A rule kind that does
        not really carry Gap can accept the assignment and keep its old
        value, so the reply carries ``gap_written``, ``gap_after_mm``
        and, when it did not take, a note saying the rule still holds
        the old number. Kind 63 in particular is included on the
        strength of its position in the TRuleKind order rather than a
        documented interface, so let ``gap_written`` decide whether it
        worked rather than the count.

        Pass only the parameters you want to change; everything else
        stays untouched. Each VERIFIED field write increments
        ``properties_updated`` in the response, so a refused constraint
        no longer inflates it.

        NOTE: Priority is NOT writable from this tool. ``IPCB_Rule.Priority``
        is a read-only function in the PCB scripting API
        (``Function Priority : TRulePrecedence``), not a property; there
        is no ``SetState_Priority`` or ``SetPriority`` method either.
        Assigning to it crashes the DelphiScript engine. To reorder rule
        priorities, drag them in Altium's UI (PCB > Rules and Constraints
        Editor; rules earlier in a category have higher priority).

        Args:
            name: Rule name to update.
            enabled: Whether DRC enforces the rule.
            scope1 / scope2: Rule scope query expressions. A comparison
                joined by And/Or/Xor/Not must be bracketed
                (``"IsPad And (HoleSize > 3)"``) or joined with ``&&``;
                an unbracketed one is refused before anything is sent.
            comment: Free-form comment.
            gap_mils: Clearance gap, or the sliver width for a
                MinimumSolderMaskSliver rule. Applies to every kind
                listed above.
            min_width_mils / max_width_mils / favored_width_mils:
                Width constraint values (applied to every layer); decimals
                allowed. The *_mm forms are exact (0.09 mm is 3.543 mil).
                On a Differential Pairs Routing rule (kind 51) they set the
                pair's track widths.
            dp_min_gap_mils / dp_max_gap_mils / dp_preferred_gap_mils and
                the *_mm forms: a Differential Pairs Routing rule's gaps,
                every layer. Read back in ``diff_pair_descriptor``.
            dp_impedance_driven, dp_min_impedance / dp_max_impedance /
                dp_preferred_impedance: a Differential Pairs Routing
                rule's width and gap follow an impedance profile, and its
                limits in ohms. Read back in ``impedance``; any that did not
                take is in ``impedance_not_applied``.
            height_min_mils / height_max_mils / height_preferred_mils: a
                Height rule's part height limits.
            vertical_gap_mils, show_distances, collision_check_mode: a
                Component Clearance rule's vertical gap, whether it shows
                the distances, and its check mode (Altium's number).
            corner_min_setback_mils / corner_max_setback_mils: a Routing
                Corners rule's setbacks.
            antenna_tolerance_mils: a Net Antennae rule's tolerance.
            fanout_style, fanout_direction, bga_fanout_direction,
                bga_via_mode (Altium's numbers) and fanout_via_grid_mils:
                a Fanout Control rule.
            width_impedance_driven, width_min_impedance /
                width_max_impedance / width_preferred_impedance (ohms) and
                check_connected_copper: a Width rule.
                These settings are read back in ``settings``; any that did
                not take is in ``settings_not_applied``. A setting for a
                rule of another kind is refused.
            connect_style: Polygon Connect (kind 20) or Power Plane Connect
                (kind 6) rule: "relief", "direct" or "none". Confirmed from
                the rule's own descriptor (``connect_style_confirmed``).
            relief_width_mils / relief_width_mm, air_gap_mils / air_gap_mm,
                entries (2 or 4), relief_angle (45 or 90, polygon only),
                relief_expansion_mils (plane only): the relief's settings.
            min_hole_size_mils / max_hole_size_mils: HoleSize
                constraint limits.

        Returns:
            Dict with name, rule_kind, and properties_updated count.
        """
        for given in (scope1, scope2):
            refusal = _scope_refusal(given, properties_updated=0) if given else None
            if refusal:
                return refusal
        params: dict[str, Any] = {"name": name}
        for key, value in [
            ("scope1", scope1),
            ("scope2", scope2),
            ("comment", comment),
            ("gap_mils", gap_mils),
            ("gap_mm", gap_mm),
            ("min_width_mils", min_width_mils),
            ("max_width_mils", max_width_mils),
            ("favored_width_mils", favored_width_mils),
            ("min_width_mm", min_width_mm),
            ("max_width_mm", max_width_mm),
            ("favored_width_mm", favored_width_mm),
            ("connect_style", connect_style),
            ("relief_width_mils", relief_width_mils),
            ("relief_width_mm", relief_width_mm),
            ("air_gap_mils", air_gap_mils),
            ("air_gap_mm", air_gap_mm),
            ("entries", entries),
            ("relief_angle", relief_angle),
            ("relief_expansion_mils", relief_expansion_mils),
            ("dp_min_gap_mils", dp_min_gap_mils),
            ("dp_max_gap_mils", dp_max_gap_mils),
            ("dp_preferred_gap_mils", dp_preferred_gap_mils),
            ("dp_min_gap_mm", dp_min_gap_mm),
            ("dp_max_gap_mm", dp_max_gap_mm),
            ("dp_preferred_gap_mm", dp_preferred_gap_mm),
            ("min_hole_size_mils", min_hole_size_mils),
            ("max_hole_size_mils", max_hole_size_mils),
            ("min_via_size_mils", min_via_size_mils),
            ("max_via_size_mils", max_via_size_mils),
            ("preferred_via_size_mils", preferred_via_size_mils),
            ("min_via_hole_mils", min_via_hole_mils),
            ("max_via_hole_mils", max_via_hole_mils),
            ("preferred_via_hole_mils", preferred_via_hole_mils),
            ("dp_min_impedance", dp_min_impedance),
            ("dp_max_impedance", dp_max_impedance),
            ("dp_preferred_impedance", dp_preferred_impedance),
            ("height_min_mils", height_min_mils),
            ("height_max_mils", height_max_mils),
            ("height_preferred_mils", height_preferred_mils),
            ("vertical_gap_mils", vertical_gap_mils),
            ("collision_check_mode", collision_check_mode),
            ("corner_min_setback_mils", corner_min_setback_mils),
            ("corner_max_setback_mils", corner_max_setback_mils),
            ("antenna_tolerance_mils", antenna_tolerance_mils),
            ("fanout_style", fanout_style),
            ("fanout_direction", fanout_direction),
            ("bga_fanout_direction", bga_fanout_direction),
            ("bga_via_mode", bga_via_mode),
            ("fanout_via_grid_mils", fanout_via_grid_mils),
            ("width_min_impedance", width_min_impedance),
            ("width_max_impedance", width_max_impedance),
            ("width_preferred_impedance", width_preferred_impedance),
        ]:
            if value is not None:
                params[key] = str(value)
        for key in ("dp_min_impedance", "dp_max_impedance", "dp_preferred_impedance",
                    "width_min_impedance", "width_max_impedance",
                    "width_preferred_impedance"):
            if key in params and float(params[key]) <= 0:
                return {"ok": False, "reason": f"{key} is more than 0 ohms"}
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        for key in ("height_min_mils", "height_max_mils", "height_preferred_mils",
                    "vertical_gap_mils", "corner_min_setback_mils",
                    "corner_max_setback_mils", "antenna_tolerance_mils",
                    "fanout_via_grid_mils", "collision_check_mode", "fanout_style",
                    "fanout_direction", "bga_fanout_direction", "bga_via_mode"):
            if key in params and float(params[key]) < 0:
                return {"ok": False, "reason": f"{key} is 0 or more"}
        for key, value in (("width_impedance_driven", width_impedance_driven),
                           ("check_connected_copper", check_connected_copper)):
            if value is not None:
                params[key] = "true" if value else "false"
        if show_distances is not None:
            params["show_distances"] = "true" if show_distances else "false"
        if dp_impedance_driven is not None:
            params["dp_impedance_driven"] = "true" if dp_impedance_driven else "false"
        for key, value in (testpoint or {}).items():
            if key not in _TESTPOINT_SETTINGS:
                return {"ok": False, "reason": f"testpoint has no setting {key}; it takes "
                        + ", ".join(_TESTPOINT_SETTINGS)}
            if _TESTPOINT_SETTINGS[key]:
                if not isinstance(value, bool):
                    return {"ok": False, "reason": f"testpoint {key} is True or False"}
                params["testpoint_" + key] = "true" if value else "false"
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                    return {"ok": False, "reason": f"testpoint {key} is a length of 0 or more"}
                params["testpoint_" + key] = repr(float(value))

        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.set_rule_properties", params
        )

    @mcp.tool()
    async def pcb_place_embedded_board(
        child_path: str,
        x: int,
        y: int,
        rows: int = 1,
        cols: int = 1,
        row_spacing_mils: int = 0,
        col_spacing_mils: int = 0,
        mirror: bool = False,
        layer: str = "TopLayer",
    ) -> dict[str, Any]:
        """Place an embedded-board array (panel) referencing a child PCB.

        An embedded board is a grid of copies of a child .PcbDoc file,
        used for panelization (multi-up arrays, step-and-repeat).

        Args:
            child_path: Full path to the child .PcbDoc file.
            x, y: Bottom-left corner of the array in mils.
            rows, cols: Grid size (default 1x1).
            row_spacing_mils, col_spacing_mils: Gap between array cells.
            mirror: Flip the child board over when True.
            layer: Placement layer for the embedded-board primitive.

        Returns:
            Dict with success, child_path, rows, cols, x, y.
        """
        bridge = get_bridge()
        return await bridge.send_command_async(
            "pcb.place_embedded_board",
            {
                "child_path": child_path,
                "x": str(x),
                "y": str(y),
                "rows": str(rows),
                "cols": str(cols),
                "row_spacing_mils": str(row_spacing_mils),
                "col_spacing_mils": str(col_spacing_mils),
                "mirror": "true" if mirror else "false",
                "layer": layer,
            },
        )

    @mcp.tool()
    async def pcb_get_fab_board_facts(board_path: str) -> dict[str, Any]:
        """Read one uncapped fab comparison snapshot from the exact PcbDoc."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.get_fab_board_facts", {"board_path": board_path}, timeout=120.0,
        )
        try:
            _fab_board_facts(reply, board_path)
        except (ValueError, TypeError, KeyError) as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_get_xsignals(board_path: str) -> dict[str, Any]:
        """Read every xSignal, its lengths and path items from one exact PcbDoc.

        The reply names the board. A missing native pair or mismatched count
        is reported as incomplete rather than silently returning a short list.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.get_xsignals", {"board_path": board_path}, timeout=120.0,
        )
        pairs = reply.get("xsignals") if isinstance(reply, dict) else None
        count = reply.get("count") if isinstance(reply, dict) else None
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or type(count) is not int or count < 0
                or not isinstance(pairs, list) or len(pairs) != count):
            return {"ok": False, "reason": "native xSignal read is incomplete or from a different board",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_create_xsignals(
        board_path: str,
        expected_count: int,
        pins: list[str],
        class_name: str = "",
    ) -> dict[str, Any]:
        """Create xSignals between at least two pads on an exact board.

        Obtain expected_count from pcb_get_xsignals immediately before the
        write. The native handler rejects a changed count and reads back
        created pairs; a failed or partial result is exposed to the caller.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if type(expected_count) is not int or expected_count < 0:
            return {"ok": False, "reason": "expected_count must be non-negative"}
        if not isinstance(pins, list) or len(pins) < 2 or any(
            not isinstance(p, str) or "\t" in p or "." not in p
            or not p.split(".", 1)[0] or not p.split(".", 1)[1]
            for p in pins
        ):
            return {"ok": False, "reason": "pins must contain at least two designator.pad names"}
        if len({p.casefold() for p in pins}) != len(pins) or "\t" in class_name:
            return {"ok": False, "reason": "pins must be unique and class_name cannot contain tabs"}
        reply = await get_bridge().send_command_async(
            "pcb.create_xsignals",
            {"board_path": board_path, "expected_count": str(expected_count),
             "pins": "\t".join(pins), "class_name": class_name}, timeout=120.0,
        )
        created = reply.get("created") if isinstance(reply, dict) else None
        after = reply.get("count_after") if isinstance(reply, dict) else None
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or reply.get("count_before") != expected_count
                or type(after) is not int or after <= expected_count
                or not isinstance(created, list) or len(created) != after - expected_count
                or not reply.get("returned_pairs")
                or (class_name and not reply.get("class_assigned"))):
            return {"ok": False, "reason": "xSignal creation was not fully verified",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_delete_xsignals(
        board_path: str,
        expected_count: int,
        names: list[str] | None = None,
        all: bool = False,
    ) -> dict[str, Any]:
        """Delete named xSignals, or all, with exact-board/count preconditions."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if type(expected_count) is not int or expected_count < 0:
            return {"ok": False, "reason": "expected_count must be non-negative"}
        names = names or []
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() or "\t" in n for n in names):
            return {"ok": False, "reason": "names must be a list of nonempty xSignal names"}
        if not all and not names:
            return {"ok": False, "reason": "give names, or all=true"}
        reply = await get_bridge().send_command_async(
            "pcb.delete_xsignals",
            {"board_path": board_path, "expected_count": str(expected_count),
             "names": "\t".join(names), "all": "true" if all else "false"},
            timeout=120.0,
        )
        deleted = reply.get("deleted") if isinstance(reply, dict) else None
        after = reply.get("count_after") if isinstance(reply, dict) else None
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or reply.get("count_before") != expected_count
                or type(after) is not int or after < 0 or after > expected_count
                or not isinstance(deleted, list) or len(deleted) != expected_count - after
                or (all and after != 0)):
            return {"ok": False, "reason": "xSignal deletion was not fully verified",
                    "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_find_same_package(
        board_path: str,
        designator: str = "",
    ) -> dict[str, Any]:
        """Find placed parts with the same native Altium package geometry.

        With a designator, return other matching parts. Without one, group
        all matching parts, including packages with no package hash. The
        complete read names the exact PcbDoc and reports comparison errors.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        params = {"board_path": board_path}
        if designator.strip():
            params["designator"] = designator.strip()
        reply = await get_bridge().send_command_async(
            "pcb.find_same_package", params, timeout=120.0,
        )
        count = reply.get("parts_examined") if isinstance(reply, dict) else None
        errors = reply.get("compare_errors") if isinstance(reply, dict) else None
        if (not isinstance(reply, dict)
                or not isinstance(reply.get("board_path"), str)
                or reply["board_path"].casefold() != board_path.casefold()
                or type(count) is not int or count < 0
                or type(errors) is not int or errors < 0):
            return {"ok": False, "reason": "package comparison did not identify a complete board read",
                    "native_reply": reply}
        if errors:
            return {"ok": False, "reason": f"{errors} native package comparisons failed",
                    "native_reply": reply}
        if designator.strip():
            matches = reply.get("same_package")
            if not isinstance(matches, list) or len(matches) >= count:
                return {"ok": False, "reason": "package match list is incomplete",
                        "native_reply": reply}
        else:
            groups = reply.get("groups")
            group_count = reply.get("group_count")
            if (not isinstance(groups, list) or type(group_count) is not int
                    or len(groups) != group_count):
                return {"ok": False, "reason": "package groups are incomplete",
                        "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_net_display(
        board_path: str,
        nets: Optional[list[str]] = None,
        show_connections: Optional[bool] = None,
        loop_removal: Optional[bool] = None,
        use_net_color: Optional[bool] = None,
        show_jumpers: Optional[bool] = None,
        color: Optional[str] = None,
        dry_run: bool = True,
        from_project: bool = False,
        project_path: str = "",
    ) -> dict[str, Any]:
        """Read or set PCB net display flags on an exact PcbDoc.

        Without any flags, reads all requested nets. With flags, the default
        dry run returns the current state and proposed settings. Set
        dry_run=false to write; the native handler verifies the old state of
        every net before touching any and returns a per-net readback.
        With from_project, supply the exact PrjPcb path. Each net with a
        project colour receives it in one guarded board write; nets without
        a project colour are left unchanged. Omit nets to use all board nets.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if from_project and color is not None:
            return {"ok": False, "reason": "color and from_project cannot be combined"}
        if from_project and use_net_color is False:
            return {"ok": False, "reason": "from_project requires use_net_color=true or omitted"}
        if from_project and (not Path(project_path).is_absolute()
                             or Path(project_path).suffix.casefold() != ".prjpcb"):
            return {"ok": False, "reason": "from_project requires an absolute PrjPcb path"}
        bridge = get_bridge()
        if nets is None and from_project:
            inventory = await bridge.send_command_async(
                "pcb.get_nets", {"board_path": board_path})
            discovered = inventory.get("nets") if isinstance(inventory, dict) else None
            if (not isinstance(inventory, dict)
                    or not isinstance(inventory.get("board_path"), str)
                    or inventory["board_path"].casefold() != board_path.casefold()
                    or not isinstance(discovered, list)
                    or inventory.get("count") != len(discovered)):
                return {"ok": False, "reason": "board net inventory is incomplete",
                        "native_reply": inventory}
            nets = discovered
        if (not isinstance(nets, list) or not nets
                or any(not isinstance(n, str) or not n.strip() or "\t" in n for n in nets)):
            return {"ok": False, "reason": "nets must be nonempty net names without tabs"}
        names = [n.strip() for n in nets]
        if len({n.casefold() for n in names}) != len(names):
            return {"ok": False, "reason": "nets must be unique"}
        updates = {"show_connections": show_connections,
                   "loop_removal": loop_removal,
                   "use_net_color": use_net_color,
                   "show_jumpers": show_jumpers}
        if any(type(v) is not bool for v in updates.values() if v is not None):
            return {"ok": False, "reason": "display settings must be booleans"}
        wanted_color: int | None = None
        if color is not None:
            if use_net_color is False:
                return {"ok": False, "reason": "color cannot be combined with use_net_color=false"}
            hexpart = color.strip().removeprefix("#")
            if len(hexpart) != 6 or any(c not in "0123456789abcdefABCDEF" for c in hexpart):
                return {"ok": False, "reason": "color must be #RRGGBB"}
            red, green, blue = (int(hexpart[i:i + 2], 16) for i in (0, 2, 4))
            wanted_color = red | (green << 8) | (blue << 16)
        params = {"board_path": board_path, "nets": "\t".join(names)}
        before = await bridge.send_command_async("pcb.net_display", params)
        rows = before.get("nets") if isinstance(before, dict) else None
        bits = before.get("before_bits") if isinstance(before, dict) else None
        flag_fields = ("connections_shown", "loop_removal", "use_net_color", "jumpers_shown")
        if (not isinstance(before, dict)
                or not isinstance(before.get("board_path"), str)
                or before["board_path"].casefold() != board_path.casefold()
                or before.get("count") != len(names)
                or not isinstance(rows, list) or len(rows) != len(names)
                or not isinstance(bits, str) or len(bits) != 4 * len(names)
                or any(not isinstance(row, dict) or row.get("net") != name
                       or any(type(row.get(field)) is not bool for field in flag_fields)
                       or type(row.get("color_bgr")) is not int
                       for row, name in zip(rows, names))):
            return {"ok": False, "reason": "native net display read is incomplete or from another board",
                    "native_reply": before}
        project_colors: list[int] = []
        no_project_color: list[str] = []
        if from_project:
            for name in names:
                source = await bridge.send_command_async("project.net_color", {
                    "project_path": project_path, "net": name,
                })
                value = source.get("color") if isinstance(source, dict) else None
                if (not isinstance(source, dict) or source.get("ok") is False
                        or not isinstance(source.get("project_path"), str)
                        or source["project_path"].casefold() != project_path.casefold()
                        or source.get("net") != name or type(value) is not int
                        or (value != 536870912 and not 0 <= value <= 16777215)):
                    return {"ok": False, "reason": "project net color read is incomplete or from another project",
                            "native_reply": source}
                project_colors.append(value if value != 536870912 else -1)
                if value == 536870912:
                    no_project_color.append(name)
        if not any(v is not None for v in updates.values()) and wanted_color is None and not from_project:
            return before
        if dry_run:
            proposed = {k: v for k, v in updates.items() if v is not None}
            if color is not None:
                proposed["color"] = "#" + hexpart.upper()
            if from_project:
                proposed["project_colors_bgr"] = dict(zip(names, project_colors))
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "before": rows, "would_set": proposed,
                    "no_project_color": no_project_color}
        if from_project and all(value < 0 for value in project_colors) and not any(
                v is not None for v in updates.values()):
            return {"ok": True, "board_path": board_path, "wrote": False,
                    "nets": rows, "no_project_color": no_project_color}
        params["expected_bits"] = bits
        params["expected_colors"] = "\t".join(str(row["color_bgr"]) for row in rows)
        if wanted_color is not None:
            params["colors"] = "\t".join([str(wanted_color)] * len(names))
        elif from_project:
            params["colors"] = "\t".join(str(value) for value in project_colors)
        for key, value in updates.items():
            if value is not None:
                params[key] = "true" if value else "false"
        result = await bridge.send_command_async("pcb.net_display", params)
        after = result.get("nets") if isinstance(result, dict) else None
        expected_fields = {"show_connections": "connections_shown",
                           "loop_removal": "loop_removal",
                           "use_net_color": "use_net_color",
                           "show_jumpers": "jumpers_shown"}
        if (not isinstance(result, dict) or result.get("ok") is False
                or not isinstance(result.get("board_path"), str)
                or result["board_path"].casefold() != board_path.casefold()
                or result.get("before_bits") != bits
                or result.get("count") != len(names)
                or result.get("wrote") is not True
                or not isinstance(after, list) or len(after) != len(names)
                or any(not isinstance(row, dict) or row.get("net") != name
                       or any(row.get(expected_fields[key]) is not value
                              for key, value in updates.items() if value is not None)
                       or (wanted_color is not None and
                           (row.get("color_bgr") != wanted_color or
                            row.get("use_net_color") is not True))
                       or (from_project and project_colors[index] >= 0 and
                           (row.get("color_bgr") != project_colors[index] or
                            row.get("use_net_color") is not True))
                       for index, (row, name) in enumerate(zip(after, names)))):
            return {"ok": False, "reason": "net display write was not fully verified",
                    "native_reply": result}
        if from_project:
            result["project_path"] = project_path
            result["no_project_color"] = no_project_color
        return result

    @mcp.tool()
    async def pcb_set_grids(
        board_path: str,
        snap_x: Optional[float] = None,
        snap_y: Optional[float] = None,
        track: Optional[float] = None,
        via: Optional[float] = None,
        visible: Optional[float] = None,
        visible_big: Optional[float] = None,
        dot_grid: Optional[bool] = None,
        visible_big_factor: Optional[float] = None,
        snap_unit: Optional[str] = None,
        visible_unit: Optional[str] = None,
        visible_big_unit: Optional[str] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read or set PCB grids in mils on one exact PcbDoc.

        Omitted values are unchanged. Component movement grids are returned
        for inspection; Altium 26.11 follows the snap grid for those. A
        change defaults to a dry-run plan. On an explicit write, all old
        values are checked natively before any setter runs, then read back.
        A changed grid remains in memory until an explicit save; on a free
        PcbDoc, app_reload_document with save_before_close=true can save
        that exact document and reopen it for persistence readback.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        requested = {"snap_x": snap_x, "snap_y": snap_y, "track": track,
                     "via": via, "visible": visible, "visible_big": visible_big}
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
               for value in requested.values() if value is not None):
            return {"ok": False, "reason": "grid sizes must be finite positive mils"}
        if dot_grid is not None and type(dot_grid) is not bool:
            return {"ok": False, "reason": "dot_grid must be boolean"}
        if (visible_big_factor is not None and
                (type(visible_big_factor) not in (int, float)
                 or not math.isfinite(visible_big_factor) or visible_big_factor <= 0)):
            return {"ok": False, "reason": "visible_big_factor must be finite and positive"}
        units = {"snap_unit": snap_unit, "visible_unit": visible_unit,
                 "visible_big_unit": visible_big_unit}
        if any(value is not None and value not in ("mm", "mil")
               for value in units.values()):
            return {"ok": False, "reason": "grid units must be mm or mil"}
        bridge = get_bridge()
        before = await bridge.send_command_async(
            "pcb.set_grids", {"board_path": board_path}, timeout=120.0,
        )
        old = before.get("grids") if isinstance(before, dict) else None
        if (not isinstance(before, dict)
                or not isinstance(before.get("board_path"), str)
                or before["board_path"].casefold() != board_path.casefold()
                or not isinstance(old, dict)
                or any(type(old.get(key)) not in (int, float)
                       or not math.isfinite(old[key])
                       for key in (*requested, "component_x", "component_y",
                                   "visible_factor", "visible_big_factor"))
                or type(old.get("dot_grid")) is not bool
                or any(old.get(key) not in ("mm", "mil") for key in units)):
            return {"ok": False, "reason": "native grid read is incomplete or from another board",
                    "native_reply": before}
        changes = {key: value for key, value in requested.items() if value is not None}
        if dot_grid is not None:
            changes["dot_grid"] = dot_grid
        if visible_big_factor is not None:
            changes["visible_big_factor"] = visible_big_factor
        changes.update({key: value for key, value in units.items() if value is not None})
        if not changes:
            return before
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "before": old, "would_set": changes}
        params = {"board_path": board_path}
        for key in requested:
            params["expect_" + key] = repr(float(old[key]))
        params["expect_dot_grid"] = "true" if old["dot_grid"] else "false"
        params["expect_visible_big_factor"] = repr(float(old["visible_big_factor"]))
        for key in units:
            params["expect_" + key] = old[key]
        for key, value in changes.items():
            if key == "dot_grid":
                params[key] = "true" if value else "false"
            elif key in units:
                params[key] = value
            else:
                params[key] = repr(float(value))
        result = await bridge.send_command_async("pcb.set_grids", params, timeout=120.0)
        actual = result.get("grids") if isinstance(result, dict) else None
        if (not isinstance(result, dict)
                or not isinstance(result.get("board_path"), str)
                or result["board_path"].casefold() != board_path.casefold()
                or result.get("wrote") is not True
                or not isinstance(actual, dict)
                or result.get("not_applied") != []
                or any(type(actual.get(key)) not in (int, float)
                       or abs(float(actual[key]) - float(value)) > 0.001
                       for key, value in changes.items()
                       if key != "dot_grid" and key not in units)
                or ("dot_grid" in changes and actual.get("dot_grid") is not dot_grid)
                or any(actual.get(key) != value for key, value in units.items()
                       if value is not None)):
            return {"ok": False, "reason": "board grid write was not fully verified",
                    "native_reply": result}
        result["save_required"] = bool(result.get("changed"))
        return result

    @mcp.tool()
    async def pcb_export_component_model(
        board_path: str, designator: str, out_path: str,
    ) -> dict[str, Any]:
        """Export one placed part as a dialog-free STEP assembly file."""
        return await _pcb_export_component_step(
            board_path, designator, out_path, "part")

    @mcp.tool()
    async def pcb_export_component_3d(
        board_path: str, designator: str, out_path: str,
    ) -> dict[str, Any]:
        """Export one placed part's model through Altium's model API."""
        return await _pcb_export_component_step(
            board_path, designator, out_path, "model")

    @mcp.tool()
    async def pcb_view_options(
        board_path: str,
        show_pad_nets: Optional[bool] = None,
        show_pad_numbers: Optional[bool] = None,
        show_via_nets: Optional[bool] = None,
        show_test_points: Optional[bool] = None,
        single_layer_mode: Optional[bool] = None,
        show_special_strings: Optional[bool] = None,
        highlight_in_net_color: Optional[bool] = None,
        highlight_full: Optional[bool] = None,
        highlight_whole_net: Optional[bool] = None,
        show_component_reference_point: Optional[bool] = None,
        plane_draw_mode: Optional[int] = None,
        pad_types_display: Optional[int] = None,
        from_tos_display: Optional[int] = None,
        layer_name_display: Optional[int] = None,
        draft_track_threshold_mils: Optional[float] = None,
        show_invisible_objects: Optional[bool] = None,
        transparent_layers: Optional[bool] = None,
        clean_redraw: Optional[bool] = None,
        redraw_layer_on_toggle: Optional[bool] = None,
        text_as_box_below: Optional[int] = None,
        pad_net_font: Optional[str] = None,
        pad_net_min_font_size: Optional[int] = None,
        pad_net_font_color: Optional[int] = None,
        pad_net_font_background: Optional[int] = None,
        default_truetype_font: Optional[str] = None,
        board_area_color: Optional[int] = None,
        board_line_color: Optional[int] = None,
        sheet_area_color: Optional[int] = None,
        sheet_line_color: Optional[int] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read or plan a change to Altium's global PCB display preferences."""
        return await _pcb_editor_options(board_path, _PCB_VIEW_OPTIONS, {
            "show_pad_nets": show_pad_nets, "show_pad_numbers": show_pad_numbers,
            "show_via_nets": show_via_nets, "show_test_points": show_test_points,
            "single_layer_mode": single_layer_mode,
            "show_special_strings": show_special_strings,
            "highlight_in_net_color": highlight_in_net_color,
            "highlight_full": highlight_full,
            "highlight_whole_net": highlight_whole_net,
            "show_component_reference_point": show_component_reference_point,
            "plane_draw_mode": plane_draw_mode,
            "pad_types_display": pad_types_display,
            "from_tos_display": from_tos_display,
            "layer_name_display": layer_name_display,
            "draft_track_threshold_mils": draft_track_threshold_mils,
            "show_invisible_objects": show_invisible_objects,
            "transparent_layers": transparent_layers,
            "clean_redraw": clean_redraw,
            "redraw_layer_on_toggle": redraw_layer_on_toggle,
            "text_as_box_below": text_as_box_below,
            "pad_net_font": pad_net_font,
            "pad_net_min_font_size": pad_net_min_font_size,
            "pad_net_font_color": pad_net_font_color,
            "pad_net_font_background": pad_net_font_background,
            "default_truetype_font": default_truetype_font,
            "board_area_color": board_area_color,
            "board_line_color": board_line_color,
            "sheet_area_color": sheet_area_color,
            "sheet_line_color": sheet_line_color,
        }, dry_run)

    @mcp.tool()
    async def pcb_edit_options(
        board_path: str,
        rotation_step: Optional[float] = None,
        protect_locked: Optional[bool] = None,
        select_only_visible: Optional[bool] = None,
        click_clears_selection: Optional[bool] = None,
        double_click_runs_inspector: Optional[bool] = None,
        snap_to_centre: Optional[bool] = None,
        allow_duplicate_designators: Optional[bool] = None,
        auto_pan: Optional[bool] = None,
        drag_mode: Optional[int] = None,
        component_move: Optional[int] = None,
        confirm_delete: Optional[bool] = None,
        confirm_global_edit: Optional[bool] = None,
        confirm_drag: Optional[bool] = None,
        confirm_selection_memory_clear: Optional[bool] = None,
        shift_to_select: Optional[bool] = None,
        global_edit_includes_arcs: Optional[bool] = None,
        pick_nearest_component: Optional[bool] = None,
        defaults_permanent: Optional[bool] = None,
        check_board_on_load: Optional[bool] = None,
        netlist_remove_unconnected_parts: Optional[bool] = None,
        netlist_remove_unconnected_objects: Optional[bool] = None,
        netlist_check_footprints: Optional[bool] = None,
        netlist_check_comments: Optional[bool] = None,
        auto_pan_mode: Optional[int] = None,
        auto_pan_step: Optional[int] = None,
        auto_pan_big_step: Optional[int] = None,
        auto_pan_speed: Optional[int] = None,
        pour_redraw_threshold: Optional[int] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read or plan a change to global PCB editing preferences."""
        return await _pcb_editor_options(board_path, _PCB_EDIT_OPTIONS, {
            "rotation_step": rotation_step, "undo_levels": None,
            "protect_locked": protect_locked,
            "select_only_visible": select_only_visible,
            "click_clears_selection": click_clears_selection,
            "double_click_runs_inspector": double_click_runs_inspector,
            "snap_to_centre": snap_to_centre,
            "allow_duplicate_designators": allow_duplicate_designators,
            "auto_pan": auto_pan, "drag_mode": drag_mode,
            "component_move": component_move,
            "confirm_delete": confirm_delete,
            "confirm_global_edit": confirm_global_edit,
            "confirm_drag": confirm_drag,
            "confirm_selection_memory_clear": confirm_selection_memory_clear,
            "shift_to_select": shift_to_select,
            "global_edit_includes_arcs": global_edit_includes_arcs,
            "pick_nearest_component": pick_nearest_component,
            "defaults_permanent": defaults_permanent,
            "check_board_on_load": check_board_on_load,
            "netlist_remove_unconnected_parts": netlist_remove_unconnected_parts,
            "netlist_remove_unconnected_objects": netlist_remove_unconnected_objects,
            "netlist_check_footprints": netlist_check_footprints,
            "netlist_check_comments": netlist_check_comments,
            "auto_pan_mode": auto_pan_mode,
            "auto_pan_step": auto_pan_step,
            "auto_pan_big_step": auto_pan_big_step,
            "auto_pan_speed": auto_pan_speed,
            "pour_redraw_threshold": pour_redraw_threshold,
        }, dry_run)

    @mcp.tool()
    async def pcb_route_options(
        board_path: str,
        route_mode: Optional[int] = None,
        plow_through_pours: Optional[bool] = None,
        auto_via: Optional[bool] = None,
        shove_depth: Optional[int] = None,
        lock_pre_routes: Optional[bool] = None,
        delete_dead_ends: Optional[bool] = None,
        smart_track_ends: Optional[bool] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read or plan a change to global PCB routing preferences."""
        return await _pcb_editor_options(board_path, _PCB_ROUTE_OPTIONS, {
            "route_mode": route_mode,
            "plow_through_pours": plow_through_pours,
            "auto_via": auto_via, "shove_depth": shove_depth,
            "lock_pre_routes": lock_pre_routes,
            "delete_dead_ends": delete_dead_ends,
            "smart_track_ends": smart_track_ends,
        }, dry_run)

    @mcp.tool()
    async def pcb_get_drill_pairs(board_path: str) -> dict[str, Any]:
        """Read all drill layer pairs, their spans and backdrill/plot flags."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        reply = await get_bridge().send_command_async(
            "pcb.get_drill_pairs", {"board_path": board_path}, timeout=120.0,
        )
        try:
            _drill_pairs_snapshot(reply, board_path)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": reply}
        return reply

    @mcp.tool()
    async def pcb_set_drill_pair(
        board_path: str,
        index: int,
        backdrill: Optional[bool] = None,
        plot_drill_drawing: Optional[bool] = None,
        plot_drill_guide: Optional[bool] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Set one drill pair's flags with exact identity and old-state checks.

        Returns a plan by default. A write requires dry_run=false and reads
        the selected pair back. Saving the PcbDoc remains a separate step.
        """
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if type(index) is not int or index < 0:
            return {"ok": False, "reason": "index must be non-negative"}
        updates = {"backdrill": backdrill, "plot_drill_drawing": plot_drill_drawing,
                   "plot_drill_guide": plot_drill_guide}
        if not any(value is not None for value in updates.values()):
            return {"ok": False, "reason": "give at least one drill pair flag"}
        if any(type(value) is not bool for value in updates.values() if value is not None):
            return {"ok": False, "reason": "drill pair flags must be booleans"}
        bridge = get_bridge()
        snapshot = await bridge.send_command_async(
            "pcb.get_drill_pairs", {"board_path": board_path}, timeout=120.0,
        )
        try:
            pairs = _drill_pairs_snapshot(snapshot, board_path)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": snapshot}
        if index >= len(pairs):
            return {"ok": False, "reason": "drill pair index is out of range"}
        old = pairs[index]
        changes = {key: value for key, value in updates.items() if value is not None}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "before": old, "would_set": changes}
        params = {"board_path": board_path, "index": str(index),
                  "expected_count": str(len(pairs)),
                  "expect_low_layer_id": str(old["low_layer_id"]),
                  "expect_high_layer_id": str(old["high_layer_id"])}
        for key in updates:
            params["expect_" + key] = "true" if old[key] else "false"
        for key, value in changes.items():
            params[key] = "true" if value else "false"
        result = await bridge.send_command_async("pcb.set_drill_pair", params, timeout=120.0)
        pair = result.get("pair") if isinstance(result, dict) else None
        if (not isinstance(result, dict)
                or not isinstance(result.get("board_path"), str)
                or result["board_path"].casefold() != board_path.casefold()
                or result.get("count") != len(pairs)
                or not isinstance(pair, dict) or pair.get("index") != index
                or pair.get("low_layer_id") != old["low_layer_id"]
                or pair.get("high_layer_id") != old["high_layer_id"]
                or any(pair.get(key) is not value for key, value in changes.items())):
            return {"ok": False, "reason": "drill pair write was not fully verified",
                    "native_reply": result}
        result["save_required"] = bool(result.get("changed"))
        return result

    @mcp.tool()
    async def pcb_add_drill_pair(
        board_path: str,
        low_layer: str,
        high_layer: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Add a drill span between two copper layers on one exact PcbDoc."""
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if (not low_layer.strip() or not high_layer.strip()
                or low_layer.strip().casefold() == high_layer.strip().casefold()):
            return {"ok": False, "reason": "give two distinct copper layer names"}
        bridge = get_bridge()
        snapshot = await bridge.send_command_async(
            "pcb.get_drill_pairs", {"board_path": board_path}, timeout=120.0,
        )
        try:
            pairs = _drill_pairs_snapshot(snapshot, board_path)
        except ValueError as exc:
            return {"ok": False, "reason": str(exc), "native_reply": snapshot}
        if dry_run:
            return {"ok": True, "dry_run": True, "board_path": board_path,
                    "count_before": len(pairs), "low_layer": low_layer.strip(),
                    "high_layer": high_layer.strip()}
        result = await bridge.send_command_async(
            "pcb.add_drill_pair",
            {"board_path": board_path, "low_layer": low_layer.strip(),
             "high_layer": high_layer.strip(), "expected_count": str(len(pairs))},
            timeout=120.0,
        )
        after = result.get("pairs") if isinstance(result, dict) else None
        old_spans = {(p["low_layer_id"], p["high_layer_id"]) for p in pairs}
        valid_after = isinstance(after, list) and len(after) == len(pairs) + 1
        if valid_after:
            for i, pair in enumerate(after):
                if (not isinstance(pair, dict) or pair.get("index") != i
                        or type(pair.get("low_layer_id")) is not int
                        or type(pair.get("high_layer_id")) is not int):
                    valid_after = False
                    break
        after_spans = {(p["low_layer_id"], p["high_layer_id"]) for p in after} if valid_after else set()
        if (not isinstance(result, dict)
                or not isinstance(result.get("board_path"), str)
                or result["board_path"].casefold() != board_path.casefold()
                or result.get("count_before") != len(pairs)
                or result.get("count_after") != len(pairs) + 1
                or result.get("returned_count") != len(pairs) + 1
                or result.get("unreadable_count") != 0
                or not valid_after or not old_spans.issubset(after_spans)
                or len(after_spans - old_spans) != 1):
            return {"ok": False, "reason": "new drill pair was not fully verified",
                    "native_reply": result}
        result["save_required"] = True
        return result

    @mcp.tool()
    async def pcb_check_fab_output(
        directory: str,
        board_path: str,
        min_drill_mm: float = 0.0,
        min_feature_mm: float = 0.0,
        board_name: str = "board",
    ) -> dict[str, Any]:
        """Compare Gerber/Excellon output with one focused, exact PCB.

        Requires the absolute path of the focused PcbDoc. Native facts are
        captured in one uncapped pass; incomplete reads cannot pass. The
        optional gerbonara extra is required to parse the exported package.
        Thresholds are millimetres; zero skips each respective threshold.
        """
        from ..fileio.gerber_check import compare_with_board, summarise_package

        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        if not math.isfinite(min_drill_mm) or not math.isfinite(min_feature_mm) or min_drill_mm < 0 or min_feature_mm < 0:
            return {"ok": False, "reason": "fab limits must be finite and non-negative millimetres"}
        summary = summarise_package(directory, board_name=board_name)
        if not summary.get("ok"):
            return {"ok": False, "reason": summary.get("reason"),
                    "files": summary.get("files", [])}
        try:
            facts_reply = await get_bridge().send_command_async(
                "pcb.get_fab_board_facts", {"board_path": board_path}, timeout=120.0,
            )
            board = _fab_board_facts(facts_reply, board_path)
        except (AltiumError, ValueError, TypeError, KeyError, OSError) as exc:
            return {"ok": False, "reason": f"board facts unavailable: {exc}"}
        if min_drill_mm:
            board["min_drill_mm"] = min_drill_mm
        if min_feature_mm:
            board["min_feature_mm"] = min_feature_mm
        result = compare_with_board(summary, board)
        required = {"copper_layers", "outline", "hole_count"}
        missing = sorted(required - set(result.get("checks_run", [])))
        if missing:
            result["ok"] = False
            result["passed"] = False
            result["reason"] = "required fab comparisons did not run: " + ", ".join(missing)
        result["board_path"] = board_path
        result["board_facts"] = facts_reply
        return result


    @mcp.tool()
    async def pcb_paste_options(
        board_path: str,
        paste_same_net: Optional[bool] = None,
        paste_same_class: Optional[bool] = None,
        paste_same_layer: Optional[bool] = None,
        paste_same_designator: Optional[bool] = None,
        repeat_count: Optional[int] = None,
        repeat_increment: Optional[str] = None,
        repeat_circular: Optional[bool] = None,
        repeat_angle: Optional[float] = None,
        repeat_rotate: Optional[bool] = None,
        repeat_x_mils: Optional[float] = None,
        repeat_y_mils: Optional[float] = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Read, or set, what the board editor keeps when pasting, and
        its paste array (Paste Special > Paste Array): how many
        instances, how designators step, and a line or circle of them.

        These are Altium's own preferences and apply to every board. An
        exact active board is required; changes are planned by default.

        Args:
            paste_same_net / paste_same_class / paste_same_layer /
                paste_same_designator: Pasted objects keep their net,
                classes, layer and designators.
            repeat_count: How many instances a paste array places.
            repeat_increment: How each instance's designator steps, e.g.
                "1".
            repeat_circular: Lay the instances on a circle instead of a
                line.
            repeat_angle: Degrees between instances on a circle.
            repeat_rotate: Turn each instance on a circle with it.
            repeat_x_mils / repeat_y_mils: Step between instances in a
                line; may be negative.

        Returns:
            ``options`` (each option by these names), ``changed``,
            ``not_applied``, ``refused`` and ``unknown``.
        """
        refusal = _option_number_refusal({"repeat_count": repeat_count}, {})
        if refusal:
            return refusal
        if repeat_angle is not None and repeat_angle < 0:
            return {"ok": False, "reason": "repeat_angle is 0 or more"}
        reply = await _pcb_editor_options(board_path, _PCB_PASTE_OPTIONS, {
            "paste_same_net": paste_same_net, "paste_same_class": paste_same_class,
            "paste_same_layer": paste_same_layer,
            "paste_same_designator": paste_same_designator,
            "repeat_count": repeat_count, "repeat_increment": repeat_increment,
            "repeat_circular": repeat_circular,
            "repeat_angle": None if repeat_angle is None else float(repeat_angle),
            "repeat_rotate": repeat_rotate,
            # Altium keeps the steps at 10000 to the mil (measured: 1000 mils
            # read 10000000).
            "repeat_x_mils": None if repeat_x_mils is None else float(repeat_x_mils) * 10000,
            "repeat_y_mils": None if repeat_y_mils is None else float(repeat_y_mils) * 10000},
            dry_run)
        for field in ("options", "before", "would_set"):
            options = reply.get(field) if isinstance(reply, dict) else None
            if isinstance(options, dict):
                for key in ("repeat_x_mils", "repeat_y_mils"):
                    if isinstance(options.get(key), (int, float)):
                        options[key] = options[key] / 10000
        return reply


    @mcp.tool()
    async def pcb_gerber_options(
        board_path: str,
        units: Optional[int] = None,
        decimals: Optional[int] = None,
        sort_output: Optional[bool] = None,
        software_arcs: Optional[bool] = None,
        centre_on_film: Optional[bool] = None,
        embed_apertures: Optional[bool] = None,
        panelize: Optional[bool] = None,
        g54: Optional[bool] = None,
        relief_shapes_allowed: Optional[bool] = None,
        flash_pads_only: Optional[bool] = None,
        flash_all_fills: Optional[bool] = None,
        plus_tolerance_mils: Optional[float] = None,
        minus_tolerance_mils: Optional[float] = None,
        film_x_mils: Optional[float] = None,
        film_y_mils: Optional[float] = None,
        border_mils: Optional[float] = None,
        max_aperture_mils: Optional[float] = None,
    ) -> dict[str, Any]:
        """Read, or set, the Gerber setup saved in the exact active board: the
        units and decimals, apertures, flashing, film size and border.

        Call with nothing to read; every option set is read back.
        proj_generate_fab_package writes the files.

        Args:
            board_path: Absolute path of the active PcbDoc.
            units: Altium's number for the Gerber units (read it first).
            decimals: Altium's number for the coordinate format.
            sort_output: Sort the plot output.
            software_arcs: Write arcs as short straight segments.
            centre_on_film: Centre the plots on the film.
            embed_apertures: Write the apertures into each file (RS-274X).
            panelize: Plot the panel's layers.
            g54: Write G54 before each aperture change.
            relief_shapes_allowed: Allow relief apertures.
            flash_pads_only: Flash pad shapes only.
            flash_all_fills: Flash every fill.
            plus_tolerance_mils / minus_tolerance_mils: Aperture match
                tolerances.
            film_x_mils / film_y_mils: Film size.
            border_mils: Border around the plot.
            max_aperture_mils: Largest aperture.

        Returns:
            ``board``, ``options`` (by these names), ``changed``,
            ``not_applied``, ``refused`` and ``unknown``.
        """
        values = {"units": units, "decimals": decimals, "sort_output": sort_output,
                  "software_arcs": software_arcs, "centre_on_film": centre_on_film,
                  "embed_apertures": embed_apertures, "panelize": panelize, "g54": g54,
                  "relief_shapes_allowed": relief_shapes_allowed,
                  "flash_pads_only": flash_pads_only, "flash_all_fills": flash_all_fills,
                  "plus_tolerance_mils": plus_tolerance_mils,
                  "minus_tolerance_mils": minus_tolerance_mils,
                  "film_x_mils": film_x_mils, "film_y_mils": film_y_mils,
                  "border_mils": border_mils, "max_aperture_mils": max_aperture_mils}
        for key, value in values.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if value < 0:
                    return {"ok": False, "reason": f"{key} is 0 or more"}
                if key.endswith("_mils"):
                    values[key] = float(value)
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        return await run_options("pcb.output_options", _GERBER_OPTIONS, values,
                                 {"group": "gerber", "board_path": board_path})


    @mcp.tool()
    async def pcb_print_options(
        board_path: str,
        scale: Optional[float] = None,
        scale_to_fit_page: Optional[bool] = None,
        x_correction: Optional[float] = None,
        y_correction: Optional[float] = None,
        show_holes: Optional[bool] = None,
        printer_fonts: Optional[bool] = None,
        software_arcs: Optional[bool] = None,
        pad_nets: Optional[bool] = None,
        pad_numbers: Optional[bool] = None,
        border_mils: Optional[float] = None,
        composite_type: Optional[int] = None,
        batch_type: Optional[int] = None,
    ) -> dict[str, Any]:
        """Read, or set, the print setup saved in the exact active board:
        scale, fit to page, corrections, holes and pad labels.

        Call with nothing to read; every option set is read back.
        proj_export_pdf prints.

        Args:
            board_path: Absolute path of the active PcbDoc.
            scale: Print scale (1 is full size).
            scale_to_fit_page: Fit the board to the page instead.
            x_correction / y_correction: Scale corrections for the
                printer (1 is none).
            show_holes: Draw the holes.
            printer_fonts: Print text with the printer's fonts.
            software_arcs: Draw arcs as short straight segments.
            pad_nets: Print net names on pads.
            pad_numbers: Print pad numbers.
            border_mils: Border around the print.
            composite_type / batch_type: Altium's numbers for how layers
                are combined and split into pages (read them first).

        Returns:
            ``board``, ``options`` (by these names), ``changed``,
            ``not_applied``, ``refused`` and ``unknown``.
        """
        values = {"scale": scale, "scale_to_fit_page": scale_to_fit_page,
                  "x_correction": x_correction, "y_correction": y_correction,
                  "show_holes": show_holes, "printer_fonts": printer_fonts,
                  "software_arcs": software_arcs, "pad_nets": pad_nets,
                  "pad_numbers": pad_numbers, "border_mils": border_mils,
                  "composite_type": composite_type, "batch_type": batch_type}
        for key in ("scale", "x_correction", "y_correction"):
            if values[key] is not None:
                if values[key] <= 0:
                    return {"ok": False, "reason": f"{key} is more than 0"}
                values[key] = float(values[key])
        for key in ("border_mils", "composite_type", "batch_type"):
            if values[key] is not None and values[key] < 0:
                return {"ok": False, "reason": f"{key} is 0 or more"}
        if border_mils is not None:
            values["border_mils"] = float(border_mils)
        if not Path(board_path).is_absolute() or Path(board_path).suffix.casefold() != ".pcbdoc":
            return {"ok": False, "reason": "board_path must be an absolute PcbDoc path"}
        return await run_options("pcb.output_options", _PRINT_OPTIONS, values,
                                 {"group": "print", "board_path": board_path})
