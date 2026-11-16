# SPDX-License-Identifier: Apache-2.0
"""Render an offline routing plan and its obstacles as structured SVG."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any


def render_route_plan_svg(
    tracks: list[dict[str, Any]],
    vias: list[dict[str, Any]],
    obstacles: list[dict[str, Any]] | None = None,
    margin: float = 100,
) -> tuple[str, dict[str, Any]]:
    obstacles = obstacles or []
    points: list[tuple[float, float]] = []
    length = 0.0
    nets = set()
    for track in tracks:
        x1, y1 = float(track["x1"]), float(track["y1"])
        x2, y2 = float(track["x2"]), float(track["y2"])
        points.extend(((x1, y1), (x2, y2)))
        length += math.hypot(x2 - x1, y2 - y1)
        nets.add(str(track.get("net_name", track.get("net", ""))))
    for via in vias:
        points.append((float(via["x"]), float(via["y"])))
        nets.add(str(via.get("net", "")))
    for item in obstacles:
        points.extend(((float(item["x1"]), float(item["y1"])),
                       (float(item["x2"]), float(item["y2"]))))
    if not points:
        raise ValueError("route plan contains no geometry")
    min_x = min(p[0] for p in points) - margin
    min_y = min(p[1] for p in points) - margin
    max_x = max(p[0] for p in points) + margin
    max_y = max(p[1] for p in points) + margin
    width, height = max_x - min_x, max_y - min_y
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{min_x:g} {min_y:g} {width:g} {height:g}">',
        '<rect x="-100000" y="-100000" width="200000" height="200000" fill="#111827"/>',
        '<g class="obstacles" fill="#ef4444" fill-opacity=".28" stroke="#f87171">',
    ]
    for item in obstacles:
        x1, x2 = sorted((float(item["x1"]), float(item["x2"])))
        y1, y2 = sorted((float(item["y1"]), float(item["y2"])))
        out.append(f'<rect x="{x1:g}" y="{y1:g}" width="{x2-x1:g}" height="{y2-y1:g}"/>')
    out.append('</g><g class="planned-tracks" fill="none" stroke="#22d3ee">')
    for track in tracks:
        net = html.escape(str(track.get("net_name", track.get("net", ""))), quote=True)
        out.append(
            f'<line data-net="{net}" data-layer="{html.escape(str(track.get("layer", "")), quote=True)}" '
            f'x1="{float(track["x1"]):g}" y1="{float(track["y1"]):g}" '
            f'x2="{float(track["x2"]):g}" y2="{float(track["y2"]):g}" '
            f'stroke-width="{float(track.get("width", 10)):g}"/>'
        )
    out.append('</g><g class="planned-vias" fill="#fbbf24" stroke="#fde68a">')
    for via in vias:
        net = html.escape(str(via.get("net", "")), quote=True)
        radius = float(via.get("size", 30)) / 2
        out.append(f'<circle data-net="{net}" cx="{float(via["x"]):g}" cy="{float(via["y"]):g}" r="{radius:g}"/>')
    out.append('</g></svg>')
    metrics = {
        "track_count": len(tracks), "via_count": len(vias),
        "obstacle_count": len(obstacles), "net_count": len(nets - {""}),
        "total_track_length_mils": round(length, 3),
        "bbox": {"x1": min_x, "y1": min_y, "x2": max_x, "y2": max_y},
    }
    return "".join(out), metrics


def write_route_plan_svg(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    svg, metrics = render_route_plan_svg(
        list(plan.get("tracks", [])), list(plan.get("vias", [])),
        list(plan.get("obstacles", [])),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    return {"ok": True, "svg_path": str(output), "metrics": metrics}
