# SPDX-License-Identifier: Apache-2.0
"""Offline routing-package orchestration and conservative geometry extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eda_agent.render.route_plan_svg import write_route_plan_svg
from eda_agent.route import RouterOptions, RoutingProblem, route_problem


def geometry_obstacle_rects(geometry: dict[str, Any]) -> list[dict[str, float]]:
    """Convert pads/components/regions into review-only obstacle rectangles."""
    result: list[dict[str, float]] = []
    for pad in geometry.get("pads", []):
        x, y = float(pad.get("x", 0)), float(pad.get("y", 0))
        sx = float(pad.get("x_size", pad.get("size", 0))) / 2
        sy = float(pad.get("y_size", pad.get("size", 0))) / 2
        result.append({"x1": x - sx, "y1": y - sy,
                       "x2": x + sx, "y2": y + sy})
    for region in geometry.get("keepouts", []) + geometry.get("regions", []):
        if all(k in region for k in ("x1", "y1", "x2", "y2")):
            result.append({k: float(region[k]) for k in ("x1", "y1", "x2", "y2")})
    return result


def build_route_package(
    geometry: dict[str, Any],
    output_dir: Path,
    rules: dict[str, Any] | None = None,
    nets: list[str] | None = None,
    net_classes: dict[str, str] | None = None,
    grid_pitch_mils: int = 25,
    routing_style: str = "45deg",
    bend_penalty: float = 1.0,
    via_cost: float = 10.0,
    max_expansions: int = 200_000,
) -> dict[str, Any]:
    """Route, validate, render and persist a reviewable offline package."""
    style = routing_style.strip().lower()
    if style not in {"manhattan", "45deg", "octilinear"}:
        raise ValueError("routing_style must be manhattan or 45deg")
    problem = RoutingProblem.from_geometry(
        geometry, rules, net_classes=net_classes,
        grid_pitch_mils=grid_pitch_mils,
    )
    unknown: list[str] = []
    if nets is not None:
        wanted = set(nets)
        unknown = sorted(wanted - set(problem.terminals))
        problem.terminals = {n: t for n, t in problem.terminals.items() if n in wanted}
    route = route_problem(problem, RouterOptions(
        bend_penalty=float(bend_penalty), via_cost=float(via_cost),
        max_expansions=int(max_expansions),
        allow_diagonal=style in {"45deg", "octilinear"},
    ))
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_plan = {
        "tracks": route.get("tracks", []), "vias": route.get("vias", []),
        "obstacles": geometry_obstacle_rects(geometry),
    }
    preview = write_route_plan_svg(preview_plan, output_dir / "routing-plan.svg")
    summary = route.get("summary", {})
    acceptance = {
        "all_requested_nets_known": not unknown,
        "all_routable_nets_routed": int(summary.get("failed", 0)) == 0,
        "validation_ok": bool(route.get("validation", {}).get("ok", False)),
        "requires_drc_after_apply": True,
        "safe_to_apply": (
            not unknown and int(summary.get("failed", 0)) == 0
            and bool(route.get("validation", {}).get("ok", False))
        ),
    }
    package = {
        "ok": True, "routing_style": style, "route": route,
        "preview": preview, "unknown_nets": unknown,
        "acceptance": acceptance,
    }
    manifest = output_dir / "routing-plan.json"
    manifest.write_text(json.dumps(package, indent=2), encoding="utf-8")
    package["manifest_path"] = str(manifest)
    return package
