# SPDX-License-Identifier: Apache-2.0
"""Pure-Python placement acceptance checks with actionable findings."""

from __future__ import annotations

import math
from typing import Any


def audit_placement(
    components: list[dict[str, Any]],
    board: dict[str, float],
    decoupling_max_mils: float = 200,
    termination_max_mils: float = 300,
    connector_edge_max_mils: float = 150,
    courtyard_mils: float = 10,
) -> dict[str, Any]:
    """Audit legality and role-aware proximity using explicit component data.

    Optional component keys: ``role`` (decoupling/termination/connector),
    ``serves`` (anchor designator), ``fixed``, width/height, x/y.
    """
    required = {"x1", "y1", "x2", "y2"}
    if not required <= board.keys():
        raise ValueError("board requires x1, y1, x2, y2")
    by_ref = {str(c.get("designator", c.get("ref", ""))): c for c in components}
    findings: list[dict[str, Any]] = []

    def ref(c):
        return str(c.get("designator", c.get("ref", "")))

    def bounds(c):
        hw = float(c.get("width", c.get("width_mils", 0))) / 2 + courtyard_mils
        hh = float(c.get("height", c.get("height_mils", 0))) / 2 + courtyard_mils
        x, y = float(c["x"]), float(c["y"])
        return x - hw, y - hh, x + hw, y + hh

    for c in components:
        x1, y1, x2, y2 = bounds(c)
        if x1 < board["x1"] or y1 < board["y1"] or x2 > board["x2"] or y2 > board["y2"]:
            findings.append({"code": "outside_board", "severity": "error", "component": ref(c)})
    for i, a in enumerate(components):
        ax1, ay1, ax2, ay2 = bounds(a)
        for b in components[i + 1:]:
            bx1, by1, bx2, by2 = bounds(b)
            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                findings.append({
                    "code": "courtyard_overlap", "severity": "error",
                    "components": [ref(a), ref(b)],
                })
    limits = {"decoupling": decoupling_max_mils, "termination": termination_max_mils}
    for c in components:
        role = str(c.get("role", "")).strip().lower()
        if role in limits and c.get("serves"):
            anchor = by_ref.get(str(c["serves"]))
            if anchor is None:
                findings.append({"code": "missing_anchor", "severity": "error",
                                 "component": ref(c), "anchor": str(c["serves"])})
            else:
                distance = math.hypot(float(c["x"]) - float(anchor["x"]),
                                      float(c["y"]) - float(anchor["y"]))
                if distance > limits[role]:
                    findings.append({
                        "code": f"{role}_too_far", "severity": "warning",
                        "component": ref(c), "anchor": ref(anchor),
                        "distance_mils": round(distance, 3),
                        "limit_mils": limits[role],
                    })
        if role == "connector":
            x, y = float(c["x"]), float(c["y"])
            edge_distance = min(x - board["x1"], board["x2"] - x,
                                y - board["y1"], board["y2"] - y)
            if edge_distance > connector_edge_max_mils:
                findings.append({
                    "code": "connector_far_from_edge", "severity": "warning",
                    "component": ref(c), "distance_mils": round(edge_distance, 3),
                    "limit_mils": connector_edge_max_mils,
                })
    errors = sum(f["severity"] == "error" for f in findings)
    warnings = sum(f["severity"] == "warning" for f in findings)
    return {
        "ok": errors == 0, "component_count": len(components),
        "errors": errors, "warnings": warnings, "findings": findings,
        "score": max(0, 100 - errors * 25 - warnings * 5),
    }
