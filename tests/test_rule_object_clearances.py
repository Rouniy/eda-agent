# SPDX-License-Identifier: Apache-2.0
"""A Clearance rule's table of one value per pair of object kinds.

A Clearance rule holds more than its Gap: the Rules editor's "Minimum
Clearance" grid has one value per pair of object kinds (Track to SMD pad,
Hole to Region, ...), and the DRC judges a pair by its cell. The bridge
read and wrote the Gap only, so a rule whose cells differ from its Gap
could neither be seen nor made, and a board that lost the table on the
way in could not be given it back.

``pcb_set_rule_properties`` takes ``object_clearances_mils`` and
``pcb_get_rule_properties`` returns the table. An empty ``comment`` now
clears a rule's comment: the bridge reads an empty value as "not given".
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import pcb
from tests.pascal_source import load

PCB_PAS = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"
KINDS = ("Track", "Arc", "SMDPad", "THPad", "Via", "Fill", "Poly", "Region", "Text", "Hole")


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self):
        self.sent = []

    async def send_command_async(self, command, params=None, **kwargs):
        self.sent.append((command, params))
        return {"name": params.get("name"), "properties_updated": 1}


def _tool(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_set_rule_properties"], bridge


def _sent(bridge):
    return [p for c, p in bridge.sent if c == "pcb.set_rule_properties"]


def test_cells_reach_the_bridge_in_its_spelling(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    asyncio.run(tool(name="Clearance", object_clearances_mils={"track-smdpad": 4, "Hole-*": 0}))
    assert _sent(bridge)[0]["object_clearances"] == "Track-SMDPad=4.0;Hole-*=0.0"


def test_an_unknown_kind_or_a_bad_length_is_refused_before_sending(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    for cells in ({"Track-Pad": 4}, {"Track": 4}, {"Track-Via-Hole": 4}, {"Track-Via": -1},
                  {"Track-Via": "wide"}, {}):
        out = asyncio.run(tool(name="Clearance", object_clearances_mils=cells))
        assert out.get("ok") is False and "object_clearances" in out["reason"], cells
    assert not _sent(bridge)


def test_an_empty_comment_clears_it(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    asyncio.run(tool(name="R", comment=""))
    asyncio.run(tool(name="R", comment="kept"))
    first, second = _sent(bridge)
    assert first.get("clear_comment") == "true" and "comment" not in first
    assert second.get("comment") == "kept" and "clear_comment" not in second
    text = PCB_PAS.read_text(encoding="latin-1")
    assert "If ExtractJsonValue(Params, 'clear_comment') = 'true' Then" in text


GENERIC_PAS = PCB_PAS.with_name("PCBGeneric.pas")


def test_a_scope_write_says_the_batch_drc_may_not_use_it_yet(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    scoped = asyncio.run(tool(name="R", scope1="InComponent('P5') And IsPad"))
    plain = asyncio.run(tool(name="R", comment="x"))
    assert scoped["batch_drc_uses_new_scope"] is False and "Rules" in scoped["batch_drc_note"]
    assert "batch_drc_note" not in plain


def test_the_python_kinds_are_the_bridge_kinds():
    assert tuple(pcb._CLEARANCE_KINDS.values()) == KINDS
    names = load(GENERIC_PAS)["ClearanceKindName"]
    for index, kind in enumerate(KINDS):
        assert f"I = {index} Then Result := '{kind}'" in names


def test_a_cell_is_addressed_by_two_primitives_that_are_destroyed_again():
    units = load(GENERIC_PAS)
    prim = units["ClearanceKindPrim"]
    for kind in ("eTrackObject", "eArcObject", "ePadObject", "eViaObject", "eFillObject",
                 "ePolyObject", "eRegionObject", "eTextObject"):
        assert f"PCBServer.PCBObjectFactory({kind}, eNoDimension, eCreate_Default)" in prim
    assert "Pad.HoleSize := 0;" in prim and "Pad.Layer := eMultiLayer;" in prim
    cell = units["ClearanceCell"]
    assert "R.SetClearance(P1, P2, Want);" in cell and "R.SetClearance(P2, P1, Want);" in cell
    assert "Result := R.GetClearance(P1, P2);" in cell
    assert cell.count("PCBServer.DestroyPCBObject(") == 2
    assert "AddPCBObject" not in prim + cell, "the helper primitives must never reach the board"


def test_each_cell_is_written_and_read_back():
    units = load(PCB_PAS)
    write = units["ClearanceCellsWrite"]
    assert "(R.RuleKind = eRule_Clearance) And (R.Name = RuleName)" in write
    assert "Got := ClearanceCell(R, A, B, Want);" in write
    assert "If Got <> Want Then" in write, "a cell that did not take is not reported"
    assert "PCBM_BeginModify" in write and "PCBM_EndModify" in write
    assert "Board.BoardIterator_Destroy(Iter);" in write
    read = units["ClearanceCellsJson"]
    assert "For B := A To 9 Do" in read, "each pair is listed once"
    assert "V := ClearanceCell(R, A, B, -1);" in read
    assert "If V < 0 Then S := S + 'null'" in read


def test_the_table_is_for_a_clearance_rule_and_is_returned_by_both_tools():
    text = PCB_PAS.read_text(encoding="latin-1")
    assert "If (XCells <> '') And (Kind <> 0) Then XBad := 'object_clearances is for a Clearance rule';" in text
    assert "XCellCount := ClearanceCellsWrite(Board, RuleName, XCells, XMissed);" in text
    get = load(PCB_PAS)["PCB_GetRuleProperties"]
    assert "If Rule.RuleKind = eRule_Clearance Then CellsField := ClearanceCellsJson(Board, RuleName);" in get
    assert '"scope_1":"' in get and '"scope_2":"' in get and '"comment":"' in get


def test_obj_query_reads_a_rule():
    units = load(GENERIC_PAS)
    names = units["IsPCBRuleProperty"]
    text = units["PCBRulePropertyText"]
    for name in ("Scope1Expression", "Scope2Expression", "DRCEnabled", "Priority", "RuleKind",
                 "Comment", "Name", "ObjectClearances"):
        assert f"PropName = '{name}'" in names and f"PropName = '{name}'" in text
    assert ("If (Oid = eRuleObject) And IsPCBRuleProperty(PropName) Then "
            "Result := PCBRulePropertyText(Obj, PropName)") in units["GetPCBProperty"]
    assert "IsGeneratedPCBProperty(PropName) Or IsPCBRuleProperty(PropName)" in units["IsKnownPCBProperty"]
