# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Regression tests for exact .SchDoc coordinates (the ``*_Frac`` fields).

Altium stores every schematic coordinate as a PAIR: an integer field in
10-mil units plus an optional ``<name>_Frac`` holding the fraction over a
denominator of 100000. The reader used to drop ``_Frac``, truncating every
coordinate toward the integer unit below. On an off-grid sheet that made real
wires miss real pin ends -- and because ``Location`` and ``PinLength``
truncated independently, the error accumulated to ~20 mil, enough to
fabricate breaks in the reconstructed netlist that do not exist on the sheet.

These tests pin down the exact behaviour and, just as importantly, pin down
that an on-grid sheet (no ``_Frac``, or ``_Frac=0``) is bit-for-bit
unaffected: plain ``int``, same values as before.

No binary fixture needed -- the readers are driven with synthetic
FileHeader records, so this runs everywhere.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from eda_agent.fileio import altium_sch
from eda_agent.fileio.altium_sch import (
    _read_coord,
    _read_coord_units,
    read_schematic_junctions,
    read_schematic_net_label_locations,
    read_schematic_pins,
    read_schematic_power_ports,
    read_schematic_wires,
)


@pytest.fixture
def sheet(monkeypatch):
    """Feed synthetic FileHeader records to every reader in the module."""
    def install(records):
        monkeypatch.setattr(altium_sch, "read_schdoc_records",
                            lambda path: records)
    return install


# --- the shared coordinate parser -----------------------------------------

def test_field_absent_is_none():
    assert _read_coord({}, "Location.X") is None
    assert _read_coord_units({}, "Location.X") is None
    # A present-but-unparsable integer field is still None (unchanged).
    assert _read_coord({"Location.X": "n/a"}, "Location.X") is None


def test_no_frac_field_gives_an_unchanged_int():
    """No ``_Frac`` at all -- byte-identical to the pre-fix reader."""
    rec = {"Location.X": "840"}
    value = _read_coord(rec, "Location.X")
    assert value == 840
    assert type(value) is int
    assert _read_coord_units(rec, "Location.X") == 84_000_000


def test_zero_frac_gives_an_unchanged_int():
    """``_FRAC=0`` must not turn an on-grid coordinate into a Decimal."""
    value = _read_coord({"Location.X": "840", "Location.X_Frac": "0"},
                        "Location.X")
    assert value == 840
    assert type(value) is int


def test_frac_is_kept():
    """840 + 30000/100000 == 840.3 units == 8403 mil."""
    rec = {"Location.X": "840", "Location.X_Frac": "30000"}
    value = _read_coord(rec, "Location.X")
    assert value == Decimal("840.3")
    assert isinstance(value, Decimal)      # exact -- never a float
    assert value * 10 == Decimal("8403")   # mils
    assert _read_coord_units(rec, "Location.X") == 84_030_000


def test_frac_suffix_spelling_is_case_tolerant():
    assert _read_coord({"X1": "840", "X1_FRAC": "30000"}, "X1") \
        == Decimal("840.3")


def test_unparsable_frac_counts_as_zero():
    value = _read_coord({"Location.X": "840", "Location.X_Frac": ""},
                        "Location.X")
    assert value == 840 and type(value) is int


def test_negative_coordinate_frac_is_additive_not_sign_magnitude():
    """The non-obvious one: the fraction is ADDED, never sign-magnitude.

    Altium writes a negative off-grid coordinate as the integer unit BELOW
    it plus a positive fraction, so -841 with ``_Frac=70000`` is -840.3 --
    NOT -841.7. Getting this backwards would move such points by up to two
    whole units in the wrong direction.
    """
    rec = {"Location.Y": "-841", "Location.Y_Frac": "70000"}
    assert _read_coord_units(rec, "Location.Y") == -84_030_000
    assert _read_coord(rec, "Location.Y") == Decimal("-840.3")

    # ... so a fraction on a negative coordinate moves it toward zero.
    assert _read_coord({"Location.Y": "-840", "Location.Y_Frac": "30000"},
                       "Location.Y") == Decimal("-839.7")

    # A whole negative coordinate still comes back as a plain int.
    whole = _read_coord({"Location.Y": "-840", "Location.Y_Frac": "0"},
                        "Location.Y")
    assert whole == -840 and type(whole) is int


def test_decimal_and_int_coordinates_share_one_key_space():
    """Mixed int / Decimal must not split the solver's coordinate keys."""
    whole = _read_coord({"X1": "840", "X1_Frac": "0"}, "X1")
    same = _read_coord({"X1": "839", "X1_Frac": "100000"}, "X1")
    assert whole == same
    assert hash((whole, 0)) == hash((same, 0))
    assert len({(whole, 0), (same, 0)}) == 1


# --- the readers -----------------------------------------------------------

ON_GRID = [
    {"RECORD": "2", "OwnerIndex": "3", "Designator": "1", "Name": "VIN",
     "Location.X": "100", "Location.Y": "200", "PinLength": "10",
     "PinConglomerate": "2"},
    {"RECORD": "27", "LocationCount": "2",
     "X1": "90", "Y1": "200", "X2": "150", "Y2": "200"},
    {"RECORD": "25", "Text": "VBUS", "Location.X": "120", "Location.Y": "200"},
    {"RECORD": "17", "Text": "GND", "Location.X": "150", "Location.Y": "200",
     "Orientation": "1"},
    {"RECORD": "29", "Location.X": "120", "Location.Y": "200"},
]

OFF_GRID = [
    {"RECORD": "2", "OwnerIndex": "3", "Designator": "1", "Name": "VIN",
     "Location.X": "100", "Location.X_Frac": "30000", "Location.Y": "200",
     "PinLength": "10", "PinLength_Frac": "70000", "PinConglomerate": "0"},
    {"RECORD": "27", "LocationCount": "2",
     "X1": "111", "Y1": "200", "Y1_Frac": "50000",
     "X2": "150", "Y2": "200", "Y2_Frac": "50000"},
    {"RECORD": "25", "Text": "VBUS", "Location.X": "120",
     "Location.X_Frac": "25000", "Location.Y": "200"},
    {"RECORD": "17", "Text": "GND", "Location.X": "150", "Location.Y": "200",
     "Location.Y_Frac": "50000", "Orientation": "1"},
    {"RECORD": "29", "Location.X": "120", "Location.X_Frac": "25000",
     "Location.Y": "200"},
]


def test_readers_are_unchanged_on_an_on_grid_sheet(sheet):
    """Every reader returns plain ints when no ``_Frac`` is present."""
    sheet(ON_GRID)

    pin = read_schematic_pins("x")[0]
    assert (pin["x"], pin["y"], pin["length"]) == (100, 200, 10)
    assert pin["orientation"] == 180 and pin["owner_index"] == 3
    assert all(type(pin[k]) is int for k in ("x", "y", "length"))

    wire = read_schematic_wires("x")[0]
    assert wire == {"x1": 90, "y1": 200, "x2": 150, "y2": 200}
    assert all(type(v) is int for v in wire.values())

    label = read_schematic_net_label_locations("x")[0]
    port = read_schematic_power_ports("x")[0]
    junction = read_schematic_junctions("x")[0]
    assert (label["x"], label["y"]) == (120, 200)
    assert (port["x"], port["y"], port["orientation"]) == (150, 200, 1)
    assert junction == {"x": 120, "y": 200}
    assert all(type(v) is int
               for v in (label["x"], label["y"], port["x"], port["y"],
                         junction["x"], junction["y"]))


def test_readers_keep_fractions_on_an_off_grid_sheet(sheet):
    sheet(OFF_GRID)

    pin = read_schematic_pins("x")[0]
    assert pin["x"] == Decimal("100.3")
    assert pin["y"] == 200            # no _Frac on this one -> still int
    assert pin["length"] == Decimal("10.7")

    wire = read_schematic_wires("x")[0]
    assert (wire["y1"], wire["y2"]) == (Decimal("200.5"), Decimal("200.5"))
    assert (wire["x1"], wire["x2"]) == (111, 150)

    assert read_schematic_net_label_locations("x")[0]["x"] == Decimal("120.25")
    assert read_schematic_power_ports("x")[0]["y"] == Decimal("200.5")
    assert read_schematic_junctions("x")[0]["x"] == Decimal("120.25")


def test_off_grid_pin_end_lands_on_its_wire(sheet):
    """End-to-end: exactly the failure the truncating reader produced.

    The pin anchor (100.3) and its length (10.7) each truncate DOWN, so the
    old reader put the electrical end at 110 instead of 111 -- a whole unit
    short of the wire, splitting one real net into two phantom ones. That is
    the accumulation the fix removes: neither error alone reached a unit.
    """
    from eda_agent.fileio.netlist_solver import pin_electrical_end, solve_nets

    sheet([
        # Anchor 100.3, length 10.7, pointing right -> electrical end 111.0
        {"RECORD": "2", "OwnerIndex": "0", "Designator": "1",
         "Location.X": "100", "Location.X_Frac": "30000",
         "Location.Y": "200", "PinLength": "10", "PinLength_Frac": "70000",
         "PinConglomerate": "0"},
        # Anchor 160.6, length 9.4, pointing left -> electrical end 151.2
        {"RECORD": "2", "OwnerIndex": "1", "Designator": "2",
         "Location.X": "160", "Location.X_Frac": "60000",
         "Location.Y": "200", "PinLength": "9", "PinLength_Frac": "40000",
         "PinConglomerate": "2"},
        {"RECORD": "27", "LocationCount": "2",
         "X1": "111", "Y1": "200", "X2": "151", "Y2": "200",
         "X2_Frac": "20000"},
        {"RECORD": "17", "Text": "VTEST", "Location.X": "111",
         "Location.Y": "200"},
    ])

    pins = []
    for p in read_schematic_pins("x"):
        end = pin_electrical_end(p["x"], p["y"], p["length"], p["orientation"])
        pins.append({"component": f"U{p['owner_index']}",
                     "pin": p["designator"], "x": end[0], "y": end[1]})
    assert [(p["x"], p["y"]) for p in pins] == [
        (Decimal("111.0"), 200), (Decimal("151.2"), 200)]

    solved = solve_nets(pins, read_schematic_wires("x"),
                        read_schematic_power_ports("x"), [], [])
    assert set(solved["pin_nets"].values()) == {"VTEST"}
    assert len(solved["nets"]["VTEST"]) == 2
