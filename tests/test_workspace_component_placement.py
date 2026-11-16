# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Managed Altium Workspace component resolution and placement."""

from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.tools import generic as generic_mod
from eda_agent.tools import library as library_mod
from eda_agent.tools.metadata import tool_metadata


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_GUID = "11111111-1111-1111-1111-111111111111"
ITEM_GUID = "22222222-2222-2222-2222-222222222222"
REVISION_GUID = "33333333-3333-3333-3333-333333333333"


def _tools(module, register_name):
    captured = {}

    class _Mcp:
        def tool(self):
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

    getattr(module, register_name)(_Mcp())
    return captured


LIBRARY_TOOLS = _tools(library_mod, "register_library_tools")
GENERIC_TOOLS = _tools(generic_mod, "register_generic_tools")


class _Bridge:
    def __init__(self):
        self.calls = []

    async def send_command_async(self, command, params=None, timeout=None):
        self.calls.append((command, params or {}, timeout))
        if command == "application.get_active_document":
            return {"file_path": r"C:\Design\Power.SchDoc"}
        return {"success": True}


def test_workspace_resolver_sends_exact_name_to_live_handler(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(library_mod, "get_bridge", lambda: bridge)
    tool = LIBRARY_TOOLS["lib_resolve_workspace_component"]

    asyncio.run(tool(component_name="  CMD298C4  "))

    assert bridge.calls == [(
        "library.resolve_workspace_component",
        {"component_name": "CMD298C4"},
        45.0,
    )]


def test_workspace_resolver_rejects_an_empty_name_without_a_bridge_call(
    monkeypatch,
):
    bridge = _Bridge()
    monkeypatch.setattr(library_mod, "get_bridge", lambda: bridge)
    tool = LIBRARY_TOOLS["lib_resolve_workspace_component"]

    result = asyncio.run(tool(component_name="  "))

    assert result["error"] == "MISSING_COMPONENT_NAME"
    assert bridge.calls == []


def test_workspace_placement_packs_stable_ids_and_coordinates(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(generic_mod, "get_bridge", lambda: bridge)
    tool = GENERIC_TOOLS["sch_place_workspace_components"]

    result = asyncio.run(tool(placements=[{
        "workspace_guid": "{" + WORKSPACE_GUID + "}",
        "item_guid": ITEM_GUID,
        "revision_guid": REVISION_GUID,
        "item_revision_id": "CMP-001-03",
        "x": 4500,
        "y": 3500,
        "rotation": 90,
    }]))

    assert result["success"] is True
    assert len(bridge.calls) == 1
    command, params, timeout = bridge.calls[0]
    assert command == "generic.place_workspace_components"
    assert timeout == 60.0
    packed = params["placements"]
    assert f"workspace_guid={WORKSPACE_GUID}" in packed
    assert f"item_guid={ITEM_GUID}" in packed
    assert f"revision_guid={REVISION_GUID}" in packed
    assert "item_revision_id=CMP-001-03" in packed
    assert "x=4500;y=3500;rotation=90" in packed


def test_workspace_placement_focuses_the_named_sheet_first(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(generic_mod, "get_bridge", lambda: bridge)
    tool = GENERIC_TOOLS["sch_place_workspace_components"]

    asyncio.run(tool(
        placements=[{
            "workspace_guid": WORKSPACE_GUID,
            "item_guid": ITEM_GUID,
            "revision_guid": REVISION_GUID,
            "x": 100,
            "y": 200,
        }],
        document_path=r"C:\Design\Power.SchDoc",
    ))

    assert [c[0] for c in bridge.calls] == [
        "application.set_active_document",
        "application.get_active_document",
        "generic.place_workspace_components",
    ]


def test_workspace_placement_rejects_a_malformed_guid_before_mutation(
    monkeypatch,
):
    bridge = _Bridge()
    monkeypatch.setattr(generic_mod, "get_bridge", lambda: bridge)
    tool = GENERIC_TOOLS["sch_place_workspace_components"]

    result = asyncio.run(tool(placements=[{
        "workspace_guid": "not-a-guid",
        "item_guid": ITEM_GUID,
        "revision_guid": REVISION_GUID,
    }]))

    assert result["error"] == "INVALID_WORKSPACE_GUID"
    assert bridge.calls == []


def test_workspace_placement_refuses_wrong_focused_sheet(monkeypatch):
    bridge = _Bridge()

    async def wrong_focus(command, params=None, timeout=None):
        bridge.calls.append((command, params or {}, timeout))
        if command == "application.get_active_document":
            return {"file_path": r"C:\Design\Other.SchDoc"}
        return {"success": True}

    bridge.send_command_async = wrong_focus
    monkeypatch.setattr(generic_mod, "get_bridge", lambda: bridge)
    tool = GENERIC_TOOLS["sch_place_workspace_components"]
    result = asyncio.run(tool(placements=[{
        "workspace_guid": WORKSPACE_GUID,
        "item_guid": ITEM_GUID,
        "revision_guid": REVISION_GUID,
    }], document_path=r"C:\Design\Power.SchDoc"))

    assert result["error"] == "SHEET_MISMATCH"
    assert not any(c[0] == "generic.place_workspace_components" for c in bridge.calls)


def test_pascal_handlers_use_the_live_workspace_apis():
    library = (ROOT / "scripts" / "altium" / "Library.pas").read_text(
        encoding="utf-8"
    )
    generic = (ROOT / "scripts" / "altium" / "Generic.pas").read_text(
        encoding="utf-8"
    )

    resolver = library.split(
        "Function Lib_ResolveWorkspaceComponent", 1
    )[1].split("Function LibTypeName", 1)[0]
    placer = generic.split(
        "Function Gen_PlaceWorkspaceComponents", 1
    )[1].split("Function Gen_PlaceNetLabels", 1)[0]

    assert "GetDotNetObjectInterface('EDMS_GetDXPServerManager')" in resolver
    assert "SearchItemRevisions" in resolver
    assert "GetLastItemRevision" in resolver
    assert "DM_UseItemRevision" in placer
    assert "SHEET_MISMATCH" in placer
    assert "LoadComponentFromLibrary" not in placer
    assert "'resolve_workspace_component':" in library
    assert "'place_workspace_components':" in generic


def test_workspace_tools_publish_their_real_interaction_types():
    resolve = tool_metadata("lib_resolve_workspace_component")
    place = tool_metadata("sch_place_workspace_components")

    assert resolve["interaction"] == "readonly"
    assert resolve["maturity"] == "live_only"
    assert place["interaction"] == "silent"
    assert place["maturity"] == "live_only"
