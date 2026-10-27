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
