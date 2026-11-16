# SPDX-License-Identifier: Apache-2.0
"""The 3D body move is scoped to one footprint and checked against its read."""

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

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        if command == "library.get_footprint_primitives":
            return {"library_path": self.path, "name": "FP", "bodies": 1,
                    "body_models": [{"x1": -1.0, "x2": 1.0,
                                     "y1": -0.5, "y2": 0.5}]}
        return {"success": True, "library_path": self.path,
                "footprint_name": "FP", "body_index": 1, "body_count": 1,
                "changed": 1, "after_x_mm": 2.0, "after_y_mm": 3.0}


@pytest.mark.asyncio
async def test_position_3d_body_plans_then_checks_write(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    path.write_bytes(b"test")
    bridge = _Bridge(path)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    tool = mcp.tools["lib_position_3d_body"]

    planned = await tool(str(path), "FP", target_x_mm=2.0, target_y_mm=3.0)
    assert planned["before_x_mm"] == planned["before_y_mm"] == 0.0
    assert planned["dry_run"] is True
    assert [name for name, _ in bridge.calls] == ["library.get_footprint_primitives"]

    moved = await tool(str(path), "FP", target_x_mm=2.0, target_y_mm=3.0,
                       dry_run=False)
    assert moved["ok"] is True
    assert moved["save_required"] is True
    assert bridge.calls[-1] == (
        "library.position_3d_body",
        {"library_path": str(path), "footprint_name": "FP", "body_index": 1,
         "expected_count": 1, "expected_x_mm": "0.000000000",
         "expected_y_mm": "0.000000000",
         "target_x_mm": "2.000000000", "target_y_mm": "3.000000000"})


@pytest.mark.asyncio
async def test_position_3d_body_rejects_invalid_index_without_write(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    path.write_bytes(b"test")
    bridge = _Bridge(path)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    result = await mcp.tools["lib_position_3d_body"](str(path), "FP", body_index=2,
                                                       dry_run=False)
    assert result["ok"] is False
    assert [name for name, _ in bridge.calls] == ["library.get_footprint_primitives"]


@pytest.mark.asyncio
async def test_position_3d_body_sends_decimal_coordinates(tmp_path, monkeypatch):
    from eda_agent.tools import library

    path = tmp_path / "sample.PcbLib"
    path.write_bytes(b"test")
    bridge = _Bridge(path)
    original = bridge.send_command_async

    async def near_zero(command, params, timeout=None):
        result = await original(command, params, timeout)
        if command == "library.get_footprint_primitives":
            result["body_models"][0]["x1"] = -1.00000127
            result["body_models"][0]["x2"] = 0.99999873
        return result

    bridge.send_command_async = near_zero
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    await mcp.tools["lib_position_3d_body"](
        str(path), "FP", target_x_mm=2.0, target_y_mm=3.0, dry_run=False)
    assert bridge.calls[-1][1]["expected_x_mm"] == "-0.000001270"
