# SPDX-License-Identifier: Apache-2.0
"""Project annotation must preserve fractional-mil position ordering."""

from pathlib import Path

from tests.pascal_source import load


def test_annotation_sorts_native_coordinates_without_whole_mil_rounding():
    source = load(Path(__file__).resolve().parents[1] / "scripts" / "altium"
                  / "Project.pas")
    annotate = source["Proj_Annotate"]
    assert "XCoords.Add(IntToStr(Comp.Location.X))" in annotate
    assert "YCoords.Add(IntToStr(Comp.Location.Y))" in annotate
    assert "CoordToMils(Comp.Location" not in annotate
    assert "StrToIntDef(XCoords[J], 0)" in annotate
    assert "CompareAnnotationOrder(Order, AX, AY, ADoc, BX, BY, BDoc)" in annotate
