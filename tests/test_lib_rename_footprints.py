# SPDX-License-Identifier: Apache-2.0
"""lib_rename_footprints: many renames in one PcbLib, one edit round.

Ported from TechAUmNu's fork (carrier-local) onto this tree's helpers.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import library
from tests.pascal_source import load

LIBRARY_PAS = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Library.pas"


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
        return {"renamed": 1, "failed": 0, "total": 1, "results": []}


def _tool(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return mcp.tools["lib_rename_footprints"], bridge


def test_the_renames_go_as_one_batch(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    out = asyncio.run(tool([{"from": "A,1", "to": "A.1"}, {"from": "B", "to": "C"}], library_path="L.PcbLib"))
    assert bridge.sent == [("library.rename_footprints",
                            {"renames": "old=A,1;new=A.1~~old=B;new=C", "library_path": "L.PcbLib"})]
    assert out["refused"] == []


def test_a_name_the_wire_cannot_carry_is_refused_not_altered(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    out = asyncio.run(tool([{"from": "A;B", "to": "C"}, {"from": "D", "to": "E~"},
                            {"from": "F", "to": "F"}, {"from": "G", "to": "\u4e2d"}, "junk",
                            {"from": "OK", "to": "FINE"}]))
    assert bridge.sent[0][1]["renames"] == "old=OK;new=FINE"
    assert len(out["refused"]) == 5
    nothing = asyncio.run(tool([{"from": "", "to": "X"}]))
    assert nothing["ok"] is False and len(bridge.sent) == 1


def test_the_handler_renames_inside_one_edit_round_and_reads_back():
    units = load(LIBRARY_PAS)
    body = units["Lib_RenameFootprints"]
    assert body.count("PcbBeginEdit(0);") == 1 and body.count("PcbEndEdit(0);") == 1
    assert body.index("PcbBeginEdit(0);") < body.index("NextBatchOp(Remaining)") < body.index("PcbEndEdit(0);")
    assert "PcbLib := FocusPcbLibAt(LibPath);" in body
    assert "Try ReadBack := Target.Name;" in body
    for status in ("renamed", "unchanged", "not_found", "name_exists", "same_name", "missing_field"):
        assert f"'{status}'" in body
    text = LIBRARY_PAS.read_text(encoding="utf-8")
    assert "'rename_footprints':    Result := Lib_RenameFootprints(Params, RequestId);" in text
    assert text.index("Function FocusPcbLibAt(") < text.index("Function Lib_RenameFootprints(")
