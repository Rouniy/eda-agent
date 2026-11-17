# SPDX-License-Identifier: Apache-2.0
"""pcb_set_rule_properties: Matched Lengths tolerance, pair uncoupled length.

Asked for while comparing another tool's length check with Altium's: with
the tolerance of a Matched Lengths rule at 0.001 mil every net of its scope
gets a DRC row that prints the length Altium uses. Neither value could be
written through the bridge.

Measured on AD 26.11 on a copy: both wrote and read back 0.001 mil, and the
Matched Lengths rule then reported one row per net of its class.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import pcb
from tests.pascal_source import load

PCB_PAS = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


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


def test_both_values_reach_the_bridge(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    asyncio.run(tool(name="ML", matched_length_tolerance_mils=0.001))
    asyncio.run(tool(name="DP", dp_max_uncoupled_length_mils=7.874))
    sent = [p for c, p in bridge.sent if c == "pcb.set_rule_properties"]
    assert sent[0]["matched_length_tolerance_mils"] == "0.001"
    assert sent[1]["dp_max_uncoupled_length_mils"] == "7.874"


def test_a_negative_length_is_refused_before_sending(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    for field in ("matched_length_tolerance_mils", "dp_max_uncoupled_length_mils"):
        out = asyncio.run(tool(name="R", **{field: -1.0}))
        assert out.get("ok") is False and field in out["reason"]
    assert not [c for c, _ in bridge.sent if c == "pcb.set_rule_properties"]


def test_each_value_is_written_to_its_own_rule_kind_and_read_back():
    units = load(PCB_PAS)
    matched = units["RuleExtrasMatched"]
    assert "(R.RuleKind = 4) And (R.Name = RuleName)" in matched
    assert "R.Tolerance := MilsToCoordF(" in matched
    assert "CoordToMilsF(R.Tolerance)" in matched, "the tolerance is not read back"
    pair = units["RuleExtrasUncoupled"]
    assert "(R.RuleKind = 51) And (R.Name = RuleName)" in pair
    assert "R.MaxUncoupledLength := MilsToCoordF(" in pair
    assert "CoordToMilsF(R.MaxUncoupledLength)" in pair, "the length is not read back"
    for body, field in ((matched, "matched_length_tolerance_mils"), (pair, "dp_max_uncoupled_length_mils")):
        assert f"Missed := Missed + '\"{field}\",'" in body, f"{field} that did not take is not reported"
        assert "Board.BoardIterator_Destroy(Iter);" in body


def test_a_value_for_another_rule_kind_is_refused():
    text = PCB_PAS.read_text(encoding="latin-1")
    assert "If (XMTol <> '') And (Kind <> 4) Then XBad := 'matched_length_tolerance_mils is for a Matched Lengths rule';" in text
    assert ("If (XDUnc <> '') And (Kind <> 51) Then XBad := "
            "'dp_max_uncoupled_length_mils is for a Differential Pairs Routing rule';") in text
    assert (text.index("Function RuleExtrasMatched(") < text.index("Function RuleExtrasUncoupled(")
            < text.index("XReport := RuleExtrasMatched(Board, RuleName, XMTol, XMissed);"))
