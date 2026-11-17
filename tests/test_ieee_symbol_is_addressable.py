# SPDX-License-Identifier: Apache-2.0
"""A free IEEE symbol on a sheet can be listed and read.

A sheet of 46 IEEE symbols (Place > Drawing Tools > IEEE Symbols) rendered
in Altium, and ``obj_query`` answered "Unknown object type: eIEEESymbol":
the objects could be seen and not counted. Altium's constant for them is
``eSymbol`` and the interface ``ISch_Symbol``.

Measured on AD 26.11 against that sheet: 46 objects, and ``Symbol``,
``ScaleFactor`` (mils), ``Orientation``, ``LineWidth`` and ``Location`` equal
to the file's. ``IsMirrored`` read False for the one mirrored symbol, so it is
reported unreadable instead.
"""
from __future__ import annotations

import re
from pathlib import Path

from eda_agent import sch_members
from tests.pascal_source import load

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "altium"
GENERIC = SCRIPTS / "Generic.pas"


def _units():
    return load(GENERIC)


def test_the_type_resolves_under_both_spellings():
    body = _units()["ObjectTypeFromString"]
    assert re.search(r"\(N = 'ieeesymbol'\) Or \(N = 'symbol'\) Then Result := eSymbol", body), (
        "eIEEESymbol and Altium's own eSymbol no longer resolve")
    assert "eSymbol (a free IEEE symbol" in _units()["SchObjectTypeNames"], (
        "the refusal for an unknown type does not offer the IEEE symbol")
    assert "'ieee_symbol'" in _units()["SchTypeName"]


def test_its_own_members_are_read_through_its_interface():
    """Symbol and ScaleFactor exist on ISch_Symbol only.

    Asked of any other object they are an undeclared identifier, which
    stops the script, so the reader checks the type before the cast.
    """
    body = _units()["ReadIeeeSymbolProp"]
    assert body.index("If Obj.ObjectId <> eSymbol Then Exit;") < body.index("S := Obj;")
    for member in ("S.Symbol", "S.ScaleFactor", "S.Orientation"):
        assert member in body, f"{member} is no longer read"
    # Measured: a mirrored symbol read False. No value is given for it.
    assert "S.IsMirrored" not in body
    assert "NotePropertyDiag('unreadable', PropName)" in body
    assert "CoordToMilsF(S.ScaleFactor)" in body, "ScaleFactor is a length and is given in mils"
    gated = _units()["GetSchPropertyGated"]
    arm = gated[gated.index("(Obj.ObjectId = eSymbol) And"):]
    arm = arm[:arm.index("ReadIeeeSymbolProp(Obj, PropName)")]
    for name in ("Symbol", "ScaleFactor", "Orientation", "IsMirrored"):
        assert f"(PropName = '{name}')" in arm, f"{name} is not routed to the IEEE reader"
    assert (gated.index("ReadIeeeSymbolProp(Obj, PropName)")
            < gated.index("If SchObjectHasOrientation(Obj) Then")), (
        "the general Orientation reader answers first and calls it unreadable")


def test_the_reader_is_declared_before_its_caller():
    text = GENERIC.read_text(encoding="latin-1")
    assert (text.index("Function ReadIeeeSymbolProp(")
            < text.index("Function GetSchPropertyGated("))


def test_line_width_is_allowed_for_it():
    row = next(r for r in sch_members.ROWS if "LineWidth" in r.members)
    assert "eSymbol" in row.types and "ISch_Symbol" in row.sdk


def test_the_constant_is_known_to_the_lint():
    names = (SCRIPTS / "lint_external_names.txt").read_text(encoding="utf-8").splitlines()
    assert "eSymbol" in names
