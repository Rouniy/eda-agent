# SPDX-License-Identifier: Apache-2.0
"""Keep the impedance profile reader wired into the PCB script."""

from pathlib import Path

from tests.pascal_source import load


PCB = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


def test_impedance_profile_reader_uses_typed_sdk_interfaces():
    functions = load(PCB, minimum=20)
    body = functions["PCB_GetImpedanceProfiles"]
    assert "Stack : IPCB_MasterLayerStack2;" in body
    assert "Profile : IPCB_ImpedanceProfile;" in body
    assert "Trace : IPCB_TraceImpedance;" in body
    assert "GetImpedanceProfileCount" in body
    assert "read_errors" in body
    assert "ExtractFileName(Board.FileName)" in body
    assert "'get_impedance_profiles':   Result := PCB_GetImpedanceProfiles" in functions["HandlePCBCommand"]
