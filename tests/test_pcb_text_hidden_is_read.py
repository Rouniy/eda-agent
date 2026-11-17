# SPDX-License-Identifier: Apache-2.0
"""IsHidden of a board text reads back, and so do a component's NameOn / CommentOn.

IsHidden was in the list of known names with no branch in the reader, so a
query for it was accepted and every text answered with an empty value
(measured 2026-11-17 on 869 silkscreen texts of two boards).
"""
from pathlib import Path

from tests.pascal_source import load

UNIT = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCBGeneric.pas"


def test_the_reader_has_a_branch_for_each():
    body = load(UNIT)["GetPCBProperty"]
    assert "Result := BoolToJsonStr(Txt.IsHidden);" in body
    assert "Result := BoolToJsonStr(Comp.NameOn);" in body
    assert "Result := BoolToJsonStr(Comp.CommentOn);" in body


def test_the_names_are_known_and_listed():
    text = UNIT.read_text(encoding="utf-8")
    for name in ("IsHidden", "NameOn", "CommentOn"):
        assert f"(PropName = '{name}')" in text, name
        assert name in load(UNIT)["KnownPCBPropertyList"], name
