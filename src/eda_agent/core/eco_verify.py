# SPDX-License-Identifier: Apache-2.0
"""Verify that an ECO actually finished binding the board's pad nets.

Altium's Update-PCB ECO can report success and still leave pads unbound:
observed live on a real board where U15 came back with 10 of its 13 pads
carrying no net while its sibling U14 was complete. Nothing in the ECO
response said so, so the omission only surfaced much later as phantom
"unrouted" nets and a manual repair with ``pcb_bind_pad_nets``.

This module turns that silent partial failure into data. It is pure: it
takes the compiled schematic's (designator, pin, net) triples and the
board's pad records and reports which pads the ECO left unbound, which
disagree with the schematic, and which exist on only one side. Keeping it
free of Altium means the comparison itself is unit-testable, and only the
two data fetches remain live-dependent.

Matching rules, and why:

* Pins are matched to pads by ``(designator, pin)`` with both sides
  upper-cased and whitespace-stripped. Altium is inconsistent about pad
  name case for alphanumeric BGA pins ("A1" vs "a1"), and a case-only
  mismatch reported as "unbound" would be a false alarm.
* A schematic pin with an EMPTY net is not a defect -- an unconnected pin
  legitimately has no net -- so those are excluded from the unbound set
  and counted separately.
* Power pins hidden in the symbol still appear in the compiled netlist,
  so they are compared like any other pin.
"""

from __future__ import annotations

from typing import Any, Iterable


def _key(designator: Any, pin: Any) -> tuple[str, str]:
    return (str(designator or "").strip().upper(),
            str(pin or "").strip().upper())


def _clean(value: Any) -> str:
    return str(value or "").strip()


def netlist_pin_map(components: Iterable[dict[str, Any]]
                    ) -> dict[tuple[str, str], str]:
    """(designator, pin) -> net, from ``proj_get_connectivity_many``.

    Accepts the per-component records that handler returns:
    ``{"designator": "U15", "pins": [{"pin_number": "1", "net": "GND"},
    ...]}``. Records without a designator, and pins without a number, are
    skipped -- they cannot be matched to a pad either way.
    """
    out: dict[tuple[str, str], str] = {}
    for comp in components or []:
        if not isinstance(comp, dict):
            continue
        desig = _clean(comp.get("designator"))
        if not desig:
            continue
        for pin in comp.get("pins") or []:
            if not isinstance(pin, dict):
                continue
            number = _clean(pin.get("pin_number") or pin.get("pin"))
            if not number:
                continue
            out[_key(desig, number)] = _clean(pin.get("net"))
    return out


def pad_net_map(pads: Iterable[dict[str, Any]]
                ) -> dict[tuple[str, str], str]:
    """(designator, pad) -> net, from ``pcb_get_pad_properties``.

    Pads with no parent component are free pads (fiducials, tooling,
    stitching) and are dropped: they have no schematic counterpart, so
    including them would manufacture false "extra on the PCB" findings.
    """
    out: dict[tuple[str, str], str] = {}
    for pad in pads or []:
        if not isinstance(pad, dict):
            continue
        comp = _clean(pad.get("component"))
        name = _clean(pad.get("name"))
        if not comp or not name:
            continue
        out[_key(comp, name)] = _clean(pad.get("net"))
    return out


def compare_netlist_to_pads(
    netlist_pins: dict[tuple[str, str], str],
    pad_nets: dict[tuple[str, str], str],
    *,
    limit: int = 200,
) -> dict[str, Any]:
    """Compare compiled schematic pins against board pad nets.

    Args:
        netlist_pins: ``(designator, pin) -> net`` from the schematic.
        pad_nets: ``(designator, pad) -> net`` from the board.
        limit: Cap on each reported list. The counts are always the true
            totals and each list carries its own ``*_truncated`` flag, so
            a capped list can never be mistaken for a complete one.

    Returns:
        Dict with ``complete`` plus:
          - ``pads_unbound``: pin has a net in the schematic, the matching
            pad has none. This is the ECO-left-it-behind case.
          - ``pads_mismatched``: both sides have a net and they differ.
          - ``pins_missing_pad``: schematic pin with no pad on the board.
          - ``pads_not_in_schematic``: component pad with no schematic pin.
          - ``pins_unconnected``: schematic pins with no net at all (not a
            defect; reported so the numbers reconcile).
    """
    unbound: list[dict[str, str]] = []
    mismatched: list[dict[str, str]] = []
    missing_pad: list[dict[str, str]] = []
    unconnected = 0

    for (desig, pin), sch_net in sorted(netlist_pins.items()):
        if not sch_net:
            unconnected += 1
            continue
        if (desig, pin) not in pad_nets:
            missing_pad.append(
                {"designator": desig, "pin": pin, "net": sch_net})
            continue
        pcb_net = pad_nets[(desig, pin)]
        if not pcb_net:
            unbound.append(
                {"designator": desig, "pin": pin, "expected_net": sch_net})
        elif pcb_net != sch_net:
            mismatched.append({
                "designator": desig, "pin": pin,
                "schematic_net": sch_net, "pcb_net": pcb_net,
            })

    extra = [
        {"designator": d, "pin": p, "net": n}
        for (d, p), n in sorted(pad_nets.items())
        if (d, p) not in netlist_pins
    ]

    # Per-component rollup: "U15 has 10 unbound pads" is the actionable
    # sentence, and it is what a pcb_bind_pad_nets repair is organised by.
    by_component: dict[str, int] = {}
    for row in unbound:
        by_component[row["designator"]] = (
            by_component.get(row["designator"], 0) + 1)

    return {
        "complete": not unbound and not mismatched and not missing_pad,
        "schematic_pins_checked": len(netlist_pins),
        "pcb_pads_checked": len(pad_nets),
        "pins_unconnected_in_schematic": unconnected,
        "pads_unbound_count": len(unbound),
        "pads_unbound": unbound[:limit],
        "pads_unbound_truncated": len(unbound) > limit,
        "pads_unbound_by_component": dict(sorted(by_component.items())),
        "pads_mismatched_count": len(mismatched),
        "pads_mismatched": mismatched[:limit],
        "pads_mismatched_truncated": len(mismatched) > limit,
        "pins_missing_pad_count": len(missing_pad),
        "pins_missing_pad": missing_pad[:limit],
        "pins_missing_pad_truncated": len(missing_pad) > limit,
        "pads_not_in_schematic_count": len(extra),
        "pads_not_in_schematic": extra[:limit],
        "pads_not_in_schematic_truncated": len(extra) > limit,
    }


def verify_eco(components: Iterable[dict[str, Any]],
               pads: Iterable[dict[str, Any]],
               *,
               limit: int = 200) -> dict[str, Any]:
    """Convenience wrapper: raw handler payloads in, comparison out."""
    return compare_netlist_to_pads(
        netlist_pin_map(components), pad_net_map(pads), limit=limit)
