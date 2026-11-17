# SPDX-License-Identifier: Apache-2.0
"""A board object's *_mm properties read back a value.

X_mm, Width_mm, BoundsLeft_mm and the rest were in the list of known names,
so a query naming them was accepted, and no branch of the reader produced
them: every one came back empty, for every object type. Measured on a live
board on 2026-11-17 (keep-out tracks and arcs, and copper texts).
"""
from pathlib import Path

from tests.pascal_source import load

UNIT = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCBGeneric.pas"


def test_the_reader_answers_a_millimetre_name_from_the_mil_one():
    units = load(UNIT)
    body = units["GetPCBProperty"]
    head = body[:body.index("Try")]
    assert "Copy(PropName, Length(PropName) - 2, 3) = '_mm'" in head
    assert "PCBMilsTextAsMm(GetPCBProperty(Obj, Copy(PropName, 1, Length(PropName) - 3)))" in head
    helper = units["PCBMilsTextAsMm"]
    assert "* 0.0254" in helper and "IsFloatStr(S)" in helper
    assert "Round(" in helper and "/ 100000" in helper      # 10 nm, so 1.9685 mil is 0.05 mm


def test_the_helper_is_declared_before_the_reader():
    text = UNIT.read_text(encoding="utf-8")
    assert text.index("Function PCBMilsTextAsMm(") < text.index("Function GetPCBProperty(")


def test_every_listed_millimetre_name_has_a_mil_name_behind_it():
    """A *_mm name is only as good as the name it converts."""
    text = UNIT.read_text(encoding="utf-8")
    listed = load(UNIT)["KnownPCBPropertyList"]
    import re
    for name in sorted(set(re.findall(r"\b([A-Za-z0-9]+)_mm\b", listed))):
        assert f"PropName = '{name}'" in text, f"{name}_mm is listed but {name} is not a property"
