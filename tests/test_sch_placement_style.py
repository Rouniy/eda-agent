# SPDX-License-Identifier: Apache-2.0
"""The placement handlers keep sheet typography and fixed port geometry."""
from __future__ import annotations

import pytest

from tests.test_sch_properties_match_their_interface import _routine, _source
from tests.test_gap_fixes import _RecordingBridge, _capture


def test_new_objects_infer_font_before_creation_and_use_typed_writes():
    source = _source()
    assert "VoteSheetFonts(SchDoc, eNetLabel" in _routine(source, "InferSheetFontFor")
    assert "ExtractJsonValue(Params, 'font_id')" in _routine(source, "PlacementFontId")
    for handler, kind, write in (
        ("Gen_PlacePort", "ePort", "SchPort.FontId := FontToUse"),
        ("Gen_PlacePowerPort", "ePowerObject", "PowerObj.FontId := FontToUse"),
        ("Gen_PlaceTextFrame", "eTextFrame", "TF.FontId := FontToUse"),
        ("Gen_PlaceSheetEntry", "eSheetEntry", "Entry.TextFontID := FontToUse"),
    ):
        body = _routine(source, handler)
        assert body.index(f"PlacementFontId(SchDoc, {kind}, Params)") < body.index(
            "SchObjectFactory(")
        assert write in body
    entry = _routine(source, "Gen_PlaceSheetEntry")
    assert entry.index("Sym.AddAndPositionSchObject(Entry)") < entry.index(
        "Entry.TextFontID := FontToUse")


def test_width_and_text_line_breaks_are_applied_in_native_order():
    port = _routine(_source(), "Gen_PlacePort")
    assert port.index("SchPort.FontId := FontToUse") < port.index(
        "SchPort.AutoSize := False") < port.index("SchPort.Width := MilsToCoordF(WantWidth)")
    assert "GotAuto := SchPort.AutoSize" in port
    assert "GotWidth := CoordToMilsF(SchPort.Width)" in port
    getter = _routine(_source(), "GetSchProperty")
    assert "Result := BoolToJsonStr(PortObj.AutoSize)" in getter
    assert "If Obj.ObjectId = ePort Then" in getter
    frame = _routine(_source(), "Gen_PlaceTextFrame")
    assert frame.index("StringReplace(TextStr, '\\' + 'n', #10") < frame.index(
        "StringReplace(TextStr, #10, #13 + #10") < frame.index("TF.Text := TextStr")


def test_value_stamps_update_existing_parameter_and_hide_new_ones():
    source = _source()
    setter = _routine(source, "SetExistingCompParamText")
    assert "SetState_IterationDepth(eIterateFirstLevel)" in setter
    assert "SchObjectFactory" not in setter
    creator = _routine(source, "SetCompParamText")
    assert "SetState_IterationDepth(eIterateFirstLevel)" in creator
    assert creator.index("NewParam.IsHidden := True") < creator.index(
        "Comp.AddSchObject(NewParam)")
    for handler, comp in (("Gen_SetSchComponentParameters", "TargetComp"),
                          ("Gen_SetSchComponentsParameters", "Comp")):
        body = _routine(source, handler)
        assert f"SetExistingCompParamText({comp}, 'Value', Val)" in body


@pytest.mark.asyncio
async def test_port_and_text_frame_forward_requested_style(monkeypatch):
    from eda_agent.tools import generic as g

    bridge = _RecordingBridge()
    monkeypatch.setattr(g, "get_bridge", lambda: bridge)
    captured = _capture(g, "register_generic_tools")
    await captured["sch_place_port"]("DATA", 100, 200, width=420, font_id=7)
    assert bridge.calls[-1][1]["width"] == "420.0"
    assert bridge.calls[-1][1]["font_id"] == "7"
    await captured["sch_place_text_frame"](0, 0, 500, 200, "A\\nB", font_id=7)
    assert bridge.calls[-1][1]["text"] == "A\\nB"
    assert bridge.calls[-1][1]["font_id"] == "7"
    await captured["sch_place_text_frame"](
        0.125, 0.0625, 500.5, 200.0625, "note")
    assert {key: bridge.calls[-1][1][key] for key in
            ("x1", "y1", "x2", "y2")} == {
                "x1": "0.125", "y1": "0.0625",
                "x2": "500.5", "y2": "200.0625"}
