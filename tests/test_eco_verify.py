# SPDX-License-Identifier: Apache-2.0
"""Netlist-vs-pad-nets comparison used to verify an ECO finished its job.

Regression cover for the live failure where Update-PCB returned success
having left one component's pads entirely unbound while its identical
sibling was fully assigned, and nothing in the response said so.
"""

from __future__ import annotations

from eda_agent.core.eco_verify import (
    compare_netlist_to_pads,
    netlist_pin_map,
    pad_net_map,
    verify_eco,
)


def _comp(designator, pins):
    return {"designator": designator,
            "pins": [{"pin_number": p, "net": n} for p, n in pins]}


def _pad(component, name, net):
    return {"component": component, "name": name, "net": net}


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------


def test_netlist_pin_map_keys_are_upper_and_stripped():
    m = netlist_pin_map([_comp(" u1 ", [(" a1 ", "GND")])])
    assert m == {("U1", "A1"): "GND"}


def test_netlist_pin_map_skips_records_without_designator_or_pin():
    m = netlist_pin_map([
        {"designator": "", "pins": [{"pin_number": "1", "net": "N"}]},
        {"designator": "U1", "pins": [{"pin_number": "", "net": "N"}]},
        "not a dict",
    ])
    assert m == {}


def test_pad_net_map_drops_free_pads():
    # A fiducial or tooling hole has no parent component and no schematic
    # counterpart; counting it would invent a false finding.
    m = pad_net_map([_pad("", "1", "GND"), _pad("U1", "1", "GND")])
    assert m == {("U1", "1"): "GND"}


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------


def test_fully_bound_board_is_complete():
    rep = verify_eco(
        [_comp("U14", [("1", "GND"), ("2", "3V3")])],
        [_pad("U14", "1", "GND"), _pad("U14", "2", "3V3")],
    )
    assert rep["complete"] is True
    assert rep["pads_unbound"] == []
    assert rep["schematic_pins_checked"] == 2
    assert rep["pcb_pads_checked"] == 2


def test_the_u15_case_unbound_pads_are_reported():
    # The live shape: U14 complete, U15's pads left with no nets.
    netlist = [
        _comp("U14", [("1", "GND"), ("2", "RX_B_HF")]),
        _comp("U15", [("1", "GND"), ("2", "RX_B_HF"), ("3", "3V3")]),
    ]
    pads = [
        _pad("U14", "1", "GND"), _pad("U14", "2", "RX_B_HF"),
        _pad("U15", "1", ""), _pad("U15", "2", ""), _pad("U15", "3", ""),
    ]
    rep = verify_eco(netlist, pads)
    assert rep["complete"] is False
    assert rep["pads_unbound_count"] == 3
    assert rep["pads_unbound_by_component"] == {"U15": 3}
    assert {r["designator"] for r in rep["pads_unbound"]} == {"U15"}
    assert rep["pads_unbound"][0]["expected_net"] == "GND"


def test_unconnected_schematic_pin_is_not_a_defect():
    # A pin with no net in the schematic SHOULD have an unbound pad.
    rep = verify_eco(
        [_comp("U1", [("1", "GND"), ("2", "")])],
        [_pad("U1", "1", "GND"), _pad("U1", "2", "")],
    )
    assert rep["complete"] is True
    assert rep["pads_unbound"] == []
    assert rep["pins_unconnected_in_schematic"] == 1


def test_net_disagreement_is_reported_separately_from_unbound():
    rep = verify_eco(
        [_comp("U1", [("1", "GND")])],
        [_pad("U1", "1", "VCC")],
    )
    assert rep["complete"] is False
    assert rep["pads_unbound"] == []
    assert rep["pads_mismatched_count"] == 1
    assert rep["pads_mismatched"][0] == {
        "designator": "U1", "pin": "1",
        "schematic_net": "GND", "pcb_net": "VCC"}


def test_case_only_difference_is_not_a_finding():
    # Altium is inconsistent about BGA pad-name case; a case-only mismatch
    # reported as unbound would be a false alarm.
    rep = verify_eco([_comp("U1", [("a1", "GND")])], [_pad("u1", "A1", "GND")])
    assert rep["complete"] is True


def test_pin_without_a_pad_and_pad_without_a_pin():
    rep = verify_eco(
        [_comp("U1", [("1", "GND"), ("9", "SPARE")])],
        [_pad("U1", "1", "GND"), _pad("U1", "5", "STRAY")],
    )
    assert rep["complete"] is False
    assert rep["pins_missing_pad_count"] == 1
    assert rep["pins_missing_pad"][0]["pin"] == "9"
    assert rep["pads_not_in_schematic_count"] == 1
    assert rep["pads_not_in_schematic"][0]["pin"] == "5"


def test_empty_inputs_are_complete_not_crashing():
    rep = verify_eco([], [])
    assert rep["complete"] is True
    assert rep["pads_unbound_count"] == 0


# ---------------------------------------------------------------------------
# Truncation of the report's own lists
# ---------------------------------------------------------------------------


def test_report_lists_announce_their_own_truncation():
    # The counts must stay true even when the lists are capped -- the whole
    # point of this module is to not repeat a silent cap.
    netlist = [_comp("U1", [(str(i), f"N{i}") for i in range(1, 11)])]
    pads = [_pad("U1", str(i), "") for i in range(1, 11)]
    rep = compare_netlist_to_pads(
        netlist_pin_map(netlist), pad_net_map(pads), limit=3)
    assert rep["pads_unbound_count"] == 10
    assert len(rep["pads_unbound"]) == 3
    assert rep["pads_unbound_truncated"] is True


def test_report_not_flagged_truncated_when_it_fits():
    rep = compare_netlist_to_pads(
        {("U1", "1"): "GND"}, {("U1", "1"): ""}, limit=10)
    assert rep["pads_unbound_count"] == 1
    assert rep["pads_unbound_truncated"] is False
