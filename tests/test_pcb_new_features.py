# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Wiring tests for the production-feature tools: placement import, teardrops,
silkscreen auto-placement, length tuning, panelization, and fab-package
generation. No Altium: a recording fake bridge captures the dispatched
command + params (and, for the fab package, scripts the OutJob responses)."""

from __future__ import annotations

import pytest

from eda_agent.tools import pcb as pcb_module
from eda_agent.tools import project as project_module


class RecBridge:
    def __init__(self, responder=None):
        self.calls: list[tuple[str, dict]] = []
        self._responder = responder

    async def send_command_async(self, command, params=None, timeout=None):
        self.calls.append((command, params or {}))
        if self._responder:
            return self._responder(command, params or {})
        return {"ok": True}


def _capture(module, register_fn, monkeypatch, bridge):
    monkeypatch.setattr(module, "get_bridge", lambda: bridge)
    cap: dict = {}

    class M:
        def tool(self):
            def d(fn):
                cap[fn.__name__] = fn
                return fn
            return d

    register_fn(M())
    return cap


def _pcb(monkeypatch, bridge):
    return _capture(pcb_module, pcb_module.register_pcb_tools, monkeypatch, bridge)


def _project(monkeypatch, bridge):
    return _capture(project_module, project_module.register_project_tools, monkeypatch, bridge)


@pytest.mark.asyncio
async def test_stitching_vias_preserves_fractional_mils(monkeypatch):
    bridge = RecBridge()
    tools = _pcb(monkeypatch, bridge)
    await tools["pcb_place_stitching_vias"](
        "GND", 10.25, 20.5, 30.75, 40.125,
        spacing_mils=2.5, via_size_mils=1.75,
        via_hole_mils=0.625, clearance_mils=0.375,
    )
    command, params = bridge.calls[-1]
    assert command == "pcb.place_stitching_vias"
    assert {key: params[key] for key in (
        "x1_mils", "y1_mils", "x2_mils", "y2_mils",
        "spacing_mils", "via_size_mils", "via_hole_mils", "clearance_mils",
    )} == {
        "x1_mils": "10.25", "y1_mils": "20.5",
        "x2_mils": "30.75", "y2_mils": "40.125",
        "spacing_mils": "2.5", "via_size_mils": "1.75",
        "via_hole_mils": "0.625", "clearance_mils": "0.375",
    }
    assert params["dry_run"] == "true"


@pytest.mark.asyncio
async def test_circular_board_shape_preserves_fractional_mils(monkeypatch):
    bridge = RecBridge()
    tools = _pcb(monkeypatch, bridge)
    await tools["pcb_set_board_shape"](
        shape="circle", center_x=10.25, center_y=-20.5, radius=492.126,
    )
    assert bridge.calls[-1] == (
        "pcb.set_board_shape",
        {"shape": "circle", "cx": "10.25", "cy": "-20.5", "radius": "492.126"},
    )
    before = len(bridge.calls)
    assert (await tools["pcb_set_board_shape"](shape="circle", radius=0))["success"] is False
    assert len(bridge.calls) == before


@pytest.mark.asyncio
async def test_place_arc_sends_fractional_geometry(monkeypatch):
    bridge = RecBridge()
    tools = _pcb(monkeypatch, bridge)
    await tools["pcb_place_arc"](
        x_center=-1000.5, y_center=500.25, radius=48.2842,
        width=0.3937,
    )
    command, params = bridge.calls[-1]
    assert command == "pcb.place_arc"
    assert {key: params[key] for key in (
        "x_center", "y_center", "radius", "width",
    )} == {
        "x_center": "-1000.5", "y_center": "500.25",
        "radius": "48.2842", "width": "0.3937",
    }


@pytest.mark.asyncio
async def test_import_placement_packs_records(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_import_placement"]([
        {"designator": "U1", "x": 5000, "y": 4000, "rotation": 90, "side": "bottom"},
        {"designator": "R1", "x": 100, "y": 200},
        {"designator": "", "x": 1},          # dropped: no designator
    ])
    cmd, params = b.calls[-1]
    assert cmd == "pcb.import_placement"
    recs = params["placements"].split("|")
    assert recs[0] == "U1,5000,4000,90,BottomLayer"
    assert recs[1] == "R1,100,200,,"
    assert len(recs) == 2


@pytest.mark.asyncio
async def test_import_placement_layer_overrides_side(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_import_placement"]([
        {"designator": "U1", "layer": "TopLayer", "side": "bottom"},
    ])
    assert b.calls[-1][1]["placements"] == "U1,,,,TopLayer"


@pytest.mark.asyncio
async def test_import_placement_nothing_valid_sends_nothing(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    out = await tools["pcb_import_placement"]([{"x": 1}])
    assert out["applied"] == 0
    assert b.calls == []


@pytest.mark.asyncio
async def test_teardrops_both_hit_one_handler(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_add_teardrops"]()
    await tools["pcb_remove_teardrops"]()
    assert [c[0] for c in b.calls] == ["pcb.teardrops", "pcb.teardrops"]


@pytest.mark.asyncio
async def test_autoplace_silkscreen(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_autoplace_silkscreen"]()
    assert b.calls[-1][0] == "pcb.autoplace_silkscreen"


@pytest.mark.asyncio
async def test_tune_length_params(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_tune_length"](
        net="USB_DP", add_length_mils=300, x_mils=1000, y_mils=2000, amplitude_mils=50
    )
    cmd, params = b.calls[-1]
    assert cmd == "pcb.tune_length"
    assert params["net"] == "USB_DP"
    assert params["add_length_mils"] == 300
    assert params["amplitude_mils"] == 50
    assert params["layer"] == "TopLayer"
    assert params["width_mils"] == 6


@pytest.mark.asyncio
async def test_panelize_params(monkeypatch):
    b = RecBridge()
    tools = _pcb(monkeypatch, b)
    await tools["pcb_panelize"](
        child_path="C:/x/board.PcbDoc", board_width_mils=2000,
        board_height_mils=1500, rows=3, cols=4, fiducials=False,
    )
    cmd, params = b.calls[-1]
    assert cmd == "pcb.panelize"
    assert params["rows"] == 3 and params["cols"] == 4
    assert params["board_width_mils"] == 2000
    assert params["fiducials"] is False
    assert params["tooling_holes"] is True


@pytest.mark.asyncio
async def test_generate_fab_package_collects_files(monkeypatch, tmp_path):
    (tmp_path / "top.gbr").write_text("x")

    def responder(cmd, params):
        if cmd == "project.get_outjob_containers":
            return {"containers": [{"name": "Fab", "type": "GeneratedFiles"}]}
        if cmd == "project.run_outjob":
            return {"success": True, "container_type": "GeneratedFiles",
                    "output_dir": str(tmp_path)}
        return {"ok": True}

    b = RecBridge(responder)
    tools = _project(monkeypatch, b)
    out = await tools["proj_generate_fab_package"]()
    assert out["ok"] is True
    assert out["containers_run"] == ["Fab"]
    assert any("top.gbr" in f for f in out["all_files"])


@pytest.mark.asyncio
async def test_generate_fab_package_no_outjob(monkeypatch):
    def responder(cmd, params):
        if cmd == "project.get_outjob_containers":
            return {"containers": []}
        return {"ok": True}

    b = RecBridge(responder)
    tools = _project(monkeypatch, b)
    out = await tools["proj_generate_fab_package"]()
    assert out["ok"] is False
    assert "OutJob" in out["reason"]


@pytest.mark.asyncio
async def test_generate_fab_package_extras(monkeypatch, tmp_path):
    def responder(cmd, params):
        if cmd == "project.get_outjob_containers":
            return {"containers": [{"name": "Fab"}]}
        if cmd == "project.run_outjob":
            return {"success": True, "output_dir": str(tmp_path)}
        if cmd == "project.export_step":
            return {"success": True, "file": "x.step"}
        return {"ok": True}

    b = RecBridge(responder)
    tools = _project(monkeypatch, b)
    out = await tools["proj_generate_fab_package"](include_step=True)
    assert "step" in out["extras"]
    assert any(c[0] == "project.export_step" for c in b.calls)
