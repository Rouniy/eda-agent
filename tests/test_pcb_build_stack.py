# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""pcb_build_stack: a whole stack through the AD19+ MasterLayerStack.

The Rosen controller (AD 25.8.1, 2026-10-27) needed a 4-layer board turned
into L1 Top / L2 GND / L3 Sig / L4 Pwr / L5 GND / L6 Bottom. Done with the
LayerStack_V7 tools it read back right and came out corrupt. These tests run
the planner and the tool against a fake stack that behaves as AD 25.8.1 did
live on a scratch copy of that board: copper inserted below a layer lands
after that layer's dielectrics, Altium adds a dielectric under each new copper
layer by itself, and no dielectric can be created any other way.
"""
from __future__ import annotations

import asyncio

import pytest

from eda_agent.design import stack_build
from eda_agent.tools import pcb


FOUR_LAYER = [
    {"name": "Top Overlay", "kind": "overlay", "thickness_mils": 0.25},
    {"name": "Top Solder", "kind": "solder_mask", "thickness_mils": 0.4, "dielectric_type": 3,
     "constant": 3.5},
    {"name": "Top Layer", "kind": "copper", "thickness_mils": 0.7},
    {"name": "Dielectric 1", "kind": "dielectric", "thickness_mils": 4.7244, "dielectric_type": 2,
     "constant": 4.3},
    {"name": "Dielectric 2", "kind": "dielectric", "thickness_mils": 4.7244, "dielectric_type": 2,
     "constant": 4.3},
    {"name": "Internal Plane 1", "kind": "copper", "thickness_mils": 0.7},
    {"name": "Dielectric 3", "kind": "dielectric", "thickness_mils": 55.1181, "dielectric_type": 1,
     "constant": 4.55},
    {"name": "Internal Plane 2", "kind": "copper", "thickness_mils": 0.7},
    {"name": "Dielectric 4", "kind": "dielectric", "thickness_mils": 9.4488, "dielectric_type": 2,
     "constant": 4.3},
    {"name": "Bottom Layer", "kind": "copper", "thickness_mils": 0.7},
    {"name": "Bottom Solder", "kind": "solder_mask", "thickness_mils": 0.4, "dielectric_type": 3,
     "constant": 3.5},
]


def _cu(name, plane=False):
    return {"kind": "copper", "name": name, "thickness_mils": 1.378, "plane": plane}


def _d(t, kind="prepreg", dk=4.0):
    return {"kind": "dielectric", "type": kind, "thickness_mils": t, "constant": dk,
            "material": "FR-4"}


SIX_LAYER = [_cu("L1 Top"), _d(4.33), _cu("L2 GND", True), _d(3.937, "core", 4.3),
             _cu("L3 Signal"), _d(37.4, "core", 4.3), _cu("L4 Power"),
             _d(3.937, "core", 4.3), _cu("L5 GND", True), _d(4.33), _cu("L6 Bottom")]


# Planner ---------------------------------------------------------------------

PLANES_USED = [{"name": "Top Layer", "layer_id": 16777217, "used_by_prims": True},
               {"name": "Internal Plane 1", "layer_id": 16842753, "used_by_prims": True},
               {"name": "Internal Plane 2", "layer_id": 16842754, "used_by_prims": True},
               {"name": "Bottom Layer", "layer_id": 16842751, "used_by_prims": True}]


def test_plan_keeps_the_planes_and_inserts_copper_around_them():
    plan = stack_build.normalise(SIX_LAYER)
    ops = stack_build.plan_ops(FOUR_LAYER, plan, PLANES_USED)
    assert [o for o in ops if o["op"] == "remove"] == []
    finals = {o["name"]: o["new_name"] for o in ops
              if o["op"] == "set_copper" and o["name"].startswith("__")}
    assert set(finals.values()) == {"L1 Top", "L6 Bottom", "L2 GND", "L5 GND"}
    inserts = [(o["kind"], o["name"], o["ref"]) for o in ops if o["op"] == "insert"]
    assert inserts == [("signal", "L3 Signal", "L2 GND"), ("signal", "L4 Power", "L3 Signal")]


def test_dielectric_phase_fits_each_gap_and_sets_it():
    plan = stack_build.normalise(SIX_LAYER)
    back = [{"name": "L1 Top", "kind": "copper"},
            {"name": "Dielectric 1", "kind": "dielectric"},
            {"name": "Dielectric 2", "kind": "dielectric"},
            {"name": "L2 GND", "kind": "copper"},
            {"name": "Dielectric 3", "kind": "dielectric"},
            {"name": "L3 Signal", "kind": "copper"},
            {"name": "Dielectric6", "kind": "dielectric"},
            {"name": "L4 Power", "kind": "copper"},
            {"name": "Dielectric7", "kind": "dielectric"},
            {"name": "L5 GND", "kind": "copper"},
            {"name": "Dielectric 4", "kind": "dielectric"},
            {"name": "Dielectric 5", "kind": "dielectric"},
            {"name": "L6 Bottom", "kind": "copper"}]
    ops = stack_build.dielectric_ops(back, plan)
    assert [o["name"] for o in ops if o["op"] == "remove"] == ["Dielectric 2", "Dielectric 5"]
    finals = [o for o in ops if o["op"] == "set_dielectric" and o["name"].startswith("__")]
    assert [o["new_name"] for o in finals] == [f"Dielectric {n}" for n in range(1, 6)]
    assert finals[2]["thickness_mils"] == "37.4" and finals[2]["type"] == "1"


def test_a_gap_short_of_dielectrics_is_refused():
    plan = stack_build.normalise([_cu("A"), _d(2), _d(2), _cu("B")])
    back = [{"name": "A", "kind": "copper"}, {"name": "D", "kind": "dielectric"},
            {"name": "B", "kind": "copper"}]
    with pytest.raises(stack_build.StackPlanError, match="cannot add one"):
        stack_build.dielectric_ops(back, plan)


def test_copper_that_came_out_wrong_is_refused():
    plan = stack_build.normalise([_cu("A"), _d(2), _cu("B")])
    back = [{"name": "A", "kind": "copper"}, {"name": "D", "kind": "dielectric"},
            {"name": "X", "kind": "copper"}]
    with pytest.raises(stack_build.StackPlanError, match="came out"):
        stack_build.dielectric_ops(back, plan)


def test_a_busy_layer_the_plan_drops_is_refused_before_any_change():
    plan = stack_build.normalise([_cu("A"), _d(4), _cu("B")])
    with pytest.raises(stack_build.StackPlanError, match="Internal Plane 1, Internal Plane 2"):
        stack_build.plan_ops(FOUR_LAYER, plan, PLANES_USED)


def test_an_idle_layer_the_plan_drops_is_removed():
    idle = [dict(i, used_by_prims=False) for i in PLANES_USED]
    plan = stack_build.normalise([_cu("A"), _d(4), _cu("B")])
    ops = stack_build.plan_ops(FOUR_LAYER, plan, idle)
    assert {"op": "remove", "name": "Internal Plane 1"} in ops


@pytest.mark.parametrize("layer_id,kind", [
    (16842753, "plane"), (16777218, "signal"), (39, "plane"), (2, "signal"), (None, "signal")])
def test_copper_type_from_layer_id(layer_id, kind):
    assert stack_build.copper_type(layer_id) == kind


@pytest.mark.parametrize("bad,why", [
    ([_cu("A"), _cu("B"), _cu("C")], "no dielectric"),
    ([_d(4), _cu("A"), _d(4)], "starts and ends with copper"),
    ([_cu("A", True), _d(4), _cu("B")], "signal layers"),
    ([_cu("A"), _d(4), _cu("A")], "used twice"),
    ([_cu("A"), _d(0), _cu("B")], "positive"),
    ([_cu("A"), {"kind": "dielectric", "type": "glass", "thickness_mils": 4}, _cu("B")], "core or prepreg"),
    ([_cu("A")], "at least"),
])
def test_bad_plans_are_refused(bad, why):
    with pytest.raises(stack_build.StackPlanError, match=why):
        stack_build.normalise(bad)


def test_two_dielectrics_in_a_row_are_allowed():
    plan = stack_build.normalise([_cu("A"), _d(2), _d(2), _cu("B")])
    assert [p["name"] for p in plan] == ["A", "Dielectric 1", "Dielectric 2", "B"]


def test_check_reports_each_difference():
    plan = stack_build.normalise([_cu("A"), _d(4.33), _cu("B")])
    back = [{"name": "A", "kind": "copper", "thickness_mils": 1.378},
            {"name": "Dielectric 1", "kind": "dielectric", "thickness_mils": -0.39,
             "dielectric_type": 1, "constant": 4.0},
            {"name": "B", "kind": "copper", "thickness_mils": 1.378}]
    checks = [m["check"] for m in stack_build.check(back, plan)]
    assert checks == ["thickness_mils", "material", "type"]




def test_readback_rejects_wrong_plane_type_and_material():
    plan = stack_build.normalise([_cu("Top"), _d(4), _cu("Plane", True),
                                  _d(4), _cu("Bottom")])
    back = [dict(name=p["name"], kind=p["kind"],
                 thickness_mils=p["thickness_mils"],
                 **({"dielectric_type": p["type"], "constant": p["constant"],
                     "material": "Wrong"} if p["kind"] == "dielectric" else {}))
            for p in plan]
    ids = [{"name": "Top", "layer_id": 1},
           {"name": "Plane", "layer_id": 2},
           {"name": "Bottom", "layer_id": 32}]
    checks = stack_build.check(back, plan, ids)
    assert [c["check"] for c in checks] == ["material", "copper_type", "material"]


def test_additive_and_nonconductive_copper_is_rejected():
    inventory = [
        {"name": "Top", "additive": False, "resistivity": 1.7},
        {"name": "Signal", "additive": True, "resistivity": 2147483647},
        {"name": "Dielectric 1"},
    ]
    assert [(f["check"], f["layer"]) for f in
            stack_build.check_copper_flags(inventory)] == [
                ("additive", "Signal"), ("non_conductive", "Signal")]


def test_loss_tangent_is_written_and_checked():
    raw = [_cu("Top"), {**_d(4), "loss_tangent": 0.018}, _cu("Bottom")]
    plan = stack_build.normalise(raw)
    back = [
        {"name": "Top", "kind": "copper", "thickness_mils": 1.378},
        {"name": "Dielectric 1", "kind": "dielectric", "thickness_mils": 4,
         "dielectric_type": 1, "constant": 4.0, "material": "FR-4",
         "loss_tangent": 0.025},
        {"name": "Bottom", "kind": "copper", "thickness_mils": 1.378},
    ]
    assert any(op.get("loss_tangent") == "0.018"
               for op in stack_build.dielectric_ops(back, plan))
    assert any(f["check"] == "loss_tangent"
               for f in stack_build.check(back, plan))
    back[1]["loss_tangent"] = 0.018
    assert not any(f["check"] == "loss_tangent"
                   for f in stack_build.check(back, plan))


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf"), "bad"])
def test_invalid_loss_tangent_is_refused(value):
    with pytest.raises(stack_build.StackPlanError, match="loss_tangent"):
        stack_build.normalise([_cu("Top"), {**_d(4), "loss_tangent": value},
                               _cu("Bottom")])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0, 0.0])
def test_nonfinite_or_nonpositive_thickness_is_refused(bad):
    with pytest.raises(stack_build.StackPlanError, match="finite and positive"):
        stack_build.normalise([_cu("Top"), {"kind": "dielectric",
                                "thickness_mils": bad}, _cu("Bottom")])


def test_first_native_write_timeout_reports_possible_unsaved_edit(monkeypatch):
    path = r"C:\scratch\Stack.PcbDoc"
    layers = [
        {"name": "Top", "kind": "copper", "thickness_mils": 1},
        {"name": "Dielectric 1", "kind": "dielectric", "thickness_mils": 4,
         "dielectric_type": 1, "constant": 4, "material": "FR-4"},
        {"name": "Bottom", "kind": "copper", "thickness_mils": 1},
    ]

    class Bridge:
        def __init__(self):
            self.calls = []

        async def send_command_async(self, command, params, timeout=None):
            self.calls.append((command, params))
            if command == "application.get_open_documents":
                return [{"file_path": path, "modified": False}]
            if command == "pcb.physical_stack":
                return {"board_path": path, "style": 0, "layer_count": 3,
                        "total_thickness_mils": 6, "layers": layers}
            if command == "pcb.stack_edit":
                if params["op"] == "inspect":
                    return {"board_path": path, "layers": [
                        {"name": "Top", "layer_id": 1, "used_by_prims": True},
                        {"name": "Bottom", "layer_id": 32, "used_by_prims": True}]}
                raise TimeoutError("reply lost after native write")
            return {}

    class Mcp:
        def __init__(self):
            self.tools = {}

        def tool(self, *args, **kwargs):
            def register(fn):
                self.tools[fn.__name__] = fn
                return fn
            return register

    bridge = Bridge()
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = Mcp()
    pcb.register_pcb_tools(mcp)
    result = asyncio.run(mcp.tools["pcb_build_stack"](
        path, [_cu("Top"), _d(4, "core"), _cu("Bottom")], dry_run=False))
    assert result["ok"] is False
    assert result["applied"] == 0
    assert result["partial_unsaved"] is True
    assert result["native_state_unknown"] is True
    assert result["failure"]["error"] == "reply lost after native write"
    assert not any(command.startswith("application.save") for command, _ in bridge.calls)
