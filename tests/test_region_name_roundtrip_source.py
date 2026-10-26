"""Region names can be written and read across both placement paths."""

from pathlib import Path

from tests.pascal_source import load


ROOT = Path(__file__).resolve().parents[1] / "scripts" / "altium"


def test_region_name_in_generic_properties():
    functions = load(ROOT / "PCBGeneric.pas", minimum=20)
    assert "If Oid = eRegionObject Then Begin Rgn := Obj; Result := Rgn.Name; End;" in functions["GetPCBProperty"]
    setter = functions["SetPCBProperty"]
    assert "(PropName = 'Name') And (Oid = eRegionObject)" in setter
    assert "Rgn.Name := Value;" in setter


def test_region_name_is_set_before_board_add_and_echoed():
    functions = load(ROOT / "PCB.pas", minimum=20)
    for function in ("PCB_PlaceRegion", "PCB_PlaceRegionPoly"):
        body = functions[function]
        assert "NameStr := ExtractJsonValue(Params, 'name');" in body
        assert body.index("If NameStr <> '' Then Region.Name := NameStr;") < body.index("Board.AddPCBObject(Region);")
        assert "EscapeJsonString(Region.Name)" in body
