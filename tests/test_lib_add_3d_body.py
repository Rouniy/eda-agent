# SPDX-License-Identifier: Apache-2.0
"""An added STEP body requires exact readback and never removes old bodies."""

import pytest


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func
        return register


class _Bridge:
    def __init__(self, path):
        self.path = str(path)
        self.calls = []
        self.added = False
        self.model_path = None
        self.height = 0.0

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        if command == "library.get_footprint_primitives":
            bodies = [{"model_file": "old.step"}]
            if self.added:
                bodies.append({"model_file": self.model_path,
                               "overall_height_mm": self.height})
            return {"library_path": self.path, "name": "FP", "bodies": len(bodies),
                    "body_models": bodies}
        if command == "library.add_3d_body":
            self.added = True
            self.model_path = params["model_path"]
            self.height = params["overall_height_mm"]
            return {"success": True, "library_path": self.path,
                    "footprint_name": "FP", "model_file": "new.step",
                    "body_count_before": 1, "body_count_after": 2,
                    "after_x_mm": 2.0, "after_y_mm": -1.0,
                    "overall_height_mm": self.height}
        raise AssertionError(command)


@pytest.mark.asyncio
async def test_add_3d_body_plans_then_verifies_write(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    model = tmp_path / "new.step"
    path.write_bytes(b"library")
    model.write_bytes(b"STEP")
    bridge = _Bridge(path)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    tool = mcp.tools["lib_add_3d_body"]

    plan = await tool(str(path), "FP", str(model), offset_x_mm=2,
                      offset_y_mm=-1, rot_z_deg=90, mech_layer=13)
    assert plan["dry_run"] is True
    assert plan["body_count_after"] == 2
    assert [name for name, _ in bridge.calls] == ["library.get_footprint_primitives"]

    added = await tool(str(path), "FP", str(model), offset_x_mm=2,
                       offset_y_mm=-1, rot_z_deg=90, mech_layer=13,
                       overall_height_mm=8.5, dry_run=False)
    assert added["ok"] is True
    assert added["save_required"] is True
    assert bridge.calls[-2][0] == "library.add_3d_body"
    assert bridge.calls[-2][1]["expected_count"] == 1
    assert bridge.calls[-2][1]["rot_z_deg"] == 90
    assert bridge.calls[-2][1]["overall_height_mm"] == 8.5
    assert bridge.calls[-1][0] == "library.get_footprint_primitives"


@pytest.mark.asyncio
async def test_add_3d_body_refuses_missing_model_before_native_call(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    path.write_bytes(b"library")
    bridge = _Bridge(path)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    result = await mcp.tools["lib_add_3d_body"](
        str(path), "FP", str(tmp_path / "missing.step"), dry_run=False)
    assert result["ok"] is False
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_add_3d_body_rejects_negative_height_without_touching_library(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    model = tmp_path / "new.step"
    path.write_bytes(b"library")
    model.write_bytes(b"STEP")
    bridge = _Bridge(path)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    result = await mcp.tools["lib_add_3d_body"](
        str(path), "FP", str(model), overall_height_mm=-1, dry_run=False)
    assert result["ok"] is False
    assert bridge.calls == []
