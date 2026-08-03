# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Routing tools: the in-house Manhattan router and DRC-feedback
repair planning. No third-party routing engines.

All computation is pure Python over the board geometry dict the bridge
returns (the ``Gen_GetPcbGeometry`` shape that ``pcb_render_svg`` also
consumes). Every tool accepts its data as arguments so calls are
testable and composable; the bridge is touched ONLY when the explicit
``fetch_geometry`` flag is set. All coordinates are MILS, integers on
the wire.

Intended live sequence (the closed routing loop):

1. Fetch the board: any ``pcb_*`` getter that returns the geometry
   payload, or pass ``fetch_geometry=True`` here.
2. Route offline with ``route_plan`` (grid A*).
3. Apply the resulting ops verbatim: ``tracks`` to
   ``pcb_place_tracks``, each via to ``pcb_place_via``.
4. ``pcb_run_drc``; feed the violation payload to
   ``route_plan_repairs``.
5. Apply the repair actions in order (``rip_and_reroute`` =
   ``pcb_delete_net`` + route that net again; ``nudge`` =
   ``obj_modify`` on the offending primitive; ``widen``/``narrow`` =
   ``pcb_set_track_width``; ``escalate`` = stop and ask the user),
   then re-run DRC and repeat from step 4 until clean.
"""

from __future__ import annotations

from typing import Any, Optional

from ..bridge import get_bridge
from ..route import (
    DEFAULT_GRID_PITCH_MILS,
    GridTooFineError,
    RouterOptions,
    RoutingProblem,
    route_problem,
)
from ..route.repair import plan_drc_repairs


async def _resolve_geometry(geometry: Any,
                            fetch_geometry: bool) -> dict[str, Any] | None:
    """Return the geometry dict, fetching from the live board only when
    ``fetch_geometry`` is set and no geometry was passed in."""
    if geometry is None and fetch_geometry:
        bridge = get_bridge()
        geometry = await bridge.send_command_async(
            "generic.get_pcb_geometry", {}, timeout=120.0,
        )
    return geometry if isinstance(geometry, dict) else None


# Geometry lists that carry a matching entry in the payload's ``counts``
# block. Pascal increments each counter in lockstep with the JSON it
# emits, so a shorter list than the declared count means the payload lost
# entries somewhere between the handler and here.
_COUNTED_LISTS = ("pads", "tracks", "vias", "arcs", "regions", "components")


def _geometry_summary(geom: dict[str, Any],
                      problem: Any) -> dict[str, Any]:
    """Describe the routing input and flag a short payload.

    ``truncated`` is True only on hard evidence: the payload declared N
    of something and delivered fewer than N. It is deliberately not a
    guess about size.
    """
    counts = geom.get("counts")
    mismatches: dict[str, dict[str, int]] = {}
    if isinstance(counts, dict):
        for key in _COUNTED_LISTS:
            declared = counts.get(key)
            if not isinstance(declared, int):
                continue
            got = len(geom.get(key) or [])
            if got < declared:
                mismatches[key] = {"declared": declared, "received": got}
    summary = {
        "truncated": bool(mismatches),
        "count_mismatches": mismatches,
        "declared_counts": counts if isinstance(counts, dict) else {},
        "pads_seen": problem.pads_seen,
        "pads_used_as_terminals": problem.pads_used,
        "pads_dropped_off_routing_layers": sum(
            problem.pads_off_routing_layer.values()),
        "routing_layers": list(problem.layers),
        "nets_with_pads": len(problem.pad_nets_seen),
        "nets_with_terminals": len(problem.terminals),
    }
    # The grid scale sits next to the pad tally on purpose: pitch is the
    # one knob that changes every downstream cost without touching the
    # netlist, so anyone reading "unknown net" can see at a glance
    # whether the netlist or the resolution moved.
    summary.update(problem.grid_info())
    return summary


# Unknown-net reasons that mean the ROUTER lost the net, not that the
# board lacks it. Only "absent_from_geometry" on an otherwise healthy
# payload is a genuine "no such net"; every other code is a mechanism
# failure and must not be reported as a clean result.
_MECHANISM_REASONS = frozenset({
    "geometry_has_no_pads",
    "pads_off_routing_layers",
    "pads_present_but_no_terminal",
})


def _unknown_reason(net: str, problem: Any) -> dict[str, Any]:
    """Why ``net`` produced no terminals, plus whether that is our fault."""
    out = _classify_unknown(net, problem)
    out["mechanism_failure"] = out["reason"] in _MECHANISM_REASONS
    return out


def _classify_unknown(net: str, problem: Any) -> dict[str, Any]:
    """Explain why ``net`` produced no terminals.

    Four genuinely different situations that all used to surface as the
    single word "unknown": the payload carried no pads at all, the net is
    absent from an otherwise healthy payload, its pads exist but sit off
    the routing layers, or it has pads that were dropped for another
    reason. Every branch is stamped with ``mechanism_failure`` from
    :data:`_MECHANISM_REASONS` so the caller never has to re-derive which
    of them is the board's fault.
    """
    if problem.pads_seen == 0:
        # Zero pads with nets requested is never a netlist verdict. Saying
        # "no such net" here is the exact confidently-wrong answer this
        # field exists to prevent -- the pad list never arrived.
        return {
            "reason": "geometry_has_no_pads",
            "detail": (
                f"The geometry payload contained no pads at all, so no net "
                f"could resolve -- including '{net}'. This is a fetch or "
                f"payload failure, not a missing net. Re-fetch the "
                f"geometry and check geometry_summary.declared_counts."
            ),
        }
    dropped = problem.pads_off_routing_layer.get(net, 0)
    if dropped:
        return {
            "reason": "pads_off_routing_layers",
            "pads_dropped": dropped,
            "routing_layers": list(problem.layers),
            "detail": (
                f"{net} has {dropped} pad(s) in the geometry, but none on "
                f"{list(problem.layers)}. Add the layer to rules.layers, "
                f"or route it on a layer that is in the stack."
            ),
        }
    if net in problem.pad_nets_seen:
        return {
            "reason": "pads_present_but_no_terminal",
            "detail": (
                f"{net} appears on a pad in the geometry but produced no "
                f"terminal; the pad record is likely malformed."
            ),
        }
    return {
        "reason": "absent_from_geometry",
        "detail": (
            f"No pad in the geometry payload carries net '{net}'. Either "
            f"the name is wrong, or the payload did not include those "
            f"pads -- check geometry_summary.truncated."
        ),
    }


def register_route_tools(mcp):
    """Register routing tools with the MCP server."""

    @mcp.tool()
    async def route_plan(
        geometry: Optional[dict[str, Any]] = None,
        rules: Optional[dict[str, Any]] = None,
        nets: Optional[list[str]] = None,
        net_classes: Optional[dict[str, str]] = None,
        grid_pitch_mils: int = DEFAULT_GRID_PITCH_MILS,
        bend_penalty: float = 1.0,
        via_cost: float = 10.0,
        max_expansions: int = 200_000,
        routing_style: str = "manhattan",
        fetch_geometry: bool = False,
    ) -> dict[str, Any]:
        """Route the board offline (grid A*) and return placeable ops.

        Pure Python -- no Altium round-trip unless ``fetch_geometry``
        is set. Output ``tracks`` are ``{x1, y1, x2, y2, width, layer,
        net_name}`` (the ``pcb_place_tracks`` item shape) and ``vias``
        are ``{x, y, net, size, hole_size}`` (the ``pcb_place_via``
        params), integer mils, so the result applies verbatim. Per-net
        failure is honest data (status ``failed``), not a tool error.

        Live sequence: fetch geometry -> this tool ->
        ``pcb_place_tracks`` / ``pcb_place_via`` -> ``pcb_run_drc`` ->
        ``route_plan_repairs`` -> apply -> repeat.

        Args:
            geometry: ``Gen_GetPcbGeometry`` payload (bbox / outline /
                pads / tracks / vias, all mils). Pads and copper of
                nets NOT being routed stay in the obstacle map.
            rules: Routing rules, all mils -- ``clearance_mils``,
                ``track_width_mils`` (int, or per-class dict with
                ``"default"``), ``via_size_mils``, ``via_drill_mils``,
                ``layers`` (default TopLayer + BottomLayer). ``None``
                uses defaults.
            nets: Route only these net names; everything else stays a
                static obstacle. Unknown names are reported in
                ``unknown_nets``. ``None`` routes every netted pad
                group.
            net_classes: Net name -> class (``power`` / ``ground`` /
                ``differential`` / ...). Sets routing order and the
                per-class track width. Unlisted nets are ``signal``.
            grid_pitch_mils: Routing grid pitch in mils (default 25).
                Never changes which nets exist -- a pitch too fine for
                the node budget fails with ``reason_code
                "grid_too_fine"`` rather than degrading.
            bend_penalty: A* corner cost in grid-pitch units.
            via_cost: A* layer-change cost in grid-pitch units.
            max_expansions: Per-connection A* budget so a walled-in
                net fails fast. Halving the pitch quadruples the cells a
                flood must chew through, so a failure carrying hint
                ``expansion_budget_exhausted`` means this knob ran out,
                not that the route is impossible.
            routing_style: ``manhattan`` or ``45deg``. The latter permits
                diagonal moves but conservatively prevents corner cutting.
            fetch_geometry: When True and ``geometry`` is None, pull
                the live board over the bridge.

        Returns:
            ``{"ok": True, "summary": {nets_total, routed, failed,
            skipped, attempted, completion, track_count, via_count,
            total_length_mils}, "order": [...], "nets": {net:
            {status, class, width, tracks, vias, ...}}, "tracks":
            [...], "vias": [...], "validation": {...},
            "geometry_summary": {...}}``; with a ``nets`` filter also
            ``requested_nets``, ``unknown_nets``,
            ``unknown_net_reasons``, and ``summary.requested_count`` /
            ``summary.unknown_count``.
            ``{"ok": False, "reason": ...}`` on malformed input.

            ``completion`` with a ``nets`` filter is routed / requested,
            so a run that routes none of them reports 0.0. It previously
            divided by the nets it attempted, which meant filtering every
            requested net away reported 1.0 while routing nothing.

            ``ok`` is False when the geometry payload is short of its own
            declared ``counts`` (``geometry_summary.truncated``), when ANY
            requested net is unknown for a mechanism reason, or when every
            requested net is unknown -- an unknown net can come from a
            truncated input, not just a wrong name, and must not be
            mistaken for "no such net".

            Every ``unknown_net_reasons`` entry carries ``reason`` plus
            ``mechanism_failure``. Only ``absent_from_geometry`` is
            benign; ``geometry_has_no_pads`` (the payload carried no pads
            at all), ``pads_off_routing_layers`` (pads exist but outside
            ``rules.layers``) and ``pads_present_but_no_terminal`` are
            mechanism failures, listed in
            ``unknown_nets_mechanism_failures``.

            A failed net carries ``hint`` + ``detail`` + the measurements
            behind them: ``expansion_budget_exhausted`` (raise
            ``max_expansions``), ``grid_too_coarse`` (with
            ``suggested_grid_pitch_mils`` and the limiting pad pitch),
            ``no_corridor_at_any_pitch`` (real geometry -- no pitch helps),
            ``pad_node_blocked``, or ``no_route``. ``summary.failed_hints``
            tallies them and ``summary.grid`` reports the resolved grid.
        """
        geom = await _resolve_geometry(geometry, fetch_geometry)
        if geom is None:
            return {"ok": False,
                    "reason": "no geometry: pass the geometry dict or set "
                              "fetch_geometry=True"}
        if nets is not None:
            if (not isinstance(nets, list)
                    or not all(isinstance(n, str) and n for n in nets)):
                return {"ok": False,
                        "reason": "nets must be a list of net names"}
        try:
            style = routing_style.strip().lower()
            if style not in {"manhattan", "45deg", "octilinear"}:
                raise ValueError("routing_style must be manhattan or 45deg")
            problem = RoutingProblem.from_geometry(
                geom, rules, net_classes=net_classes,
                grid_pitch_mils=grid_pitch_mils)
            options = RouterOptions(
                bend_penalty=float(bend_penalty),
                via_cost=float(via_cost),
                max_expansions=int(max_expansions),
                allow_diagonal=style in {"45deg", "octilinear"})
        except GridTooFineError as exc:
            # A resource bound must fail loudly and by name, carrying the
            # node count and the limit. Degrading to a coarser grid here
            # would reclassify nets as a side effect of a memory cap --
            # exactly the silent behaviour this reports instead.
            out = {"ok": False, "reason": str(exc)}
            out.update(exc.as_dict())
            if nets is not None:
                # The nets were never looked at. Saying nothing about them
                # is honest; calling them unknown would not be.
                out["requested_nets"] = sorted(set(nets))
                out["unknown_nets"] = []
            return out
        except (ValueError, TypeError) as exc:
            return {"ok": False, "reason": str(exc)}

        unknown: list[str] = []
        if nets is not None:
            wanted = set(nets)
            unknown = sorted(wanted - set(problem.terminals))
            problem.terminals = {
                n: t for n, t in problem.terminals.items() if n in wanted
            }
        result = route_problem(problem, options)

        # Report what the router was actually given. A geometry payload
        # that arrived short -- for any reason: a capped handler, a
        # truncated transport, a partial parse -- otherwise presents as
        # "that net does not exist", which is the same confidently-wrong
        # failure as a silent list cap. ``counts`` is the payload's own
        # self-declared tally, so comparing it against the lists actually
        # received detects a short payload without trusting either side.
        result["geometry_summary"] = _geometry_summary(geom, problem)
        if result["geometry_summary"]["truncated"]:
            result["ok"] = False
            result["reason"] = (
                "geometry payload is short of its own declared counts "
                f"({result['geometry_summary']['count_mismatches']}); the "
                "routing input is incomplete, so unknown_nets and "
                "completion cannot be trusted. Re-fetch the geometry."
            )

        if nets is not None:
            requested = sorted(set(nets))
            result["requested_nets"] = requested
            result["unknown_nets"] = unknown
            # WHY each unknown net is unknown. Without this an unknown net
            # reads as "no such net", and that is exactly the conclusion
            # that was wrong: pads existed but sat on layers outside the
            # routing stack, so they never became terminals.
            result["unknown_net_reasons"] = {
                n: _unknown_reason(n, problem) for n in unknown
            }
            summary = result.get("summary")
            if isinstance(summary, dict):
                # Completion against what the CALLER asked for. The
                # router's own figure divides by the nets it attempted,
                # so filtering every requested net away left it dividing
                # by zero and reporting 1.0 while routing nothing.
                summary["requested_count"] = len(requested)
                summary["unknown_count"] = len(unknown)
                summary["completion"] = (
                    summary.get("routed", 0) / len(requested)
                    if requested else 0.0
                )
            # An unknown net is only benign when the payload was healthy
            # and the name simply is not in it. Every other reason means
            # the router lost a net that exists, and a caller that trusts
            # ``ok`` must not have to read the reasons to find that out.
            # Previously ok flipped only when ALL requested nets vanished,
            # so 6 of 7 dropped for a mechanism failure still reported a
            # clean run.
            mechanism = sorted(
                n for n, r in result["unknown_net_reasons"].items()
                if r.get("mechanism_failure"))
            if mechanism:
                result["unknown_nets_mechanism_failures"] = mechanism
                result["ok"] = False
                result.setdefault("reason", (
                    f"{len(mechanism)} requested net(s) exist in the "
                    f"geometry but were dropped by the routing model "
                    f"({', '.join(mechanism[:5])}"
                    f"{'...' if len(mechanism) > 5 else ''}); see "
                    f"unknown_net_reasons. This is a mechanism failure, "
                    f"not a missing net."))
            elif requested and len(unknown) == len(requested):
                result["ok"] = False
                result.setdefault("reason", (
                    "none of the requested nets had routable pads in the "
                    "geometry; see unknown_net_reasons"))
        return result

    @mcp.tool()
    async def route_plan_repairs(
        violations: Any,
        max_rounds: int = 5,
    ) -> dict[str, Any]:
        """Turn a DRC violation payload into an ordered repair plan.

        Pure Python, stateless. Classifies the ``pcb_run_drc`` payload
        (or a bare violation list) into buckets (net_clearance /
        pad_clearance / unrouted / antenna / width / other), then plans
        actions: ``rip_and_reroute`` (worst clearance offender first),
        ``nudge`` {net, dx, dy, x_mils, y_mils} for a lone
        pad-clearance conflict, ``widen``/``narrow`` {net} for width
        violations, ``escalate`` {reason} when the plan cannot converge
        alone. Deltas/coordinates are integer mils.

        Executor contract: apply the actions in order
        (``rip_and_reroute`` = ``pcb_delete_net`` + route that net
        again via ``route_plan`` with the ``nets`` filter or a DSN
        round-trip; ``nudge`` = ``obj_modify`` on the primitive nearest
        (x_mils, y_mils); ``widen``/``narrow`` =
        ``pcb_set_track_width``; ``escalate`` = stop and surface the
        reason). Then ``pcb_run_drc`` again and re-plan from the fresh
        violations -- the loop's outer iteration bound is the caller's.

        Args:
            violations: ``pcb_run_drc`` result ``{violation_count,
                violations}`` or a bare list of violation dicts.
            max_rounds: Rip budget for the clearance worst-offender
                loop, integer >= 0 (0 = escalate-only for clearance).

        Returns:
            ``{"ok": True, "actions": [...], "rounds_used": n,
            "ripped_nets": [...], "counts": {bucket: n}}``;
            ``{"ok": False, "reason": ...}`` on malformed input.
        """
        return plan_drc_repairs(violations, max_rounds=max_rounds)

    @mcp.tool()
    async def route_build_offline_package(
        geometry: dict[str, Any],
        output_dir: str,
        rules: Optional[dict[str, Any]] = None,
        nets: Optional[list[str]] = None,
        net_classes: Optional[dict[str, str]] = None,
        grid_pitch_mils: int = DEFAULT_GRID_PITCH_MILS,
        routing_style: str = "45deg",
        bend_penalty: float = 1.0,
        via_cost: float = 10.0,
        max_expansions: int = 200_000,
    ) -> dict[str, Any]:
        """Build a route + validation + SVG + JSON package entirely offline."""
        from pathlib import Path
        from ..route.pipeline import build_route_package
        try:
            return build_route_package(
                geometry, Path(output_dir).expanduser().resolve(), rules, nets,
                net_classes, grid_pitch_mils, routing_style, bend_penalty,
                via_cost, max_expansions,
            )
        except (ValueError, TypeError) as exc:
            return {"ok": False, "reason": str(exc)}

    @mcp.tool()
    async def route_audit_plan(
        plan: dict[str, Any],
        reference_vias: Optional[list[dict[str, Any]]] = None,
        high_speed_nets: Optional[list[str]] = None,
        return_via_max_mils: float = 100,
        max_vias_per_net: int = 8,
        diff_pairs: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Offline length/via/return-path/differential-skew route audit."""
        from ..route.audit import audit_route_plan
        try:
            return audit_route_plan(
                plan, reference_vias, high_speed_nets,
                return_via_max_mils, max_vias_per_net, diff_pairs,
            )
        except (ValueError, TypeError, KeyError) as exc:
            return {"ok": False, "reason": str(exc), "findings": []}
