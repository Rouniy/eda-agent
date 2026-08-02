# SPDX-License-Identifier: Apache-2.0
"""Offline route-plan quality and return-path acceptance checks."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def audit_route_plan(
    plan: dict[str, Any],
    reference_vias: list[dict[str, Any]] | None = None,
    high_speed_nets: list[str] | None = None,
    return_via_max_mils: float = 100,
    max_vias_per_net: int = 8,
    diff_pairs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tracks = list(plan.get("tracks", []))
    vias = list(plan.get("vias", []))
    refs = reference_vias or []
    high_speed = set(high_speed_nets or [])
    findings: list[dict[str, Any]] = []
    lengths: dict[str, float] = defaultdict(float)
    via_counts: dict[str, int] = defaultdict(int)
    for track in tracks:
        net = str(track.get("net_name", track.get("net", "")))
        lengths[net] += math.hypot(float(track["x2"]) - float(track["x1"]),
                                   float(track["y2"]) - float(track["y1"]))
    for via in vias:
        net = str(via.get("net", ""))
        via_counts[net] += 1
        if net in high_speed:
            nearest = min((math.hypot(float(via["x"]) - float(rv["x"]),
                                      float(via["y"]) - float(rv["y"]))
                           for rv in refs), default=math.inf)
            if nearest > return_via_max_mils:
                findings.append({
                    "code": "missing_nearby_return_via", "severity": "error",
                    "net": net, "x": via["x"], "y": via["y"],
                    "nearest_mils": None if math.isinf(nearest) else round(nearest, 3),
                    "limit_mils": return_via_max_mils,
                })
    for net, count in sorted(via_counts.items()):
        if count > max_vias_per_net:
            findings.append({"code": "excessive_vias", "severity": "warning",
                             "net": net, "count": count,
                             "limit": max_vias_per_net})
    pair_results = []
    for pair in diff_pairs or []:
        positive, negative = str(pair["positive"]), str(pair["negative"])
        tolerance = float(pair.get("max_skew_mils", 10))
        skew = abs(lengths.get(positive, 0) - lengths.get(negative, 0))
        item = {"positive": positive, "negative": negative,
                "skew_mils": round(skew, 3), "max_skew_mils": tolerance,
                "ok": skew <= tolerance}
        pair_results.append(item)
        if not item["ok"]:
            findings.append({"code": "diff_pair_skew", "severity": "error", **item})
    errors = sum(f["severity"] == "error" for f in findings)
    warnings = sum(f["severity"] == "warning" for f in findings)
    return {
        "ok": errors == 0, "errors": errors, "warnings": warnings,
        "findings": findings, "lengths_mils": {k: round(v, 3) for k, v in lengths.items()},
        "via_counts": dict(via_counts), "diff_pairs": pair_results,
        "requires_live_drc": True,
    }
