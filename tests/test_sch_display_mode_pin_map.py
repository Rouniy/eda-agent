"""Placed symbol mode and current footprint pin-map integration."""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from tests.test_sch_properties_match_their_interface import _routine, _source


def test_component_only_properties_and_readback():
    source = _source()
    preflight = _routine(source, "UnsupportedSchProperty")
    getter = _routine(source, "GetSchProperty")
    setter = _routine(source, "SetSchProperty")
    assert "(Obj.ObjectId <> eSchComponent)" in preflight
    assert "(PropName = 'DisplayMode')" in preflight
    assert "(PropName = 'FootprintPinMap')" in preflight
    assert "Or (PropName = 'DisplayModeCount')" in preflight
    assert "If Obj.ObjectId = eSchComponent Then" in getter
    assert "Result := ReadFootprintPinMap(Comp)" in getter
    assert "(NewMode < 0) Or (NewMode >= ModeCount)" in setter
    assert "WroteOK := (Comp.DisplayMode = NewMode)" in setter
    assert "WroteOK := WriteFootprintPinMap(Comp, Value)" in setter
    assert "Impl.MapAsString := Old" in _routine(source, "WriteFootprintPinMap")
    assert source.index("Function CurrentFootprintImpl(") < source.index("Function GetSchProperty(")


def test_placement_chooses_its_own_model_and_reports_failures():
    source = _source()
    chooser = _routine(source, "ChooseFootprintModel")
    walk_end = chooser.index("Comp.SchIterator_Destroy(ImplIter)")
    assert "IsCurrent :=" not in chooser[:walk_end]
    clear = chooser.index("Impl.IsCurrent := False", walk_end)
    select = chooser.index("Impl.IsCurrent := True", walk_end)
    verify = chooser.index("Held := True", walk_end)
    assert clear < select < verify
    assert "UpperCase(Trim(MN)) = UpperCase(Trim(Name))" in chooser
    assert "Result := -1" in chooser
    assert ".Free" not in chooser
    for name in ("Gen_PlaceSchComponentFromLibrary",
                 "Gen_PlaceSchComponentsFromLibrary"):
        body = _routine(source, name)
        assert "ChooseFootprintModel(Comp," in body
        assert "FOOTPRINT_NOT_ON_SYMBOL" in body
        assert "FOOTPRINT_NOT_APPLIED" in body
        assert "SchRegisterObject(SchDoc, Comp)" in body
    batch = _routine(source, "Gen_PlaceSchComponentsFromLibrary")
    assert '"footprints_chosen":' in batch
    assert '"footprint_issues":[' in batch


def test_footprint_stamp_selects_existing_model_before_renaming():
    source = _source()
    helper = _routine(source, "SetPlacedFootprintName")
    choose = helper.index("ChooseFootprintModel(Comp, NewName, Before, After)")
    rename = helper.index("Target.ModelName := NewName")
    assert choose < helper.index("If Choice <> 0 Then") < rename
    assert "Result := (Choice = 1)" in helper
    assert "Target.ModelName := NewName" in helper
    for name in ("Gen_SetSchComponentParameters",
                 "Gen_SetSchComponentsParameters"):
        body = _routine(source, name)
        assert "SetPlacedFootprintName(" in body
        assert "Impl.ModelName := Val" not in body
    batch = _routine(source, "Gen_SetSchComponentsParameters")
    assert "SHEET_NOT_LOADED" in batch
    assert '"footprints_applied":' in batch
    assert '"footprints_not_applied":' in batch


def test_pin_map_parser_and_merge_check_run_in_pascal(tmp_path):
    fpc = shutil.which("fpc")
    if not fpc:
        pytest.skip("Free Pascal Compiler is not installed")
    helpers = "\n".join(_routine(_source(), name)
                        for name in ("CanonicalPinMap", "PinMapHolds"))
    helpers = helpers.replace(", -1)", ", [rfReplaceAll])")
    program = """program pinmaps;
{$mode delphi}
uses SysUtils;
@@HELPERS@@
procedure Check(Got, Want: String; Code: Integer);
begin
  if Got <> Want then begin WriteLn(Code, ': ', Got); Halt(Code); end;
end;
begin
  Check(CanonicalPinMap('(G:1),(D:2),(S:3)'), '(G:1),(D:2),(S:3)', 1);
  Check(CanonicalPinMap('G:1;D:2'), '(G:1),(D:2)', 2);
  Check(CanonicalPinMap(' G -> 1 , D->2 '), '(G:1),(D:2)', 3);
  Check(CanonicalPinMap('G1'), '', 4);
  Check(CanonicalPinMap('G:'), '', 5);
  if not PinMapHolds('(G:1),(D:2)', '(S:3), (D:2),(G:1)') then Halt(6);
  if PinMapHolds('(G:1),(D:2)', '(G:1),(D:3)') then Halt(7);
  if PinMapHolds('', '(G:1)') then Halt(8);
  if PinMapHolds('(G:1)', '(G:11)') then Halt(9);
end.
""".replace("@@HELPERS@@", helpers)
    path = tmp_path / "pinmaps.pas"
    path.write_text(program, encoding="utf-8")
    built = subprocess.run([fpc, str(path)], cwd=tmp_path,
                           capture_output=True, text=True, check=False)
    assert built.returncode == 0, built.stdout + built.stderr
    exe = path.with_suffix(".exe" if os.name == "nt" else "")
    ran = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
    assert ran.returncode == 0, ran.stdout
