# SPDX-License-Identifier: Apache-2.0
"""lib_set_current_footprint: the PcbLib twin of lib_set_current_component.

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
        return {"success": True, "footprint": params["footprint_name"]}


def _tool(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return mcp.tools["lib_set_current_footprint"], bridge


def test_the_name_and_the_library_go_to_the_bridge(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    asyncio.run(tool(" SOIC8 ", library_path=r"C:\\libs\\A.PcbLib"))
    assert bridge.sent == [("library.set_current_footprint",
                            {"footprint_name": "SOIC8",
                             "library_path": r"C:\\libs\\A.PcbLib"})]
    asyncio.run(tool("QFN"))
    assert bridge.sent[-1][1] == {"footprint_name": "QFN"}


def test_an_empty_name_is_refused_before_the_bridge(monkeypatch):
    tool, bridge = _tool(monkeypatch)
    assert asyncio.run(tool("  "))["ok"] is False
    assert bridge.sent == []


def test_the_handler_selects_through_the_checked_helper():
    units = load(LIBRARY_PAS)
    body = units["Lib_SetCurrentFootprint"]
    assert "PcbLib := FocusPcbLibAt(LibPath);" in body
    # PcbLibTarget reads the switch back by name; a failed switch is refused.
    assert "Footprint := PcbLibTarget(PcbLib, Wanted, Problem);" in body
    assert "'NO_FOOTPRINT', Problem" in body
    assert "PreProcess" not in body            # nothing is written
    text = LIBRARY_PAS.read_text(encoding="utf-8")
    assert "'set_current_footprint': Result := Lib_SetCurrentFootprint(Params, RequestId);" in text
    # DelphiScript cannot call a routine declared further down.
    assert text.index("Function FocusPcbLibAt(") < text.index("Function Lib_SetCurrentFootprint(")
    assert text.index("Function PcbLibTarget(") < text.index("Function Lib_SetCurrentFootprint(")
