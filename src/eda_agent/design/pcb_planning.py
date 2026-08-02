# SPDX-License-Identifier: Apache-2.0
"""Deterministic, offline PCB escape and return-path planning helpers."""

from __future__ import annotations

import math
from typing import Any


def plan_bga_fanout(
    pads: list[dict[str, Any]],
    center_x: float,
    center_y: float,
    escape_mils: float,
    track_width_mils: float,
    via_size_mils: float,
    via_hole_mils: float,
    layer: str,
) -> dict[str, Any]:
    """Plan radial dog-bone tracks/vias without touching a board."""
    if not pads:
        raise ValueError("pads must not be empty")
    for label, value in (
        ("escape_mils", escape_mils), ("track_width_mils", track_width_mils),
        ("via_size_mils", via_size_mils), ("via_hole_mils", via_hole_mils),
    ):
        if float(value) <= 0:
            raise ValueError(f"{label} must be positive")
    if via_hole_mils >= via_size_mils:
        raise ValueError("via_hole_mils must be smaller than via_size_mils")

    tracks = []
    vias = []
    for index, pad in enumerate(pads):
        x, y = float(pad["x"]), float(pad["y"])
        dx, dy = x - center_x, y - center_y
        length = math.hypot(dx, dy)
        if length == 0:
            dx, dy, length = (1.0 if index % 2 == 0 else -1.0), 0.0, 1.0
        vx = round(x + escape_mils * dx / length)
        vy = round(y + escape_mils * dy / length)
        net = str(pad.get("net_name", pad.get("net", "")))
        tracks.append({
            "x1": round(x), "y1": round(y), "x2": vx, "y2": vy,
            "width": round(track_width_mils), "layer": layer,
            "net_name": net,
        })
        vias.append({
            "x": vx, "y": vy, "net": net,
            "size": round(via_size_mils), "hole_size": round(via_hole_mils),
        })
    return {"tracks": tracks, "vias": vias, "count": len(pads)}


def plan_return_vias(
    transitions: list[dict[str, Any]],
    reference_net: str,
    offset_mils: float,
    via_size_mils: float,
    via_hole_mils: float,
) -> list[dict[str, Any]]:
    """Place one nearby reference via per signal-layer transition."""
    if not reference_net.strip():
        raise ValueError("reference_net is required")
    if offset_mils <= 0 or via_size_mils <= 0 or via_hole_mils <= 0:
        raise ValueError("offset and via dimensions must be positive")
    if via_hole_mils >= via_size_mils:
        raise ValueError("via_hole_mils must be smaller than via_size_mils")
    result = []
    for index, via in enumerate(transitions):
        angle = math.radians(float(via.get("angle", index * 137.507764)))
        result.append({
            "x": round(float(via["x"]) + offset_mils * math.cos(angle)),
            "y": round(float(via["y"]) + offset_mils * math.sin(angle)),
            "net": reference_net,
            "size": round(via_size_mils),
            "hole_size": round(via_hole_mils),
        })
    return result
