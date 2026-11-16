# SPDX-License-Identifier: Apache-2.0
"""Automatic EasyEDA plan emission remains a two-pass, offline operation."""

import asyncio

from eda_agent.tools.easyeda import register_easyeda_tools
from tests.test_easyeda_template import PLAN, RESOLVED


def _tools():
    tools = {}

    class Capture:
        def tool(self, *args, **kwargs):
            def register(fn):
                tools[fn.__name__] = fn
                return fn
            return register

    register_easyeda_tools(Capture())
    return tools


def test_auto_layout_emits_placement_and_explicit_wiring_step():
    tools = _tools()
    result = asyncio.run(tools["easyeda_emit_plan"](PLAN, RESOLVED))
    assert result["ok"]
    assert result["nets_pending"] == 1
    assert result["next_step"] == "easyeda_emit_connections"
    assert len([c for c in result["calls"]
                if c["tool"] == "easyeda_place_schematic_component"]) == 2


def test_connections_use_real_pins_and_refuse_missing_positions():
    tools = _tools()
    complete = asyncio.run(tools["easyeda_emit_connections"](
        PLAN, {"R1.1": [100, 100], "R2.2": [300, 200]}))
    assert complete["ok"] and not complete["blockers"]
    wires = [c["arguments"]["points"] for c in complete["calls"]
             if c["tool"] == "easyeda_add_wire"]
    assert wires == [[[100.0, 100.0], [300.0, 100.0], [300.0, 200.0]]]
    missing = asyncio.run(tools["easyeda_emit_connections"](
        PLAN, {"R1.1": [100, 100]}))
    assert missing["blockers"] and not missing["calls"]


def test_nonfinite_pin_position_is_refused_before_emission():
    tools = _tools()
    result = asyncio.run(tools["easyeda_emit_connections"](
        PLAN, {"R1.1": [float("nan"), 100]}))
    assert result["ok"] is False


def test_auto_emitter_is_registered_for_easyeda_backend():
    from eda_agent.tools import register_backend
    from eda_agent.tools.registry import ToolRegistry

    registry = ToolRegistry()
    register_backend(registry, "easyeda", "full")
    assert {"easyeda_emit_plan", "easyeda_emit_connections"} <= set(registry.names)
